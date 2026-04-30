"""Export captured data to PCAP, HAR, and cURL formats."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from netcatcher.models.packet import PacketRecord
from netcatcher.models.http_flow import HTTPFlowRecord


def export_pcap(packets: list[PacketRecord], filepath: str | Path):
    """Export packets to PCAP format using scapy."""
    from scapy.all import wrpcap, Ether

    scapy_packets = []
    for pkt in packets:
        if pkt.raw_bytes:
            try:
                sp = Ether(pkt.raw_bytes)
                scapy_packets.append(sp)
            except Exception:
                pass

    if not scapy_packets:
        raise RuntimeError("No valid packets to export")

    wrpcap(str(filepath), scapy_packets)


def export_har(flows: list[HTTPFlowRecord], filepath: str | Path):
    """Export HTTP flows to HAR (HTTP Archive) format."""
    entries = []
    for flow in flows:
        entry = {
            "startedDateTime": datetime.fromtimestamp(flow.timestamp, tz=timezone.utc).isoformat(),
            "time": flow.duration_ms,
            "request": {
                "method": flow.method,
                "url": flow.url,
                "httpVersion": "HTTP/1.1",
                "headers": [{"name": k, "value": v} for k, v in flow.request_headers.items()],
                "content": {
                    "size": len(flow.request_body),
                    "mimeType": flow.request_headers.get("content-type", ""),
                },
            },
            "response": {
                "status": flow.status_code,
                "statusText": "",
                "httpVersion": "HTTP/1.1",
                "headers": [{"name": k, "value": v} for k, v in flow.response_headers.items()],
                "content": {
                    "size": len(flow.response_body),
                    "mimeType": flow.content_type or "",
                },
            },
        }
        entries.append(entry)

    har = {
        "log": {
            "version": "1.2",
            "creator": {"name": "NetCatcher", "version": "0.1.0"},
            "entries": entries,
        }
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(har, f, indent=2, ensure_ascii=False)


def export_curl(flow: HTTPFlowRecord) -> str:
    """Export a single HTTP flow as a cURL command string."""
    parts = [f"curl -X {flow.method}"]

    for name, value in flow.request_headers.items():
        value_escaped = value.replace("'", "'\\''")
        parts.append(f"-H '{name}: {value_escaped}'")

    if flow.request_body:
        body_str = flow.request_body.decode("utf-8", errors="replace")
        body_escaped = body_str.replace("'", "'\\''")
        parts.append(f"-d '{body_escaped}'")

    parts.append(f"'{flow.url}'")
    return " \\\n  ".join(parts)
