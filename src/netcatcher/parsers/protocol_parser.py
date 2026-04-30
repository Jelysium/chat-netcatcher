"""Parse scapy packets into PacketRecord objects."""

from __future__ import annotations

import time

from netcatcher.models.packet import PacketRecord
from netcatcher.parsers.dns_parser import extract_dns_info


def parse_packet(scapy_pkt) -> PacketRecord | None:
    """Convert a scapy packet to a PacketRecord."""
    record = PacketRecord()
    record.timestamp = time.time()
    record.length = len(scapy_pkt)
    try:
        record.raw_bytes = bytes(scapy_pkt)
    except Exception:
        record.raw_bytes = b""
    record.capture_source = "scapy"

    # Extract IP layer
    if scapy_pkt.haslayer("IP"):
        ip = scapy_pkt["IP"]
        record.src_ip = ip.src
        record.dst_ip = ip.dst
        record.layer_details["ip"] = {
            "version": ip.version,
            "ttl": ip.ttl,
            "id": ip.id,
            "flags": str(ip.flags),
        }
    elif scapy_pkt.haslayer("IPv6"):
        ip6 = scapy_pkt["IPv6"]
        record.src_ip = ip6.src
        record.dst_ip = ip6.dst
        record.layer_details["ipv6"] = {"hop_limit": ip6.hlim}
    elif scapy_pkt.haslayer("ARP"):
        arp = scapy_pkt["ARP"]
        record.protocol = "ARP"
        record.src_ip = arp.psrc or ""
        record.dst_ip = arp.pdst or ""
        record.info = f"ARP {arp.op}: {arp.psrc} → {arp.pdst}"
        return record
    else:
        # Unknown or Ethernet-level packet
        record.protocol = "ETH"
        return record

    # Transport layer
    if scapy_pkt.haslayer("TCP"):
        tcp = scapy_pkt["TCP"]
        record.src_port = tcp.sport
        record.dst_port = tcp.dport
        flags = str(tcp.flags)
        record.layer_details["tcp"] = {
            "flags": flags,
            "seq": tcp.seq,
            "ack": tcp.ack,
            "window": tcp.window,
        }
        # Identify application protocol by port and layer
        if scapy_pkt.haslayer("DNS"):
            record.protocol = "DNS"
            try:
                record.info = extract_dns_info(scapy_pkt["DNS"])
            except Exception:
                record.info = "DNS"
        elif tcp.dport == 80 or tcp.sport == 80:
            record.protocol = "HTTP"
            record.info = _tcp_info(tcp, scapy_pkt)
        elif tcp.dport == 443 or tcp.sport == 443:
            record.protocol = "TLS"
            record.info = _tcp_info(tcp, scapy_pkt)
        else:
            record.protocol = "TCP"
            record.info = _tcp_info(tcp, scapy_pkt)

    elif scapy_pkt.haslayer("UDP"):
        udp = scapy_pkt["UDP"]
        record.src_port = udp.sport
        record.dst_port = udp.dport
        record.layer_details["udp"] = {"len": udp.len}
        if scapy_pkt.haslayer("DNS"):
            record.protocol = "DNS"
            try:
                record.info = extract_dns_info(scapy_pkt["DNS"])
            except Exception:
                record.info = "DNS"
        else:
            record.protocol = "UDP"
            record.info = _udp_info(udp, scapy_pkt)

    elif scapy_pkt.haslayer("ICMP"):
        icmp = scapy_pkt["ICMP"]
        record.protocol = "ICMP"
        icmp_types = {0: "Echo Reply", 8: "Echo Request", 3: "Dest Unreachable", 11: "Time Exceeded"}
        record.info = icmp_types.get(icmp.type, f"Type {icmp.type}")
        record.layer_details["icmp"] = {"type": icmp.type, "code": icmp.code}

    return record


def _tcp_info(tcp, pkt) -> str:
    """Generate info string for TCP packets."""
    port_services = {
        80: "HTTP", 443: "TLS", 8080: "HTTP-ALT", 8443: "HTTPS-ALT",
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        110: "POP3", 143: "IMAP", 3306: "MySQL", 5432: "PostgreSQL",
        6379: "Redis", 27017: "MongoDB",
    }
    flags = str(tcp.flags)
    dst_service = port_services.get(tcp.dport, "")
    src_service = port_services.get(tcp.sport, "")

    if dst_service:
        return f"{dst_service} [{flags}] Seq={tcp.seq} Ack={tcp.ack} Win={tcp.window}"
    if src_service:
        return f"{src_service} [{flags}] Seq={tcp.seq} Ack={tcp.ack} Win={tcp.window}"
    return f"[{flags}] Seq={tcp.seq} Ack={tcp.ack} Win={tcp.window}"


def _udp_info(udp, pkt) -> str:
    """Generate info string for UDP packets."""
    port_services = {53: "DNS", 123: "NTP", 161: "SNMP", 5353: "mDNS", 1900: "SSDP"}

    if pkt.haslayer("DNS"):
        try:
            return extract_dns_info(pkt["DNS"])
        except Exception:
            return "DNS"

    dst_service = port_services.get(udp.dport, "")
    if dst_service:
        return f"{dst_service} Len={udp.len}"
    return f"Len={udp.len}"
