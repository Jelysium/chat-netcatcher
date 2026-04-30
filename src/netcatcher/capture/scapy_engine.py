"""Scapy-based raw packet capture engine running in a QThread."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from netcatcher.models.packet import PacketRecord
from netcatcher.parsers.protocol_parser import parse_packet

logger = logging.getLogger(__name__)


class ScapyEngine(QThread):
    """Wraps scapy's AsyncSniffer inside a QThread.

    Emits `packet_captured(PacketRecord)` for each captured packet.
    """

    packet_captured = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._interface = None
        self._bpf_filter = ""
        self._sniffer = None

    def configure(self, interface: str | None = None, bpf_filter: str = ""):
        """Set capture parameters before starting."""
        self._interface = interface
        self._bpf_filter = bpf_filter

    def start_capture(self):
        """Start the capture thread."""
        self._running = True
        self.start()

    def stop_capture(self):
        """Stop the capture thread."""
        self._running = False
        if self._sniffer is not None:
            try:
                self._sniffer.stop()
            except Exception:
                pass
        self.wait(3000)

    def is_running(self) -> bool:
        return self._running and self.isRunning()

    def run(self):
        """Thread entry point: run scapy sniffer."""
        try:
            from scapy.all import sniff, conf

            conf.verb = 0

            kwargs = {
                "store": False,
                "prn": self._on_packet,
            }
            if self._interface:
                kwargs["iface"] = self._interface
            if self._bpf_filter:
                kwargs["filter"] = self._bpf_filter

            self._sniffer = sniff(**kwargs)

        except ImportError:
            logger.error("scapy is not installed")
            self._running = False
        except Exception as e:
            logger.error(f"Scapy capture error: {e}")
            self._running = False

    def _on_packet(self, scapy_pkt):
        """Callback for each captured scapy packet."""
        if not self._running:
            return
        try:
            record = parse_packet(scapy_pkt)
            if record:
                self.packet_captured.emit(record)
        except Exception:
            pass

    @staticmethod
    def get_interfaces() -> list[str]:
        """Get available network interfaces."""
        try:
            from scapy.all import get_if_list
            return get_if_list()
        except ImportError:
            return []
