"""ZPL to PIL.Image rendering pipeline.

Provides three tiers of rendering:
1. Labelary API (online, uses actual Zebra firmware — perfect rendering)
2. Pillow direct rendering (local, no internet — ~95% accuracy)
"""

from __future__ import annotations

import io
import logging
import os
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from .barcodes import BARCODE_TYPES, is_2d_barcode, normalize_barcode_type
from .preview_symbols import encode_linear_symbol, encode_matrix_symbol

if TYPE_CHECKING:
    from .layout import LabelLayout

logger = logging.getLogger(__name__)

LABELARY_BASE_URL = "http://api.labelary.com/v1/print"
_REQUEST_TIMEOUT = 15  # seconds for Labelary API calls


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_zpl_preview(
    zpl: str,
    *,
    layout: LabelLayout,
    width_mm: float,
    height_mm: float,
    dpi: int,
    text_lines: tuple[str, ...] = (),
    inverted: bool = False,
    border: bool = False,
    alignment: str = "center",
    barcode_type: str = "code128",
    barcode_text: str = "",
    barcode_show_text: bool = True,
    barcode_magnification: int = 4,
    font_size: int = 58,
    line_gap: int = 10,
) -> tuple[Image.Image, str]:
    """Render a label preview — tries Labelary first, falls back to Pillow.

    Returns
    -------
    (image, method)
        ``method`` is ``"labelary"`` or ``"pillow"`` so callers can show an
        indicator of which renderer was used.

    The *layout* and *text_lines* arguments are required for the Pillow
    fallback.  Everything else is forwarded to whichever renderer is active.
    """
    # 1) Try Labelary — perfect, but needs internet
    img = _render_via_labelary(zpl, width_mm, height_mm, dpi)
    if img is not None:
        return img, "labelary"

    # 2) Pillow fallback — local, fast, good approximation
    img = _render_via_pillow(
        layout=layout,
        text_lines=text_lines,
        width_mm=width_mm,
        height_mm=height_mm,
        dpi=dpi,
        inverted=inverted,
        border=border,
        alignment=alignment,
        barcode_type=barcode_type,
        barcode_text=barcode_text,
        barcode_show_text=barcode_show_text,
        barcode_magnification=barcode_magnification,
        font_size=font_size,
        line_gap=line_gap,
    )
    if img is not None:
        return img, "pillow"

    # 3) Absolute emergency — 1x1 transparent pixel
    logger.error("Both Labelary and Pillow renderers failed")
    return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), "error"


# ---------------------------------------------------------------------------
# Tier 1 — Labelary API
# ---------------------------------------------------------------------------

