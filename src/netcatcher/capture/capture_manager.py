"""Capture manager orchestrates both capture engines."""

from __future__ import annotations

import queue
import logging

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from netcatcher.config.constants import DEFAULT_QUEUE_POLL_INTERVAL_MS, DEFAULT_MITM_PORT
from netcatcher.capture.scapy_engine import ScapyEngine
from netcatcher.capture.mitm_engine import MitmEngine
from netcatcher.storage.ring_buffer import RingBuffer
from netcatcher.models.packet import PacketRecord
from netcatcher.models.http_flow import HTTPFlowRecord
from netcatcher.proxy.system_proxy import set_system_proxy, clear_system_proxy

logger = logging.getLogger(__name__)


class CaptureManager(QObject):
    """Unified manager for packet capture and HTTP interception."""

    packet_captured = pyqtSignal(object)   # PacketRecord
    flow_captured = pyqtSignal(object)     # HTTPFlowRecord
    capture_error = pyqtSignal(str)        # error message

    def __init__(self, ring_buffer: RingBuffer, parent=None):
        super().__init__(parent)
        self._buffer = ring_buffer
        self._scapy_engine: ScapyEngine | None = None
        self._mitm_engine: MitmEngine | None = None
        self._flow_queue: queue.Queue = queue.Queue()

        # Timer to poll mitmproxy flow queue
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(DEFAULT_QUEUE_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._drain_flow_queue)

        self._capture_active = False
        self._mitm_active = False
        self._proxy_was_set = False

    def start_capture(self, interface: str | None = None, bpf_filter: str = ""):
        """Start raw packet capture via scapy."""
        if self._capture_active:
            return
        try:
            self._scapy_engine = ScapyEngine(self)
            self._scapy_engine.configure(interface=interface, bpf_filter=bpf_filter)
            self._scapy_engine.packet_captured.connect(self._on_packet)
            self._scapy_engine.start_capture()
            self._capture_active = True
        except Exception as e:
            self.capture_error.emit(f"Failed to start capture: {e}")

    def stop_capture(self):
        """Stop raw packet capture."""
        if self._scapy_engine and self._capture_active:
            try:
                self._scapy_engine.stop_capture()
            except Exception as e:
                logger.debug(f"Error stopping scapy: {e}")
            self._capture_active = False

    def start_mitm(self, port: int = DEFAULT_MITM_PORT):
        """Start HTTPS MITM interception and set system proxy."""
        if self._mitm_active:
            return
        try:
            self._mitm_engine = MitmEngine(self._flow_queue, port)
            self._mitm_engine.start_capture()
            self._poll_timer.start()
            self._mitm_active = True

            # Set system proxy to redirect browser traffic through MITM
            set_system_proxy(host="127.0.0.1", port=port)
            self._proxy_was_set = True
        except Exception as e:
            self.capture_error.emit(f"Failed to start MITM: {e}")

    def stop_mitm(self):
        """Stop HTTPS MITM interception and restore system proxy."""
        if self._mitm_engine and self._mitm_active:
            try:
                self._mitm_engine.stop_capture()
            except Exception as e:
                logger.debug(f"Error stopping MITM: {e}")
            self._poll_timer.stop()
            self._mitm_active = False

        # Restore system proxy
        if self._proxy_was_set:
            clear_system_proxy()
            self._proxy_was_set = False

    def stop_all(self):
        """Stop all capture engines."""
        self.stop_capture()
        self.stop_mitm()

    def _on_packet(self, record: PacketRecord):
        """Handle a packet from the scapy engine."""
        self._buffer.append(record)
        self.packet_captured.emit(record)

    def _drain_flow_queue(self):
        """Poll the mitmproxy flow queue and emit signals."""
        batch: list[HTTPFlowRecord] = []
        while True:
            try:
                flow = self._flow_queue.get_nowait()
                if isinstance(flow, HTTPFlowRecord):
                    batch.append(flow)
            except queue.Empty:
                break
        for flow in batch:
            self.flow_captured.emit(flow)
