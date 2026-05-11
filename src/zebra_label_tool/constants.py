"""Shared application constants."""

from __future__ import annotations

from . import __version__

APP_TITLE = "Zebra Label Tool"
APP_VERSION = __version__

MAX_HISTORY = 10
PREVIEW_MAX_W = 420
PREVIEW_MAX_H = 220

DPI_OPTIONS = {
    "203 dpi  (ZD220, GX420, many desktop printers)": 203,
    "300 dpi  (ZD421-300, ZT410-300)": 300,
    "600 dpi  (ZT610-600)": 600,
}

DEFAULT_SETTINGS = {
    "printer": "",
    "dpi": 300,
    "width_mm": 57,
    "height_mm": 19,
    "font_size": 58,
    "copies": 1,
    "inverted": False,
    "border": False,
    "barcode": False,
    "barcode_pos": "below",
    "font_style": "A0",
    "text_lines": [""],
    "alignment": "center",
    "rotation": "normal",
    "line_gap": 10,
    "offset_x": 0,
    "offset_y": 0,
    "auto_fit": True,
    "barcode_text": "",
    "history": [],
    "templates": {},
}

COL_BG = "#1c1c1e"
COL_PANEL = "#252528"
COL_CARD = "#2c2c30"
COL_BORDER = "#3a3a3e"
COL_ACCENT = "#1a73e8"
COL_SUCCESS = "#34a853"
COL_WARN = "#fbbc04"
COL_ERR = "#ea4335"
COL_TEXT = "#e8e8ed"
COL_MUTED = "#88888f"
