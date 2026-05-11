"""Canvas based label preview used by the desktop application."""

from __future__ import annotations

from typing import Iterable
import tkinter as tk

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
    ):
        self.delete("all")

        cw = max(self.winfo_width(), PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)
        text_lines = normalize_text_lines(lines, line1, line2)

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
        )
        pw_dots = layout.pw
        ll_dots = layout.ll

        scale = min((cw - 40) / pw_dots, (ch - 40) / ll_dots)
        lw = int(pw_dots * scale)
        lh = int(ll_dots * scale)
        ox = (cw - lw) // 2
        oy = (ch - lh) // 2

        self.create_rectangle(ox + 4, oy + 4, ox + lw + 4, oy + lh + 4, fill="#0a0a0a", outline="")

        bg_col = "#141414" if inverted else "#ffffff"
        txt_col = "#ffffff" if inverted else "#111111"
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
            color = "#999" if placeholder_used else txt_col
            y = text_y + index * (fs_px + line_gap_px)
            self.create_text(text_x, y, text=line, fill=color, font=font, anchor=anchor)

        if layout.has_bar:
            bar_y_px = oy + int(layout.pos_y_bar * scale)
            bar_h_px = max(12, int(layout.bar_h * scale))
            self._draw_barcode(ox, bar_y_px, lw, bar_h_px, txt_col, barcode_text, scale, int(offset_x))

        self.create_text(
            ox + lw // 2,
            oy + lh + 14,
            text=f"{width_mm} x {height_mm} mm  @{dpi} dpi{rotate_hint}",
            fill=COL_MUTED,
            font=("Helvetica", 9),
        )

    def _draw_barcode(self, ox, bar_y, lw, bar_h, color, text, scale, offset_x=0):
        margin = int((MARGIN_X + offset_x) * scale)
        bx = ox + margin
        bw = lw - margin * 2
        pattern = [1, 2, 1, 1, 3, 1, 2, 1, 1, 2, 3, 1, 1, 2, 1, 1, 2, 1, 3, 1, 1, 2, 1]
        total = sum(pattern)
        unit_w = bw / total if total else 1
        x = bx
        for i, units in enumerate(pattern):
            w = unit_w * units
            if i % 2 == 0:
                self.create_rectangle(x, bar_y, x + w, bar_y + bar_h * 0.78, fill=color, outline="")
            x += w
        self.create_text(
            ox + lw // 2,
            bar_y + bar_h,
            text=text[:26] + ("..." if len(text) > 26 else ""),
            fill=color,
            font=("Courier New", max(6, int(8 * scale))),
            anchor="n",
        )
