"""Canvas based label preview used by the desktop application."""

from __future__ import annotations

from typing import Iterable
import tkinter as tk

from .barcodes import BARCODE_TYPES, is_2d_barcode, normalize_barcode_type
from .constants import COL_BORDER, COL_MUTED, COL_PANEL, PREVIEW_MAX_H, PREVIEW_MAX_W
from .layout import MARGIN_X, calculate_layout_for_lines, normalize_text_lines


class LabelPreviewCanvas(tk.Canvas):

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
            )

        self.create_text(
            ox + lw // 2,
            oy + lh + 14,
            text=f"{width_mm} x {height_mm} mm  @{dpi} dpi{rotate_hint}",
            fill=COL_MUTED,
            font=("Helvetica", 9),
        )

    def _draw_symbol(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type, show_text):
        if is_2d_barcode(barcode_type):
            self._draw_2d_code(ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type)
        else:
            self._draw_linear_barcode(ox, bar_y, lw, bar_h, color, text, scale, offset_x, barcode_type, show_text)

    def _draw_linear_barcode(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x=0, barcode_type="code128", show_text=True):
        margin = int((MARGIN_X + offset_x) * scale)
        bx = ox + margin
        bw = max(8, lw - margin * 2)
        seed = sum(ord(ch) for ch in str(text or barcode_type)) or 37
        pattern = [1 + ((seed + i * 7) % 3) for i in range(31)]
        total = sum(pattern)
        unit_w = bw / total if total else 1
        x = bx
        for i, units in enumerate(pattern):
            w = unit_w * units
            if i % 2 == 0:
                self.create_rectangle(x, bar_y, x + w, bar_y + bar_h * (0.78 if show_text else 0.92), fill=color, outline="")
            x += w
        if show_text:
            self.create_text(
                ox + lw // 2,
                bar_y + bar_h,
                text=text[:30] + ("..." if len(text) > 30 else ""),
                fill=color,
                font=("Courier New", max(6, int(8 * scale))),
                anchor="n",
            )

    def _draw_2d_code(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x=0, barcode_type="qr"):
        margin = int((MARGIN_X + offset_x) * scale)
        size = min(max(22, int(bar_h * 0.86)), max(22, lw - margin * 2))
        x0 = ox + (lw - size) // 2
        y0 = bar_y
        self.create_rectangle(x0, y0, x0 + size, y0 + size, outline=color, fill="")
        cells = 9 if barcode_type == "qr" else 8
        cell = size / cells
        seed = sum(ord(ch) for ch in str(text or barcode_type))
        for row in range(cells):
            for col in range(cells):
                finder = barcode_type == "qr" and ((row < 3 and col < 3) or (row < 3 and col >= cells - 3) or (row >= cells - 3 and col < 3))
                filled = finder or ((row * 17 + col * 31 + seed) % 5 in {0, 2})
                if filled:
                    self.create_rectangle(
                        x0 + col * cell + 1,
                        y0 + row * cell + 1,
                        x0 + (col + 1) * cell - 1,
                        y0 + (row + 1) * cell - 1,
                        fill=color,
                        outline="",
                    )
        label = BARCODE_TYPES[normalize_barcode_type(barcode_type)].label
        self.create_text(
            ox + lw // 2,
            y0 + size + 4,
            text=label,
            fill=COL_MUTED,
            font=("Helvetica", max(7, int(8 * scale))),
            anchor="n",
        )
