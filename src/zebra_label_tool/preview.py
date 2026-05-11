"""Canvas based label preview used by the desktop application."""

from __future__ import annotations

import tkinter as tk

from .constants import COL_BORDER, COL_MUTED, COL_PANEL, PREVIEW_MAX_H, PREVIEW_MAX_W
from .layout import LINE_GAP, MARGIN_X, calc_positions


class LabelPreviewCanvas(tk.Canvas):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COL_PANEL, highlightthickness=0, **kwargs)

    def update_preview(self, line1, line2, width_mm, height_mm, font_size, dpi,
                       inverted=False, border=False, barcode=False,
                       barcode_text="", barcode_pos="below"):
        self.delete("all")

        cw = max(self.winfo_width(),  PREVIEW_MAX_W)
        ch = max(self.winfo_height(), PREVIEW_MAX_H)

        # Same layout calculation as the ZPL generator
        p = calc_positions(line1, line2, width_mm, height_mm, font_size, dpi,
                           barcode, barcode_text, barcode_pos)
        pw_dots = p["pw"]
        ll_dots = p["ll"]

        scale = min((cw - 40) / pw_dots, (ch - 40) / ll_dots)
        lw = int(pw_dots * scale)
        lh = int(ll_dots * scale)
        ox = (cw - lw) // 2
        oy = (ch - lh) // 2

        # Shadow
        self.create_rectangle(ox+4, oy+4, ox+lw+4, oy+lh+4, fill="#0a0a0a", outline="")

        # Label background
        bg_col  = "#141414" if inverted else "#ffffff"
        txt_col = "#ffffff"  if inverted else "#111111"
        self.create_rectangle(ox, oy, ox+lw, oy+lh, fill=bg_col, outline=COL_BORDER, width=1)

        # Border
        if border:
            pad = max(1, int(2 * scale))
            self.create_rectangle(ox+pad, oy+pad, ox+lw-pad, oy+lh-pad,
                                  outline=txt_col, width=max(1, int(2*scale)), fill="")

        # Negative Tkinter font size means pixels, which keeps preview and ZPL dot sizing aligned
        fs_dots = p["fs"]
        fs_px   = max(7, int(fs_dots * scale))
        font    = ("Helvetica", -fs_px, "bold")

        # Positions in pixels, scaled from printer dots
        ty_px    = oy + int(p["pos_y_text"] * scale)
        bar_y_px = oy + int(p["pos_y_bar"]  * scale)
        bar_h_px = max(12, int(p["bar_h"]   * scale))
        gap_px   = int(LINE_GAP * scale)
        cx       = ox + lw // 2

        # Line 1: top-center anchor matches the ZPL origin model closely enough for preview
        l1_text = line1 if line1.strip() else ("Line 1 ..." if not line2.strip() else "")
        l1_col  = txt_col if line1.strip() else "#999"
        self.create_text(cx, ty_px, text=l1_text, fill=l1_col, font=font, anchor="n")

        # Line 2
        if line2.strip():
            self.create_text(cx, ty_px + fs_px + gap_px,
                             text=line2, fill=txt_col, font=font, anchor="n")

        # Barcode
        if p["has_bar"]:
            self._draw_barcode(ox, bar_y_px, lw, bar_h_px, txt_col, barcode_text, scale)

        # Size info
        self.create_text(ox + lw // 2, oy + lh + 14,
                         text=f"{width_mm} x {height_mm} mm  @{dpi} dpi",
                         fill=COL_MUTED, font=("Helvetica", 9))

    def _draw_barcode(self, ox, bar_y, lw, bar_h, color, text, scale):
        margin  = int(MARGIN_X * scale)
        bx      = ox + margin
        bw      = lw - margin * 2
        pattern = [1,2,1,1,3,1,2,1,1,2,3,1,1,2,1,1,2,1,3,1,1,2,1]
        total   = sum(pattern)
        unit_w  = bw / total
        x = bx
        for i, units in enumerate(pattern):
            w = unit_w * units
            if i % 2 == 0:
                self.create_rectangle(x, bar_y, x+w, bar_y + bar_h * 0.78,
                                      fill=color, outline="")
            x += w
        self.create_text(ox + lw // 2, bar_y + bar_h,
                         text=text[:26] + ("..." if len(text) > 26 else ""),
                         fill=color, font=("Courier New", max(6, int(8*scale))), anchor="n")