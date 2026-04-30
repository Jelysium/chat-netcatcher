"""TLS/SNI packet parsing helpers."""

from __future__ import annotations


def extract_tls_info(pkt) -> str | None:
    """Extract TLS SNI (Server Name Indication) from a packet if present."""
    try:
        if pkt.haslayer("TLS"):
            tls = pkt["TLS"]
            # Try to extract SNI from ClientHello
            if hasattr(tls, "msg"):
                for msg in tls.msg:
                    if hasattr(msg, "extensions"):
                        for ext in msg.extensions:
                            if hasattr(ext, "servernames"):
                                names = [sn.servername for sn in ext.servernames if sn.servername]
                                if names:
                                    return f"TLS SNI: {', '.join(names)}"
    except Exception:
        pass
    return None


def is_tls_handshake(pkt) -> bool:
    """Check if a TCP packet carries TLS handshake data."""
    try:
        if pkt.haslayer("TCP") and pkt.haslayer("Raw"):
            raw = bytes(pkt["Raw"])
            # TLS records start with content type byte: 0x16 = Handshake
            return len(raw) > 0 and raw[0] == 0x16
    except Exception:
        pass
    return False
