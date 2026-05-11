"""ZPL generation logic independent from GUI and printer backends."""

from __future__ import annotations

from .layout import MARGIN_X, calculate_layout

SUPPORTED_FONT_STYLES = {"A0", "A"}


def _clean_text(value: str) -> str:
    """Normalize text for simple ^FD usage.

    The tool intentionally stays small and opinionated. It strips control
    characters that would make generated labels unpredictable while preserving
    ordinary visible text.
    """
    return "".join(ch for ch in str(value) if ch in "\t" or ord(ch) >= 32)


def generate_zpl(
    line1: str,
    line2: str,
    width_mm: float,
    height_mm: float,
    font_size: int,
    dpi: int = 300,
    copies: int = 1,
    inverted: bool = False,
    border: bool = False,
    barcode: bool = False,
    barcode_text: str = "",
    barcode_pos: str = "below",
    font_style: str = "A0",
) -> str:
    """Generate ZPL for a simple one- or two-line label."""
    line1 = _clean_text(line1)
    line2 = _clean_text(line2)
    barcode_text = _clean_text(barcode_text).strip()
    copies = max(1, int(copies))
    font_style = font_style if font_style in SUPPORTED_FONT_STYLES else "A0"

    layout = calculate_layout(
        line1=line1,
        line2=line2,
        width_mm=width_mm,
        height_mm=height_mm,
        font_size=font_size,
        dpi=dpi,
        barcode=barcode,
        barcode_text=barcode_text,
        barcode_pos=barcode_pos,
    )

    printable_w = layout.pw - MARGIN_X * 2
    zpl = ["^XA", f"^PW{layout.pw}", f"^LL{layout.ll}", "^LH0,0"]

    if copies > 1:
        zpl.append(f"^PQ{copies},0,1,Y")
    if inverted:
        zpl.append(f"^FO0,0^GB{layout.pw},{layout.ll},{layout.ll}^FS")
    if border:
        zpl.append(f"^FO2,2^GB{layout.pw - 4},{layout.ll - 4},2^FS")

    zpl_text = f"{line1}\\&{line2}" if line2.strip() else line1
    inv_flag = "^FR" if inverted else ""
    zpl += [
        f"^FO{MARGIN_X},{layout.pos_y_text}",
        f"^{font_style}N,{layout.fs},{layout.fs}",
        f"^FB{printable_w},{layout.num_lines},2,C,0",
        f"{inv_flag}^FD{zpl_text}^FS",
    ]

    if layout.has_bar:
        zpl += [
            f"^FO{MARGIN_X},{layout.pos_y_bar}",
            f"^BCN,{layout.bar_h},Y,N,N",
            f"^FD{barcode_text}^FS",
        ]

    zpl.append("^XZ")
    return "\n".join(zpl)
