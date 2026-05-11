"""Built-in label presets for common Zebra workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PresetField:
    """User-fillable value used by a built-in preset."""

    key: str
    label: str
    default: str = ""
    help_text: str = ""


@dataclass(frozen=True)
class LabelPreset:
    """Small named preset that updates label configuration but not the printer."""

    name: str
    description: str
    settings: dict[str, Any]
    fields: tuple[PresetField, ...] = ()

    @property
    def needs_input(self) -> bool:
        return bool(self.fields)


BUILTIN_PRESETS: tuple[LabelPreset, ...] = (
    LabelPreset(
        name="Device label",
        description="Compact equipment label with device and location fields.",
        fields=(
            PresetField("device", "Device name", "ESP32 Kitchen"),
            PresetField("location", "Location", "Kitchen"),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 19,
            "dpi": 300,
            "font_size": 42,
            "line_gap": 7,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": False,
            "text_lines": ["{device}", "{location}"],
        },
    ),
    LabelPreset(
        name="Asset tag",
        description="Asset ID text with a Code 128 barcode below.",
        fields=(
            PresetField("asset_id", "Asset ID", "ASSET-001", "This value is also used as the barcode payload."),
            PresetField("location", "Location / owner", "Rack A"),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 25,
            "dpi": 300,
            "font_size": 34,
            "line_gap": 5,
            "alignment": "center",
            "rotation": "normal",
            "barcode": True,
            "barcode_type": "code128",
            "barcode_pos": "below",
            "barcode_text": "{asset_id}",
            "barcode_height": 50,
            "barcode_show_text": True,
            "border": True,
            "text_lines": ["{asset_id}", "{location}"],
        },
    ),
    LabelPreset(
        name="Storage bin",
        description="Large readable shelf/bin label.",
        fields=(
            PresetField("bin_id", "Bin / shelf ID", "BIN A-01"),
            PresetField("item", "Item description", "PART NAME"),
        ),
        settings={
            "width_mm": 100,
            "height_mm": 50,
            "dpi": 300,
            "font_size": 68,
            "line_gap": 10,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": True,
            "text_lines": ["{bin_id}", "{item}"],
        },
    ),
    LabelPreset(
        name="QR device link",
        description="Readable device label with a QR payload below.",
        fields=(
            PresetField("device", "Device name", "ESP32 Kitchen"),
            PresetField("url", "QR URL / payload", "https://example.local/device/esp32-kitchen"),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 32,
            "dpi": 300,
            "font_size": 30,
            "line_gap": 5,
            "alignment": "center",
            "rotation": "normal",
            "barcode": True,
            "barcode_type": "qr",
            "barcode_pos": "below",
            "barcode_text": "{url}",
            "barcode_height": 105,
            "barcode_magnification": 4,
            "border": False,
            "text_lines": ["{device}", "Scan for details"],
        },
    ),
    LabelPreset(
        name="Wi-Fi QR label",
        description="QR code containing a Wi-Fi network payload.",
        fields=(
            PresetField("ssid", "Wi-Fi SSID", "Workshop-WiFi"),
            PresetField("security", "Security", "WPA", "Use WPA, WEP, or nopass."),
            PresetField("password", "Password", "change-me"),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 35,
            "dpi": 300,
            "font_size": 30,
            "line_gap": 5,
            "alignment": "center",
            "barcode": True,
            "barcode_type": "qr",
            "barcode_pos": "below",
            "barcode_text": "WIFI:S:{ssid};T:{security};P:{password};;",
            "barcode_height": 110,
            "barcode_magnification": 4,
            "border": True,
            "text_lines": ["Wi-Fi", "{ssid}"],
        },
    ),
    LabelPreset(
        name="Part number",
        description="Part number label using Code 39 for older industrial workflows.",
        fields=(
            PresetField("part_no", "Part number", "PN-10042"),
            PresetField("revision", "Revision / batch", "REV A"),
        ),
        settings={
            "width_mm": 62,
            "height_mm": 29,
            "dpi": 300,
            "font_size": 34,
            "line_gap": 5,
            "alignment": "center",
            "barcode": True,
            "barcode_type": "code39",
            "barcode_pos": "below",
            "barcode_text": "{part_no}",
            "barcode_height": 50,
            "barcode_show_text": True,
            "border": True,
            "text_lines": ["{part_no}", "{revision}"],
        },
    ),
    LabelPreset(
        name="Retail EAN-13",
        description="Retail label with EAN-13 barcode. Enter 12 digits to auto-preview the check digit.",
        fields=(
            PresetField("title", "Product title", "Product"),
            PresetField("ean", "EAN-13 / GTIN", "4006381333931", "12 or 13 digits."),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 32,
            "dpi": 300,
            "font_size": 28,
            "line_gap": 5,
            "alignment": "center",
            "barcode": True,
            "barcode_type": "ean13",
            "barcode_pos": "below",
            "barcode_text": "{ean}",
            "barcode_height": 70,
            "barcode_show_text": True,
            "border": False,
            "text_lines": ["{title}"],
        },
    ),
    LabelPreset(
        name="Cable marker",
        description="Narrow marker for cable IDs.",
        fields=(
            PresetField("cable_id", "Cable ID", "CAB-001"),
            PresetField("route", "Route / target", "PLC -> Sensor"),
        ),
        settings={
            "width_mm": 57,
            "height_mm": 17,
            "dpi": 300,
            "font_size": 30,
            "line_gap": 4,
            "alignment": "center",
            "rotation": "normal",
            "barcode": False,
            "border": False,
            "text_lines": ["{cable_id}", "{route}"],
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


def _render_value(value: Any, field_values: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        rendered = value
        for key, replacement in field_values.items():
            rendered = rendered.replace("{" + key + "}", str(replacement))
        return rendered
    if isinstance(value, list):
        return [_render_value(item, field_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_render_value(item, field_values) for item in value)
    if isinstance(value, dict):
        return {key: _render_value(item, field_values) for key, item in value.items()}
    return value


def render_preset_settings(name: str, field_values: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return a preset settings dictionary with placeholders replaced."""
    preset = get_builtin_preset(name)
    values = {field.key: field.default for field in preset.fields}
    values.update({key: str(value) for key, value in (field_values or {}).items()})
    return {key: _render_value(value, values) for key, value in preset.settings.items()}


def preset_settings(name: str) -> dict[str, Any]:
    """Return a defensive copy of a preset settings dictionary using default fields."""
    return render_preset_settings(name)
