"""CustomTkinter desktop application for Zebra Label Tool."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from .barcodes import BARCODE_TYPES, BARCODE_TYPE_LABELS, barcode_key_from_label, barcode_label
from .batch import generate_batch_zpl, parse_batch_blocks
from .constants import (
    APP_TITLE,
    COL_ACCENT,
    COL_ACCENT_DARK,
    COL_BG,
    COL_BORDER,
    COL_CARD,
    COL_CARD_ALT,
    COL_ERR,
    COL_MUTED,
    COL_PANEL,
    COL_SOFT,
    COL_SUCCESS,
    COL_TEXT,
    COL_WARN,
    DPI_OPTIONS,
    MAX_HISTORY,
)
from .label_spec import LabelSpec, LabelSpecError, MAX_TEXT_LINES
from .layout import calculate_layout_for_lines, mm_to_dots
from .presets import BUILTIN_PRESET_NAMES, BUILTIN_PRESETS, preset_settings
from .preview import LabelPreviewCanvas
from .printing import get_printers, send_zpl_to_printer
from .settings import load_settings, save_settings
from .text_tools import normalize_editor_text, transform_lines, wrap_lines
from .zpl_import import parse_simple_zpl


FONT_STYLE_LABELS = ["A0  (smooth)", "A  (Bitmap)"]
ALIGNMENT_LABELS = ["center", "left", "right", "justify"]
ROTATION_LABELS = ["normal", "90", "180", "270"]
BARCODE_POSITION_LABELS = ["below  (bottom)", "above  (top)"]


def _short_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class ZebraApp(ctk.CTk):
    """Main desktop application."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COL_BG)
        self.settings = load_settings()
        self._init_variables()
        self._closing = False
        self._status_after_id = None
        self._zpl_window: ctk.CTkToplevel | None = None
        self._zpl_window_box: ctk.CTkTextbox | None = None
        self._batch_window: ctk.CTkToplevel | None = None
        self._batch_text_box: ctk.CTkTextbox | None = None

        self.title(APP_TITLE)
        self.geometry("1120x760")
        self.minsize(940, 620)
        self.protocol("WM_DELETE_WINDOW", self._safe_close)
        self._bind_shortcuts()
        self._build_menu()
        self._build_ui()
        self._load_values()
        self.after(120, self._update_all)

    def _init_variables(self) -> None:
        """Create Tk variables before widgets are built so controls stay bound."""
        self.printer_var = tk.StringVar(value="")
        self.dpi_var = tk.StringVar(value=list(DPI_OPTIONS.keys())[1])
        self.width_var = tk.StringVar(value=str(self.settings.get("width_mm", 57)))
        self.height_var = tk.StringVar(value=str(self.settings.get("height_mm", 19)))
        self.copies_var = tk.StringVar(value=str(self.settings.get("copies", 1)))
        self.font_size_var = tk.IntVar(value=int(self.settings.get("font_size", 58)))
        self.font_style_var = tk.StringVar(value="A0  (smooth)" if self.settings.get("font_style", "A0") == "A0" else "A  (Bitmap)")
        self.inverted_var = tk.BooleanVar(value=bool(self.settings.get("inverted", False)))
        self.border_var = tk.BooleanVar(value=bool(self.settings.get("border", False)))
        self.barcode_var = tk.BooleanVar(value=bool(self.settings.get("barcode", False)))
        self.barcode_text_var = tk.StringVar(value=str(self.settings.get("barcode_text", "")))
        self.barcode_type_var = tk.StringVar(value=barcode_label(str(self.settings.get("barcode_type", "code128"))))
        self.barcode_pos_var = tk.StringVar(value="above  (top)" if self.settings.get("barcode_pos", "below") == "above" else "below  (bottom)")
        self.barcode_height_var = tk.StringVar(value=str(self.settings.get("barcode_height", 40)))
        self.barcode_show_text_var = tk.BooleanVar(value=bool(self.settings.get("barcode_show_text", True)))
        self.barcode_magnification_var = tk.StringVar(value=str(self.settings.get("barcode_magnification", 4)))
        self.alignment_var = tk.StringVar(value=str(self.settings.get("alignment", "center")))
        self.rotation_var = tk.StringVar(value=str(self.settings.get("rotation", "normal")))
        self.line_gap_var = tk.StringVar(value=str(self.settings.get("line_gap", 10)))
        self.offset_x_var = tk.StringVar(value=str(self.settings.get("offset_x", 0)))
        self.offset_y_var = tk.StringVar(value=str(self.settings.get("offset_y", 0)))
        self.auto_fit_var = tk.BooleanVar(value=bool(self.settings.get("auto_fit", True)))

    def _bind_shortcuts(self) -> None:
        self.bind("<Escape>", lambda e: self._safe_close())
        self.bind("<Control-p>", lambda e: self._on_print())
        self.bind("<Control-s>", lambda e: self._save_all_settings())
        self.bind("<Control-n>", lambda e: self._reset_label())
        self.bind("<Control-l>", lambda e: self._open_label_setup())
        self.bind("<Control-t>", lambda e: self._open_text_options())
        self.bind("<Control-b>", lambda e: self._open_barcode_options())
        self.bind("<Control-Shift-B>", lambda e: self._open_batch_window())
        self.bind("<F5>", lambda e: self._refresh_printers())

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New label", accelerator="Ctrl+N", command=self._reset_label)
        file_menu.add_separator()
        file_menu.add_command(label="Import ZPL...", command=self._import_zpl)
        file_menu.add_command(label="Export ZPL...", command=self._export_zpl)
        file_menu.add_command(label="Copy ZPL", command=self._copy_zpl)
        file_menu.add_separator()
        file_menu.add_command(label="Print", accelerator="Ctrl+P", command=self._on_print)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Esc", command=self._safe_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Clear text", command=self._clear_text)
        edit_menu.add_command(label="Use barcode text from label", command=self._barcode_from_first_line)
        edit_menu.add_separator()
        edit_menu.add_command(label="Save current settings", accelerator="Ctrl+S", command=self._save_all_settings)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        label_menu = tk.Menu(menubar, tearoff=False)
        label_menu.add_command(label="Label setup...", accelerator="Ctrl+L", command=self._open_label_setup)
        label_menu.add_separator()
        for label, width, height in [("57 x 19 mm", 57, 19), ("57 x 17 mm", 57, 17), ("62 x 29 mm", 62, 29), ("100 x 50 mm", 100, 50)]:
            label_menu.add_command(label=label, command=lambda w=width, h=height: self._set_size(w, h))
        label_menu.add_separator()
        preset_menu = tk.Menu(label_menu, tearoff=False)
        for preset in BUILTIN_PRESETS:
            preset_menu.add_command(label=preset.name, command=lambda name=preset.name: self._apply_builtin_preset(name))
        label_menu.add_cascade(label="Apply built-in preset", menu=preset_menu)
        menubar.add_cascade(label="Label", menu=label_menu)

        text_menu = tk.Menu(menubar, tearoff=False)
        text_menu.add_command(label="Text options...", accelerator="Ctrl+T", command=self._open_text_options)
        text_menu.add_separator()
        text_menu.add_command(label="Clean up whitespace", command=lambda: self._format_text("cleanup"))
        text_menu.add_command(label="Remove empty lines", command=lambda: self._format_text("remove_empty"))
        text_menu.add_command(label="Wrap long lines...", command=self._wrap_text_dialog)
        text_menu.add_separator()
        text_menu.add_command(label="UPPERCASE", command=lambda: self._format_text("uppercase"))
        text_menu.add_command(label="lowercase", command=lambda: self._format_text("lowercase"))
        text_menu.add_command(label="Title Case", command=lambda: self._format_text("title_case"))
        text_menu.add_separator()
        for alignment in ALIGNMENT_LABELS:
            text_menu.add_command(label=f"Align {alignment}", command=lambda a=alignment: self._set_alignment(a))
        menubar.add_cascade(label="Text", menu=text_menu)

        barcode_menu = tk.Menu(menubar, tearoff=False)
        barcode_menu.add_command(label="Barcode / QR options...", accelerator="Ctrl+B", command=self._open_barcode_options)
        barcode_menu.add_command(label="Use first label line as payload", command=self._barcode_from_first_line)
        barcode_menu.add_command(label="Toggle code", command=self._toggle_barcode)
        barcode_menu.add_separator()
        type_menu = tk.Menu(barcode_menu, tearoff=False)
        for barcode in BARCODE_TYPES.values():
            type_menu.add_command(label=barcode.label, command=lambda key=barcode.key: self._set_barcode_type(key))
        barcode_menu.add_cascade(label="Symbology", menu=type_menu)
        barcode_menu.add_separator()
        barcode_menu.add_command(label="Disable code", command=lambda: (self.barcode_var.set(False), self._update_all()))
        menubar.add_cascade(label="Barcode / QR", menu=barcode_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Batch labels...", accelerator="Ctrl+Shift+B", command=self._open_batch_window)
        tools_menu.add_separator()
        tools_menu.add_command(label="Reset layout options", command=self._reset_layout_options)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="Show ZPL...", command=self._open_zpl_window)
        view_menu.add_command(label="Refresh preview", accelerator="F5", command=self._update_all)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Quick guide", command=self._show_quick_guide)
        help_menu.add_command(label="Keyboard shortcuts", command=self._show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=430)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self) -> None:
        left = ctk.CTkFrame(self, width=420, fg_color=COL_PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_TITLE, font=ctk.CTkFont(size=21, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Fast local Zebra/ZPL label creation",
            font=ctk.CTkFont(size=11),
            text_color=COL_MUTED,
        ).grid(row=1, column=0, sticky="w")
        self.status_lbl = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=11), text_color=COL_SUCCESS)
        self.status_lbl.grid(row=0, column=1, sticky="e")

        printer = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        printer.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        printer.grid_columnconfigure(0, weight=1)
        self.printer_dd = ctk.CTkOptionMenu(
            printer,
            variable=self.printer_var,
            values=get_printers(),
            height=34,
            command=lambda _: self._autosave(),
        )
        self.printer_dd.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(
            printer,
            text="Refresh",
            width=76,
            height=34,
            fg_color=COL_SOFT,
            text_color=COL_TEXT,
            hover_color=COL_BORDER,
            command=self._refresh_printers,
        ).grid(row=0, column=1, padx=(0, 10), pady=10)

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        actions.grid_columnconfigure(0, weight=2)
        actions.grid_columnconfigure(1, weight=1)
        self.print_btn = ctk.CTkButton(
            actions,
            text="Print label",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COL_ACCENT,
            hover_color=COL_ACCENT_DARK,
            command=self._on_print,
        )
        self.print_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="New",
            height=42,
            fg_color=COL_CARD,
            text_color=COL_TEXT,
            border_width=1,
            border_color=COL_BORDER,
            hover_color=COL_CARD_ALT,
            command=self._reset_label,
        ).grid(row=0, column=1, sticky="ew")

        text_card = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        text_card.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        text_card.grid_columnconfigure(0, weight=1)
        text_card.grid_rowconfigure(4, weight=1)

        text_header = ctk.CTkFrame(text_card, fg_color="transparent")
        text_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        text_header.grid_columnconfigure(1, weight=1)
        self.clear_text_btn = ctk.CTkButton(
            text_header,
            text="✕",
            width=32,
            height=28,
            corner_radius=8,
            fg_color=COL_ERR,
            hover_color="#991b1b",
            command=self._clear_text,
        )
        self.clear_text_btn.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(text_header, text="Label text", font=ctk.CTkFont(size=14, weight="bold"), text_color=COL_TEXT).grid(row=0, column=1, sticky="w")
        self.text_counter_lbl = ctk.CTkLabel(text_header, text="", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.text_counter_lbl.grid(row=0, column=2, sticky="e")

        text_controls = ctk.CTkFrame(text_card, fg_color=COL_CARD_ALT, corner_radius=10)
        text_controls.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 8))
        text_controls.grid_columnconfigure(1, weight=1)
        text_controls.grid_columnconfigure(3, weight=0)
        ctk.CTkLabel(text_controls, text="Font", text_color=COL_MUTED, font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=8)
        self.font_slider = ctk.CTkSlider(text_controls, from_=8, to=160, number_of_steps=152, variable=self.font_size_var, command=self._on_inline_font_size)
        self.font_slider.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        self.font_size_inline_lbl = ctk.CTkLabel(text_controls, text=str(self.font_size_var.get()), width=34, text_color=COL_TEXT)
        self.font_size_inline_lbl.grid(row=0, column=2, padx=(0, 8), pady=8)
        self.inline_alignment = ctk.CTkOptionMenu(text_controls, variable=self.alignment_var, values=ALIGNMENT_LABELS, width=105, height=28, command=lambda _: self._update_all())
        self.inline_alignment.grid(row=0, column=3, padx=(0, 8), pady=8)
        ctk.CTkCheckBox(text_controls, text="Auto-fit", variable=self.auto_fit_var, command=self._update_all).grid(row=0, column=4, padx=(0, 10), pady=8)

        quick_tools = ctk.CTkFrame(text_card, fg_color="transparent")
        quick_tools.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        for col in range(4):
            quick_tools.grid_columnconfigure(col, weight=1)
        ctk.CTkButton(quick_tools, text="Options", height=28, fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, font=ctk.CTkFont(size=11), command=self._open_text_options).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text="Clean", height=28, fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, font=ctk.CTkFont(size=11), command=lambda: self._format_text("cleanup")).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text="Wrap", height=28, fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, font=ctk.CTkFont(size=11), command=self._wrap_text_dialog).grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text="Case", height=28, fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, font=ctk.CTkFont(size=11), command=lambda: self._format_text("uppercase")).grid(row=0, column=3, sticky="ew")

        ctk.CTkLabel(
            text_card,
            text=f"Enter adds a printed line. Use Ctrl+P or the Print label button to print. Up to {MAX_TEXT_LINES} lines.",
            font=ctk.CTkFont(size=10),
            text_color=COL_MUTED,
        ).grid(row=3, column=0, sticky="w", padx=10)
        self.text_box = ctk.CTkTextbox(
            text_card,
            height=240,
            font=ctk.CTkFont(size=20),
            fg_color="#ffffff",
            text_color=COL_TEXT,
            border_width=1,
            border_color=COL_BORDER,
            wrap="none",
            activate_scrollbars=True,
        )
        self.text_box.grid(row=4, column=0, sticky="nsew", padx=10, pady=(6, 10))
        self.text_box.bind("<Return>", self._text_box_return)
        self.text_box.bind("<KeyRelease>", lambda _: self._update_all())

        lower = ctk.CTkFrame(left, fg_color="transparent")
        lower.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))
        lower.grid_columnconfigure(0, weight=1)
        self.template_var = tk.StringVar(value="- choose template -")
        self.template_dd = ctk.CTkOptionMenu(lower, variable=self.template_var, values=self._template_names(), height=30, command=self._load_template)
        self.template_dd.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(lower, text="Save template", width=110, height=30, fg_color=COL_CARD, text_color=COL_TEXT, border_width=1, border_color=COL_BORDER, hover_color=COL_CARD_ALT, command=self._save_template).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(lower, text="Delete", width=70, height=30, fg_color=COL_CARD, text_color=COL_ERR, border_width=1, border_color=COL_BORDER, hover_color="#fee2e2", command=self._delete_template).grid(row=0, column=2)

        self.history_frame = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        self.history_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.history_frame.grid_columnconfigure(0, weight=1)
        self._rebuild_history()

    def _build_right_panel(self) -> None:
        right = ctk.CTkFrame(self, fg_color=COL_PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Live preview", font=ctk.CTkFont(size=16, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w")
        self.preview_info = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.preview_info.grid(row=0, column=1, sticky="e")

        canvas_frame = ctk.CTkFrame(right, fg_color=COL_CARD, corner_radius=14, border_width=1, border_color=COL_BORDER)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)
        self.preview_canvas = LabelPreviewCanvas(canvas_frame)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        summary = ctk.CTkFrame(right, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        summary.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        summary.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(summary, text="Current setup", font=ctk.CTkFont(size=12, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        self.setup_summary_lbl = ctk.CTkLabel(summary, text="", justify="left", anchor="w", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.setup_summary_lbl.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 0))
        self.quality_lbl = ctk.CTkLabel(summary, text="", justify="left", anchor="w", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.quality_lbl.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        footer = ctk.CTkFrame(right, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.preview_hint = ctk.CTkLabel(
            footer,
            text="Tip: Enter creates another label line. Advanced label, barcode/QR and ZPL tools are in the top menu.",
            font=ctk.CTkFont(size=11),
            text_color=COL_MUTED,
        )
        self.preview_hint.grid(row=0, column=0, sticky="w")

    # ---- input/state helpers -------------------------------------------------

    def _get_dpi(self) -> int:
        return DPI_OPTIONS.get(self.dpi_var.get(), 300)

    def _get_text_lines(self) -> list[str]:
        raw = self.text_box.get("1.0", "end-1c") if hasattr(self, "text_box") else ""
        lines = [line.rstrip() for line in raw.splitlines()]
        while lines and not lines[-1].strip():
            lines.pop()
        return lines or [""]

    def _set_text_lines(self, lines: list[str] | tuple[str, ...]) -> None:
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", "\n".join(lines))

    def _text_box_return(self, _event=None):
        """Keep Enter inside the editor as a normal line break.

        The application intentionally does not bind Enter to printing. A label
        editor must allow fast multi-line entry without the risk of printing by
        accident.
        """
        return None

    def _set_entry(self, entry: ctk.CTkEntry, value: str | int | float) -> None:
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def _load_values(self) -> None:
        s = self.settings
        printers = get_printers()
        saved = s.get("printer", "")
        self.printer_var.set(saved if saved in printers else (printers[0] if printers else ""))

        saved_dpi = s.get("dpi", 300)
        dpi_label = next((k for k, v in DPI_OPTIONS.items() if v == saved_dpi), list(DPI_OPTIONS.keys())[1])
        self.dpi_var.set(dpi_label)
        self.width_var.set(str(s.get("width_mm", 57)))
        self.height_var.set(str(s.get("height_mm", 19)))
        self.copies_var.set(str(s.get("copies", 1)))
        self.font_size_var.set(int(s.get("font_size", 58)))
        self.font_style_var.set("A0  (smooth)" if s.get("font_style", "A0") == "A0" else "A  (Bitmap)")
        self.inverted_var.set(bool(s.get("inverted", False)))
        self.border_var.set(bool(s.get("border", False)))
        self.barcode_var.set(bool(s.get("barcode", False)))
        self.barcode_text_var.set(str(s.get("barcode_text", "")))
        self.barcode_type_var.set(barcode_label(str(s.get("barcode_type", "code128"))))
        self.barcode_pos_var.set("above  (top)" if s.get("barcode_pos", "below") == "above" else "below  (bottom)")
        self.barcode_height_var.set(str(s.get("barcode_height", 40)))
        self.barcode_show_text_var.set(bool(s.get("barcode_show_text", True)))
        self.barcode_magnification_var.set(str(s.get("barcode_magnification", 4)))
        self.alignment_var.set(str(s.get("alignment", "center")))
        self.rotation_var.set(str(s.get("rotation", "normal")))
        self.line_gap_var.set(str(s.get("line_gap", 10)))
        self.offset_x_var.set(str(s.get("offset_x", 0)))
        self.offset_y_var.set(str(s.get("offset_y", 0)))
        self.auto_fit_var.set(bool(s.get("auto_fit", True)))
        if hasattr(self, "font_size_inline_lbl"):
            self.font_size_inline_lbl.configure(text=str(self.font_size_var.get()))

        lines = s.get("text_lines")
        if not lines:
            lines = [s.get("line1", ""), s.get("line2", "")]
        self._set_text_lines([str(line) for line in lines])
        self._refresh_template_dropdown()

    def _read_spec(self) -> LabelSpec:
        return LabelSpec.from_raw(
            lines=self._get_text_lines(),
            width_mm=self.width_var.get() or 57,
            height_mm=self.height_var.get() or 19,
            font_size=int(self.font_size_var.get()),
            dpi=self._get_dpi(),
            copies=self.copies_var.get() or 1,
            inverted=self.inverted_var.get(),
            border=self.border_var.get(),
            barcode=self.barcode_var.get(),
            barcode_text=self.barcode_text_var.get(),
            barcode_type=barcode_key_from_label(self.barcode_type_var.get()),
            barcode_pos=self.barcode_pos_var.get(),
            barcode_height=self.barcode_height_var.get() or 40,
            barcode_show_text=self.barcode_show_text_var.get(),
            barcode_magnification=self.barcode_magnification_var.get() or 4,
            font_style=self.font_style_var.get(),
            alignment=self.alignment_var.get(),
            rotation=self.rotation_var.get(),
            line_gap=self.line_gap_var.get() or 0,
            offset_x=self.offset_x_var.get() or 0,
            offset_y=self.offset_y_var.get() or 0,
            auto_fit=self.auto_fit_var.get(),
        )

    def _update_all(self, _=None) -> None:
        if self._closing:
            return
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            self.print_btn.configure(state="disabled")
            self.preview_info.configure(text=f"Input error: {exc}")
            self.text_counter_lbl.configure(text="invalid")
            self.setup_summary_lbl.configure(text=f"Invalid input: {exc}")
            if hasattr(self, "quality_lbl"):
                self.quality_lbl.configure(text="Fix the highlighted input before printing.", text_color=COL_ERR)
            self._refresh_zpl_window(f"-- Invalid input --\n{exc}\n", error=True)
            return

        self.print_btn.configure(state="normal")
        line_count = len([line for line in spec.text_lines if line.strip()]) or 1
        self.text_counter_lbl.configure(text=f"{line_count} line{'s' if line_count != 1 else ''}")
        dots_w = mm_to_dots(spec.width_mm, spec.dpi)
        dots_h = mm_to_dots(spec.height_mm, spec.dpi)
        self.preview_info.configure(text=f"{dots_w} x {dots_h} dots  @{spec.dpi} dpi")
        self.setup_summary_lbl.configure(
            text=(
                f"{_short_number(spec.width_mm)} x {_short_number(spec.height_mm)} mm, {spec.dpi} dpi, {spec.copies} copies\n"
                f"Font {spec.font_style}, size {spec.font_size}, {spec.alignment}, rotation {spec.rotation}, gap {spec.line_gap}\n"
                f"Border {'on' if spec.border else 'off'}, inverted {'on' if spec.inverted else 'off'}, "
                f"code {BARCODE_TYPES[spec.barcode_type].label if spec.active_barcode else 'off'}"
            )
        )
        self._update_quality_warning(spec)
        self.preview_canvas.update_preview(
            lines=spec.text_lines,
            width_mm=spec.width_mm,
            height_mm=spec.height_mm,
            font_size=spec.font_size,
            dpi=spec.dpi,
            inverted=spec.inverted,
            border=spec.border,
            barcode=spec.barcode,
            barcode_text=spec.barcode_text,
            barcode_pos=spec.barcode_pos,
            barcode_type=spec.barcode_type,
            barcode_height=spec.barcode_height,
            barcode_show_text=spec.barcode_show_text,
            barcode_magnification=spec.barcode_magnification,
            alignment=spec.alignment,
            rotation=spec.rotation,
            line_gap=spec.line_gap,
            offset_x=spec.offset_x,
            offset_y=spec.offset_y,
            auto_fit=spec.auto_fit,
        )
        self._refresh_zpl_window(spec.to_zpl())

    def _build_zpl(self) -> str:
        return self._read_spec().to_zpl()

    def _update_quality_warning(self, spec: LabelSpec) -> None:
        layout = calculate_layout_for_lines(
            spec.text_lines,
            width_mm=spec.width_mm,
            height_mm=spec.height_mm,
            font_size=spec.font_size,
            dpi=spec.dpi,
            barcode=spec.barcode,
            barcode_text=spec.barcode_text,
            barcode_pos=spec.barcode_pos,
            line_gap=spec.line_gap,
            offset_x=spec.offset_x,
            offset_y=spec.offset_y,
            auto_fit=spec.auto_fit,
            barcode_height=spec.barcode_height,
        )
        warnings: list[str] = []
        if spec.auto_fit and layout.fs < spec.font_size:
            warnings.append(f"Auto-fit reduced font to {layout.fs} dots")
        if not spec.has_text:
            warnings.append("Type label text first; Enter adds another printed line")
        if spec.active_barcode and len(spec.barcode_text.strip()) > 32:
            warnings.append("Long barcode text may become hard to scan")
        if len(spec.text_lines) >= MAX_TEXT_LINES:
            warnings.append(f"Maximum of {MAX_TEXT_LINES} lines reached")
        if warnings:
            self.quality_lbl.configure(text="Warning: " + " | ".join(warnings), text_color=COL_WARN)
        else:
            self.quality_lbl.configure(text="Ready: preview and generated ZPL share the same layout calculation.", text_color=COL_MUTED)

    # ---- dialogs -------------------------------------------------------------

    def _dialog(self, title: str, width: int = 420, height: int = 360) -> ctk.CTkToplevel:
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry(f"{width}x{height}")
        win.transient(self)
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)
        return win

    def _open_label_setup(self, _=None) -> None:
        win = self._dialog("Label setup", 460, 440)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        width_entry = self._dialog_entry(frame, 0, "Width (mm)", self.width_var.get())
        height_entry = self._dialog_entry(frame, 1, "Height (mm)", self.height_var.get())
        copies_entry = self._dialog_entry(frame, 2, "Copies", self.copies_var.get())
        dpi_var = tk.StringVar(value=self.dpi_var.get())
        ctk.CTkLabel(frame, text="Printer DPI").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        ctk.CTkOptionMenu(frame, variable=dpi_var, values=list(DPI_OPTIONS.keys())).grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        border_var = tk.BooleanVar(value=self.border_var.get())
        inverted_var = tk.BooleanVar(value=self.inverted_var.get())
        ctk.CTkCheckBox(frame, text="Draw border", variable=border_var).grid(row=4, column=1, sticky="w", padx=10, pady=8)
        ctk.CTkCheckBox(frame, text="Inverted label", variable=inverted_var).grid(row=5, column=1, sticky="w", padx=10, pady=8)

        presets = ctk.CTkFrame(frame, fg_color="transparent")
        presets.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(6, 10))
        for col, (label, w, h) in enumerate([("57x19", 57, 19), ("57x17", 57, 17), ("62x29", 62, 29), ("100x50", 100, 50)]):
            presets.grid_columnconfigure(col, weight=1)
            ctk.CTkButton(presets, text=label, fg_color=COL_CARD, hover_color=COL_BORDER, command=lambda ww=w, hh=h: (self._set_entry(width_entry, ww), self._set_entry(height_entry, hh))).grid(row=0, column=col, sticky="ew", padx=3)

        def apply() -> None:
            self.width_var.set(width_entry.get())
            self.height_var.set(height_entry.get())
            self.copies_var.set(copies_entry.get())
            self.dpi_var.set(dpi_var.get())
            self.border_var.set(border_var.get())
            self.inverted_var.set(inverted_var.get())
            self._update_all()
            win.destroy()

        self._dialog_buttons(frame, 7, apply, win.destroy)

    def _open_text_options(self, _=None) -> None:
        win = self._dialog("Text options", 500, 520)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        font_size = ctk.CTkSlider(frame, from_=8, to=160, number_of_steps=152)
        font_size.set(int(self.font_size_var.get()))
        ctk.CTkLabel(frame, text="Font size").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        font_size.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        font_size_lbl = ctk.CTkLabel(frame, text=str(int(font_size.get())), width=40)
        font_size_lbl.grid(row=0, column=2, padx=10, pady=8)
        font_size.configure(command=lambda value: font_size_lbl.configure(text=str(int(float(value)))))

        font_style_var = tk.StringVar(value=self.font_style_var.get())
        self._dialog_option(frame, 1, "Font style", font_style_var, FONT_STYLE_LABELS)
        alignment_var = tk.StringVar(value=self.alignment_var.get())
        self._dialog_option(frame, 2, "Alignment", alignment_var, ALIGNMENT_LABELS)
        rotation_var = tk.StringVar(value=self.rotation_var.get())
        self._dialog_option(frame, 3, "Rotation", rotation_var, ROTATION_LABELS)
        line_gap = self._dialog_entry(frame, 4, "Line gap (dots)", self.line_gap_var.get())
        offset_x = self._dialog_entry(frame, 5, "Horizontal offset (dots)", self.offset_x_var.get())
        offset_y = self._dialog_entry(frame, 6, "Vertical offset (dots)", self.offset_y_var.get())
        auto_fit_var = tk.BooleanVar(value=self.auto_fit_var.get())
        ctk.CTkCheckBox(frame, text="Auto-fit font to available height", variable=auto_fit_var).grid(row=7, column=1, sticky="w", padx=10, pady=8)

        def apply() -> None:
            self.font_size_var.set(int(font_size.get()))
            self.font_style_var.set(font_style_var.get())
            self.alignment_var.set(alignment_var.get())
            self.rotation_var.set(rotation_var.get())
            self.line_gap_var.set(line_gap.get())
            self.offset_x_var.set(offset_x.get())
            self.offset_y_var.set(offset_y.get())
            self.auto_fit_var.set(auto_fit_var.get())
            self._update_all()
            win.destroy()

        self._dialog_buttons(frame, 8, apply, win.destroy)

    def _open_barcode_options(self, _=None) -> None:
        win = self._dialog("Barcode / QR options", 520, 500)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        enabled_var = tk.BooleanVar(value=self.barcode_var.get())
        type_var = tk.StringVar(value=self.barcode_type_var.get())
        content_entry = self._dialog_entry(frame, 2, "Payload", self.barcode_text_var.get())
        position_var = tk.StringVar(value=self.barcode_pos_var.get())
        height_entry = self._dialog_entry(frame, 4, "Height / reserved area (dots)", self.barcode_height_var.get())
        mag_entry = self._dialog_entry(frame, 5, "QR/Data Matrix magnification", self.barcode_magnification_var.get())
        show_text_var = tk.BooleanVar(value=self.barcode_show_text_var.get())

        ctk.CTkCheckBox(frame, text="Print barcode / 2D code", variable=enabled_var).grid(row=0, column=1, sticky="w", padx=10, pady=10)
        self._dialog_option(frame, 1, "Symbology", type_var, BARCODE_TYPE_LABELS)
        self._dialog_option(frame, 3, "Position", position_var, BARCODE_POSITION_LABELS)
        ctk.CTkCheckBox(frame, text="Human-readable text under linear barcodes", variable=show_text_var).grid(row=6, column=1, sticky="w", padx=10, pady=8)

        helper = ctk.CTkFrame(frame, fg_color="transparent")
        helper.grid(row=7, column=1, sticky="ew", padx=10, pady=(2, 8))
        helper.grid_columnconfigure(0, weight=1)
        helper.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(helper, text="Use first label line", fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, command=lambda: (content_entry.delete(0, "end"), content_entry.insert(0, self._get_text_lines()[0] if self._get_text_lines() else ""))).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(helper, text="Use all label text", fg_color=COL_SOFT, text_color=COL_TEXT, hover_color=COL_BORDER, command=lambda: (content_entry.delete(0, "end"), content_entry.insert(0, " | ".join(line for line in self._get_text_lines() if line.strip())))).grid(row=0, column=1, sticky="ew")

        note = ctk.CTkLabel(
            frame,
            text="Supported: Code 128, Code 39, EAN-13, UPC-A, QR Code, Data Matrix and PDF417. EAN/UPC require numeric payloads.",
            justify="left",
            wraplength=430,
            text_color=COL_MUTED,
            font=ctk.CTkFont(size=11),
        )
        note.grid(row=8, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 8))

        def apply() -> None:
            self.barcode_var.set(enabled_var.get())
            self.barcode_type_var.set(type_var.get())
            self.barcode_text_var.set(content_entry.get())
            self.barcode_pos_var.set(position_var.get())
            self.barcode_height_var.set(height_entry.get())
            self.barcode_show_text_var.set(show_text_var.get())
            self.barcode_magnification_var.set(mag_entry.get())
            self._update_all()
            win.destroy()

        self._dialog_buttons(frame, 9, apply, win.destroy)

    def _dialog_entry(self, parent, row: int, label: str, value: str | int | float) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        entry = ctk.CTkEntry(parent)
        entry.insert(0, str(value))
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=8)
        return entry

    def _dialog_option(self, parent, row: int, label: str, variable: tk.StringVar, values: list[str]) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        ctk.CTkOptionMenu(parent, variable=variable, values=values).grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=8)

    def _dialog_buttons(self, parent, row: int, apply_command, cancel_command) -> None:
        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=(16, 10))
        buttons.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(buttons, text="Cancel", fg_color=COL_CARD, hover_color=COL_BORDER, command=cancel_command).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(buttons, text="Apply", command=apply_command).grid(row=0, column=2)

    def _open_zpl_window(self, _=None) -> None:
        if self._zpl_window is not None and self._zpl_window.winfo_exists():
            self._zpl_window.focus()
            self._refresh_zpl_window()
            return
        win = ctk.CTkToplevel(self)
        win.title("Generated ZPL")
        win.geometry("760x520")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        win.protocol("WM_DELETE_WINDOW", self._close_zpl_window)
        self._zpl_window = win

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Generated ZPL", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="Copy", width=86, command=self._copy_zpl).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(header, text="Export .zpl", width=104, fg_color=COL_CARD, hover_color=COL_BORDER, command=self._export_zpl).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(header, text="Import .zpl", width=104, fg_color=COL_CARD, hover_color=COL_BORDER, command=self._import_zpl).grid(row=0, column=3)

        self._zpl_window_box = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Courier New", size=12), fg_color="#141416", text_color="#5bc8e8")
        self._zpl_window_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._refresh_zpl_window()

    def _close_zpl_window(self) -> None:
        if self._zpl_window is not None:
            self._zpl_window.destroy()
        self._zpl_window = None
        self._zpl_window_box = None

    def _refresh_zpl_window(self, text: str | None = None, error: bool = False) -> None:
        if self._zpl_window_box is None:
            return
        if text is None:
            try:
                text = self._build_zpl()
                error = False
            except LabelSpecError as exc:
                text = f"-- Invalid input --\n{exc}\n"
                error = True
        self._zpl_window_box.configure(state="normal")
        self._zpl_window_box.delete("1.0", "end")
        self._zpl_window_box.insert("1.0", text)
        self._zpl_window_box.configure(text_color=COL_ERR if error else "#5bc8e8")
        self._zpl_window_box.configure(state="disabled")

    def _apply_setting_values(self, values: dict[str, object]) -> None:
        if "width_mm" in values:
            self.width_var.set(_short_number(values["width_mm"]))
        if "height_mm" in values:
            self.height_var.set(_short_number(values["height_mm"]))
        if "copies" in values:
            self.copies_var.set(str(values["copies"]))
        if "font_size" in values:
            self.font_size_var.set(int(values["font_size"]))
        if "dpi" in values:
            saved_dpi = int(values["dpi"])
            self.dpi_var.set(next((k for k, v in DPI_OPTIONS.items() if v == saved_dpi), list(DPI_OPTIONS.keys())[1]))
        if "font_style" in values:
            self.font_style_var.set("A0  (smooth)" if values["font_style"] == "A0" else "A  (Bitmap)")
        if "text_lines" in values:
            self._set_text_lines([str(line) for line in values.get("text_lines", [""])])
        elif "line1" in values or "line2" in values:
            self._set_text_lines([str(values.get("line1", "")), str(values.get("line2", ""))])
        if "inverted" in values:
            self.inverted_var.set(bool(values["inverted"]))
        if "border" in values:
            self.border_var.set(bool(values["border"]))
        if "barcode" in values:
            self.barcode_var.set(bool(values["barcode"]))
        if "barcode_text" in values:
            self.barcode_text_var.set(str(values["barcode_text"] or ""))
        if "barcode_type" in values:
            self.barcode_type_var.set(barcode_label(str(values["barcode_type"] or "code128")))
        if "barcode_pos" in values:
            self.barcode_pos_var.set("above  (top)" if values["barcode_pos"] == "above" else "below  (bottom)")
        if "barcode_height" in values:
            self.barcode_height_var.set(str(values["barcode_height"]))
        if "barcode_show_text" in values:
            self.barcode_show_text_var.set(bool(values["barcode_show_text"]))
        if "barcode_magnification" in values:
            self.barcode_magnification_var.set(str(values["barcode_magnification"]))
        if "alignment" in values:
            self.alignment_var.set(str(values["alignment"] or "center"))
        if "rotation" in values:
            self.rotation_var.set(str(values["rotation"] or "normal"))
        if "line_gap" in values:
            self.line_gap_var.set(str(values["line_gap"]))
        if "offset_x" in values:
            self.offset_x_var.set(str(values["offset_x"]))
        if "offset_y" in values:
            self.offset_y_var.set(str(values["offset_y"]))
        if "auto_fit" in values:
            self.auto_fit_var.set(bool(values["auto_fit"]))
        self._update_all()

    def _apply_builtin_preset(self, name: str) -> None:
        try:
            values = preset_settings(name)
        except KeyError:
            self._status("Unknown preset", COL_ERR)
            return
        self._apply_setting_values(values)
        self._status(f"Preset applied: {name}", COL_SUCCESS)

    def _format_text(self, action: str) -> None:
        current = self._get_text_lines()
        if action == "cleanup":
            lines = normalize_editor_text("\n".join(current), remove_empty=False, collapse_spaces=True)
        else:
            try:
                lines = transform_lines(current, action)
            except ValueError as exc:
                self._status(str(exc), COL_ERR)
                return
        self._set_text_lines(list(lines[:MAX_TEXT_LINES]))
        self._update_all()
        self._status("Text updated", COL_SUCCESS)

    def _wrap_text_dialog(self) -> None:
        value = simpledialog.askinteger("Wrap long lines", "Maximum characters per printed line:", parent=self, initialvalue=28, minvalue=4, maxvalue=80)
        if value is None:
            return
        try:
            lines = wrap_lines(self._get_text_lines(), value, max_lines=MAX_TEXT_LINES)
        except ValueError as exc:
            self._status(str(exc), COL_ERR)
            messagebox.showwarning("Invalid wrap width", str(exc), parent=self)
            return
        self._set_text_lines(list(lines))
        self._update_all()
        self._status("Text wrapped", COL_SUCCESS)

    def _reset_layout_options(self) -> None:
        self.font_size_var.set(58)
        self.font_style_var.set("A0  (smooth)")
        self.alignment_var.set("center")
        self.rotation_var.set("normal")
        self.line_gap_var.set("10")
        self.offset_x_var.set("0")
        self.offset_y_var.set("0")
        self.auto_fit_var.set(True)
        self.inverted_var.set(False)
        self.border_var.set(False)
        self._update_all()
        self._status("Layout options reset", COL_SUCCESS)

    def _open_batch_window(self, _=None) -> None:
        if self._batch_window is not None and self._batch_window.winfo_exists():
            self._batch_window.focus()
            return
        win = ctk.CTkToplevel(self)
        win.title("Batch labels")
        win.geometry("740x560")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(2, weight=1)
        win.protocol("WM_DELETE_WINDOW", self._close_batch_window)
        self._batch_window = win

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Batch labels", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w")
        self.batch_barcode_from_first_var = tk.BooleanVar(value=self.barcode_var.get())
        ctk.CTkCheckBox(header, text="Use first line as barcode", variable=self.batch_barcode_from_first_var).grid(row=0, column=1, padx=(8, 0))

        hint = ctk.CTkLabel(
            win,
            text="Enter one or more labels. Blank lines separate labels; lines inside a block stay on the same label.",
            font=ctk.CTkFont(size=11),
            text_color=COL_MUTED,
        )
        hint.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        self._batch_text_box = ctk.CTkTextbox(win, font=ctk.CTkFont(size=15), fg_color="#18181b", wrap="none")
        self._batch_text_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        current = "\n".join(line for line in self._get_text_lines() if line.strip())
        example = current or "ASSET-001\nRack A\n\nASSET-002\nRack B\n\nASSET-003\nRack C"
        self._batch_text_box.insert("1.0", example)

        footer = ctk.CTkFrame(win, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        self.batch_info_lbl = ctk.CTkLabel(footer, text="", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.batch_info_lbl.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(footer, text="Copy batch ZPL", command=self._copy_batch_zpl).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(footer, text="Export .zpl", fg_color=COL_CARD, hover_color=COL_BORDER, command=self._export_batch_zpl).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(footer, text="Close", fg_color=COL_CARD, hover_color=COL_BORDER, command=self._close_batch_window).grid(row=0, column=3)
        self._batch_text_box.bind("<KeyRelease>", lambda _: self._update_batch_info())
        self._update_batch_info()

    def _close_batch_window(self) -> None:
        if self._batch_window is not None:
            self._batch_window.destroy()
        self._batch_window = None
        self._batch_text_box = None

    def _batch_blocks(self) -> tuple[tuple[str, ...], ...]:
        if self._batch_text_box is None:
            return ()
        return parse_batch_blocks(self._batch_text_box.get("1.0", "end-1c"))

    def _update_batch_info(self) -> None:
        if not hasattr(self, "batch_info_lbl"):
            return
        count = len(self._batch_blocks())
        self.batch_info_lbl.configure(text=f"{count} label{'s' if count != 1 else ''} ready")

    def _batch_zpl(self) -> str:
        blocks = self._batch_blocks()
        if not blocks:
            raise LabelSpecError("Batch text does not contain any labels")
        return generate_batch_zpl(self._read_spec(), blocks, barcode_from_first_line=self.batch_barcode_from_first_var.get())

    def _copy_batch_zpl(self) -> None:
        try:
            zpl = self._batch_zpl()
        except LabelSpecError as exc:
            self._status("Batch blocked", COL_ERR)
            messagebox.showwarning("Batch blocked", str(exc), parent=self._batch_window or self)
            return
        self.clipboard_clear()
        self.clipboard_append(zpl)
        self._status("Batch ZPL copied", COL_SUCCESS)

    def _export_batch_zpl(self) -> None:
        try:
            zpl = self._batch_zpl()
        except LabelSpecError as exc:
            self._status("Batch export blocked", COL_ERR)
            messagebox.showwarning("Batch blocked", str(exc), parent=self._batch_window or self)
            return
        path = filedialog.asksaveasfilename(parent=self._batch_window or self, title="Export batch ZPL", defaultextension=".zpl", filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(zpl)
                file.write("\n")
        except OSError as exc:
            self._status("Batch export failed", COL_ERR)
            messagebox.showerror("Batch export failed", str(exc), parent=self._batch_window or self)
            return
        self._status("Batch ZPL exported", COL_SUCCESS)

    # ---- actions -------------------------------------------------------------

    def _on_inline_font_size(self, value) -> None:
        size = int(float(value))
        self.font_size_var.set(size)
        if hasattr(self, "font_size_inline_lbl"):
            self.font_size_inline_lbl.configure(text=str(size))
        self._update_all()

    def _set_barcode_type(self, barcode_type: str) -> None:
        self.barcode_type_var.set(barcode_label(barcode_type))
        if self.barcode_text_var.get().strip():
            self.barcode_var.set(True)
        self._update_all()
        self._status(f"Code type: {barcode_label(barcode_type)}", COL_SUCCESS)

    def _set_size(self, w, h) -> None:
        self.width_var.set(str(w))
        self.height_var.set(str(h))
        self._update_all()

    def _set_alignment(self, alignment: str) -> None:
        self.alignment_var.set(alignment)
        self._update_all()

    def _clear_text(self) -> None:
        self._set_text_lines([""])
        self._update_all()

    def _barcode_from_first_line(self) -> None:
        first = self._get_text_lines()[0] if self._get_text_lines() else ""
        self.barcode_text_var.set(first.strip())
        self.barcode_var.set(bool(first.strip()))
        self._update_all()

    def _toggle_barcode(self) -> None:
        self.barcode_var.set(not self.barcode_var.get())
        self._update_all()

    def _reset_label(self, _=None) -> None:
        self._set_text_lines([""])
        self.barcode_text_var.set("")
        self.barcode_var.set(False)
        self.copies_var.set("1")
        self.template_var.set(self._template_names()[0])
        self._update_all()
        self._status("New label ready", COL_SUCCESS)

    def _on_print(self, _=None) -> None:
        printer = self.printer_var.get()
        if not printer or printer.startswith("(") or printer.startswith("Error") or printer.startswith("[Test mode"):
            self._status("No printer selected", COL_WARN)
            messagebox.showwarning("No printer", "Please select a printer.")
            return
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            self._status("Invalid input", COL_ERR)
            messagebox.showwarning("Invalid input", str(exc))
            return
        if not spec.has_text:
            self._status("No text entered", COL_WARN)
            messagebox.showwarning("No text", "Please fill at least one text line.")
            return
        try:
            send_zpl_to_printer(printer, spec.to_zpl())
        except RuntimeError as exc:
            self._status("Print error", COL_ERR)
            messagebox.showerror("Print error", str(exc))
            return
        except Exception as exc:
            self._status("Error", COL_ERR)
            messagebox.showerror("Error", str(exc))
            return
        label = spec.history_label()
        self._status(f"Printed: {label}", COL_SUCCESS)
        self._add_history(label)
        self._autosave()

    def _refresh_printers(self) -> None:
        printers = get_printers()
        self.printer_dd.configure(values=printers)
        cur = self.printer_var.get()
        if cur not in printers and printers:
            self.printer_var.set(printers[0])
        self._status("Printer list refreshed", COL_SUCCESS)

    def _copy_zpl(self, _=None) -> None:
        try:
            zpl = self._build_zpl()
        except LabelSpecError as exc:
            self._status("Cannot copy invalid ZPL", COL_ERR)
            messagebox.showwarning("Invalid input", str(exc))
            return
        self.clipboard_clear()
        self.clipboard_append(zpl)
        self._status("ZPL copied to clipboard", COL_SUCCESS)

    def _export_zpl(self) -> None:
        try:
            zpl = self._build_zpl()
        except LabelSpecError as exc:
            self._status("Export blocked", COL_ERR)
            messagebox.showwarning("Invalid input", str(exc))
            return
        path = filedialog.asksaveasfilename(parent=self, title="Export ZPL", defaultextension=".zpl", filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(zpl)
                file.write("\n")
        except OSError as exc:
            self._status("Export failed", COL_ERR)
            messagebox.showerror("Export failed", str(exc))
            return
        self._status("ZPL exported", COL_SUCCESS)

    def _import_zpl(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Import ZPL", filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                imported = parse_simple_zpl(file.read(), dpi=self._get_dpi())
        except OSError as exc:
            self._status("Import failed", COL_ERR)
            messagebox.showerror("Import failed", str(exc))
            return
        self._set_text_lines(list(imported.text_lines))
        if imported.width_mm is not None:
            self.width_var.set(_short_number(imported.width_mm))
        if imported.height_mm is not None:
            self.height_var.set(_short_number(imported.height_mm))
        if imported.font_size is not None:
            self.font_size_var.set(imported.font_size)
        self.copies_var.set(str(imported.copies))
        self.inverted_var.set(imported.inverted)
        self.border_var.set(imported.border)
        self.barcode_var.set(imported.barcode)
        self.barcode_type_var.set(barcode_label(imported.barcode_type))
        self.barcode_pos_var.set("above  (top)" if imported.barcode_pos == "above" else "below  (bottom)")
        self.barcode_height_var.set(str(imported.barcode_height))
        self.barcode_show_text_var.set(imported.barcode_show_text)
        self.barcode_magnification_var.set(str(imported.barcode_magnification))
        self.font_style_var.set("A0  (smooth)" if imported.font_style == "A0" else "A  (Bitmap)")
        self.alignment_var.set(imported.alignment)
        self.rotation_var.set(imported.rotation)
        self.line_gap_var.set(str(imported.line_gap))
        self.barcode_text_var.set(imported.barcode_text)
        self._update_all()
        self._status("ZPL imported", COL_SUCCESS)

    def _autosave(self) -> None:
        self.settings["printer"] = self.printer_var.get()
        save_settings(self.settings)

    def _persist_current_settings(self, show_errors: bool = True) -> bool:
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            if show_errors:
                self._status("Invalid input", COL_ERR)
                messagebox.showwarning("Invalid input", str(exc))
            return False
        self.settings.update(self._spec_to_settings(spec))
        self.settings["printer"] = self.printer_var.get()
        save_settings(self.settings)
        return True

    def _spec_to_settings(self, spec: LabelSpec) -> dict[str, object]:
        return {
            "dpi": spec.dpi,
            "width_mm": spec.width_mm,
            "height_mm": spec.height_mm,
            "font_size": spec.font_size,
            "copies": spec.copies,
            "inverted": spec.inverted,
            "border": spec.border,
            "barcode": spec.barcode,
            "barcode_text": spec.barcode_text,
            "barcode_type": spec.barcode_type,
            "barcode_pos": spec.barcode_pos,
            "barcode_height": spec.barcode_height,
            "barcode_show_text": spec.barcode_show_text,
            "barcode_magnification": spec.barcode_magnification,
            "font_style": spec.font_style,
            "text_lines": list(spec.text_lines),
            "alignment": spec.alignment,
            "rotation": spec.rotation,
            "line_gap": spec.line_gap,
            "offset_x": spec.offset_x,
            "offset_y": spec.offset_y,
            "auto_fit": spec.auto_fit,
        }

    def _save_all_settings(self, _=None) -> None:
        if self._persist_current_settings(show_errors=True):
            self._status("Settings saved", COL_SUCCESS)

    # ---- templates/history ---------------------------------------------------

    def _template_names(self) -> list[str]:
        names = list(self.settings.get("templates", {}).keys())
        return names if names else ["- no templates -"]

    def _refresh_template_dropdown(self) -> None:
        self.template_dd.configure(values=self._template_names())

    def _save_template(self) -> None:
        name = simpledialog.askstring("Save template", "Name:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            self._status("Invalid input", COL_ERR)
            messagebox.showwarning("Invalid input", str(exc))
            return
        self.settings.setdefault("templates", {})[name] = self._spec_to_settings(spec)
        save_settings(self.settings)
        self._refresh_template_dropdown()
        self.template_var.set(name)
        self._status(f"Template '{name}' saved", COL_SUCCESS)

    def _load_template(self, name: str) -> None:
        template = self.settings.get("templates", {}).get(name)
        if not template:
            return
        self.width_var.set(str(template.get("width_mm", 57)))
        self.height_var.set(str(template.get("height_mm", 19)))
        self.copies_var.set(str(template.get("copies", 1)))
        self.font_size_var.set(int(template.get("font_size", 58)))
        saved_dpi = template.get("dpi", 300)
        self.dpi_var.set(next((k for k, v in DPI_OPTIONS.items() if v == saved_dpi), list(DPI_OPTIONS.keys())[1]))
        self.font_style_var.set("A0  (smooth)" if template.get("font_style", "A0") == "A0" else "A  (Bitmap)")
        text_lines = template.get("text_lines") or [template.get("line1", ""), template.get("line2", "")]
        self._set_text_lines([str(line) for line in text_lines])
        self.inverted_var.set(bool(template.get("inverted", False)))
        self.border_var.set(bool(template.get("border", False)))
        self.barcode_var.set(bool(template.get("barcode", False)))
        self.barcode_text_var.set(str(template.get("barcode_text", "")))
        self.barcode_type_var.set(barcode_label(str(template.get("barcode_type", "code128"))))
        self.barcode_pos_var.set("above  (top)" if template.get("barcode_pos", "below") == "above" else "below  (bottom)")
        self.barcode_height_var.set(str(template.get("barcode_height", 40)))
        self.barcode_show_text_var.set(bool(template.get("barcode_show_text", True)))
        self.barcode_magnification_var.set(str(template.get("barcode_magnification", 4)))
        self.alignment_var.set(str(template.get("alignment", "center")))
        self.rotation_var.set(str(template.get("rotation", "normal")))
        self.line_gap_var.set(str(template.get("line_gap", 10)))
        self.offset_x_var.set(str(template.get("offset_x", 0)))
        self.offset_y_var.set(str(template.get("offset_y", 0)))
        self.auto_fit_var.set(bool(template.get("auto_fit", True)))
        self._update_all()
        self._status(f"Template '{name}' loaded", COL_SUCCESS)

    def _delete_template(self) -> None:
        name = self.template_var.get()
        if name not in self.settings.get("templates", {}):
            return
        if messagebox.askyesno("Delete?", f"Delete '{name}'?", parent=self):
            del self.settings["templates"][name]
            save_settings(self.settings)
            self._refresh_template_dropdown()
            self.template_var.set(self._template_names()[0])
            self._status(f"Template '{name}' deleted", COL_WARN)

    def _add_history(self, label_text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        self.settings.setdefault("history", []).insert(0, f"[{now}]  {label_text}")
        self.settings["history"] = self.settings["history"][:MAX_HISTORY]
        save_settings(self.settings)
        self._rebuild_history()

    def _rebuild_history(self) -> None:
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.history_frame, text="Recent labels", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        history = self.settings.get("history", [])
        if not history:
            ctk.CTkLabel(self.history_frame, text="No labels printed yet.", font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
            return
        for index, entry in enumerate(history[:5], start=1):
            label = ctk.CTkLabel(self.history_frame, text=entry, font=ctk.CTkFont(size=11), text_color=COL_MUTED, anchor="w", cursor="hand2")
            label.grid(row=index, column=0, sticky="ew", padx=10, pady=1)
            text = entry.split("]  ", 1)[1] if "]  " in entry else entry
            lines = [part.strip() for part in text.replace(" ...", "").split("  |  ")]
            label.bind("<Button-1>", lambda e, value=lines: self._recall(value))

    def _recall(self, lines: list[str]) -> None:
        self._set_text_lines(lines)
        self._update_all()

    # ---- status/window lifecycle -------------------------------------------

    def _status(self, message: str, color=COL_SUCCESS) -> None:
        if self._closing:
            return
        self.status_lbl.configure(text=message, text_color=color)
        if self._status_after_id is not None:
            try:
                self.after_cancel(self._status_after_id)
            except Exception:
                pass
        self._status_after_id = self.after(5000, self._clear_status)

    def _clear_status(self) -> None:
        self._status_after_id = None
        if not self._closing:
            self.status_lbl.configure(text="")

    def _show_quick_guide(self) -> None:
        messagebox.showinfo(
            "Quick guide",
            "1. Select a printer on the left.\n"
            "2. Type one or more label lines. Press Enter for another printed line.\n"
            "3. Tune font, alignment and auto-fit in the main view.\n"
            "4. Use Label and Barcode / QR menus for advanced setup.\n"
            "5. Use View > Show ZPL when you need copy/export/import tools.\n"
            "6. Print with the Print label button or Ctrl+P. Enter never prints.",
            parent=self,
        )

    def _show_shortcuts(self) -> None:
        messagebox.showinfo(
            "Keyboard shortcuts",
            "Enter: add a new line in the label text editor\n"
            "Ctrl+P: print current label\n"
            "Esc: close the app\n"
            "Ctrl+N: start a new label\n"
            "Ctrl+S: save current settings\n"
            "Ctrl+L: label setup\n"
            "Ctrl+T: text options\n"
            "Ctrl+B: barcode / QR options\n"
            "Ctrl+Shift+B: batch labels\n"
            "F5: refresh printer list\n\n"
            "Ctrl+C and Ctrl+Z are intentionally left to normal text editing behavior.",
            parent=self,
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About Zebra Label Tool",
            "Zebra Label Tool\n\nA small local desktop utility for creating, previewing, copying, exporting, and printing simple ZPL labels.",
            parent=self,
        )

    def _safe_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._status_after_id is not None:
            try:
                self.after_cancel(self._status_after_id)
            except Exception:
                pass
            self._status_after_id = None
        try:
            self._persist_current_settings(show_errors=False)
        except Exception:
            pass
        try:
            if self._zpl_window is not None and self._zpl_window.winfo_exists():
                self._zpl_window.destroy()
        except Exception:
            pass
        try:
            if self._batch_window is not None and self._batch_window.winfo_exists():
                self._batch_window.destroy()
        except Exception:
            pass
        self.destroy()


def run() -> None:
    """Start the desktop application."""
    app: ZebraApp | None = None
    try:
        app = ZebraApp()
        app.mainloop()
    except KeyboardInterrupt:
        if app is not None:
            try:
                app._safe_close()
            except Exception:
                pass
