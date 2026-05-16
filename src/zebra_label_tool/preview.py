"""Canvas based label preview used by the desktop application.

Supports two display modes:
1. **ZPL-rendered image** — shows a PIL image rendered from the actual ZPL
   (via Labelary API / Pillow fallback).
2. **Native Canvas fallback** — the original tkinter drawing, kept as a
   last-resort when neither renderer is available.
"""

from __future__ import annotations

from typing import Iterable
import tkinter as tk

from PIL import Image, ImageTk

from .barcodes import is_2d_barcode, normalize_barcode_type
from .constants import COL_BORDER, COL_MUTED, COL_PANEL, PREVIEW_MAX_H, PREVIEW_MAX_W
from .layout import MARGIN_X, calculate_layout_for_lines, normalize_text_lines
from .preview_symbols import encode_linear_symbol, encode_matrix_symbol
from .barcodes import BARCODE_TYPES  # for fallback label text


class LabelPreviewCanvas(tk.Canvas):
    """Draw a local preview of the generated label.

    By default the canvas attempts to render the ZPL through
    :mod:`zpl_renderer` and show the returned image.  If that fails it
    falls back to the original Canvas-primitive drawing routine.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COL_PANEL, highlightthickness=0, **kwargs)
        self._photo_ref: ImageTk.PhotoImage | None = None
        self._render_method: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_preview(
        self,
        line1="",
        line2="",
        width_mm=57,
        height_mm=19,
        font_size=58,
        dpi=300,
        inverted=False,
        border=False,
        barcode=False,
        barcode_text="",
        barcode_pos="below",
        *,
        lines: Iterable[str] | None = None,
        alignment="center",
        rotation="normal",
        line_gap=10,
        offset_x=0,
        offset_y=0,
        auto_fit=True,
        barcode_type="code128",
        barcode_height=40,
        barcode_show_text=True,
        barcode_magnification=4,
        # New argument: pass a pre-rendered PIL image
        zpl_image: Image.Image | None = None,
        render_method: str = "",
    ):
        """Update the preview — either from a ZPL-rendered image or fallback.

        If *zpl_image* is provided it is displayed directly (fast path
        for callers that already rendered via ``zpl_renderer``).
        Otherwise the old Canvas-drawing fallback is used.
        """
        if zpl_image is not None:
            self.show_zpl_image(zpl_image, render_method)
            return

        # --- legacy fallback (Canvas drawing) -------------------------
        self._draw_fallback(
            line1=line1, line2=line2,
            width_mm=width_mm, height_mm=height_mm,
            font_size=font_size, dpi=dpi,
            inverted=inverted, border=border,
            barcode=barcode, barcode_text=barcode_text,
            barcode_pos=barcode_pos,
            lines=lines,
            alignment=alignment, rotation=rotation,
            line_gap=line_gap,
            offset_x=offset_x, offset_y=offset_y,
            auto_fit=auto_fit,
            barcode_type=barcode_type,
            barcode_height=barcode_height,
            barcode_show_text=barcode_show_text,
            barcode_magnification=barcode_magnification,
        )

    def show_zpl_image(self, pil_image: Image.Image, method: str = "") -> None:
        """Display a PIL image rendered from the actual ZPL.

        Parameters
        ----------
        pil_image
            RGB image (typically from :func:`zpl_renderer.render_zpl_preview`).
        method
            Short label like ``"labelary"`` or ``"pillow"`` shown as a badge.
        """
        self.delete("all")
        self._render_method = method

        cw = max(self.winfo_width(), PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)
        pad = 10

        iw, ih = pil_image.size
        if iw == 0 or ih == 0:
            self._show_error("Empty image from renderer")
            return

        scale = min((cw - pad * 2) / iw, (ch - pad * 2) / ih, 3.0)
        display_w = max(1, int(iw * scale))
        display_h = max(1, int(ih * scale))

        resized = pil_image.resize((display_w, display_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(resized)
        self._photo_ref = photo  # prevent GC

        ox = (cw - display_w) // 2
        oy = (ch - display_h) // 2

        # Drop shadow
        self.create_rectangle(
            ox + 5, oy + 6, ox + display_w + 5, oy + display_h + 6,
            fill="#cbd5e1", outline="",
        )
        # Label border
        self.create_image(ox, oy, image=photo, anchor="nw")

        # Render-method badge
        if method:
            badge = {
                "labelary": "Labelary \u2713",
                "pillow": "Preview (local)",
            }.get(method, method)
            self.create_text(
                ox + display_w - 6, oy + 6,
                text=badge,
                fill=COL_MUTED,
                font=("Helvetica", 8),
                anchor="ne",
            )

    # ------------------------------------------------------------------
    # Legacy Canvas drawing (fallback)
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        self.delete("all")
        cw = max(self.winfo_width(), PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)
        self.create_text(
            cw // 2, ch // 2,
            text=message,
            fill="#dc2626",
            font=("Helvetica", 12),
            anchor="center",
        )

    def _draw_fallback(self, **kwargs):
        """Original Canvas-primitive drawing — kept for compatibility."""
        self.delete("all")

        line1 = kwargs.get("line1", "")
        line2 = kwargs.get("line2", "")
        width_mm = kwargs.get("width_mm", 57)
        height_mm = kwargs.get("height_mm", 19)
        font_size = kwargs.get("font_size", 58)
        dpi = kwargs.get("dpi", 300)
        inverted = kwargs.get("inverted", False)
        border = kwargs.get("border", False)
        barcode = kwargs.get("barcode", False)
        barcode_text = kwargs.get("barcode_text", "")
        barcode_pos = kwargs.get("barcode_pos", "below")
        lines = kwargs.get("lines")
        alignment = kwargs.get("alignment", "center")
        rotation = kwargs.get("rotation", "normal")
        line_gap = kwargs.get("line_gap", 10)
        offset_x = kwargs.get("offset_x", 0)
        offset_y = kwargs.get("offset_y", 0)
        auto_fit = kwargs.get("auto_fit", True)
        barcode_type = kwargs.get("barcode_type", "code128")
        barcode_height = kwargs.get("barcode_height", 40)
        barcode_show_text = kwargs.get("barcode_show_text", True)
        barcode_magnification = kwargs.get("barcode_magnification", 4)

        cw = max(self.winfo_width(), PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)
        text_lines = normalize_text_lines(lines, line1, line2)
        barcode_type_key = normalize_barcode_type(barcode_type)
        effective_barcode_height = int(barcode_height or 40)
        if is_2d_barcode(barcode_type_key):
            effective_barcode_height = max(
                effective_barcode_height, int(barcode_magnification or 4) * 18
            )

        layout = calculate_layout_for_lines(
            text_lines,
            width_mm=width_mm,
            height_mm=height_mm,
            font_size=font_size,
            dpi=dpi,
            barcode=barcode,
            barcode_text=barcode_text,
            barcode_pos=barcode_pos,
            line_gap=int(line_gap),
            offset_x=int(offset_x),
            offset_y=int(offset_y),
            auto_fit=bool(auto_fit),
            barcode_height=effective_barcode_height,
        )
        pw_dots = layout.pw
        ll_dots = layout.ll

        scale = min((cw - 40) / pw_dots, (ch - 40) / ll_dots)
        lw = int(pw_dots * scale)
        lh = int(ll_dots * scale)
        ox = (cw - lw) // 2
        oy = (ch - lh) // 2

        self.create_rectangle(
            ox + 5, oy + 6, ox + lw + 5, oy + lh + 6,
            fill="#cbd5e1", outline="",
        )

        bg_col = "#111827" if inverted else "#ffffff"
        txt_col = "#ffffff" if inverted else "#111827"
        self.create_rectangle(
            ox, oy, ox + lw, oy + lh,
            fill=bg_col, outline=COL_BORDER, width=1,
        )

        if border:
            pad = max(1, int(2 * scale))
            self.create_rectangle(
                ox + pad, oy + pad, ox + lw - pad, oy + lh - pad,
                outline=txt_col, width=max(1, int(2 * scale)), fill="",
            )

        fs_px = max(7, int(layout.fs * scale))
        font = ("Courier New", -fs_px, "bold")
        line_gap_px = int(layout.line_gap * scale)
        text_y = oy + int(layout.pos_y_text * scale)
        text_area_x = ox + int(layout.text_x * scale)
        text_area_w = max(1, int(layout.text_w * scale))

        if alignment == "left":
            anchor = "nw"
            text_x = text_area_x
        elif alignment == "right":
            anchor = "ne"
            text_x = text_area_x + text_area_w
        else:
            anchor = "n"
            text_x = text_area_x + text_area_w // 2

        rotate_hint = (
            "" if str(rotation).lower() == "normal"
            else f"  text rotation: {rotation}"
        )
        placeholder_used = not any(line.strip() for line in text_lines)
        if placeholder_used:
            text_lines = ["Label text ..."]

        for index, line in enumerate(text_lines):
            color = "#94a3b8" if placeholder_used else txt_col
            y = text_y + index * (fs_px + line_gap_px)
            self.create_text(
                text_x, y, text=line, fill=color,
                font=font, anchor=anchor,
            )

        if layout.has_bar:
            bar_x_px = ox + int(layout.bar_x * scale)
            bar_y_px = oy + int(layout.pos_y_bar * scale)
            bar_w_px = max(18, int(layout.bar_w * scale))
            bar_h_px = max(12, int(layout.bar_h * scale))
            self._draw_symbol(
                bar_x_px, bar_y_px, bar_w_px, bar_h_px,
                txt_col, barcode_text, scale,
                barcode_type_key,
                bool(barcode_show_text),
                int(barcode_magnification or 4),
            )

        self.create_text(
            ox + lw // 2, oy + lh + 14,
            text=f"{width_mm} x {height_mm} mm  @{dpi} dpi{rotate_hint}",
            fill=COL_MUTED, font=("Helvetica", 9),
        )

    def _draw_symbol(self, x, bar_y, width, bar_h, color, text, scale,
                     barcode_type, show_text, magnification):
        if is_2d_barcode(barcode_type):
            self._draw_2d_code(
                x, bar_y, width, bar_h, color, text, scale,
                barcode_type, magnification,
            )
        else:
            self._draw_linear_barcode(
                x, bar_y, width, bar_h, color, text, scale,
                barcode_type, show_text,
            )

    def _draw_linear_barcode(self, x, bar_y, width, bar_h, color, text,
                             scale, barcode_type="code128", show_text=True):
        bx = x
        bw = max(8, width)
        try:
            symbol = encode_linear_symbol(barcode_type, text)
        except Exception as exc:
            self.create_text(
                x + width // 2, bar_y + 4,
                text=f"Barcode error: {exc}",
                fill="#dc2626", font=("Helvetica", 10), anchor="n",
            )
            return

        quiet = max(4, int(10 * scale))
        draw_x = bx + quiet
        draw_w = max(4, bw - quiet * 2)
        total_modules = sum(width for _, width in symbol.modules) or 1
        module_w = draw_w / total_modules
        bar_body_h = bar_h * (0.72 if show_text else 0.88)

        draw_cursor = draw_x
        for is_bar, units in symbol.modules:
            w = units * module_w
            if is_bar:
                self.create_rectangle(
                    round(draw_cursor), bar_y,
                    round(draw_cursor + w), bar_y + bar_body_h,
                    fill=color, outline="",
                )
            draw_cursor += w

        if show_text:
            self.create_text(
                x + width // 2,
                bar_y + bar_h * 0.77,
                text=symbol.label[:34] +
                     ("..." if len(symbol.label) > 34 else ""),
                fill=color,
                font=("Courier New", max(6, int(8 * scale))),
                anchor="n",
            )

    def _draw_2d_code(self, x, bar_y, width, bar_h, color, text, scale,
                      barcode_type="qr", magnification=4):
        margin = max(2, int(4 * scale))
        try:
            symbol = encode_matrix_symbol(
                barcode_type, text, magnification=magnification,
            )
        except Exception as exc:
            self.create_text(
                x + width // 2, bar_y + 4,
                text=f"2D code error: {exc}",
                fill="#dc2626", font=("Helvetica", 10), anchor="n",
            )
            return

        rows = len(symbol.cells)
        cols = len(symbol.cells[0]) if rows else 0
        if not rows or not cols:
            return

        max_w = max(20, width - margin * 2)
        if barcode_type == "pdf417":
            target_w = max_w
            cell = min(target_w / cols, max(2, bar_h / max(rows, 1)))
            draw_w = cols * cell
            draw_h = rows * cell
        else:
            size = min(max(22, int(bar_h * 0.92)), max_w)
            cell = size / max(cols, rows)
            draw_w = cols * cell
            draw_h = rows * cell

        x0 = x + (width - draw_w) / 2
        y0 = bar_y
        bg = "#ffffff" if color != "#ffffff" else "#111827"
        self.create_rectangle(
            x0 - 2, y0 - 2,
            x0 + draw_w + 2, y0 + draw_h + 2,
            fill=bg, outline=color,
        )

        for row_index, row in enumerate(symbol.cells):
            for col_index, filled in enumerate(row):
                if filled:
                    self.create_rectangle(
                        x0 + col_index * cell,
                        y0 + row_index * cell,
                        x0 + (col_index + 1) * cell,
                        y0 + (row_index + 1) * cell,
                        fill=color, outline="",
                    )
        if not symbol.exact:
            self.create_text(
                x + width // 2,
                y0 + draw_h + 4,
                text=(
                    f"{BARCODE_TYPES[normalize_barcode_type(barcode_type)].label}"
                    f" preview"
                ),
                fill=COL_MUTED,
                font=("Helvetica", max(7, int(8 * scale))),
                anchor="n",
            )
