"""DNS packet parsing helpers."""

from __future__ import annotations


def extract_dns_info(dns_layer) -> str:
    """Extract DNS query/response info from scapy DNS layer."""
    if dns_layer.qr == 0:
        # Query
        try:
            qname = dns_layer.qd.qname if dns_layer.qd else "unknown"
        except Exception:
            qname = "unknown"
        return f"Query: {qname}"
    else:
        # Response
        try:
            qname = dns_layer.qd.qname if dns_layer.qd else "unknown"
        except Exception:
            qname = "unknown"
        ancount = dns_layer.ancount
        answers = []
        try:
            for i in range(min(ancount, 5)):
                try:
                    an = dns_layer.an[i]
                    answers.append(str(an.rdata))
                except (IndexError, AttributeError):
                    break
        except Exception:
            pass
        if answers:
            return f"Response: {qname} → {', '.join(answers)}"
        return f"Response: {qname} ({ancount} answers)"
