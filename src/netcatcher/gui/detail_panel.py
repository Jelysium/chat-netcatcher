"""Detail panel showing packet/flow details with tabs for headers, body, and hex view."""

from __future__ import annotations

import json

from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QLabel, QStackedWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence, QClipboard
from PyQt6.QtWidgets import QApplication

from netcatcher.gui.hex_editor import HexEditor
from netcatcher.models.packet import PacketRecord
from netcatcher.models.http_flow import HTTPFlowRecord


class DetailPanel(QWidget):
    """Tabbed detail panel for inspecting packets and HTTP flows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_packet: PacketRecord | None = None
        self._current_flow: HTTPFlowRecord | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Overview tab (tree view of packet layers / flow summary)
        self._overview_tree = QTreeWidget()
        self._overview_tree.setHeaderLabels(["Field", "Value"])
        self._overview_tree.setAlternatingRowColors(True)
        self._overview_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        s = QShortcut(QKeySequence.StandardKey.Copy, self._overview_tree, self._copy_tree_selection)
        s.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._tabs.addTab(self._overview_tree, "Overview")

        # Headers tab (for HTTP flows)
        self._headers_text = QTextEdit()
        self._headers_text.setReadOnly(True)
        self._headers_text.setFontFamily("Consolas")
        self._tabs.addTab(self._headers_text, "Headers")

        # Body tab (for HTTP request/response body)
        self._body_stack = QStackedWidget()

        # Page 0: text display
        self._body_text = QTextEdit()
        self._body_text.setReadOnly(True)
        self._body_text.setFontFamily("Consolas")
        self._body_stack.addWidget(self._body_text)

        # Page 1: image display
        self._body_image_scroll = QScrollArea()
        self._body_image_scroll.setWidgetResizable(True)
        self._body_image_label = QLabel()
        self._body_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body_image_label.setStyleSheet("")  # bg set dynamically when showing
        self._body_image_scroll.setWidget(self._body_image_label)
        self._body_stack.addWidget(self._body_image_scroll)

        self._tabs.addTab(self._body_stack, "Body")

        # Hex tab (raw bytes)
        self._hex_editor = HexEditor()
        self._tabs.addTab(self._hex_editor, "Hex")

        layout.addWidget(self._tabs)

    def show_packet(self, packet: PacketRecord):
        """Display packet details, keeping the current tab selection."""
        self._current_packet = packet
        self._current_flow = None
        self._populate_packet(packet)
        # Do NOT change tab — keep user's current tab

    def show_flow(self, flow: HTTPFlowRecord):
        """Display HTTP flow details, keeping the current tab selection."""
        self._current_flow = flow
        self._current_packet = None
        self._populate_flow(flow)
        # Do NOT change tab — keep user's current tab

    def _populate_packet(self, packet: PacketRecord):
        """Fill all tabs with packet data."""
        # Overview
        self._overview_tree.clear()
        self._add_tree_item("General", "")
        self._add_tree_item("  ID", str(packet.id))
        self._add_tree_item("  Time", packet.time_str)
        self._add_tree_item("  Source", f"{packet.src_ip}:{packet.src_port}" if packet.src_port else packet.src_ip)
        self._add_tree_item("  Destination", f"{packet.dst_ip}:{packet.dst_port}" if packet.dst_port else packet.dst_ip)
        self._add_tree_item("  Protocol", packet.protocol)
        self._add_tree_item("  Length", f"{packet.length} bytes")

        for layer_name, fields in packet.layer_details.items():
            parent = QTreeWidgetItem(self._overview_tree, [layer_name.upper(), ""])
            for key, value in fields.items():
                QTreeWidgetItem(parent, [f"  {key}", str(value)])
            parent.setExpanded(True)

        self._overview_tree.resizeColumnToContents(0)

        # Headers (show raw layer details as JSON)
        self._headers_text.setPlainText(json.dumps(packet.layer_details, indent=2))

        # Body (empty for raw packets)
        self._body_text.clear()
        self._body_image_label.clear()
        self._body_stack.setCurrentIndex(0)

        # Hex
        if packet.raw_bytes:
            self._hex_editor.set_data(packet.raw_bytes)
        else:
            self._hex_editor.clear()

    def _populate_flow(self, flow: HTTPFlowRecord):
        """Fill all tabs with flow data."""
        # Overview
        self._overview_tree.clear()
        self._add_tree_item("Request", "")
        self._add_tree_item("  Method", flow.method)
        self._add_tree_item("  URL", flow.url)
        self._add_tree_item("  Host", flow.host)
        self._add_tree_item("  Path", flow.path)
        self._add_tree_item("  Scheme", flow.scheme)
        self._add_tree_item("Response", "")
        self._add_tree_item("  Status", str(flow.status_code) if flow.status_code else "Pending")
        self._add_tree_item("  Content-Type", flow.content_type or "N/A")
        self._add_tree_item("  Duration", f"{flow.duration_ms:.1f} ms")

        self._overview_tree.resizeColumnToContents(0)

        # Headers
        headers_text = "--- Request Headers ---\n"
        for k, v in flow.request_headers.items():
            headers_text += f"{k}: {v}\n"
        headers_text += "\n--- Response Headers ---\n"
        for k, v in flow.response_headers.items():
            headers_text += f"{k}: {v}\n"
        self._headers_text.setPlainText(headers_text)

        # Body — check for image content
        content_type = (flow.content_type or "").lower()
        from netcatcher.config.constants import _is_light_theme
        img_bg = "#ffffff" if _is_light_theme() else "#1e1e2e"
        self._body_image_label.setStyleSheet(f"background-color: {img_bg};")

        if content_type.startswith("image/") and flow.response_body:
            pixmap = QPixmap()
            if pixmap.loadFromData(flow.response_body):
                # Scale to fit while keeping aspect ratio
                self._body_image_label.setPixmap(
                    pixmap.scaled(
                        800, 600,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self._body_stack.setCurrentIndex(1)
            else:
                # Image data couldn't be decoded, show as text
                self._body_text.setPlainText(
                    f"[Image data, {len(flow.response_body)} bytes — could not decode]"
                )
                self._body_stack.setCurrentIndex(0)
        else:
            body_text = self._safe_decode(flow.request_body, "Request Body")
            resp_text = self._safe_decode(flow.response_body, "Response Body")
            if body_text and resp_text:
                self._body_text.setPlainText(body_text + "\n\n" + resp_text)
            elif body_text:
                self._body_text.setPlainText(body_text)
            elif resp_text:
                self._body_text.setPlainText(resp_text)
            else:
                self._body_text.clear()
            self._body_stack.setCurrentIndex(0)

        # Hex
        raw = flow.request_body + flow.response_body
        if raw:
            self._hex_editor.set_data(raw)
        else:
            self._hex_editor.clear()

    def _safe_decode(self, data: bytes, label: str) -> str:
        """Safely decode bytes to string for display."""
        if not data:
            return ""
        try:
            text = data.decode("utf-8", errors="replace")
            return f"--- {label} ---\n{text}"
        except Exception:
            return f"--- {label} ---\n[Binary data, {len(data)} bytes]"

    def clear(self):
        """Clear all detail panels."""
        self._overview_tree.clear()
        self._headers_text.clear()
        self._body_text.clear()
        self._hex_editor.clear()
        self._current_packet = None
        self._current_flow = None

    def _add_tree_item(self, field: str, value: str):
        item = QTreeWidgetItem(self._overview_tree, [field, value])
        if not value and not field.startswith("  "):
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)

    def _copy_tree_selection(self):
        """Copy selected tree items to clipboard as text."""
        items = self._overview_tree.selectedItems()
        if not items:
            return
        lines = []
        for item in items:
            field = item.text(0).strip()
            value = item.text(1)
            if field and value:
                lines.append(f"{field}: {value}")
            elif field:
                lines.append(field)
            elif value:
                lines.append(value)
        QApplication.clipboard().setText("\n".join(lines))
