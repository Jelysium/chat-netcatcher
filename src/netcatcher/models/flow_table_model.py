"""Table model for HTTP flow display."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont

from netcatcher.config.constants import FLOW_COLUMNS, status_bg_colors, status_fg_colors, method_fg_colors
from netcatcher.models.http_flow import HTTPFlowRecord


class FlowTableModel(QAbstractTableModel):
    """Table model for HTTP/HTTPS flow records."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._flows: list[HTTPFlowRecord] = []
        self._pending: list[HTTPFlowRecord] = []
        self._next_id = 1
        self._columns = FLOW_COLUMNS

        # Batch updates
        self._batch_timer = QTimer(self)
        self._batch_timer.setInterval(100)
        self._batch_timer.timeout.connect(self._flush_pending)
        self._batch_timer.start()

    def add_flows(self, flows: list[HTTPFlowRecord]):
        """Add new flow records (called from any thread)."""
        self._pending.extend(flows)

    def clear_flows(self):
        """Clear all flows."""
        self.beginResetModel()
        self._flows.clear()
        self._pending.clear()
        self._next_id = 1
        self.endResetModel()

    def _flush_pending(self):
        if not self._pending:
            return
        flows = self._pending
        self._pending = []
        # Assign auto-increment IDs
        for f in flows:
            f.id = self._next_id
            self._next_id += 1
        first = len(self._flows)
        self.beginInsertRows(QModelIndex(), first, first + len(flows) - 1)
        self._flows.extend(flows)
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._flows)

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._columns[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole,
                        Qt.ItemDataRole.ForegroundRole, Qt.ItemDataRole.FontRole):
            return None

        flow = self._flows[index.row()]

        # Background color by status code category
        if role == Qt.ItemDataRole.BackgroundRole:
            if flow.status_code:
                cat = flow.status_code // 100
                color = status_bg_colors().get(cat)
                return QBrush(QColor(color)) if color else None
            return None

        # Foreground color for Method and Status columns
        if role == Qt.ItemDataRole.ForegroundRole:
            col = index.column()
            if col == 1:  # Method
                fg = method_fg_colors().get(flow.method)
                return QBrush(QColor(fg)) if fg else None
            if col == 4 and flow.status_code:  # Status
                cat = flow.status_code // 100
                fg = status_fg_colors().get(cat)
                return QBrush(QColor(fg)) if fg else None
            return None

        # Bold font for Method and Status columns
        if role == Qt.ItemDataRole.FontRole:
            if index.column() in (1, 4):
                font = QFont()
                font.setBold(True)
                return font
            return None

        # Display data
        col = index.column()
        if col == 0:
            return str(flow.id)
        elif col == 1:
            return flow.method
        elif col == 2:
            return flow.host
        elif col == 3:
            return flow.path
        elif col == 4:
            return flow.status_text
        elif col == 5:
            size = flow.response_size
            if size > 1024 * 1024:
                return f"{size / 1024 / 1024:.1f} MB"
            if size > 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size} B"
        elif col == 6:
            return f"{flow.duration_ms:.0f}"
        return None

    def get_flow(self, row: int) -> HTTPFlowRecord | None:
        if 0 <= row < len(self._flows):
            return self._flows[row]
        return None
