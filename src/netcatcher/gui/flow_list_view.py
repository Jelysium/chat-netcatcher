"""HTTP flow list view with table, multi-field filter bar, and selection handling."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableView, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QHeaderView, QComboBox, QLabel, QApplication,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSortFilterProxyModel
from PyQt6.QtGui import QKeySequence

from netcatcher.config.constants import FLOW_COLUMN_WIDTHS
from netcatcher.models.flow_table_model import FlowTableModel


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


class _FlowFilterProxy(QSortFilterProxyModel):
    """Column-aware filter proxy for HTTP flow table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._general = ""
        self._method = ""
        self._host = ""
        self._status_prefix = ""
        self._content_type = ""

    def set_filters(self, general="", method="", host="", status_prefix="", content_type=""):
        self._general = general.lower()
        self._method = method.lower()
        self._host = host.lower()
        self._status_prefix = status_prefix
        self._content_type = content_type.lower()
        self.invalidateRowsFilter()

    def _col_contains(self, row: int, col: int, text: str, parent) -> bool:
        idx = self.sourceModel().index(row, col, parent)
        val = self.sourceModel().data(idx, Qt.ItemDataRole.DisplayRole)
        return val is not None and text in str(val).lower()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        # Method -> column 1
        if self._method and not self._col_contains(source_row, 1, self._method, source_parent):
            return False

        # Host -> column 2
        if self._host and not self._col_contains(source_row, 2, self._host, source_parent):
            return False

        # Status prefix (e.g. "2") -> column 4 (status text like "200 OK")
        if self._status_prefix and not self._col_contains(source_row, 4, self._status_prefix, source_parent):
            return False

        # Content type -> not a visible column, check source model data
        if self._content_type:
            flow = self.sourceModel().get_flow(source_row)
            if not flow or self._content_type not in (flow.content_type or "").lower():
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


class FlowListView(QWidget):
    """Widget containing the HTTP flow table and a multi-field filter bar."""

    selection_changed = pyqtSignal(int)  # row index

    def __init__(self, model: FlowTableModel, parent=None):
        super().__init__(parent)
        self._source_model = model

        self._proxy_model = _FlowFilterProxy(self)
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

        # Method filter
        filter_layout.addWidget(QLabel("Method:"))
        self._method_filter = QComboBox()
        self._method_filter.setMinimumWidth(90)
        self._method_filter.addItem("All")
        for m in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            self._method_filter.addItem(m)
        self._method_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._method_filter)

        # Host filter
        filter_layout.addWidget(QLabel("Host:"))
        self._host_filter = QLineEdit()
        self._host_filter.setPlaceholderText("Domain")
        self._host_filter.setFixedWidth(150)
        self._host_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._host_filter)

        # Status code filter
        filter_layout.addWidget(QLabel("Status:"))
        self._status_filter = QComboBox()
        self._status_filter.setMinimumWidth(100)
        self._status_filter.addItem("All")
        for s in ("2xx", "3xx", "4xx", "5xx"):
            self._status_filter.addItem(s)
        self._status_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._status_filter)

        # Content type filter
        filter_layout.addWidget(QLabel("Type:"))
        self._type_filter = QComboBox()
        self._type_filter.setMinimumWidth(120)
        self._type_filter.addItem("All")
        for t in ("text/html", "application/json", "text/css", "application/javascript", "image"):
            self._type_filter.addItem(t)
        self._type_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._type_filter)

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
        for i, width in enumerate(FLOW_COLUMN_WIDTHS):
            if i < len(FLOW_COLUMN_WIDTHS) - 1:
                header.resizeSection(i, width)
            else:
                header.setStretchLastSection(True)

        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self._table)

    def _apply_filters(self):
        """Push all filter values into the proxy model."""
        method = self._method_filter.currentText()
        status = self._status_filter.currentText()
        ctype = self._type_filter.currentText()

        self._proxy_model.set_filters(
            general=self._general_filter.text().strip(),
            method=method if method != "All" else "",
            host=self._host_filter.text().strip(),
            status_prefix=status[0] if status != "All" else "",
            content_type=ctype if ctype != "All" else "",
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
        if self._method_filter.currentText() != "All":
            return True
        if self._host_filter.text().strip():
            return True
        if self._status_filter.currentText() != "All":
            return True
        if self._type_filter.currentText() != "All":
            return True
        return False

    def get_visible_flows(self) -> list:
        """Get all HTTPFlowRecord items currently passing the filter."""
        flows = []
        for i in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(self._proxy_model.index(i, 0))
            flow = self._source_model.get_flow(source_index.row())
            if flow:
                flows.append(flow)
        return flows

    def scroll_to_bottom(self):
        """Scroll the table to the last row."""
        count = self._proxy_model.rowCount()
        if count > 0:
            self._table.scrollTo(self._proxy_model.index(count - 1, 0))
