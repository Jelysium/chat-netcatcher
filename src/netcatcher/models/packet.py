"""Unified packet record data model."""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class PacketRecord:
    """Represents a single captured network packet."""

    id: int = 0
    timestamp: float = field(default_factory=time.time)
    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0
    protocol: str = ""
    length: int = 0
    info: str = ""
    raw_bytes: bytes = b""
    layer_details: dict = field(default_factory=dict)
    capture_source: str = "scapy"  # "scapy" or "mitmproxy"

    @property
    def time_str(self) -> str:
        """Formatted timestamp string."""
        t = time.localtime(self.timestamp)
        ms = int((self.timestamp % 1) * 1000)
        return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"

    @property
    def summary(self) -> str:
        """One-line summary for display."""
        if self.src_port:
            return f"{self.src_ip}:{self.src_port} → {self.dst_ip}:{self.dst_port} {self.protocol} [{self.length}]"
        return f"{self.src_ip} → {self.dst_ip} {self.protocol} [{self.length}]"
