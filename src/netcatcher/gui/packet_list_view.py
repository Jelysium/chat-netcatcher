"""Packet list view with table, multi-field filter bar, and selection handling."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableView, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QHeaderView, QComboBox, QLabel, QApplication,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSortFilterProxyModel
from PyQt6.QtGui import QKeySequence

from netcatcher.config.constants import PACKET_COLUMN_WIDTHS
from netcatcher.models.packet_table_model import PacketTableModel


class _CopyableTable(QTableView):
    """QTableView subclass that supports Ctrl+C to copy the focused cell."""

    def keyPressEvent(self, event):
        if (event.key() == Qt.Key.Key_C
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            idx = self.currentIndex()
            if idx.isValid():
                val = self.model().data(idx, Qt.ItemDataRole.DisplayRole)
                if val is not None:
                    QApplication.clipboard().setText(str(val))
            event.accept()
            return
        super().keyPressEvent(event)


class _PacketFilterProxy(QSortFilterProxyModel):
    """Column-aware filter proxy: each filter field only matches its own column."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._general = ""
        self._protocol = ""
        self._src = ""
        self._dst = ""
        self._port = ""

    def set_filters(self, general="", protocol="", src="", dst="", port=""):
        self._general = general.lower()
        self._protocol = protocol.lower()
        self._src = src.lower()
        self._dst = dst.lower()
        self._port = port.lower()
        self.invalidateRowsFilter()

    def _col_contains(self, row: int, col: int, text: str, parent) -> bool:
        idx = self.sourceModel().index(row, col, parent)
        val = self.sourceModel().data(idx, Qt.ItemDataRole.DisplayRole)
        return val is not None and text in str(val).lower()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        # Protocol -> column 4
        if self._protocol and not self._col_contains(source_row, 4, self._protocol, source_parent):
            return False

        # Src IP -> column 2
        if self._src and not self._col_contains(source_row, 2, self._src, source_parent):
            return False

        # Dst IP -> column 3
        if self._dst and not self._col_contains(source_row, 3, self._dst, source_parent):
            return False

        # Port -> column 2 or 3
        if self._port:
            if not (self._col_contains(source_row, 2, self._port, source_parent)
                    or self._col_contains(source_row, 3, self._port, source_parent)):
                return False

        # General -> any column
        if self._general:
            found = False
            for col in range(self.sourceModel().columnCount(source_parent)):
                if self._col_contains(source_row, col, self._general, source_parent):
                    found = True
                    break
            if not found:
                return False

        return True


class PacketListView(QWidget):
    """Widget containing the packet table and a multi-field filter bar."""

    selection_changed = pyqtSignal(int)  # row index

    def __init__(self, model: PacketTableModel, parent=None):
        super().__init__(parent)
        self._source_model = model

        self._proxy_model = _PacketFilterProxy(self)
        self._proxy_model.setSourceModel(model)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # --- Filter bar ---
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(4, 2, 4, 2)

        # General search
        self._general_filter = QLineEdit()
        self._general_filter.setPlaceholderText("Search all columns...")
        self._general_filter.setFixedWidth(220)
        self._general_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._general_filter)

        # Protocol filter
        filter_layout.addWidget(QLabel("Protocol:"))
        self._protocol_filter = QComboBox()
        self._protocol_filter.setMinimumWidth(90)
        self._protocol_filter.addItem("All")
        for p in ("TCP", "UDP", "ICMP", "DNS", "HTTP", "HTTPS", "TLS", "ARP"):
            self._protocol_filter.addItem(p)
        self._protocol_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._protocol_filter)

        # Source filter
        filter_layout.addWidget(QLabel("Src:"))
        self._src_filter = QLineEdit()
        self._src_filter.setPlaceholderText("IP")
        self._src_filter.setFixedWidth(130)
        self._src_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._src_filter)

        # Dest filter
        filter_layout.addWidget(QLabel("Dst:"))
        self._dst_filter = QLineEdit()
        self._dst_filter.setPlaceholderText("IP")
        self._dst_filter.setFixedWidth(130)
        self._dst_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._dst_filter)

        # Port filter
        filter_layout.addWidget(QLabel("Port:"))
        self._port_filter = QLineEdit()
        self._port_filter.setPlaceholderText("Port")
        self._port_filter.setFixedWidth(70)
        self._port_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._port_filter)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # --- Table ---
        self._table = _CopyableTable()
        self._table.setModel(self._proxy_model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setDefaultSectionSize(24)

        header = self._table.horizontalHeader()
        for i, width in enumerate(PACKET_COLUMN_WIDTHS):
            if i < len(PACKET_COLUMN_WIDTHS) - 1:
                header.resizeSection(i, width)
            else:
                header.setStretchLastSection(True)

        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self._table)

    def _apply_filters(self):
        """Push all filter values into the proxy model."""
        proto = self._protocol_filter.currentText()
        self._proxy_model.set_filters(
            general=self._general_filter.text().strip(),
            protocol=proto if proto != "All" else "",
            src=self._src_filter.text().strip(),
            dst=self._dst_filter.text().strip(),
            port=self._port_filter.text().strip(),
        )

    def _on_selection(self):
        """Emit selection signal with the source model row."""
        indexes = self._table.selectionModel().selectedRows()
        if indexes:
            source_row = self._proxy_model.mapToSource(indexes[0]).row()
            self.selection_changed.emit(source_row)

    def has_active_filter(self) -> bool:
        """Check if any filter field has a non-default value."""
        if self._general_filter.text().strip():
            return True
        if self._protocol_filter.currentText() != "All":
            return True
        if self._src_filter.text().strip():
            return True
        if self._dst_filter.text().strip():
            return True
        if self._port_filter.text().strip():
            return True
        return False

    def get_visible_packets(self) -> list:
        """Get all PacketRecord items currently passing the filter."""
        packets = []
        for i in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(self._proxy_model.index(i, 0))
            packet = self._source_model.get_packet(source_index.row())
            if packet:
                packets.append(packet)
        return packets

    def scroll_to_bottom(self):
        """Scroll the table to the last row."""
        count = self._proxy_model.rowCount()
        if count > 0:
            self._table.scrollTo(self._proxy_model.index(count - 1, 0))