def _render_via_labelary(
    zpl: str,
    width_mm: float,
    height_mm: float,
    dpi: int,
) -> Image.Image | None:
    """POST the ZPL to Labelary and return the rendered PNG, or *None*."""
    url = f"{LABELARY_BASE_URL}/{dpi}/label/{width_mm}mmx{height_mm}mm/1/"
    data = zpl.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            png_bytes = resp.read()
        return Image.open(io.BytesIO(png_bytes)).convert("RGB")
    except urllib.error.URLError as exc:
        logger.info("Labelary API unreachable: %s", exc)
    except OSError as exc:
        logger.warning("Labelary returned invalid image data: %s", exc)
    except Exception as exc:
        logger.warning("Labelary rendering failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Tier 2 — Pillow local rendering
# ---------------------------------------------------------------------------

def _render_via_pillow(
    *,
    layout: LabelLayout,
    text_lines: tuple[str, ...],
    width_mm: float,
    height_mm: float,
    dpi: int,
    inverted: bool = False,
    border: bool = False,
    alignment: str = "center",
    barcode_type: str = "code128",
    barcode_text: str = "",
    barcode_show_text: bool = True,
    barcode_magnification: int = 4,
    font_size: int = 58,
    line_gap: int = 10,
) -> Image.Image | None:
    """Render the label from layout data using Pillow (no internet needed)."""
    try:
        return _pillow_render(
            layout=layout,
            text_lines=text_lines,
            dpi=dpi,
            inverted=inverted,
            border=border,
            alignment=alignment,
            barcode_type=barcode_type,
            barcode_text=barcode_text,
            barcode_show_text=barcode_show_text,
            barcode_magnification=barcode_magnification,
            font_size=font_size,
            line_gap=line_gap,
        )
    except Exception as exc:
        logger.exception("Pillow renderer failed: %s", exc)
        return None


def _pillow_render(
    *,
    layout: LabelLayout,
    text_lines: tuple[str, ...],
    dpi: int,
    inverted: bool,
    border: bool,
    alignment: str,
    barcode_type: str,
    barcode_text: str,
    barcode_show_text: bool,
    barcode_magnification: int,
    font_size: int,
    line_gap: int,
) -> Image.Image:
    """Internal Pillow drawing routine — raises on error."""
    pw = max(1, layout.pw)
    ll = max(1, layout.ll)

    # Render at 2x for crisp on-screen display
    render_scale = 2.0
    iw = int(pw * render_scale)
    ih = int(ll * render_scale)

    bg = (0, 0, 0) if inverted else (255, 255, 255)
    fg = (255, 255, 255) if inverted else (0, 0, 0)

    img = Image.new("RGB", (iw, ih), bg)
    draw = ImageDraw.Draw(img)

    # --- font ---------------------------------------------------------------
    font_pt = font_size * 72.0 / dpi * render_scale
    font = _get_monospace_font(max(1, round(font_pt)))

    # --- text area ----------------------------------------------------------
    text_x_dot = layout.text_x
    text_w_dot = layout.text_w
    fs_dot = layout.fs

    for idx, line in enumerate(text_lines):
        if not line.strip():
            continue
        y_dot = layout.pos_y_text + idx * (fs_dot + line_gap)
        x_px = int(text_x_dot * render_scale)
        y_px = int(y_dot * render_scale)

        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        avail_w = int(text_w_dot * render_scale)

        display_text = line
        while line_w > avail_w and len(display_text) > 1:
            display_text = display_text[:-1]
            bbox = draw.textbbox((0, 0), display_text + "\u2026", font=font)
            line_w = bbox[2] - bbox[0]
        if display_text != line:
            display_text += "\u2026"

        if alignment == "left":
            tx = x_px
        elif alignment == "right":
            tx = x_px + avail_w - line_w
        else:  # center
            tx = x_px + (avail_w - line_w) // 2

        draw.text((max(0, tx), max(0, y_px)), display_text, fill=fg, font=font)

    # --- barcode / 2D code --------------------------------------------------
    if layout.has_bar and barcode_text.strip():
        bx_dot = layout.bar_x
        by_dot = layout.pos_y_bar
        bw_dot = layout.bar_w
        bh_dot = layout.bar_h

        bx_px = int(bx_dot * render_scale)
        by_px = int(by_dot * render_scale)
        bw_px = int(bw_dot * render_scale)
        bh_px = int(bh_dot * render_scale)

        bar_color = fg
        barcode_type_key = normalize_barcode_type(barcode_type)

        if is_2d_barcode(barcode_type_key):
            _draw_2d_symbol(
                draw, bx_px, by_px, bw_px, bh_px,
                bar_color, barcode_text, render_scale,
                barcode_type_key, barcode_magnification,
            )
        else:
            _draw_linear_barcode(
                draw, bx_px, by_px, bw_px, bh_px,
                bar_color, barcode_text, render_scale,
                barcode_type_key, barcode_show_text,
            )

    # --- border -------------------------------------------------------------
    if border:
        pad = max(1, int(2 * render_scale))
        draw.rectangle(
            [pad, pad, iw - pad, ih - pad],
            outline=fg,
            width=max(1, int(2 * render_scale)),
        )

    return img


# ---------------------------------------------------------------------------
# Barcode drawing helpers
# ---------------------------------------------------------------------------

def _draw_linear_barcode(
    draw: ImageDraw.Draw,
    x: int, y: int, width: int, height: int,
    color, text: str, scale: float,
    barcode_type: str, show_text: bool,
) -> None:
    """Draw a linear (1D) barcode using the same encoders as the old preview."""
    try:
        symbol = encode_linear_symbol(barcode_type, text)
    except Exception as exc:
        draw.text((x + 4, y + 4), f"Barcode error: {exc}", fill=(220, 38, 38))
        return

    quiet = max(4, int(10 * scale))
    draw_x = x + quiet
    draw_w = max(4, width - quiet * 2)
    total_modules = sum(w for _, w in symbol.modules) or 1
    module_w = draw_w / total_modules
    body_h = int(height * (0.72 if show_text else 0.88))

    cursor = float(draw_x)
    for is_bar, units in symbol.modules:
        w = units * module_w
        if is_bar:
            draw.rectangle(
                [round(cursor), y, round(cursor + w), y + body_h],
                fill=color,
            )
        cursor += w

    if show_text:
        _draw_centered_text(
            draw, x + width // 2, y + int(height * 0.77),
            symbol.label[:34] + ("..." if len(symbol.label) > 34 else ""),
            color, max(6, int(8 * scale)),
        )


def _draw_2d_symbol(
    draw: ImageDraw.Draw,
    x: int, y: int, width: int, height: int,
    color, text: str, scale: float,
    barcode_type: str, magnification: int,
) -> None:
    """Draw a 2D matrix code (QR, Data Matrix, PDF417)."""
    margin = max(2, int(4 * scale))
    try:
        symbol = encode_matrix_symbol(barcode_type, text, magnification=magnification)
    except Exception as exc:
        draw.text((x + 4, y + 4), f"2D code error: {exc}", fill=(220, 38, 38))
        return

    rows = len(symbol.cells)
    cols = len(symbol.cells[0]) if rows else 0
    if not rows or not cols:
        return

    max_w = max(20, width - margin * 2)
    if barcode_type == "pdf417":
        target_w = max_w
        cell = min(target_w / cols, max(2, height / max(rows, 1)))
        draw_w = cols * cell
        draw_h = rows * cell
    elif barcode_type in ("qr", "datamatrix"):
        size = min(max(22, int(height * 0.92)), max_w)
        cell = size / max(cols, rows)
        draw_w = cols * cell
        draw_h = rows * cell
    else:
        return

    x0 = x + (width - draw_w) / 2
    y0 = y
    bg = "#ffffff" if color != (0, 0, 0) else "#111827"

    draw.rectangle(
        [x0 - 2, y0 - 2, x0 + draw_w + 2, y0 + draw_h + 2],
        fill=bg, outline=color,
    )

    for ri, row in enumerate(symbol.cells):
        for ci, filled in enumerate(row):
            if filled:
                draw.rectangle(
                    [x0 + ci * cell, y0 + ri * cell,
                     x0 + (ci + 1) * cell, y0 + (ri + 1) * cell],
                    fill=color,
                )

    if not symbol.exact:
        label = BARCODE_TYPES.get(normalize_barcode_type(barcode_type), None)
        label_text = f"{label.label} preview" if label else "preview"
        _draw_centered_text(
            draw, x + width // 2, int(y0 + draw_h + 4),
            label_text, (100, 116, 139), max(7, int(8 * scale)),
        )


def _draw_centered_text(
    draw: ImageDraw.Draw,
    cx: int, cy: int, text: str, color, font_size: int,
) -> None:
    """Draw text centered on (cx, cy)."""
    font = _get_monospace_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2), text, fill=color, font=font)


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def _get_monospace_font(size: int) -> ImageFont.FreeTypeFont:
    """Return a monospace TrueType font at the requested pixel size."""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    font_names: list[str] = []
    if os.name == "nt":
        font_names = [
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "courbd.ttf"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "cour.ttf"),
        ]
    font_names += [
        "Courier New",
        "Courier",
        "DejaVuSansMono.ttf",
        "FreeMono.ttf",
    ]

    for name in font_names:
        try:
            f = ImageFont.truetype(name, size)
            _FONT_CACHE[size] = f
            return f
        except (OSError, IOError):
            continue

    logger.warning("No monospace font found, using PIL default")
    f = ImageFont.load_default()
    _FONT_CACHE[size] = f
    return f
