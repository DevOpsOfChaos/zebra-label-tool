"""Pure layout helpers for ZPL generation and GUI preview."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

LINE_GAP = 10   # default dots between text lines
MARGIN_X = 20   # side margin in dots
BAR_H = 40      # barcode height / reserved code area in dots
BAR_GAP = 14    # gap between text and barcode in dots
SUPPORTED_BARCODE_POSITIONS = {"above", "below", "left", "right"}


@dataclass(frozen=True)
class LabelLayout:
    """Calculated label layout in printer dots.

    ``text_x``/``text_w`` and ``bar_x``/``bar_w`` are the newer area-based
    fields. The older ``pos_y_text``/``pos_y_bar`` names are kept for tests and
    compatibility with the original prototype.
    """

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
    text_x: int = MARGIN_X
    text_w: int = 1
    bar_x: int = MARGIN_X
    bar_w: int = 1
    barcode_pos: str = "below"

    def as_legacy_dict(self) -> dict[str, int | bool | str]:
        """Return the previous dictionary shape plus newer area fields."""
        return asdict(self)


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


def _clamp_area_size(value: int, limit: int) -> int:
    return max(24, min(max(24, value), max(24, limit)))


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
    """Calculate shared positions for multi-line preview and ZPL output.

    Barcode positions ``left`` and ``right`` reserve a vertical code area on one
    side and place the text in the remaining area. The existing
    ``barcode_height`` setting doubles as reserved code width for side layouts;
    that keeps the UI compact while still giving users real layout control.
    """
    barcode_pos = str(barcode_pos or "below").strip().split()[0].lower()
    if barcode_pos not in SUPPORTED_BARCODE_POSITIONS:
        raise ValueError("barcode_pos must be 'above', 'below', 'left', or 'right'")
    if line_gap < 0:
        raise ValueError("line_gap must not be negative")
    barcode_height = max(20, int(barcode_height or BAR_H))

    pw = mm_to_dots(width_mm, dpi)
    ll = mm_to_dots(height_mm, dpi)
    text_lines = normalize_text_lines(lines)
    has_bar = barcode and bool((barcode_text or "").strip())

    base_text_x = max(0, min(pw - 1, MARGIN_X + int(offset_x)))
    base_text_w = max(1, pw - MARGIN_X * 2 - max(0, abs(int(offset_x))))
    bar_x = base_text_x
    bar_w = base_text_w
    effective_bar_h = barcode_height

    if has_bar and barcode_pos in {"left", "right"}:
        max_code_w = max(24, pw - MARGIN_X * 2 - BAR_GAP - 40)
        bar_w = _clamp_area_size(barcode_height, max_code_w)
        effective_bar_h = max(20, min(ll - 8, barcode_height))
        if barcode_pos == "left":
            bar_x = MARGIN_X
            text_x = min(pw - 1, bar_x + bar_w + BAR_GAP + int(offset_x))
            text_w = max(1, pw - MARGIN_X - text_x)
        else:
            bar_x = max(MARGIN_X, pw - MARGIN_X - bar_w)
            text_x = max(0, MARGIN_X + int(offset_x))
            text_w = max(1, bar_x - BAR_GAP - text_x)
        available_h = max(8, ll - max(0, int(offset_y)) - 8)
        fs = fit_font_size(font_size, text_lines, available_h, line_gap, auto_fit=auto_fit)
        num_lines = max(1, len(text_lines))
        block_h = fs * num_lines + (line_gap * (num_lines - 1) if num_lines > 1 else 0)
        pos_y_text = max(4, (ll - block_h) // 2 + int(offset_y))
        pos_y_bar = max(4, (ll - effective_bar_h) // 2 + int(offset_y))
        pos_y_text = max(0, min(ll - 1, pos_y_text))
        pos_y_bar = max(0, min(ll - 1, pos_y_bar))
        return LabelLayout(
            pw=pw,
            ll=ll,
            fs=fs,
            num_lines=num_lines,
            block_h=block_h,
            pos_y_text=pos_y_text,
            pos_y_bar=pos_y_bar,
            bar_h=effective_bar_h,
            has_bar=has_bar,
            margin_x=MARGIN_X,
            line_gap=line_gap,
            offset_x=offset_x,
            offset_y=offset_y,
            text_x=text_x,
            text_w=text_w,
            bar_x=bar_x,
            bar_w=bar_w,
            barcode_pos=barcode_pos,
        )

    reserved_barcode_h = barcode_height + BAR_GAP + 10 if has_bar else 0
    available_h = max(8, ll - reserved_barcode_h - max(0, int(offset_y)))
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

    pos_y_text = max(0, min(ll - 1, pos_y_text + int(offset_y)))
    pos_y_bar = max(0, min(ll - 1, pos_y_bar + int(offset_y)))

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
        text_x=base_text_x,
        text_w=base_text_w,
        bar_x=base_text_x,
        bar_w=base_text_w,
        barcode_pos=barcode_pos,
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
) -> dict[str, int | bool | str]:
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
