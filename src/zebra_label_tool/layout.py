"""Pure layout helpers for ZPL generation and GUI preview."""

from __future__ import annotations

from dataclasses import asdict, dataclass

LINE_GAP = 10   # dots between line 1 and line 2
MARGIN_X = 20   # side margin in dots
BAR_H = 40      # barcode height in dots
BAR_GAP = 14    # gap between text and barcode in dots


@dataclass(frozen=True)
class LabelLayout:
    """Calculated label layout in printer dots."""

    pw: int
    ll: int
    fs: int
    num_lines: int
    block_h: int
    pos_y_text: int
    pos_y_bar: int
    bar_h: int
    has_bar: bool
    margin_x: int

    def as_legacy_dict(self) -> dict[str, int | bool]:
        """Return the previous dictionary shape used by the original prototype."""
        return asdict(self)


def mm_to_dots(mm: float, dpi: int) -> int:
    """Convert millimetres to printer dots for the selected DPI."""
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")
    if mm <= 0:
        raise ValueError("label dimensions must be greater than zero")
    return int(round(mm * dpi / 25.4))


def auto_fontsize(font_size: int, text: str, max_chars: int = 28) -> int:
    """Shrink long text so it remains usable on small labels."""
    if font_size <= 0:
        raise ValueError("font_size must be greater than zero")
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    if len(text) > max_chars:
        return max(10, int(font_size * max_chars / len(text)))
    return font_size


def calculate_layout(
    line1: str,
    line2: str,
    width_mm: float,
    height_mm: float,
    font_size: int,
    dpi: int,
    barcode: bool,
    barcode_text: str,
    barcode_pos: str,
) -> LabelLayout:
    """Calculate shared positions for preview and ZPL output."""
    if barcode_pos not in {"above", "below"}:
        raise ValueError("barcode_pos must be 'above' or 'below'")

    pw = mm_to_dots(width_mm, dpi)
    ll = mm_to_dots(height_mm, dpi)

    line1 = line1 or ""
    line2 = line2 or ""
    barcode_text = barcode_text or ""

    longest = max(line1, line2, key=len) if line2.strip() else line1
    fs = auto_fontsize(font_size, longest)

    num_lines = 2 if line2.strip() else 1
    block_h = fs * num_lines + (LINE_GAP if num_lines > 1 else 0)

    has_bar = barcode and bool(barcode_text.strip())
    if has_bar:
        text_area = ll - BAR_H - BAR_GAP - 10
        pos_y_text = max(4, (text_area - block_h) // 2)
        if barcode_pos == "below":
            pos_y_bar = pos_y_text + block_h + BAR_GAP
        else:
            pos_y_bar = max(2, pos_y_text - BAR_H - BAR_GAP)
            pos_y_text = pos_y_bar + BAR_H + BAR_GAP
        pos_y_bar = max(2, min(pos_y_bar, ll - BAR_H - 4))
    else:
        pos_y_text = max(4, (ll - block_h) // 2)
        pos_y_bar = pos_y_text

    return LabelLayout(
        pw=pw,
        ll=ll,
        fs=fs,
        num_lines=num_lines,
        block_h=block_h,
        pos_y_text=pos_y_text,
        pos_y_bar=pos_y_bar,
        bar_h=BAR_H,
        has_bar=has_bar,
        margin_x=MARGIN_X,
    )


def calc_positions(
    line1: str,
    line2: str,
    width_mm: float,
    height_mm: float,
    font_size: int,
    dpi: int,
    barcode: bool,
    barcode_text: str,
    barcode_pos: str,
) -> dict[str, int | bool]:
    """Backward-compatible wrapper returning the original dict shape."""
    return calculate_layout(
        line1,
        line2,
        width_mm,
        height_mm,
        font_size,
        dpi,
        barcode,
        barcode_text,
        barcode_pos,
    ).as_legacy_dict()
