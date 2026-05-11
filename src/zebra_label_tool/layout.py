"""Pure layout helpers for ZPL generation and GUI preview."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

LINE_GAP = 10   # default dots between text lines
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
    line_gap: int = LINE_GAP
    offset_x: int = 0
    offset_y: int = 0

    def as_legacy_dict(self) -> dict[str, int | bool]:
        """Return the previous dictionary shape used by the original prototype."""
        data = asdict(self)
        return data


def normalize_text_lines(lines: Iterable[str] | None, line1: str = "", line2: str = "") -> list[str]:
    """Return printable lines while preserving intentionally empty input as one blank line."""
    if lines is None:
        raw = [line1 or ""]
        if str(line2 or "").strip():
            raw.append(line2 or "")
    else:
        raw = [str(line) for line in lines]
    cleaned = [line.rstrip("\r") for line in raw]
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return cleaned or [""]


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


def fit_font_size(
    requested_font_size: int,
    lines: list[str],
    available_height: int,
    line_gap: int,
    *,
    auto_fit: bool = True,
) -> int:
    """Return a readable font size that fits the available vertical area."""
    longest = max(lines, key=len) if lines else ""
    fs = auto_fontsize(requested_font_size, longest) if auto_fit else requested_font_size
    if not auto_fit:
        return fs

    line_count = max(1, len(lines))
    gap_total = max(0, line_gap) * max(0, line_count - 1)
    max_by_height = (available_height - gap_total) // line_count if line_count else fs
    if max_by_height > 0:
        fs = min(fs, max(8, max_by_height))
    return max(8, fs)


def calculate_layout_for_lines(
    lines: Iterable[str],
    width_mm: float,
    height_mm: float,
    font_size: int,
    dpi: int,
    barcode: bool,
    barcode_text: str,
    barcode_pos: str,
    *,
    line_gap: int = LINE_GAP,
    offset_x: int = 0,
    offset_y: int = 0,
    auto_fit: bool = True,
    barcode_height: int = BAR_H,
) -> LabelLayout:
    """Calculate shared positions for multi-line preview and ZPL output."""
    if barcode_pos not in {"above", "below"}:
        raise ValueError("barcode_pos must be 'above' or 'below'")
    if line_gap < 0:
        raise ValueError("line_gap must not be negative")
    barcode_height = max(20, int(barcode_height or BAR_H))

    pw = mm_to_dots(width_mm, dpi)
    ll = mm_to_dots(height_mm, dpi)
    text_lines = normalize_text_lines(lines)

    has_bar = barcode and bool((barcode_text or "").strip())
    reserved_barcode_h = barcode_height + BAR_GAP + 10 if has_bar else 0
    available_h = max(8, ll - reserved_barcode_h - max(0, offset_y))
    fs = fit_font_size(font_size, text_lines, available_h, line_gap, auto_fit=auto_fit)

    num_lines = max(1, len(text_lines))
    block_h = fs * num_lines + (line_gap * (num_lines - 1) if num_lines > 1 else 0)

    if has_bar:
        text_area = max(8, ll - barcode_height - BAR_GAP - 10)
        pos_y_text = max(4, (text_area - block_h) // 2)
        if barcode_pos == "below":
            pos_y_bar = pos_y_text + block_h + BAR_GAP
        else:
            pos_y_bar = max(2, pos_y_text - barcode_height - BAR_GAP)
            pos_y_text = pos_y_bar + barcode_height + BAR_GAP
        pos_y_bar = max(2, min(pos_y_bar, ll - barcode_height - 4))
    else:
        pos_y_text = max(4, (ll - block_h) // 2)
        pos_y_bar = pos_y_text

    pos_y_text = max(0, min(ll - 1, pos_y_text + offset_y))
    pos_y_bar = max(0, min(ll - 1, pos_y_bar + offset_y))

    return LabelLayout(
        pw=pw,
        ll=ll,
        fs=fs,
        num_lines=num_lines,
        block_h=block_h,
        pos_y_text=pos_y_text,
        pos_y_bar=pos_y_bar,
        bar_h=barcode_height,
        has_bar=has_bar,
        margin_x=MARGIN_X,
        line_gap=line_gap,
        offset_x=offset_x,
        offset_y=offset_y,
    )


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
    return calculate_layout_for_lines(
        normalize_text_lines(None, line1, line2),
        width_mm=width_mm,
        height_mm=height_mm,
        font_size=font_size,
        dpi=dpi,
        barcode=barcode,
        barcode_text=barcode_text,
        barcode_pos=barcode_pos,
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
