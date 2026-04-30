"""Capture toolbar with start/stop/clear/export controls."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QToolBar, QWidget, QHBoxLayout,
    QComboBox, QCheckBox, QLabel, QSpinBox,
    QToolButton, QMenu,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction

from netcatcher.config.constants import toolbar_colors


class CaptureToolbar(QToolBar):
    """Main toolbar with capture controls."""

    start_signal = pyqtSignal(dict)   # config dict
    stop_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    export_signal = pyqtSignal(str)   # format type
    theme_signal = pyqtSignal()       # toggle theme

    def __init__(self, parent=None):
        super().__init__("Capture Controls", parent)
        self.setObjectName("captureToolbar")
        self.setMovable(False)
        self._capturing = False
        self._settings = None
        self._setup_actions()

    def _setup_actions(self):
        # Start capture
        self._start_action = QAction("  Start  ", self)
        self._start_action.setToolTip("Start packet capture")
        self._start_action.triggered.connect(self._on_start)
        self.addAction(self._start_action)

        # Stop capture
        self._stop_action = QAction("  Stop  ", self)
        self._stop_action.setToolTip("Stop packet capture")
        self._stop_action.triggered.connect(self.stop_signal.emit)
        self.addAction(self._stop_action)

        # Clear
        self._clear_action = QAction(" Clear ", self)
        self._clear_action.setToolTip("Clear captured data")
        self._clear_action.triggered.connect(self.clear_signal.emit)
        self.addAction(self._clear_action)

        self.addSeparator()

        # Interface selector
        self.addWidget(QLabel(" Interface: "))
        self._interface_combo = QComboBox()
        self._interface_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._interface_combo.setMinimumWidth(150)
        self._interface_combo.addItem("All Interfaces")
        self._populate_interfaces()
        self.addWidget(self._interface_combo)

        self.addSeparator()

        # MITM checkbox
        self._mitm_check = QCheckBox("HTTPS Intercept")
        self._mitm_check.setToolTip("Enable HTTPS MITM interception")
        self.addWidget(self._mitm_check)

        # Restore saved MITM checkbox state
        if self._settings is not None:
            self._mitm_check.setChecked(self._settings.mitm_enabled)

        # MITM port
        self.addWidget(QLabel(" Port: "))
        self._mitm_port_spin = QSpinBox()
        self._mitm_port_spin.setRange(1024, 65535)
        self._mitm_port_spin.setValue(8080)
        self._mitm_port_spin.setFixedWidth(75)
        self.addWidget(self._mitm_port_spin)

        self.addSeparator()

        # Export dropdown button (combines PCAP / HAR / cURL)
        self._export_btn = QToolButton(self)
        self._export_btn.setText(" Export ")
        self._export_btn.setToolTip("Export captured data")
        self._export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        export_menu = QMenu(self._export_btn)
        act_pcap = export_menu.addAction("Export PCAP")
        act_pcap.triggered.connect(lambda: self.export_signal.emit("pcap"))
        act_har = export_menu.addAction("Export HAR")
        act_har.triggered.connect(lambda: self.export_signal.emit("har"))
        act_curl = export_menu.addAction("Copy as cURL")
        act_curl.triggered.connect(lambda: self.export_signal.emit("curl"))
        self._export_btn.setMenu(export_menu)
        self.addWidget(self._export_btn)

        self.addSeparator()

        # Auto-follow toggle
        self._follow_check = QCheckBox("Auto Follow")
        self._follow_check.setToolTip("Auto-scroll to new data")
        self._follow_check.setChecked(True)
        self.addWidget(self._follow_check)

        self.addSeparator()

        # Theme toggle
        self._theme_btn = QToolButton(self)
        self._theme_btn.setText(" Theme ")
        self._theme_btn.setToolTip("Switch light/dark theme")
        self._theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        theme_menu = QMenu(self._theme_btn)
        act_dark = theme_menu.addAction("Dark")
        act_dark.triggered.connect(lambda: self._apply_theme("dark"))
        act_light = theme_menu.addAction("Light")
        act_light.triggered.connect(lambda: self._apply_theme("light"))
        self._theme_btn.setMenu(theme_menu)
        self.addWidget(self._theme_btn)

        # Initial state
        self._update_state(False)

    def set_capturing(self, capturing: bool):
        """Update toolbar visual state."""
        self._capturing = capturing
        self._update_state(capturing)

    def _update_state(self, capturing: bool):
        """Apply visual styles based on capture state and theme."""
        c = toolbar_colors()
        if capturing:
            self._start_action.setEnabled(False)
            self._stop_action.setEnabled(True)
            self.setStyleSheet(f"""
                QToolBar {{ background-color: {c['active_bg']}; border-bottom: 2px solid {c['active_border']}; }}
                QToolBar QToolButton {{ background-color: {c['active_btn']}; color: {c['active_text']}; border: 1px solid {c['idle_border']}; border-radius: 4px; padding: 4px 10px; }}
                QToolBar QToolButton:hover {{ background-color: {c['active_hover']}; }}
                QToolBar QToolButton:disabled {{ background-color: {c['disabled_bg']}; color: {c['disabled_text']}; border: 1px solid {c['disabled_border']}; }}
            """)
        else:
            self._start_action.setEnabled(True)
            self._stop_action.setEnabled(False)
            self.setStyleSheet(f"""
                QToolBar {{ background-color: {c['idle_bg']}; border-bottom: 1px solid {c['idle_border']}; }}
                QToolBar QToolButton {{ background-color: {c['idle_btn']}; color: {c['idle_text']}; border: 1px solid {c['idle_border']}; border-radius: 4px; padding: 4px 10px; }}
                QToolBar QToolButton:hover {{ background-color: {c['idle_hover']}; }}
                QToolBar QToolButton:disabled {{ background-color: {c['disabled_bg']}; color: {c['disabled_text']}; border: 1px solid {c['disabled_border']}; }}
            """)

    def _populate_interfaces(self):
        """Populate the interface dropdown with available interfaces."""
        try:
            from scapy.all import get_if_list, get_if_addr
            for iface in get_if_list():
                try:
                    addr = get_if_addr(iface)
                    short = iface.split("_")[-1] if "_" in iface else iface
                    if addr and addr != "0.0.0.0":
                        label = f"{short} ({addr})"
                    else:
                        label = short
                except Exception:
                    label = iface.split("_")[-1] if "_" in iface else iface
                self._interface_combo.addItem(label, iface)
        except Exception:
            pass

    def _apply_theme(self, theme: str):
        """Apply theme and persist the choice."""
        if self._settings is not None:
            self._settings.theme = theme
        self.theme_signal.emit()

    def _on_start(self):
        """Emit start signal with current configuration."""
        # Persist MITM checkbox state
        if self._settings is not None:
            self._settings.mitm_enabled = self._mitm_check.isChecked()

        iface_data = self._interface_combo.currentData()
        config = {
            "interface": iface_data if iface_data else None,
            "filter": "",
            "mitm": self._mitm_check.isChecked(),
            "mitm_port": self._mitm_port_spin.value(),
        }
        self.start_signal.emit(config)
