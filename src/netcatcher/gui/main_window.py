"""Main application window with toolbar, packet/flow tables, and detail panel."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QStatusBar, QToolBar, QLabel,
    QComboBox, QFileDialog, QMessageBox, QProgressBar, QApplication,
)
from PyQt6.QtCore import Qt, QTimer

from netcatcher.config.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, toolbar_colors
from netcatcher.config.settings import Settings
from netcatcher.storage.ring_buffer import RingBuffer
from netcatcher.models.packet_table_model import PacketTableModel
from netcatcher.models.flow_table_model import FlowTableModel
from netcatcher.models.packet import PacketRecord
from netcatcher.models.http_flow import HTTPFlowRecord
from netcatcher.capture.capture_manager import CaptureManager
from netcatcher.gui.packet_list_view import PacketListView
from netcatcher.gui.flow_list_view import FlowListView
from netcatcher.gui.detail_panel import DetailPanel
from netcatcher.gui.capture_toolbar import CaptureToolbar
from netcatcher.gui.stats_dashboard import StatsDashboard

_SPINNER_FRAMES = "⣾⣽⣻⢿⡿⣟⣯⣷"


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetCatcher - Network Packet Capture")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        self._settings = Settings()
        self._ring_buffer = RingBuffer(self._settings.buffer_size)
        self._packet_model = PacketTableModel(self._ring_buffer)
        self._flow_model = FlowTableModel()
        self._capture_manager = CaptureManager(self._ring_buffer)
        self._packet_count = 0

        # Spinner state
        self._busy_msg = ""
        self._spinner_index = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(80)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self._setup_ui()
        self._connect_signals()
        self._restore_window()

    def _setup_ui(self):
        # Central widget with splitter layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self._toolbar = CaptureToolbar(self)
        self._toolbar._settings = self._settings
        # Restore MITM checkbox state now that settings are available
        self._toolbar._mitm_check.setChecked(self._settings.mitm_enabled)
        self.addToolBar(self._toolbar)

        # Tab bar for switching between Packets and HTTP Flows
        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)

        # Packet list view
        self._packet_view = PacketListView(self._packet_model)
        self._tab_widget.addTab(self._packet_view, "Packets")

        # HTTP flow list view
        self._flow_view = FlowListView(self._flow_model)
        self._tab_widget.addTab(self._flow_view, "HTTP Flows")

        # Stats dashboard
        self._stats_dashboard = StatsDashboard()
        self._tab_widget.addTab(self._stats_dashboard, "Dashboard")

        # Detail panel
        self._detail_panel = DetailPanel()

        # Splitter: top = tables, bottom = detail
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(self._tab_widget)
        self._splitter.addWidget(self._detail_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

        layout.addWidget(self._splitter)

        # Busy banner (shown during operations like start/stop/export)
        self._busy_banner = QLabel()
        self._busy_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._busy_banner.setFixedHeight(32)
        self._busy_banner.setStyleSheet("")
        self._busy_banner.hide()
        layout.addWidget(self._busy_banner)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._packet_count_label = QLabel("Packets: 0")
        self._capture_status_label = QLabel("Stopped")
        self._status_bar.addWidget(self._status_label, 1)
        self._status_bar.addPermanentWidget(self._packet_count_label)
        self._status_bar.addPermanentWidget(self._capture_status_label)

    def _show_busy(self, msg: str):
        """Show a prominent loading banner with spinner animation."""
        c = toolbar_colors()
        bg = c['idle_btn']
        fg = c['idle_text']
        border = c['idle_border']
        self._busy_banner.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: 13px;
                font-weight: bold;
                border-top: 1px solid {border};
                padding: 4px;
            }}
        """)
        self._busy_msg = msg
        self._spinner_index = 0
        self._busy_banner.setText(f"  {_SPINNER_FRAMES[0]}  {msg}...")
        self._busy_banner.show()
        self._spinner_timer.start()
        # Force immediate repaint so the banner appears before blocking work
        QApplication.processEvents()

    def _hide_busy(self, msg: str = ""):
        """Stop the spinner and hide the loading banner."""
        self._spinner_timer.stop()
        self._busy_banner.hide()
        if msg:
            self._status_label.setText(msg)

    def _tick_spinner(self):
        """Advance spinner to next frame."""
        self._spinner_index = (self._spinner_index + 1) % len(_SPINNER_FRAMES)
        self._busy_banner.setText(f"  {_SPINNER_FRAMES[self._spinner_index]}  {self._busy_msg}...")

    def _connect_signals(self):
        # Toolbar actions
        self._toolbar.start_signal.connect(self._on_start)
        self._toolbar.stop_signal.connect(self._on_stop)
        self._toolbar.clear_signal.connect(self._on_clear)
        self._toolbar.export_signal.connect(self._on_export)
        self._toolbar.theme_signal.connect(self._on_toggle_theme)

        # Capture manager signals
        self._capture_manager.packet_captured.connect(self._on_packet_captured)
        self._capture_manager.flow_captured.connect(self._on_flow_captured)

        # Table selection
        self._packet_view.selection_changed.connect(self._on_packet_selected)
        self._flow_view.selection_changed.connect(self._on_flow_selected)

        # Tab change
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_start(self, config: dict):
        """Start capture with the given configuration."""
        interface = config.get("interface")
        bpf_filter = config.get("filter", "")
        enable_mitm = config.get("mitm", False)
        mitm_port = config.get("mitm_port", 8080)

        self._show_busy("Starting capture")

        # Clear existing data
        self._ring_buffer.clear()
        self._packet_count = 0

        # Start packet capture
        self._capture_manager.start_capture(interface=interface, bpf_filter=bpf_filter)

        # Optionally start MITM
        if enable_mitm:
            self._capture_manager.start_mitm(port=mitm_port)

        self._capture_status_label.setText("Capturing")

        # Animate for a bit so the user sees feedback
        QTimer.singleShot(800, lambda: self._hide_busy(
            f"Capturing on {interface or 'all interfaces'}"
            + (f" | MITM on port {mitm_port}" if enable_mitm else "")
        ))

        # Update toolbar visual state
        self._toolbar.set_capturing(True)

    def _on_stop(self):
        """Stop all capture."""
        self._show_busy("Stopping capture")
        self._toolbar.set_capturing(False)

        # Delay so the spinner can render before blocking stop
        QTimer.singleShot(200, self._do_stop)

    def _do_stop(self):
        """Perform the actual stop operation."""
        self._capture_manager.stop_all()
        self._capture_status_label.setText("Stopped")
        # Keep the banner for a moment after stop completes
        QTimer.singleShot(400, lambda: self._hide_busy("Capture stopped"))

    def _on_clear(self):
        """Clear all captured data (works during active capture too)."""
        self._ring_buffer.clear()
        self._packet_model.reset_model()
        self._flow_model.clear_flows()
        self._packet_count = 0
        self._packet_count_label.setText("Packets: 0")
        self._detail_panel.clear()
        self._stats_dashboard.clear()

    def _on_export(self, format_type: str):
        """Export captured data."""
        # Determine if filters are active on the relevant tab
        use_filtered = False
        if format_type == "pcap":
            has_filter = self._packet_view.has_active_filter()
        else:
            has_filter = self._flow_view.has_active_filter()

        # If filters are active, ask the user what to export
        if has_filter:
            msg = QMessageBox(self)
            msg.setWindowTitle("Export")
            msg.setText("Filters are active. What would you like to export?")
            btn_all = msg.addButton("Export all data", QMessageBox.ButtonRole.AcceptRole)
            btn_filtered = msg.addButton("Export filtered only", QMessageBox.ButtonRole.YesRole)
            btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_all)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_cancel or clicked is None:
                return
            use_filtered = (clicked == btn_filtered)

        # Build file dialog with timestamped default name
        ext = "txt" if format_type == "curl" else format_type
        default_name = f"netcatcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        start_dir = self._settings.last_export_dir
        default_path = str(Path(start_dir) / default_name) if start_dir else default_name
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Capture", default_path,
            "All Files (*)" if format_type == "curl" else f"{format_type.upper()} Files (*.{format_type})",
        )
        if not filepath:
            return

        # Remember directory
        self._settings.last_export_dir = str(Path(filepath).parent)

        self._show_busy("Exporting...")

        try:
            if format_type == "pcap":
                from netcatcher.storage.exporter import export_pcap
                if use_filtered:
                    packets = self._packet_view.get_visible_packets()
                else:
                    packets = list(self._ring_buffer._deque)
                export_pcap(packets, filepath)
            elif format_type == "har":
                from netcatcher.storage.exporter import export_har
                if use_filtered:
                    flows = self._flow_view.get_visible_flows()
                else:
                    flows = list(self._flow_model._flows)
                export_har(flows, filepath)
            elif format_type == "curl":
                from netcatcher.storage.exporter import export_curl
                if use_filtered:
                    flows = self._flow_view.get_visible_flows()
                else:
                    flows = list(self._flow_model._flows)
                if flows:
                    curl_cmd = export_curl(flows[-1])
                    with open(filepath, "w") as f:
                        f.write(curl_cmd)

            self._hide_busy(f"Exported to {filepath}")
        except Exception as e:
            self._hide_busy("Export failed")
            QMessageBox.warning(self, "Export Error", str(e))

    def _on_packet_captured(self, record: PacketRecord):
        """Handle new packet from capture manager."""
        self._packet_count += 1
        self._packet_model.notify_new_packets(1)
        self._packet_count_label.setText(f"Packets: {self._packet_count}")
        self._stats_dashboard.update_stats(record.protocol, record.length)
        if self._toolbar._follow_check.isChecked():
            self._packet_view.scroll_to_bottom()

    def _on_flow_captured(self, flow: HTTPFlowRecord):
        """Handle new HTTP flow from capture manager."""
        self._flow_model.add_flows([flow])
        if self._toolbar._follow_check.isChecked():
            self._flow_view.scroll_to_bottom()

    def _on_packet_selected(self, row: int):
        """Handle packet selection in the table."""
        packet = self._packet_model.get_packet(row)
        if packet:
            self._detail_panel.show_packet(packet)

    def _on_flow_selected(self, row: int):
        """Handle flow selection in the table."""
        flow = self._flow_model.get_flow(row)
        if flow:
            self._detail_panel.show_flow(flow)

    def _on_tab_changed(self, index: int):
        """Handle tab switch between Packets and HTTP Flows."""
        pass

    def _restore_window(self):
        """Restore window geometry, state and splitter from last session."""
        # Theme is already loaded in main() before widgets are created

        geo = self._settings.window_geometry
        if geo:
            self.restoreGeometry(geo)
        state = self._settings.window_state
        if state:
            self.restoreState(state)
        splitter = self._settings.splitter_state
        if splitter:
            self._splitter.restoreState(splitter)

    def _on_toggle_theme(self):
        """Reload the theme from settings and refresh all themed widgets."""
        from netcatcher.app import load_theme
        load_theme(self._settings.theme)
        # Refresh toolbar styles
        self._toolbar._update_state(self._toolbar._capturing)
        # Force a full repaint of the window to pick up new palette + stylesheet
        self.update()
        self.repaint()
        # Force table models to repaint with new colors
        self._packet_model.dataChanged.emit(
            self._packet_model.index(0, 0),
            self._packet_model.index(max(0, self._packet_model.rowCount() - 1),
                                     self._packet_model.columnCount() - 1),
        )
        self._flow_model.dataChanged.emit(
            self._flow_model.index(0, 0),
            self._flow_model.index(max(0, self._flow_model.rowCount() - 1),
                                   self._flow_model.columnCount() - 1),
        )

    def closeEvent(self, event):
        """Save window state and clean up on close."""
        self._settings.window_geometry = self.saveGeometry()
        self._settings.window_state = self.saveState()
        self._settings.splitter_state = self._splitter.saveState()
        self._capture_manager.stop_all()
        super().closeEvent(event)
