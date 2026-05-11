"""Validated label request model shared by GUI and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .zpl import SUPPORTED_FONT_STYLES, generate_zpl

SUPPORTED_DPI = (203, 300, 600)
SUPPORTED_BARCODE_POSITIONS = ("above", "below")


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


@dataclass(frozen=True)
class LabelSpec:
    """Complete, validated input for one label generation request."""

    line1: str = ""
    line2: str = ""
    width_mm: float = 57
    height_mm: float = 19
    font_size: int = 58
    dpi: int = 300
    copies: int = 1
    inverted: bool = False
    border: bool = False
    barcode: bool = False
    barcode_text: str = ""
    barcode_pos: str = "below"
    font_style: str = "A0"

    @classmethod
    def from_raw(
        cls,
        *,
        line1: Any = "",
        line2: Any = "",
        width_mm: Any = 57,
        height_mm: Any = 19,
        font_size: Any = 58,
        dpi: Any = 300,
        copies: Any = 1,
        inverted: bool = False,
        border: bool = False,
        barcode: bool = False,
        barcode_text: Any = "",
        barcode_pos: str = "below",
        font_style: str = "A0",
    ) -> "LabelSpec":
        parsed_dpi = _parse_int(dpi, "DPI", minimum=1)
        if parsed_dpi not in SUPPORTED_DPI:
            raise LabelSpecError(f"DPI must be one of {', '.join(str(v) for v in SUPPORTED_DPI)}")

        parsed_barcode_pos = str(barcode_pos or "below").strip().split()[0].lower()
        if parsed_barcode_pos not in SUPPORTED_BARCODE_POSITIONS:
            raise LabelSpecError("Barcode position must be above or below")

        parsed_font_style = str(font_style or "A0").strip().split()[0]
        if parsed_font_style not in SUPPORTED_FONT_STYLES:
            parsed_font_style = "A0"

        return cls(
            line1=str(line1 or ""),
            line2=str(line2 or ""),
            width_mm=_parse_float(width_mm, "Width"),
            height_mm=_parse_float(height_mm, "Height"),
            font_size=_parse_int(font_size, "Font size", minimum=1),
            dpi=parsed_dpi,
            copies=_parse_int(copies, "Copies", minimum=1),
            inverted=bool(inverted),
            border=bool(border),
            barcode=bool(barcode),
            barcode_text=str(barcode_text or ""),
            barcode_pos=parsed_barcode_pos,
            font_style=parsed_font_style,
        )

    @property
    def has_text(self) -> bool:
        return bool(self.line1.strip() or self.line2.strip())

    @property
    def active_barcode(self) -> bool:
        return self.barcode and bool(self.barcode_text.strip())

    def to_zpl(self) -> str:
        return generate_zpl(
            line1=self.line1,
            line2=self.line2,
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            font_size=self.font_size,
            dpi=self.dpi,
            copies=self.copies,
            inverted=self.inverted,
            border=self.border,
            barcode=self.barcode,
            barcode_text=self.barcode_text,
            barcode_pos=self.barcode_pos,
            font_style=self.font_style,
        )

    def history_label(self) -> str:
        line1 = self.line1.strip()
        line2 = self.line2.strip()
        return line1 + (f"  |  {line2}" if line2 else "")
