"""ZPL generation logic independent from GUI and printer backends."""

from __future__ import annotations

from typing import Iterable

from .barcodes import (
    BARCODE_TYPES,
    clamp_barcode_height,
    clamp_qr_magnification,
    is_2d_barcode,
    normalize_barcode_type,
    validate_barcode_payload,
)
from .layout import MARGIN_X, calculate_layout_for_lines, normalize_text_lines

SUPPORTED_FONT_STYLES = {"A0", "A"}
SUPPORTED_ALIGNMENTS = {"left": "L", "center": "C", "right": "R", "justify": "J"}
SUPPORTED_ROTATIONS = {"normal": "N", "90": "R", "180": "I", "270": "B"}


def _clean_text(value: str) -> str:
    """Normalize text for simple ^FD usage."""
    return "".join(ch for ch in str(value) if ch in "\t" or ord(ch) >= 32)


def _clean_lines(lines: Iterable[str]) -> list[str]:
    return [_clean_text(line) for line in lines]


def _alignment_code(alignment: str) -> str:
    return SUPPORTED_ALIGNMENTS.get(str(alignment or "center").strip().lower(), "C")


def _rotation_code(rotation: str) -> str:
    return SUPPORTED_ROTATIONS.get(str(rotation or "normal").strip().lower(), "N")


def _barcode_zpl(
    *,
    barcode_type: str,
    barcode_text: str,
    x: int,
    y: int,
    height: int,
    show_text: bool,
    magnification: int,
) -> list[str]:
    """Return ZPL lines for the selected barcode or 2D symbology."""
    key = normalize_barcode_type(barcode_type)
    text = validate_barcode_payload(key, _clean_text(barcode_text))
    human = "Y" if show_text and BARCODE_TYPES[key].supports_human_readable else "N"

    if key == "code128":
        return [f"^FO{x},{y}", f"^BCN,{height},{human},N,N", f"^FD{text}^FS"]
    if key == "code39":
        return [f"^FO{x},{y}", f"^B3N,N,{height},{human},N", f"^FD{text}^FS"]
    if key == "ean13":
        return [f"^FO{x},{y}", f"^BEN,{height},{human},N", f"^FD{text}^FS"]
    if key == "upca":
        return [f"^FO{x},{y}", f"^BUN,{height},{human},N", f"^FD{text}^FS"]
    if key == "qr":
        return [f"^FO{x},{y}", f"^BQN,2,{magnification}", f"^FDLA,{text}^FS"]
    if key == "datamatrix":
        return [f"^FO{x},{y}", f"^BXN,{magnification},200", f"^FD{text}^FS"]
    if key == "pdf417":
        return [f"^FO{x},{y}", f"^B7N,{height},5,4,8,N", f"^FD{text}^FS"]
    raise ValueError(f"Unsupported barcode type: {barcode_type}")


def generate_zpl(
    line1: str = "",
    line2: str = "",
    width_mm: float = 57,
    height_mm: float = 19,
    font_size: int = 58,
    dpi: int = 300,
    copies: int = 1,
    inverted: bool = False,
    border: bool = False,
    barcode: bool = False,
    barcode_text: str = "",
    barcode_pos: str = "below",
    font_style: str = "A0",
    *,
    lines: Iterable[str] | None = None,
    alignment: str = "center",
    rotation: str = "normal",
    line_gap: int = 10,
    offset_x: int = 0,
    offset_y: int = 0,
    auto_fit: bool = True,
    barcode_type: str = "code128",
    barcode_height: int = 40,
    barcode_show_text: bool = True,
    barcode_magnification: int = 4,
) -> str:
    """Generate ZPL for a simple multi-line text label.

    The legacy line1/line2 arguments are still supported. New callers should pass
    ``lines`` so labels are no longer limited to two text rows.
    """
    text_lines = _clean_lines(normalize_text_lines(lines, line1, line2))
    barcode_type = normalize_barcode_type(barcode_type)
    raw_barcode_text = _clean_text(barcode_text).strip()
    barcode_text = validate_barcode_payload(barcode_type, raw_barcode_text) if barcode and raw_barcode_text else raw_barcode_text
    copies = max(1, int(copies))
    font_style = font_style if font_style in SUPPORTED_FONT_STYLES else "A0"
    align_code = _alignment_code(alignment)
    rot_code = _rotation_code(rotation)
    line_gap = max(0, int(line_gap))
    offset_x = int(offset_x)
    offset_y = int(offset_y)
    barcode_height = clamp_barcode_height(barcode_height, barcode_type)
    barcode_magnification = clamp_qr_magnification(barcode_magnification)
    effective_barcode_height = barcode_height if not is_2d_barcode(barcode_type) else max(barcode_height, barcode_magnification * 18)

    layout = calculate_layout_for_lines(
        text_lines,
        width_mm=width_mm,
        height_mm=height_mm,
        font_size=font_size,
        dpi=dpi,
        barcode=barcode,
        barcode_text=barcode_text,
        barcode_pos=barcode_pos,
        line_gap=line_gap,
        offset_x=offset_x,
        offset_y=offset_y,
        auto_fit=auto_fit,
        barcode_height=effective_barcode_height,
    )

    printable_w = max(1, layout.pw - MARGIN_X * 2 - max(0, abs(offset_x)))
    text_x = max(0, MARGIN_X + offset_x)
    zpl = ["^XA", f"^PW{layout.pw}", f"^LL{layout.ll}", "^LH0,0"]

    if copies > 1:
        zpl.append(f"^PQ{copies},0,1,Y")
    if inverted:
        zpl.append(f"^FO0,0^GB{layout.pw},{layout.ll},{layout.ll}^FS")
    if border:
        zpl.append(f"^FO2,2^GB{layout.pw - 4},{layout.ll - 4},2^FS")

    zpl_text = "\\&".join(text_lines)
    inv_flag = "^FR" if inverted else ""
    zpl += [
        f"^FO{text_x},{layout.pos_y_text}",
        f"^{font_style}{rot_code},{layout.fs},{layout.fs}",
        f"^FB{printable_w},{layout.num_lines},{line_gap},{align_code},0",
        f"{inv_flag}^FD{zpl_text}^FS",
    ]

    if layout.has_bar:
        zpl += _barcode_zpl(
            barcode_type=barcode_type,
            barcode_text=barcode_text,
            x=max(0, MARGIN_X + offset_x),
            y=layout.pos_y_bar,
            height=layout.bar_h,
            show_text=bool(barcode_show_text),
            magnification=barcode_magnification,
        )

    zpl.append("^XZ")
    return "\n".join(zpl)
