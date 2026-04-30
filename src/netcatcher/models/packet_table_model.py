"""High-performance table model for packet display."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont

from netcatcher.config.constants import PACKET_COLUMNS, protocol_bg, protocol_fg
from netcatcher.storage.ring_buffer import RingBuffer
from netcatcher.models.packet import PacketRecord


class PacketTableModel(QAbstractTableModel):
    """Qt table model backed by a ring buffer, optimized for high-frequency updates."""

    def __init__(self, ring_buffer: RingBuffer, parent=None):
        super().__init__(parent)
        self._buffer = ring_buffer
        self._known_rows = 0
        self._pending_count = 0
        self._columns = PACKET_COLUMNS

        # Batch UI updates at ~10 Hz
        self._batch_timer = QTimer(self)
        self._batch_timer.setInterval(100)
        self._batch_timer.timeout.connect(self._flush_pending)
        self._batch_timer.start()

    def notify_new_packets(self, count: int):
        """Called from capture thread to signal new packets arrived."""
        self._pending_count += count

    def reset_model(self):
        """Reset the model after buffer is cleared."""
        self.beginResetModel()
        self._known_rows = 0
        self._pending_count = 0
        self.endResetModel()

    def _flush_pending(self):
        """Batch-insert pending rows into the model."""
        if self._pending_count > 0:
            actual = len(self._buffer)
            if actual <= self._known_rows:
                self._pending_count = 0
                self.beginResetModel()
                self._known_rows = actual
                self.endResetModel()
                return

            new_rows = actual - self._known_rows
            if new_rows <= 0:
                self._pending_count = 0
                return

            self._pending_count = 0
            first = self._known_rows
            self._known_rows = actual
            self.beginInsertRows(QModelIndex(), first, first + new_rows - 1)
            self.endInsertRows()

    # --- QAbstractTableModel interface ---

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self._known_rows

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

        row = index.row()
        packet = self._buffer.get(row)
        if packet is None:
            return None

        # Background color per protocol
        if role == Qt.ItemDataRole.BackgroundRole:
            color = protocol_bg().get(packet.protocol)
            return QBrush(QColor(color)) if color else None

        # Foreground accent for protocol column
        if role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == 4:  # Protocol column
                fg = protocol_fg().get(packet.protocol)
                return QBrush(QColor(fg)) if fg else None
            return None

        # Bold font for protocol column
        if role == Qt.ItemDataRole.FontRole:
            if index.column() == 4:
                font = QFont()
                font.setBold(True)
                return font
            return None

        col = index.column()
        if col == 0:
            return str(packet.id)
        elif col == 1:
            return packet.time_str
        elif col == 2:
            if packet.src_port and packet.src_port > 0:
                return f"{packet.src_ip}:{packet.src_port}"
            return packet.src_ip
        elif col == 3:
            if packet.dst_port and packet.dst_port > 0:
                return f"{packet.dst_ip}:{packet.dst_port}"
            return packet.dst_ip
        elif col == 4:
            return packet.protocol
        elif col == 5:
            return str(packet.length)
        elif col == 6:
            return packet.info
        return None

    def get_packet(self, row: int) -> PacketRecord | None:
        """Get the PacketRecord at the given row index."""
        return self._buffer.get(row)
