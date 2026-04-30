"""Application constants."""

from PyQt6.QtCore import QSettings

# Capture settings
DEFAULT_CAPTURE_BUFFER_SIZE = 50000
DEFAULT_MITM_PORT = 8080
DEFAULT_BATCH_INTERVAL_MS = 100
DEFAULT_QUEUE_POLL_INTERVAL_MS = 50

# GUI settings
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900

# Table columns for packet list
PACKET_COLUMNS = ["#", "Time", "Source", "Destination", "Protocol", "Length", "Info"]
PACKET_COLUMN_WIDTHS = [60, 100, 150, 150, 80, 60, 400]

# Table columns for HTTP flow list
FLOW_COLUMNS = ["#", "Method", "Host", "Path", "Status", "Size", "Time(ms)"]
FLOW_COLUMN_WIDTHS = [60, 70, 200, 300, 60, 80, 80]

# Filter keywords
FILTER_FIELDS = {"protocol", "src", "dst", "port", "host", "method", "status", "contains"}


def _is_light_theme() -> bool:
    """Check if the current theme is light."""
    return QSettings().value("appearance/theme", "dark") == "light"


# ── Protocol colors (dark / light) ──

_DARK_PROTOCOL_COLORS = {
    "TCP": "#2a2a3d", "UDP": "#2a332d", "ICMP": "#33302a",
    "DNS": "#302a3a", "HTTP": "#2a3033", "HTTPS": "#2a3033",
    "TLS": "#332a2e", "ARP": "#30302a",
}
_LIGHT_PROTOCOL_COLORS = {
    "TCP": "#dfe6f5", "UDP": "#dfe9df", "ICMP": "#e9e3d5",
    "DNS": "#e5dfee", "HTTP": "#d5e5e9", "HTTPS": "#d5e5e9",
    "TLS": "#e9d5da", "ARP": "#e9e9d5",
}

_DARK_PROTOCOL_FG = {
    "TCP": "#89b4fa", "UDP": "#a6e3a1", "ICMP": "#fab387",
    "DNS": "#cba6f7", "HTTP": "#94e2d5", "HTTPS": "#94e2d5",
    "TLS": "#f38ba8", "ARP": "#f9e2af",
}
_LIGHT_PROTOCOL_FG = {
    "TCP": "#1e66f5", "UDP": "#40a02b", "ICMP": "#fe640b",
    "DNS": "#8839ef", "HTTP": "#179299", "HTTPS": "#179299",
    "TLS": "#d20f39", "ARP": "#df8e1d",
}


def protocol_bg() -> dict:
    return _LIGHT_PROTOCOL_COLORS if _is_light_theme() else _DARK_PROTOCOL_COLORS

def protocol_fg() -> dict:
    return _LIGHT_PROTOCOL_FG if _is_light_theme() else _DARK_PROTOCOL_FG


# ── HTTP flow colors (dark / light) ──

_DARK_STATUS_BG = {2: "#252e2a", 3: "#252a30", 4: "#302a25", 5: "#302527"}
_LIGHT_STATUS_BG = {2: "#dcedde", 3: "#dde4f0", 4: "#f0e4d4", 5: "#f0d6d8"}

_DARK_STATUS_FG = {2: "#a6e3a1", 3: "#89b4fa", 4: "#fab387", 5: "#f38ba8"}
_LIGHT_STATUS_FG = {2: "#40a02b", 3: "#1e66f5", 4: "#fe640b", 5: "#d20f39"}

_DARK_METHOD_FG = {
    "GET": "#89b4fa", "POST": "#a6e3a1", "PUT": "#f9e2af",
    "DELETE": "#f38ba8", "PATCH": "#cba6f7", "HEAD": "#94e2d5", "OPTIONS": "#b4befe",
}
_LIGHT_METHOD_FG = {
    "GET": "#1e66f5", "POST": "#40a02b", "PUT": "#df8e1d",
    "DELETE": "#d20f39", "PATCH": "#8839ef", "HEAD": "#179299", "OPTIONS": "#7287fd",
}


def status_bg_colors() -> dict:
    return _LIGHT_STATUS_BG if _is_light_theme() else _DARK_STATUS_BG

def status_fg_colors() -> dict:
    return _LIGHT_STATUS_FG if _is_light_theme() else _DARK_STATUS_FG

def method_fg_colors() -> dict:
    return _LIGHT_METHOD_FG if _is_light_theme() else _DARK_METHOD_FG


# ── Hex editor colors (dark / light) ──

_DARK_HEX = {
    "offset": "#A0A0A0", "hex": "#D0D0D0", "ascii": "#80C080",
    "separator": "#505050", "sel_bg": "#45475A",
}
_LIGHT_HEX = {
    "offset": "#888888", "hex": "#404040", "ascii": "#2a7a2a",
    "separator": "#c0c0c0", "sel_bg": "#b4befe",
}


def hex_colors() -> dict:
    return _LIGHT_HEX if _is_light_theme() else _DARK_HEX


# ── Toolbar colors (dark / light) ──

_DARK_TOOLBAR = {
    "idle_bg": "#181825", "idle_btn": "#313244", "idle_border": "#45475a",
    "idle_text": "#cdd6f4", "idle_hover": "#45475a",
    "active_bg": "#1a2e1a", "active_border": "#a6e3a1",
    "active_btn": "#2a3a2a", "active_hover": "#3a4a3a",
    "active_text": "#cdd6f4",
    "disabled_bg": "#1e1e2e", "disabled_text": "#585b70", "disabled_border": "#313244",
}
_LIGHT_TOOLBAR = {
    "idle_bg": "#e6e9ef", "idle_btn": "#ccd0da", "idle_border": "#bcc0cc",
    "idle_text": "#4c4f69", "idle_hover": "#bcc0cc",
    "active_bg": "#dcedde", "active_border": "#40a02b",
    "active_btn": "#c4d9c0", "active_hover": "#b0c8ac",
    "active_text": "#4c4f69",
    "disabled_bg": "#e6e9ef", "disabled_text": "#9ca0b0", "disabled_border": "#d0d4de",
}


def toolbar_colors() -> dict:
    return _LIGHT_TOOLBAR if _is_light_theme() else _DARK_TOOLBAR
