"""Parse mitmproxy HTTPFlow objects into HTTPFlowRecord."""

from __future__ import annotations

import time

from netcatcher.models.http_flow import HTTPFlowRecord


def parse_flow(flow) -> HTTPFlowRecord | None:
    """Convert a mitmproxy HTTPFlow to an HTTPFlowRecord."""
    if not flow or not flow.request:
        return None

    record = HTTPFlowRecord()
    record.timestamp = getattr(flow, "timestamp_start", None) or time.time()
    record.method = flow.request.method or ""
    record.url = flow.request.pretty_url or ""
    record.host = flow.request.pretty_host or ""
    record.path = flow.request.path or ""
    record.request_headers = dict(flow.request.headers) if flow.request.headers else {}
    record.is_https = flow.request.scheme == "https"

    # Request body
    try:
        body = flow.request.get_content()
        record.request_body = body if isinstance(body, bytes) else (body.encode("utf-8") if body else b"")
    except Exception:
        record.request_body = b""

    # Response (may not exist yet during request hook)
    if flow.response:
        record.status_code = flow.response.status_code or 0
        record.response_headers = dict(flow.response.headers) if flow.response.headers else {}
        record.content_type = flow.response.headers.get("content-type", "") if flow.response.headers else ""
        try:
            body = flow.response.get_content()
            record.response_body = body if isinstance(body, bytes) else (body.encode("utf-8") if body else b"")
        except Exception:
            record.response_body = b""

    # Duration: mitmproxy 12 has no timestamp_end, calculate from response if available
    ts_start = getattr(flow, "timestamp_start", None)
    ts_created = getattr(flow, "timestamp_created", None)
    if ts_start and record.status_code:
        record.duration_ms = (time.time() - ts_start) * 1000

    return record
