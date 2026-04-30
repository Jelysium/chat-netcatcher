"""HTTP flow record data model."""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class HTTPFlowRecord:
    """Represents a captured HTTP/HTTPS request-response pair."""

    id: int = 0
    timestamp: float = field(default_factory=time.time)
    method: str = ""
    url: str = ""
    host: str = ""
    path: str = ""
    status_code: int = 0
    request_headers: dict = field(default_factory=dict)
    request_body: bytes = b""
    response_headers: dict = field(default_factory=dict)
    response_body: bytes = b""
    content_type: str = ""
    duration_ms: float = 0.0
    is_https: bool = False

    @property
    def time_str(self) -> str:
        t = time.localtime(self.timestamp)
        ms = int((self.timestamp % 1) * 1000)
        return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"

    @property
    def response_size(self) -> int:
        return len(self.response_body)

    @property
    def status_text(self) -> str:
        return str(self.status_code) if self.status_code else "Pending"

    @property
    def scheme(self) -> str:
        return "HTTPS" if self.is_https else "HTTP"
