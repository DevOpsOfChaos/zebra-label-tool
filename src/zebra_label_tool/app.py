"""CustomTkinter desktop application for Zebra Label Tool."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from .constants import (
    APP_TITLE,
    APP_VERSION,
    COL_ACCENT,
    COL_BORDER,
    COL_CARD,
    COL_ERR,
    COL_MUTED,
    COL_PANEL,
    COL_SUCCESS,
    COL_WARN,
    DPI_OPTIONS,
    MAX_HISTORY,
)
from .layout import mm_to_dots
from .preview import LabelPreviewCanvas
from .printing import get_printers, send_zpl_to_printer
from .settings import load_settings, save_settings
from .zpl import generate_zpl


class ZebraApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.settings = load_settings()
        self.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.geometry("1060x760")
        self.minsize(860, 620)
        self.bind("<Escape>",    lambda e: self.destroy())
        self.bind("<Return>",    lambda e: self._on_print())
        self.bind("<Control-c>", lambda e: self._copy_zpl())
        self.bind("<F5>",        lambda e: self._refresh_printers())
        self._build_ui()
        self._load_values()
        self.after(120, self._update_all)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=476)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        left = ctk.CTkScrollableFrame(
            self, width=472, fg_color=COL_PANEL,
            scrollbar_button_color=COL_BORDER,
            scrollbar_button_hover_color=COL_ACCENT
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_columnconfigure(0, weight=1)
        p = {"padx": 10, "pady": 4}

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", **p)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Zebra Label Printer",
                     font=ctk.CTkFont(size=17, weight="bold")).grid(row=0, column=0, sticky="w")
        self.status_lbl = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=11), text_color=COL_SUCCESS)
        self.status_lbl.grid(row=0, column=1, sticky="e")

        self._div(left, 1)

        # Drucker
        self._sec(left, 2, "Printer")
        dr = ctk.CTkFrame(left, fg_color="transparent")
        dr.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        dr.grid_columnconfigure(0, weight=1)
        self.printer_var = tk.StringVar()
        self.printer_dd  = ctk.CTkOptionMenu(dr, variable=self.printer_var,
                                              values=get_printers(), height=34,
                                              command=lambda _: self._autosave())
        self.printer_dd.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(dr, text="Refresh", width=60, height=34,
                      fg_color=COL_CARD, hover_color=COL_BORDER,
                      command=self._refresh_printers).grid(row=0, column=1, padx=(6, 0))

        # DPI
        dpi_f = ctk.CTkFrame(left, fg_color="transparent")
        dpi_f.grid(row=4, column=0, sticky="ew", padx=10, pady=(2, 4))
        dpi_f.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(dpi_f, text="Printer DPI:",
                     font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=0, column=0, padx=(0, 8))
        self.dpi_var = tk.StringVar()
        self.dpi_dd = ctk.CTkOptionMenu(dpi_f, variable=self.dpi_var,
                                        values=list(DPI_OPTIONS.keys()), height=28,
                                        font=ctk.CTkFont(size=11),
                                        command=lambda _: self._update_all())
        self.dpi_dd.grid(row=0, column=1, sticky="ew")

        self._div(left, 5)

        # Groesse
        self._sec(left, 6, "Label size")
        szf = ctk.CTkFrame(left, fg_color="transparent")
        szf.grid(row=7, column=0, sticky="ew", padx=10, pady=2)
        ctk.CTkLabel(szf, text="Width (mm)").grid(row=0, column=0, sticky="w")
        self.width_entry = ctk.CTkEntry(szf, width=68, justify="center", height=32)
        self.width_entry.grid(row=0, column=1, padx=(4, 14))
        self.width_entry.bind("<KeyRelease>", lambda _: self._update_all())
        ctk.CTkLabel(szf, text="Height (mm)").grid(row=0, column=2, sticky="w")
        self.height_entry = ctk.CTkEntry(szf, width=68, justify="center", height=32)
        self.height_entry.grid(row=0, column=3, padx=(4, 14))
        self.height_entry.bind("<KeyRelease>", lambda _: self._update_all())
        ctk.CTkLabel(szf, text="Copies").grid(row=0, column=4, sticky="w")
        self.copies_var = tk.StringVar(value="1")
        self.copies_entry = ctk.CTkEntry(szf, width=48, justify="center", height=32,
                                         textvariable=self.copies_var)
        self.copies_entry.grid(row=0, column=5, padx=(4, 0))

        qf = ctk.CTkFrame(left, fg_color="transparent")
        qf.grid(row=8, column=0, sticky="ew", padx=10, pady=(2, 4))
        ctk.CTkLabel(qf, text="Presets:", font=ctk.CTkFont(size=11),
                     text_color=COL_MUTED).grid(row=0, column=0, padx=(0, 6))
        for i, (lbl, w, h) in enumerate([("57x19", 57, 19), ("57x17", 57, 17),
                                          ("100x50", 100, 50), ("62x29", 62, 29)]):
            ctk.CTkButton(qf, text=lbl, width=68, height=24,
                          fg_color=COL_CARD, hover_color=COL_BORDER,
                          font=ctk.CTkFont(size=11),
                          command=lambda ww=w, hh=h: self._set_size(ww, hh)
                          ).grid(row=0, column=i+1, padx=3)

        self._div(left, 9)

        # Schrift
        self._sec(left, 10, "Font")
        ff = ctk.CTkFrame(left, fg_color="transparent")
        ff.grid(row=11, column=0, sticky="ew", padx=10, pady=2)
        ff.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ff, text="Size:").grid(row=0, column=0, padx=(0, 8))
        self.font_size_var = tk.IntVar(value=58)
        self.font_slider = ctk.CTkSlider(ff, from_=10, to=120, variable=self.font_size_var,
                                         command=lambda _: self._update_all())
        self.font_slider.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.font_size_lbl = ctk.CTkLabel(ff, text="58", width=28,
                                           font=ctk.CTkFont(size=13, weight="bold"))
        self.font_size_lbl.grid(row=0, column=2, padx=(0, 14))
        ctk.CTkLabel(ff, text="Style:").grid(row=0, column=3, padx=(0, 4))
        self.font_style_var = tk.StringVar(value="A0  (smooth)")
        ctk.CTkOptionMenu(ff, variable=self.font_style_var,
                          values=["A0  (smooth)", "A  (Bitmap)"],
                          width=120, height=30,
                          command=lambda _: self._update_all()).grid(row=0, column=4)

        self._div(left, 12)

        # Text
        self._sec(left, 13, "Text")
        tf = ctk.CTkFrame(left, fg_color="transparent")
        tf.grid(row=14, column=0, sticky="ew", padx=10, pady=2)
        tf.grid_columnconfigure(0, weight=1)

        l1_hdr = ctk.CTkFrame(tf, fg_color="transparent")
        l1_hdr.grid(row=0, column=0, sticky="ew")
        l1_hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(l1_hdr, text="Line 1 *",
                     font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=0, column=0, sticky="w")
        self.char_lbl1 = ctk.CTkLabel(l1_hdr, text="",
                                       font=ctk.CTkFont(size=10), text_color=COL_MUTED)
        self.char_lbl1.grid(row=0, column=1, sticky="e")

        self.line1_entry = ctk.CTkEntry(tf, placeholder_text="Text line 1 ...",
                                        font=ctk.CTkFont(size=20), justify="center", height=52)
        self.line1_entry.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        self.line1_entry.bind("<KeyRelease>", lambda _: self._update_all())

        btn_f = ctk.CTkFrame(tf, fg_color="transparent")
        btn_f.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(btn_f, text="Clear", width=84, height=22,
                      fg_color=COL_CARD, hover_color="#5c1010", font=ctk.CTkFont(size=10),
                      command=lambda: (self.line1_entry.delete(0, "end"), self._update_all())
                      ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(btn_f, text="Swap lines", width=110, height=22,
                      fg_color=COL_CARD, hover_color=COL_BORDER, font=ctk.CTkFont(size=10),
                      command=self._swap_lines).grid(row=0, column=1)

        l2_hdr = ctk.CTkFrame(tf, fg_color="transparent")
        l2_hdr.grid(row=3, column=0, sticky="ew")
        l2_hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(l2_hdr, text="Line 2  (optional)",
                     font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=0, column=0, sticky="w")
        self.char_lbl2 = ctk.CTkLabel(l2_hdr, text="",
                                       font=ctk.CTkFont(size=10), text_color=COL_MUTED)
        self.char_lbl2.grid(row=0, column=1, sticky="e")

        self.line2_entry = ctk.CTkEntry(tf, placeholder_text="Text line 2 ...",
                                        font=ctk.CTkFont(size=20), justify="center", height=52)
        self.line2_entry.grid(row=4, column=0, sticky="ew", pady=(2, 4))
        self.line2_entry.bind("<KeyRelease>", lambda _: self._update_all())
        ctk.CTkButton(tf, text="Clear", width=84, height=22,
                      fg_color=COL_CARD, hover_color="#5c1010", font=ctk.CTkFont(size=10),
                      command=lambda: (self.line2_entry.delete(0, "end"), self._update_all())
                      ).grid(row=5, column=0, sticky="w", pady=(0, 2))

        self._div(left, 15)

        # Optionen
        self._sec(left, 16, "Options")
        of = ctk.CTkFrame(left, fg_color="transparent")
        of.grid(row=17, column=0, sticky="ew", padx=10, pady=2)
        self.inverted_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(of, text="Inverted  (white on black)",
                        variable=self.inverted_var, command=self._update_all
                        ).grid(row=0, column=0, sticky="w", padx=(0, 24))
        self.border_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(of, text="Border", variable=self.border_var,
                        command=self._update_all).grid(row=0, column=1, sticky="w")

        bf = ctk.CTkFrame(left, fg_color="transparent")
        bf.grid(row=18, column=0, sticky="ew", padx=10, pady=(4, 2))
        bf.grid_columnconfigure(2, weight=1)
        self.barcode_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(bf, text="Barcode (Code128)",
                        variable=self.barcode_var, command=self._on_barcode_toggle
                        ).grid(row=0, column=0, padx=(0, 10))
        self.barcode_pos_var = tk.StringVar(value="below  (bottom)")
        ctk.CTkOptionMenu(bf, variable=self.barcode_pos_var,
                          values=["below  (bottom)", "above  (top)"],
                          width=130, height=28,
                          command=lambda _: self._update_all()).grid(row=0, column=1, padx=(0, 10))
        self.barcode_entry = ctk.CTkEntry(bf, placeholder_text="Barcode content ...",
                                          height=28, state="disabled")
        self.barcode_entry.grid(row=0, column=2, sticky="ew")
        self.barcode_entry.bind("<KeyRelease>", lambda _: self._update_all())

        self._div(left, 19)

        # Vorlagen
        self._sec(left, 20, "Templates")
        vf = ctk.CTkFrame(left, fg_color="transparent")
        vf.grid(row=21, column=0, sticky="ew", padx=10, pady=2)
        vf.grid_columnconfigure(0, weight=1)
        self.template_var = tk.StringVar(value="- choose template -")
        self.template_dd = ctk.CTkOptionMenu(vf, variable=self.template_var,
                                             values=self._template_names(), height=30,
                                             command=self._load_template)
        self.template_dd.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(vf, text="Save", width=100, height=30,
                      fg_color=COL_CARD, hover_color=COL_BORDER,
                      command=self._save_template).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(vf, text="Clear", width=78, height=30,
                      fg_color=COL_CARD, hover_color="#5c1010",
                      command=self._delete_template).grid(row=0, column=2)

        self._div(left, 22)

        # Drucken
        self.print_btn = ctk.CTkButton(
            left, text="PRINT  [Enter]",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50, corner_radius=10,
            fg_color=COL_ACCENT, hover_color="#1976d2",
            command=self._on_print
        )
        self.print_btn.grid(row=23, column=0, sticky="ew", padx=10, pady=6)

        pf = ctk.CTkFrame(left, fg_color="transparent")
        pf.grid(row=24, column=0, sticky="ew", padx=10, pady=(0, 4))
        pf.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(pf, text="Save settings",
                      height=28, fg_color=COL_CARD, hover_color=COL_BORDER,
                      font=ctk.CTkFont(size=11), command=self._save_all_settings
                      ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(pf, text="Copy ZPL",
                      height=28, fg_color=COL_CARD, hover_color=COL_BORDER,
                      font=ctk.CTkFont(size=11), command=self._copy_zpl
                      ).grid(row=0, column=1)

        self._div(left, 25)
        self._sec(left, 26, "Recent labels  (click to reuse)")
        self.history_frame = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=6)
        self.history_frame.grid(row=27, column=0, sticky="ew", padx=10, pady=(2, 6))
        self.history_frame.grid_columnconfigure(0, weight=1)
        self._rebuild_history()

        self._div(left, 28)
        ctk.CTkLabel(
            left,
            text="Enter = Print  |  ESC = Exit  |  Ctrl+C = Copy ZPL  |  F5 = Printers",
            font=ctk.CTkFont(size=10), text_color=COL_MUTED
        ).grid(row=29, column=0, pady=(4, 10))

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=COL_PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Live preview  (scaled)",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        self.preview_info = ctk.CTkLabel(hdr, text="",
                                          font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.preview_info.grid(row=0, column=1, sticky="e")

        cf = ctk.CTkFrame(right, fg_color=COL_CARD, corner_radius=8)
        cf.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_rowconfigure(0, weight=1)
        self.preview_canvas = LabelPreviewCanvas(cf)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        zh = ctk.CTkFrame(right, fg_color="transparent")
        zh.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 2))
        zh.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(zh, text="ZPL-Code",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(zh, text="Copy", width=84, height=26,
                      fg_color=COL_CARD, hover_color=COL_BORDER,
                      font=ctk.CTkFont(size=11), command=self._copy_zpl
                      ).grid(row=0, column=1, sticky="e", padx=(0, 6))
        ctk.CTkButton(zh, text="Export .zpl", width=104, height=26,
                      fg_color=COL_CARD, hover_color=COL_BORDER,
                      font=ctk.CTkFont(size=11), command=self._export_zpl
                      ).grid(row=0, column=2, sticky="e")

        self.zpl_box = ctk.CTkTextbox(right, height=190,
                                      font=ctk.CTkFont(family="Courier New", size=11),
                                      fg_color="#141416", text_color="#5bc8e8",
                                      activate_scrollbars=True)
        self.zpl_box.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _div(self, parent, row):
        ctk.CTkFrame(parent, height=1, fg_color=COL_BORDER
                     ).grid(row=row, column=0, sticky="ew", padx=6, pady=4)

    def _sec(self, parent, row, title):
        ctk.CTkLabel(parent, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"), text_color=COL_MUTED
                     ).grid(row=row, column=0, sticky="w", padx=10, pady=(2, 0))

    def _get_dpi(self):
        return DPI_OPTIONS.get(self.dpi_var.get(), 300)

    def _load_values(self):
        s = self.settings
        printers = get_printers()
        saved = s.get("printer", "")
        self.printer_var.set(saved if saved in printers else (printers[0] if printers else ""))

        saved_dpi = s.get("dpi", 300)
        dpi_label = next((k for k, v in DPI_OPTIONS.items() if v == saved_dpi),
                         list(DPI_OPTIONS.keys())[1])
        self.dpi_var.set(dpi_label)

        self.width_entry.insert(0,  str(s.get("width_mm",  57)))
        self.height_entry.insert(0, str(s.get("height_mm", 19)))
        self.copies_var.set(str(s.get("copies", 1)))

        fs = s.get("font_size", 58)
        self.font_size_var.set(fs)
        self.font_size_lbl.configure(text=str(fs))

        self.inverted_var.set(s.get("inverted", False))
        self.border_var.set(s.get("border", False))
        self.barcode_var.set(s.get("barcode", False))

        pos = s.get("barcode_pos", "below")
        self.barcode_pos_var.set("below  (bottom)" if pos == "below" else "above  (top)")
        style = s.get("font_style", "A0")
        self.font_style_var.set("A0  (smooth)" if style == "A0" else "A  (Bitmap)")

        self._on_barcode_toggle()
        self._refresh_template_dropdown()

    def _update_all(self, _=None):
        fs = int(self.font_size_var.get())
        self.font_size_lbl.configure(text=str(fs))

        l1 = self.line1_entry.get()
        l2 = self.line2_entry.get()
        self.char_lbl1.configure(text=f"{len(l1)} chars")
        self.char_lbl2.configure(text=f"{len(l2)} chars" if l2 else "")

        zpl = self._build_zpl()
        self.zpl_box.configure(state="normal")
        self.zpl_box.delete("1.0", "end")
        self.zpl_box.insert("1.0", zpl)
        self.zpl_box.configure(state="disabled")

        try:
            w = int(self.width_entry.get() or 57)
            h = int(self.height_entry.get() or 19)
        except ValueError:
            w, h = 57, 19

        dpi = self._get_dpi()
        self.preview_info.configure(
            text=f"{mm_to_dots(w, dpi)} x {mm_to_dots(h, dpi)} dots  @{dpi} dpi"
        )

        barcode_pos = self.barcode_pos_var.get().split()[0]
        self.preview_canvas.update_preview(
            line1=l1, line2=l2, width_mm=w, height_mm=h, font_size=fs, dpi=dpi,
            inverted=self.inverted_var.get(), border=self.border_var.get(),
            barcode=self.barcode_var.get(), barcode_text=self.barcode_entry.get(),
            barcode_pos=barcode_pos,
        )

    def _build_zpl(self):
        try:
            w  = int(self.width_entry.get()  or 57)
            h  = int(self.height_entry.get() or 19)
            fs = int(self.font_size_var.get())
            cp = max(1, int(self.copies_var.get() or 1))
        except ValueError:
            return "-- Invalid input --"
        style = self.font_style_var.get().split()[0]
        pos   = self.barcode_pos_var.get().split()[0]
        return generate_zpl(
            line1=self.line1_entry.get(), line2=self.line2_entry.get(),
            width_mm=w, height_mm=h, font_size=fs, dpi=self._get_dpi(),
            copies=cp, inverted=self.inverted_var.get(), border=self.border_var.get(),
            barcode=self.barcode_var.get(), barcode_text=self.barcode_entry.get(),
            barcode_pos=pos, font_style=style,
        )

    def _on_barcode_toggle(self):
        state = "normal" if self.barcode_var.get() else "disabled"
        self.barcode_entry.configure(state=state)
        self._update_all()

    def _swap_lines(self):
        l1, l2 = self.line1_entry.get(), self.line2_entry.get()
        self.line1_entry.delete(0, "end"); self.line1_entry.insert(0, l2)
        self.line2_entry.delete(0, "end"); self.line2_entry.insert(0, l1)
        self._update_all()

    def _on_print(self, _=None):
        printer = self.printer_var.get()
        if not printer or printer.startswith("(") or printer.startswith("Error") or printer.startswith("[Test mode"):
            self._status("No printer selected!", COL_WARN)
            messagebox.showwarning("No printer", "Please select a printer.")
            return
        l1 = self.line1_entry.get().strip()
        l2 = self.line2_entry.get().strip()
        if not l1 and not l2:
            self._status("No text entered!", COL_WARN)
            messagebox.showwarning("No text", "Please fill at least line 1.")
            return
        zpl = self._build_zpl()
        try:
            send_zpl_to_printer(printer, zpl)
        except RuntimeError as e:
            self._status("Print error!", COL_ERR)
            messagebox.showerror("Print error", str(e))
            return
        except Exception as e:
            self._status("Error!", COL_ERR)
            messagebox.showerror("Error", str(e))
            return
        label = l1 + (f"  |  {l2}" if l2 else "")
        self._status(f"Printed: {label}", COL_SUCCESS)
        self._add_history(label)
        self._autosave()

    def _refresh_printers(self):
        printers = get_printers()
        self.printer_dd.configure(values=printers)
        cur = self.printer_var.get()
        if cur not in printers and printers:
            self.printer_var.set(printers[0])
        self._status("Printer list refreshed", COL_SUCCESS)

    def _set_size(self, w, h):
        self.width_entry.delete(0, "end"); self.width_entry.insert(0, str(w))
        self.height_entry.delete(0, "end"); self.height_entry.insert(0, str(h))
        self._update_all()

    def _copy_zpl(self, _=None):
        self.clipboard_clear(); self.clipboard_append(self._build_zpl())
        self._status("ZPL copied to clipboard", COL_SUCCESS)

    def _export_zpl(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export ZPL",
            defaultextension=".zpl",
            filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(self._build_zpl())
                f.write("\n")
        except OSError as exc:
            self._status("Export failed!", COL_ERR)
            messagebox.showerror("Export failed", str(exc))
            return
        self._status("ZPL exported", COL_SUCCESS)

    def _autosave(self):
        self.settings["printer"] = self.printer_var.get()
        save_settings(self.settings)

    def _save_all_settings(self):
        try:
            w  = int(self.width_entry.get())
            h  = int(self.height_entry.get())
            cp = max(1, int(self.copies_var.get() or 1))
        except ValueError:
            self._status("Invalid input!", COL_ERR); return
        self.settings.update({
            "printer":     self.printer_var.get(),
            "dpi":         self._get_dpi(),
            "width_mm":    w, "height_mm": h,
            "font_size":   int(self.font_size_var.get()),
            "copies":      cp,
            "inverted":    self.inverted_var.get(),
            "border":      self.border_var.get(),
            "barcode":     self.barcode_var.get(),
            "barcode_pos": self.barcode_pos_var.get().split()[0],
            "font_style":  self.font_style_var.get().split()[0],
        })
        save_settings(self.settings)
        self._status("Settings saved", COL_SUCCESS)

    def _template_names(self):
        names = list(self.settings.get("templates", {}).keys())
        return names if names else ["- no templates -"]

    def _refresh_template_dropdown(self):
        self.template_dd.configure(values=self._template_names())

    def _save_template(self):
        name = simpledialog.askstring("Save template", "Name:", parent=self)
        if not name or not name.strip(): return
        name = name.strip()
        try:
            w = int(self.width_entry.get()); h = int(self.height_entry.get())
        except ValueError:
            self._status("Invalid size!", COL_ERR); return
        self.settings.setdefault("templates", {})[name] = {
            "width_mm":     w, "height_mm": h,
            "font_size":    int(self.font_size_var.get()),
            "font_style":   self.font_style_var.get().split()[0],
            "dpi":          self._get_dpi(),
            "line1":        self.line1_entry.get(),
            "line2":        self.line2_entry.get(),
            "inverted":     self.inverted_var.get(),
            "border":       self.border_var.get(),
            "barcode":      self.barcode_var.get(),
            "barcode_text": self.barcode_entry.get(),
        }
        save_settings(self.settings)
        self._refresh_template_dropdown()
        self.template_var.set(name)
        self._status(f"Template '{name}' saved", COL_SUCCESS)

    def _load_template(self, name):
        t = self.settings.get("templates", {}).get(name)
        if not t: return
        self._set_size(t.get("width_mm", 57), t.get("height_mm", 19))
        self.font_size_var.set(t.get("font_size", 58))
        saved_dpi = t.get("dpi", 300)
        dpi_label = next((k for k, v in DPI_OPTIONS.items() if v == saved_dpi),
                         list(DPI_OPTIONS.keys())[1])
        self.dpi_var.set(dpi_label)
        style = t.get("font_style", "A0")
        self.font_style_var.set("A0  (smooth)" if style == "A0" else "A  (Bitmap)")
        self.line1_entry.delete(0, "end"); self.line1_entry.insert(0, t.get("line1", ""))
        self.line2_entry.delete(0, "end"); self.line2_entry.insert(0, t.get("line2", ""))
        self.inverted_var.set(t.get("inverted", False))
        self.border_var.set(t.get("border", False))
        self.barcode_var.set(t.get("barcode", False))
        self.barcode_entry.configure(state="normal")
        self.barcode_entry.delete(0, "end"); self.barcode_entry.insert(0, t.get("barcode_text", ""))
        if not t.get("barcode", False): self.barcode_entry.configure(state="disabled")
        self._update_all()
        self._status(f"Template '{name}' loaded", COL_SUCCESS)

    def _delete_template(self):
        name = self.template_var.get()
        if name not in self.settings.get("templates", {}): return
        if messagebox.askyesno("Delete?", f"Delete '{name}'?", parent=self):
            del self.settings["templates"][name]
            save_settings(self.settings)
            self._refresh_template_dropdown()
            self.template_var.set(self._template_names()[0])
            self._status(f"Template '{name}' deleted", COL_WARN)

    def _add_history(self, label_text):
        now = datetime.now().strftime("%H:%M")
        self.settings.setdefault("history", []).insert(0, f"[{now}]  {label_text}")
        self.settings["history"] = self.settings["history"][:MAX_HISTORY]
        save_settings(self.settings)
        self._rebuild_history()

    def _rebuild_history(self):
        for w in self.history_frame.winfo_children():
            w.destroy()
        history = self.settings.get("history", [])
        if not history:
            ctk.CTkLabel(self.history_frame, text="  No labels printed yet.",
                         font=ctk.CTkFont(size=11), text_color=COL_MUTED
                         ).grid(row=0, column=0, sticky="w", padx=8, pady=4)
            return
        self.history_frame.grid_columnconfigure(0, weight=1)
        for i, entry in enumerate(history):
            rf = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            rf.grid(row=i, column=0, sticky="ew"); rf.grid_columnconfigure(0, weight=1)
            parts = entry.split("]  ", 1)
            txt   = parts[1] if len(parts) > 1 else entry
            segs  = txt.split("  |  ", 1)
            l1, l2 = segs[0].strip(), (segs[1].strip() if len(segs) > 1 else "")
            lbl = ctk.CTkLabel(rf, text=entry, font=ctk.CTkFont(size=11),
                               text_color=COL_MUTED, anchor="w", cursor="hand2")
            lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=1)
            lbl.bind("<Button-1>", lambda e, a=l1, b=l2: self._recall(a, b))

    def _recall(self, l1, l2):
        self.line1_entry.delete(0, "end"); self.line1_entry.insert(0, l1)
        self.line2_entry.delete(0, "end"); self.line2_entry.insert(0, l2)
        self._update_all()

    def _status(self, msg, color=COL_SUCCESS):
        self.status_lbl.configure(text=msg, text_color=color)
        self.after(5000, lambda: self.status_lbl.configure(text=""))


def run() -> None:
    """Start the desktop application."""
    app = ZebraApp()
    app.mainloop()
