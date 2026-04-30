"""Certificate management for HTTPS MITM interception."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def get_cert_dir() -> Path:
    """Get the mitmproxy certificate directory."""
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "~")) / ".mitmproxy"
    return Path.home() / ".mitmproxy"


def get_cert_paths() -> dict[str, Path]:
    """Get paths to all mitmproxy certificate files."""
    cert_dir = get_cert_dir()
    return {
        "pem": cert_dir / "mitmproxy-ca-cert.pem",
        "p12": cert_dir / "mitmproxy-ca-cert.p12",
        "cer": cert_dir / "mitmproxy-ca-cert.cer",
    }


def ensure_cert_exists() -> bool:
    """Ensure the mitmproxy CA certificate exists. Returns True if cert exists."""
    paths = get_cert_paths()
    return paths["pem"].exists()


def generate_cert():
    """Generate the mitmproxy CA certificate by running mitmproxy briefly."""
    try:
        from mitmproxy.certs import CertStore
        cert_dir = get_cert_dir()
        cert_dir.mkdir(parents=True, exist_ok=True)
        # CertStore will create the CA on initialization
        CertStore.from_store(str(cert_dir), "mitmproxy", 2048)
        return True
    except Exception:
        return False


def is_cert_trusted() -> bool:
    """Check if the mitmproxy CA cert is in the Windows trusted root store."""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["certutil", "-store", "-user", "Root", "mitmproxy"],
            capture_output=True, text=True, timeout=10,
        )
        return "mitmproxy" in result.stdout and "Cert" in result.stdout
    except Exception:
        return False


def install_cert() -> bool:
    """Install the mitmproxy CA cert to the current user's trusted root store."""
    if sys.platform != "win32":
        return False

    paths = get_cert_paths()
    cer_path = paths["cer"]

    if not cer_path.exists():
        # Try generating first
        if not generate_cert():
            return False

    try:
        result = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", str(cer_path)],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def uninstall_cert() -> bool:
    """Remove the mitmproxy CA cert from the trusted root store."""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["certutil", "-delstore", "-user", "Root", "mitmproxy"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def open_cert_manager():
    """Open the Windows certificate manager (certmgr.msc)."""
    if sys.platform == "win32":
        os.startfile("certmgr.msc")
