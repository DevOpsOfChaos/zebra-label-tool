"""Built-in label presets for common Zebra workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LabelPreset:
    """Small named preset that updates label configuration but not the printer."""

    name: str
    description: str
    settings: dict[str, Any]


BUILTIN_PRESETS: tuple[LabelPreset, ...] = (
    LabelPreset(
        name="Device label",
        description="Compact two-line equipment label.",
        settings={
            "width_mm": 57,
            "height_mm": 19,
            "dpi": 300,
            "font_size": 48,
            "line_gap": 8,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": False,
            "text_lines": ["DEVICE", "LOCATION"],
        },
    ),
    LabelPreset(
        name="Asset tag",
        description="Text with Code128 barcode below.",
        settings={
            "width_mm": 57,
            "height_mm": 25,
            "dpi": 300,
            "font_size": 36,
            "line_gap": 6,
            "alignment": "center",
            "rotation": "normal",
            "barcode": True,
            "barcode_type": "code128",
            "barcode_pos": "below",
            "barcode_text": "ASSET-001",
            "barcode_height": 44,
            "border": True,
            "text_lines": ["ASSET-001"],
        },
    ),
    LabelPreset(
        name="Storage bin",
        description="Large readable shelf/bin label.",
        settings={
            "width_mm": 100,
            "height_mm": 50,
            "dpi": 300,
            "font_size": 72,
            "line_gap": 12,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": True,
            "text_lines": ["BIN A-01", "PART NAME"],
        },
    ),

    LabelPreset(
        name="QR device link",
        description="Readable device label with a QR payload below.",
        settings={
            "width_mm": 57,
            "height_mm": 29,
            "dpi": 300,
            "font_size": 32,
            "line_gap": 6,
            "alignment": "center",
            "rotation": "normal",
            "barcode": True,
            "barcode_type": "qr",
            "barcode_pos": "below",
            "barcode_text": "https://example.local/device/1",
            "barcode_height": 90,
            "barcode_magnification": 4,
            "border": False,
            "text_lines": ["DEVICE", "SCAN ME"],
        },
    ),
    LabelPreset(
        name="Cable marker",
        description="Narrow marker with rotated text.",
        settings={
            "width_mm": 57,
            "height_mm": 17,
            "dpi": 300,
            "font_size": 34,
            "line_gap": 4,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": False,
            "text_lines": ["CAB-001"],
        },
    ),
)


BUILTIN_PRESET_NAMES = tuple(preset.name for preset in BUILTIN_PRESETS)


def get_builtin_preset(name: str) -> LabelPreset:
    """Return a built-in preset by name."""
    for preset in BUILTIN_PRESETS:
        if preset.name == name:
            return preset
    raise KeyError(name)


def preset_settings(name: str) -> dict[str, Any]:
    """Return a defensive copy of a preset settings dictionary."""
    return dict(get_builtin_preset(name).settings)
