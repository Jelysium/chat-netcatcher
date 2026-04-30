"""Hex editor widget displaying data in hex + ASCII format with selection and copy."""

from __future__ import annotations

from PyQt6.QtWidgets import QAbstractScrollArea, QApplication
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QShortcut, QKeySequence

from netcatcher.config.constants import hex_colors


class HexEditor(QAbstractScrollArea):
    """Custom widget that renders data as a hex dump with ASCII column."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: bytes = b""
        self._font = QFont("Consolas", 10)
        self._char_width = 0
        self._char_height = 0
        self._bytes_per_line = 16

        # Selection state (byte offsets)
        self._sel_start: int | None = None
        self._sel_end: int | None = None

        self.setFont(self._font)
        self._update_metrics()

        # Ctrl+C to copy selected hex text
        s = QShortcut(QKeySequence.StandardKey.Copy, self, self._copy_selection)
        s.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.viewport().setMouseTracking(True)

    def _update_metrics(self):
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        self._char_width = max(fm.horizontalAdvance("0"), 1)
        self._char_height = fm.height() + 4

    def set_data(self, data: bytes):
        """Set the data to display."""
        self._data = data
        self._sel_start = None
        self._sel_end = None
        self._update_scrollbar()
        self.viewport().update()

    def clear(self):
        """Clear the displayed data."""
        self._data = b""
        self._sel_start = None
        self._sel_end = None
        self.verticalScrollBar().setValue(0)
        self.viewport().update()

    def _total_lines(self) -> int:
        if not self._data:
            return 0
        return (len(self._data) + self._bytes_per_line - 1) // self._bytes_per_line

    def _update_scrollbar(self):
        total_lines = self._total_lines()
        if total_lines == 0:
            self.verticalScrollBar().setRange(0, 0)
            return

        visible_lines = max(self.viewport().height() // self._char_height, 1)
        self.verticalScrollBar().setRange(0, max(0, total_lines - visible_lines))
        self.verticalScrollBar().setPageStep(visible_lines)
        self.verticalScrollBar().setSingleStep(1)

    # --- Layout helpers ---

    def _layout(self) -> tuple[int, int, int]:
        """Return (offset_x, hex_x, ascii_x) pixel positions."""
        x_offset = 10
        offset_x = x_offset
        hex_x = x_offset + 10 * self._char_width
        ascii_x = hex_x + (self._bytes_per_line * 3 + 1) * self._char_width
        return offset_x, hex_x, ascii_x

    def _byte_from_pos(self, x: int, y: int) -> int | None:
        """Map a pixel position to a byte offset, or None."""
        if not self._data:
            return None
        _, hex_x, ascii_x = self._layout()

        first_line = self.verticalScrollBar().value()
        line = first_line + (y // self._char_height)
        if line < 0 or line >= self._total_lines():
            return None

        col = -1
        # Check hex area
        if hex_x <= x < hex_x + self._bytes_per_line * 3 * self._char_width:
            local_x = x - hex_x
            # Each byte = 3 chars (2 hex + 1 space), but extra space at col 8
            char_pos = local_x // self._char_width
            if char_pos < 8 * 3:
                col = char_pos // 3
            elif char_pos == 8 * 3:  # extra space
                col = -1
            else:
                col = (char_pos - 1) // 3
        # Check ASCII area
        elif ascii_x <= x < ascii_x + self._bytes_per_line * self._char_width:
            col = (x - ascii_x) // self._char_width

        if 0 <= col < self._bytes_per_line:
            offset = line * self._bytes_per_line + col
            if offset < len(self._data):
                return offset
        return None

    # --- Selection range ---

    def _sel_range(self) -> tuple[int, int] | None:
        if self._sel_start is None or self._sel_end is None:
            return None
        lo = min(self._sel_start, self._sel_end)
        hi = max(self._sel_start, self._sel_end)
        if lo >= len(self._data):
            return None
        hi = min(hi, len(self._data) - 1)
        if lo > hi:
            return None
        return lo, hi

    # --- Mouse events for selection ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            byte = self._byte_from_pos(event.position().x(), event.position().y())
            if byte is not None:
                self._sel_start = byte
                self._sel_end = byte
            else:
                self._sel_start = None
                self._sel_end = None
            self.viewport().update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._sel_start is not None:
            byte = self._byte_from_pos(event.position().x(), event.position().y())
            if byte is not None:
                self._sel_end = byte
                self.viewport().update()

    def mouseReleaseEvent(self, event):
        pass  # selection already tracked

    # --- Copy ---

    def _copy_selection(self):
        rng = self._sel_range()
        if rng is None:
            return
        lo, hi = rng
        chunk = self._data[lo:hi + 1]
        # Format as hex dump lines
        lines = []
        for offset in range(0, len(chunk), self._bytes_per_line):
            piece = chunk[offset:offset + self._bytes_per_line]
            hex_str = " ".join(f"{b:02X}" for b in piece)
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in piece)
            lines.append(f"{lo + offset:08X}  {hex_str:<47s}  {ascii_str}")
        QApplication.clipboard().setText("\n".join(lines))

    # --- Painting ---

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self.viewport())
        painter.setFont(self._font)

        # Theme-aware colors
        colors = hex_colors()
        offset_color = QColor(colors["offset"])
        hex_color = QColor(colors["hex"])
        ascii_color = QColor(colors["ascii"])
        separator_color = QColor(colors["separator"])
        sel_bg = QColor(colors["sel_bg"])
        sel_bg.setAlpha(180)

        offset_x, hex_x, ascii_x = self._layout()
        first_line = self.verticalScrollBar().value()
        visible_lines = self.viewport().height() // self._char_height + 1
        total = self._total_lines()
        rng = self._sel_range()

        y = self._char_height

        for line in range(first_line, min(first_line + visible_lines, total)):
            start = line * self._bytes_per_line
            end = min(start + self._bytes_per_line, len(self._data))
            chunk = self._data[start:end]

            # Draw selection highlight for this line
            if rng:
                sel_lo, sel_hi = rng
                line_lo = start
                line_hi = end - 1
                # Overlap?
                if not (sel_hi < line_lo or sel_lo > line_hi):
                    # First and last byte in this line that are selected
                    first_sel = max(sel_lo, line_lo)
                    last_sel = min(sel_hi, line_hi)
                    # Highlight hex area
                    col_first = first_sel - line_lo
                    col_last = last_sel - line_lo
                    x1 = hex_x + col_first * 3 * self._char_width
                    x2 = hex_x + (col_last + 1) * 3 * self._char_width
                    painter.fillRect(QRect(x1, y - self._char_height + 4, x2 - x1, self._char_height), sel_bg)
                    # Highlight ASCII area
                    ax1 = ascii_x + col_first * self._char_width
                    ax2 = ascii_x + (col_last + 1) * self._char_width
                    painter.fillRect(QRect(ax1, y - self._char_height + 4, ax2 - ax1, self._char_height), sel_bg)

            # Offset
            painter.setPen(offset_color)
            painter.drawText(offset_x, y, f"{start:08X}")

            # Hex
            painter.setPen(hex_color)
            hex_parts = []
            for i, byte_val in enumerate(chunk):
                if i == 8:
                    hex_parts.append(" ")
                hex_parts.append(f"{byte_val:02X}")
            painter.drawText(hex_x, y, " ".join(hex_parts))

            # ASCII
            ascii_str = "".join(
                chr(b) if 32 <= b < 127 else "."
                for b in chunk
            )
            painter.setPen(ascii_color)
            painter.drawText(ascii_x, y, ascii_str)

            y += self._char_height

        # Vertical separators
        painter.setPen(separator_color)
        sep1_x = hex_x - self._char_width
        sep2_x = ascii_x - self._char_width * 2
        painter.drawLine(sep1_x, 0, sep1_x, self.viewport().height())
        painter.drawLine(sep2_x, 0, sep2_x, self.viewport().height())

        painter.end()

    def resizeEvent(self, event):
        self._update_scrollbar()
        super().resizeEvent(event)

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()
