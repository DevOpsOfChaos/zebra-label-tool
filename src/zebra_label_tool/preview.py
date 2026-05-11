"""Canvas based label preview used by the desktop application."""

from __future__ import annotations

from typing import Iterable
import tkinter as tk

from .barcodes import BARCODE_TYPES, is_2d_barcode, normalize_barcode_type
from .constants import COL_BORDER, COL_MUTED, COL_PANEL, PREVIEW_MAX_H, PREVIEW_MAX_W
from .layout import MARGIN_X, calculate_layout_for_lines, normalize_text_lines
from .preview_symbols import encode_linear_symbol, encode_matrix_symbol


class LabelPreviewCanvas(tk.Canvas):
    """Draw a local preview of the generated label.

    Text layout uses the same shared calculation as ZPL generation. Linear
    barcodes and QR codes are generated from real encoding patterns so the
    preview is useful rather than decorative. Data Matrix and PDF417 are shown as
    deterministic high-fidelity layout previews because the final printer render
    is produced by Zebra firmware from the generated ZPL command.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COL_PANEL, highlightthickness=0, **kwargs)

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
    ):
        self.delete("all")

        cw = max(self.winfo_width(), PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)
        text_lines = normalize_text_lines(lines, line1, line2)
        barcode_type = normalize_barcode_type(barcode_type)
        effective_barcode_height = int(barcode_height or 40)
        if is_2d_barcode(barcode_type):
            effective_barcode_height = max(effective_barcode_height, int(barcode_magnification or 4) * 18)

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

        self.create_rectangle(ox + 5, oy + 6, ox + lw + 5, oy + lh + 6, fill="#cbd5e1", outline="")

        bg_col = "#111827" if inverted else "#ffffff"
        txt_col = "#ffffff" if inverted else "#111827"
        self.create_rectangle(ox, oy, ox + lw, oy + lh, fill=bg_col, outline=COL_BORDER, width=1)

        if border:
            pad = max(1, int(2 * scale))
            self.create_rectangle(
                ox + pad,
                oy + pad,
                ox + lw - pad,
                oy + lh - pad,
                outline=txt_col,
                width=max(1, int(2 * scale)),
                fill="",
            )

        fs_px = max(7, int(layout.fs * scale))
        font = ("Helvetica", -fs_px, "bold")
        line_gap_px = int(layout.line_gap * scale)
        text_y = oy + int(layout.pos_y_text * scale)
        margin_px = int((MARGIN_X + int(offset_x)) * scale)

        if alignment == "left":
            anchor = "nw"
            text_x = ox + margin_px
        elif alignment == "right":
            anchor = "ne"
            text_x = ox + lw - margin_px
        else:
            anchor = "n"
            text_x = ox + lw // 2

        rotate_hint = "" if str(rotation).lower() == "normal" else f"  text rotation: {rotation}"
        placeholder_used = not any(line.strip() for line in text_lines)
        if placeholder_used:
            text_lines = ["Label text ..."]

        for index, line in enumerate(text_lines):
            color = "#94a3b8" if placeholder_used else txt_col
            y = text_y + index * (fs_px + line_gap_px)
            self.create_text(text_x, y, text=line, fill=color, font=font, anchor=anchor)

        if layout.has_bar:
            bar_y_px = oy + int(layout.pos_y_bar * scale)
            bar_h_px = max(12, int(layout.bar_h * scale))
            self._draw_symbol(
                ox,
                bar_y_px,
                lw,
                bar_h_px,
                txt_col,
                barcode_text,
                scale,
                int(offset_x),
                barcode_type,
                bool(barcode_show_text),
                int(barcode_magnification or 4),
            )

        self.create_text(
            ox + lw // 2,
            oy + lh + 14,
            text=f"{width_mm} x {height_mm} mm  @{dpi} dpi{rotate_hint}",
            fill=COL_MUTED,
            font=("Helvetica", 9),
        )

    def _draw_symbol(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type, show_text, magnification):
        if is_2d_barcode(barcode_type):
            self._draw_2d_code(ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type, magnification)
        else:
            self._draw_linear_barcode(ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type, show_text)

    def _draw_linear_barcode(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x=0, barcode_type="code128", show_text=True):
        margin = max(4, int((MARGIN_X + offset_x) * scale))
        bx = ox + margin
        bw = max(8, lw - margin * 2)
        try:
            symbol = encode_linear_symbol(barcode_type, text)
        except Exception as exc:
            self.create_text(ox + lw // 2, bar_y + 4, text=f"Barcode error: {exc}", fill="#dc2626", font=("Helvetica", 10), anchor="n")
            return

        quiet = max(4, int(10 * scale))
        draw_x = bx + quiet
        draw_w = max(4, bw - quiet * 2)
        total_modules = sum(width for _, width in symbol.modules) or 1
        module_w = draw_w / total_modules
        bar_body_h = bar_h * (0.72 if show_text else 0.88)

        x = draw_x
        for is_bar, units in symbol.modules:
            w = units * module_w
            if is_bar:
                # integer-ish coordinates keep the preview crisp at normal scales
                self.create_rectangle(round(x), bar_y, round(x + w), bar_y + bar_body_h, fill=color, outline="")
            x += w

        if show_text:
            self.create_text(
                ox + lw // 2,
                bar_y + bar_h * 0.77,
                text=symbol.label[:34] + ("..." if len(symbol.label) > 34 else ""),
                fill=color,
                font=("Courier New", max(6, int(8 * scale))),
                anchor="n",
            )

    def _draw_2d_code(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x=0, barcode_type="qr", magnification=4):
        margin = max(4, int((MARGIN_X + offset_x) * scale))
        try:
            symbol = encode_matrix_symbol(barcode_type, text, magnification=magnification)
        except Exception as exc:
            self.create_text(ox + lw // 2, bar_y + 4, text=f"2D code error: {exc}", fill="#dc2626", font=("Helvetica", 10), anchor="n")
            return

        rows = len(symbol.cells)
        cols = len(symbol.cells[0]) if rows else 0
        if not rows or not cols:
            return

        max_w = max(20, lw - margin * 2)
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

        x0 = ox + (lw - draw_w) / 2
        y0 = bar_y
        bg = "#ffffff" if color != "#ffffff" else "#111827"
        self.create_rectangle(x0 - 2, y0 - 2, x0 + draw_w + 2, y0 + draw_h + 2, fill=bg, outline=color)

        for row_index, row in enumerate(symbol.cells):
            for col_index, filled in enumerate(row):
                if filled:
                    self.create_rectangle(
                        x0 + col_index * cell,
                        y0 + row_index * cell,
                        x0 + (col_index + 1) * cell,
                        y0 + (row_index + 1) * cell,
                        fill=color,
                        outline="",
                    )
        if not symbol.exact:
            self.create_text(
                ox + lw // 2,
                y0 + draw_h + 4,
                text=f"{BARCODE_TYPES[normalize_barcode_type(barcode_type)].label} preview",
                fill=COL_MUTED,
                font=("Helvetica", max(7, int(8 * scale))),
                anchor="n",
            )
