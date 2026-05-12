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
    "language": None,
    "printer": "",
    "dpi": 300,
    "width_mm": 57,
    "height_mm": 19,
    "font_size": 58,
    "copies": 1,
    "inverted": False,
    "border": False,
    "barcode": False,
    "barcode_type": "code128",
    "barcode_pos": "below",
    "barcode_height": 40,
    "barcode_show_text": True,
    "barcode_magnification": 4,
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

COL_BG = "#edf1f5"
COL_PANEL = "#f8fafc"
COL_CARD = "#ffffff"
COL_CARD_ALT = "#eef3f8"
COL_BORDER = "#cbd5e1"
COL_ACCENT = "#2563eb"
COL_ACCENT_DARK = "#1e40af"
COL_SUCCESS = "#15803d"
COL_WARN = "#b45309"
COL_ERR = "#dc2626"
COL_TEXT = "#111827"
COL_MUTED = "#64748b"
COL_SOFT = "#e2e8f0"
COL_BUTTON = "#dbeafe"
COL_BUTTON_HOVER = "#bfdbfe"
COL_BUTTON_BORDER = "#60a5fa"
COL_BUTTON_TEXT = COL_TEXT
COL_DANGER_BUTTON = "#ef4444"
COL_DANGER_HOVER = "#b91c1c"
