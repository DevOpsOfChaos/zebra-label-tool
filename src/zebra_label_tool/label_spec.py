"""Validated label request model shared by GUI and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .barcodes import BARCODE_TYPES, clamp_barcode_height, clamp_qr_magnification, normalize_barcode_type, validate_barcode_payload
from .layout import LINE_GAP, normalize_text_lines
from .zpl import SUPPORTED_ALIGNMENTS, SUPPORTED_FONT_STYLES, SUPPORTED_ROTATIONS, generate_zpl

SUPPORTED_DPI = (203, 300, 600)
SUPPORTED_BARCODE_POSITIONS = ("above", "below", "left", "right")
MAX_TEXT_LINES = 12


class LabelSpecError(ValueError):
    """Raised when label input cannot be converted into a valid label request."""


def _parse_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise LabelSpecError(f"{field_name} must be a number") from exc
    if parsed <= 0:
        raise LabelSpecError(f"{field_name} must be greater than zero")
    return parsed


def _parse_int(value: Any, field_name: str, minimum: int = 1) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise LabelSpecError(f"{field_name} must be a whole number") from exc
    if parsed < minimum:
        raise LabelSpecError(f"{field_name} must be at least {minimum}")
    return parsed


def _parse_signed_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise LabelSpecError(f"{field_name} must be a whole number") from exc


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _parse_lines(lines: Iterable[Any] | None, line1: Any, line2: Any) -> tuple[str, ...]:
    if lines is None:
        parsed = normalize_text_lines(None, str(line1 or ""), str(line2 or ""))
    else:
        parsed = normalize_text_lines(str(line) for line in lines)
    parsed = [line.rstrip() for line in parsed]
    if len(parsed) > MAX_TEXT_LINES:
        raise LabelSpecError(f"Text can contain at most {MAX_TEXT_LINES} lines")
    return tuple(parsed)


@dataclass(frozen=True)
class LabelSpec:
    """Complete, validated input for one label generation request."""

    text_lines: tuple[str, ...] = field(default_factory=lambda: ("",))
    width_mm: float = 57
    height_mm: float = 19
    font_size: int = 58
    dpi: int = 300
    copies: int = 1
    inverted: bool = False
    border: bool = False
    barcode: bool = False
    barcode_text: str = ""
    barcode_type: str = "code128"
    barcode_pos: str = "below"
    barcode_height: int = 40
    barcode_show_text: bool = True
    barcode_magnification: int = 4
    font_style: str = "A0"
    alignment: str = "center"
    rotation: str = "normal"
    line_gap: int = LINE_GAP
    offset_x: int = 0
    offset_y: int = 0
    auto_fit: bool = True

    @classmethod
    def from_raw(
        cls,
        *,
        line1: Any = "",
        line2: Any = "",
        lines: Iterable[Any] | None = None,
        width_mm: Any = 57,
        height_mm: Any = 19,
        font_size: Any = 58,
        dpi: Any = 300,
        copies: Any = 1,
        inverted: bool = False,
        border: bool = False,
        barcode: bool = False,
        barcode_text: Any = "",
        barcode_type: str = "code128",
        barcode_pos: str = "below",
        barcode_height: Any = 40,
        barcode_show_text: Any = True,
        barcode_magnification: Any = 4,
        font_style: str = "A0",
        alignment: str = "center",
        rotation: str = "normal",
        line_gap: Any = LINE_GAP,
        offset_x: Any = 0,
        offset_y: Any = 0,
        auto_fit: Any = True,
    ) -> "LabelSpec":
        parsed_dpi = _parse_int(dpi, "DPI", minimum=1)
        if parsed_dpi not in SUPPORTED_DPI:
            raise LabelSpecError(f"DPI must be one of {', '.join(str(v) for v in SUPPORTED_DPI)}")

        parsed_barcode_pos = str(barcode_pos or "below").strip().split()[0].lower()
        if parsed_barcode_pos not in SUPPORTED_BARCODE_POSITIONS:
            raise LabelSpecError("Barcode position must be above, below, left, or right")

        parsed_barcode_enabled = _parse_bool(barcode)
        raw_barcode_text = str(barcode_text or "")
        try:
            parsed_barcode_type = normalize_barcode_type(barcode_type)
            parsed_barcode_text = validate_barcode_payload(parsed_barcode_type, raw_barcode_text) if parsed_barcode_enabled and raw_barcode_text.strip() else raw_barcode_text
        except ValueError as exc:
            raise LabelSpecError(str(exc)) from exc
        parsed_barcode_height = clamp_barcode_height(barcode_height, parsed_barcode_type)
        parsed_barcode_magnification = clamp_qr_magnification(barcode_magnification)

        parsed_font_style = str(font_style or "A0").strip().split()[0]
        if parsed_font_style not in SUPPORTED_FONT_STYLES:
            parsed_font_style = "A0"

        parsed_alignment = str(alignment or "center").strip().split()[0].lower()
        if parsed_alignment not in SUPPORTED_ALIGNMENTS:
            raise LabelSpecError("Text alignment must be left, center, right, or justify")

        parsed_rotation = str(rotation or "normal").strip().split()[0].lower()
        if parsed_rotation not in SUPPORTED_ROTATIONS:
            raise LabelSpecError("Text rotation must be normal, 90, 180, or 270")

        parsed_line_gap = _parse_int(line_gap, "Line gap", minimum=0)

        return cls(
            text_lines=_parse_lines(lines, line1, line2),
            width_mm=_parse_float(width_mm, "Width"),
            height_mm=_parse_float(height_mm, "Height"),
            font_size=_parse_int(font_size, "Font size", minimum=1),
            dpi=parsed_dpi,
            copies=_parse_int(copies, "Copies", minimum=1),
            inverted=_parse_bool(inverted),
            border=_parse_bool(border),
            barcode=parsed_barcode_enabled,
            barcode_text=parsed_barcode_text,
            barcode_type=parsed_barcode_type,
            barcode_pos=parsed_barcode_pos,
            barcode_height=parsed_barcode_height,
            barcode_show_text=_parse_bool(barcode_show_text),
            barcode_magnification=parsed_barcode_magnification,
            font_style=parsed_font_style,
            alignment=parsed_alignment,
            rotation=parsed_rotation,
            line_gap=parsed_line_gap,
            offset_x=_parse_signed_int(offset_x, "Horizontal offset"),
            offset_y=_parse_signed_int(offset_y, "Vertical offset"),
            auto_fit=_parse_bool(auto_fit),
        )

    @property
    def line1(self) -> str:
        return self.text_lines[0] if self.text_lines else ""

    @property
    def line2(self) -> str:
        return self.text_lines[1] if len(self.text_lines) > 1 else ""

    @property
    def has_text(self) -> bool:
        return any(line.strip() for line in self.text_lines)

    @property
    def active_barcode(self) -> bool:
        return self.barcode and bool(self.barcode_text.strip())

    def to_zpl(self) -> str:
        return generate_zpl(
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            font_size=self.font_size,
            dpi=self.dpi,
            copies=self.copies,
            inverted=self.inverted,
            border=self.border,
            barcode=self.barcode,
            barcode_text=self.barcode_text,
            barcode_type=self.barcode_type,
            barcode_pos=self.barcode_pos,
            barcode_height=self.barcode_height,
            barcode_show_text=self.barcode_show_text,
            barcode_magnification=self.barcode_magnification,
            font_style=self.font_style,
            lines=self.text_lines,
            alignment=self.alignment,
            rotation=self.rotation,
            line_gap=self.line_gap,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            auto_fit=self.auto_fit,
        )

    def history_label(self) -> str:
        visible = [line.strip() for line in self.text_lines if line.strip()]
        return "  |  ".join(visible[:3]) + (" ..." if len(visible) > 3 else "")
