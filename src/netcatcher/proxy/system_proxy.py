"""Windows system proxy configuration via registry."""

from __future__ import annotations

import sys


def set_system_proxy(host: str = "127.0.0.1", port: int = 8080):
    """Enable the Windows system HTTP proxy pointing to our MITM server."""
    if sys.platform != "win32":
        return

    import winreg
    import ctypes

    proxy_addr = f"{host}:{port}"
    bypass = "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*"

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings",
        0, winreg.KEY_WRITE,
    )

    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_addr)
    winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, bypass)
    winreg.CloseKey(key)

    # Notify system of proxy change
    _refresh_proxy_settings()


def clear_system_proxy():
    """Disable the Windows system proxy."""
    if sys.platform != "win32":
        return

    import winreg
    import ctypes

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings",
        0, winreg.KEY_WRITE,
    )

    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
    winreg.CloseKey(key)

    _refresh_proxy_settings()


def _refresh_proxy_settings():
    """Force Windows to reload proxy settings immediately."""
    try:
        import ctypes
        internet_option_settings_changed = 39
        internet_option_refresh = 37
        ctypes.windll.wininet.InternetSetOptionW(0, internet_option_settings_changed, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, internet_option_refresh, 0, 0)
    except Exception:
        pass


def is_proxy_enabled() -> bool:
    """Check if the system proxy is currently enabled."""
    if sys.platform != "win32":
        return False

    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_READ,
        )
        enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
        winreg.CloseKey(key)
        return bool(enabled)
    except Exception:
        return False
