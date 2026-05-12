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
    COL_BUTTON,
    COL_BUTTON_BORDER,
    COL_BUTTON_HOVER,
    COL_BUTTON_TEXT,
    COL_CARD,
    COL_CARD_ALT,
    COL_DANGER_BUTTON,
    COL_DANGER_HOVER,
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
from .i18n import SUPPORTED_LANGUAGES, normalize_language, translate
from .label_spec import LabelSpec, LabelSpecError, MAX_TEXT_LINES
from .layout import calculate_layout_for_lines, mm_to_dots
from .presets import BUILTIN_PRESETS, get_builtin_preset, render_preset_settings
from .preview import LabelPreviewCanvas
from .printing import get_printers, send_zpl_to_printer
from .settings import load_settings, save_settings
from .text_tools import normalize_editor_text, transform_lines, wrap_lines
from .zpl_import import parse_simple_zpl


FONT_STYLE_LABELS = ["A0  (smooth)", "A  (Bitmap)"]
ALIGNMENT_LABELS = ["center", "left", "right", "justify"]
ROTATION_LABELS = ["normal", "90", "180", "270"]
BARCODE_POSITION_KEYS = ["below", "above", "right", "left"]


def _position_label(language: str | None, position: str) -> str:
    key = str(position or "below").strip().split()[0].lower()
    return translate(language, f"position.{key}")


def _position_key(value: str) -> str:
    raw = str(value or "below").strip().lower()
    for key in BARCODE_POSITION_KEYS:
        if raw == key or raw.startswith(key) or raw == translate("en", f"position.{key}").lower() or raw == translate("de", f"position.{key}").lower():
            return key
    return "below"


def _position_labels(language: str | None) -> list[str]:
    return [_position_label(language, key) for key in BARCODE_POSITION_KEYS]


def _layout_profile_labels(language: str | None) -> list[str]:
    return [
        translate(language, "layout_profile.custom"),
        translate(language, "layout_profile.text_only"),
        translate(language, "layout_profile.code_right"),
        translate(language, "layout_profile.code_left"),
        translate(language, "layout_profile.barcode_below"),
        translate(language, "layout_profile.code_above"),
    ]


def _layout_profile_key(language: str | None, value: str) -> str:
    raw = str(value or "").strip().lower()
    keys = ["custom", "text_only", "code_right", "code_left", "barcode_below", "code_above"]
    for key in keys:
        if raw == key or raw == translate(language, f"layout_profile.{key}").lower() or raw == translate("en", f"layout_profile.{key}").lower() or raw == translate("de", f"layout_profile.{key}").lower():
            return key
    return "custom"




def _preset_i18n_key(name: str) -> str:
    return "preset." + "_".join(str(name).lower().replace("-", " ").split())


def _translated_or_fallback(language: str | None, key: str, fallback: str) -> str:
    translated = translate(language, key)
    return fallback if translated == key else translated

def _short_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _secondary_button_style() -> dict[str, object]:
    return {
        "fg_color": COL_BUTTON,
        "text_color": COL_BUTTON_TEXT,
        "border_width": 1,
        "border_color": COL_BUTTON_BORDER,
        "hover_color": COL_BUTTON_HOVER,
    }


def _danger_button_style() -> dict[str, object]:
    return {
        "fg_color": COL_DANGER_BUTTON,
        "text_color": "#ffffff",
        "hover_color": COL_DANGER_HOVER,
    }


class ZebraApp(ctk.CTk):
    """Main desktop application."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COL_BG)
        self.settings = load_settings()
        self.lang = normalize_language(self.settings.get("language"))
        self._language_missing = self.settings.get("language") not in SUPPORTED_LANGUAGES
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
        if self._language_missing:
            self._ask_initial_language()
        self._build_menu()
        self._build_ui()
        self._load_values()
        self.after(120, self._update_all)


    def _t(self, key: str, **kwargs: object) -> str:
        return translate(self.lang, key, **kwargs)

    def _ask_initial_language(self) -> None:
        """Ask for the UI language once before the main window is built."""
        win = ctk.CTkToplevel(self)
        win.title(translate("en", "language.select_title"))
        win.geometry("420x210")
        win.transient(self)
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(win, text="Zebra Label Tool", font=ctk.CTkFont(size=18, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            win,
            text="Choose your language / Sprache auswählen",
            font=ctk.CTkFont(size=13),
            text_color=COL_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
        ctk.CTkLabel(
            win,
            text="You can change this later in Settings.\nDu kannst die Sprache später in den Einstellungen ändern.",
            justify="left",
            text_color=COL_MUTED,
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        buttons = ctk.CTkFrame(win, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)

        def choose(language: str) -> None:
            self.lang = language
            self.settings["language"] = language
            save_settings(self.settings)
            win.destroy()

        ctk.CTkButton(buttons, text="Deutsch", height=36, command=lambda: choose("de")).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(buttons, text="English", height=36, command=lambda: choose("en"), **_secondary_button_style()).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.wait_window(win)

    def _set_language(self, language: str) -> None:
        self.lang = normalize_language(language)
        self.settings["language"] = self.lang
        save_settings(self.settings)
        self.layout_profile_var.set(translate(self.lang, "layout_profile.custom"))
        for child in list(self.winfo_children()):
            child.destroy()
        self._build_menu()
        self._build_ui()
        self._load_values()
        self._update_all()
        self._status(self._t("status.language_saved"), COL_SUCCESS)

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
        self.barcode_pos_var = tk.StringVar(value=_position_label(self.lang, self.settings.get("barcode_pos", "below")))
        self.barcode_height_var = tk.StringVar(value=str(self.settings.get("barcode_height", 40)))
        self.barcode_show_text_var = tk.BooleanVar(value=bool(self.settings.get("barcode_show_text", True)))
        self.barcode_magnification_var = tk.StringVar(value=str(self.settings.get("barcode_magnification", 4)))
        self.alignment_var = tk.StringVar(value=str(self.settings.get("alignment", "center")))
        self.rotation_var = tk.StringVar(value=str(self.settings.get("rotation", "normal")))
        self.line_gap_var = tk.StringVar(value=str(self.settings.get("line_gap", 10)))
        self.offset_x_var = tk.StringVar(value=str(self.settings.get("offset_x", 0)))
        self.offset_y_var = tk.StringVar(value=str(self.settings.get("offset_y", 0)))
        self.auto_fit_var = tk.BooleanVar(value=bool(self.settings.get("auto_fit", True)))
        self.layout_profile_var = tk.StringVar(value=translate(self.lang, "layout_profile.custom"))

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
        file_menu.add_command(label=self._t("action.new_label"), accelerator="Ctrl+N", command=self._reset_label)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("action.import_zpl"), command=self._import_zpl)
        file_menu.add_command(label=self._t("action.export_zpl"), command=self._export_zpl)
        file_menu.add_command(label=self._t("action.copy_zpl"), command=self._copy_zpl)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("action.print"), accelerator="Ctrl+P", command=self._on_print)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("action.exit"), accelerator="Esc", command=self._safe_close)
        menubar.add_cascade(label=self._t("menu.file"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label=self._t("action.clear_content"), command=self._clear_label_content)
        edit_menu.add_command(label=self._t("action.use_barcode_from_label"), command=self._barcode_from_first_line)
        edit_menu.add_separator()
        edit_menu.add_command(label=self._t("action.save_settings"), accelerator="Ctrl+S", command=self._save_all_settings)
        menubar.add_cascade(label=self._t("menu.edit"), menu=edit_menu)

        label_menu = tk.Menu(menubar, tearoff=False)
        label_menu.add_command(label=self._t("action.label_setup"), accelerator="Ctrl+L", command=self._open_label_setup)
        label_menu.add_separator()
        for label, width, height in [("57 x 19 mm", 57, 19), ("57 x 17 mm", 57, 17), ("62 x 29 mm", 62, 29), ("100 x 50 mm", 100, 50)]:
            label_menu.add_command(label=label, command=lambda w=width, h=height: self._set_size(w, h))
        label_menu.add_separator()
        preset_menu = tk.Menu(label_menu, tearoff=False)
        for preset in BUILTIN_PRESETS:
            preset_menu.add_command(label=_translated_or_fallback(self.lang, f"{_preset_i18n_key(preset.name)}.name", preset.name), command=lambda name=preset.name: self._apply_builtin_preset(name))
        label_menu.add_cascade(label=self._t("menu.built_in_presets"), menu=preset_menu)
        menubar.add_cascade(label=self._t("menu.label"), menu=label_menu)

        text_menu = tk.Menu(menubar, tearoff=False)
        text_menu.add_command(label=self._t("action.text_options"), accelerator="Ctrl+T", command=self._open_text_options)
        text_menu.add_separator()
        text_menu.add_command(label=self._t("action.clean_whitespace"), command=lambda: self._format_text("cleanup"))
        text_menu.add_command(label=self._t("action.remove_empty_lines"), command=lambda: self._format_text("remove_empty"))
        text_menu.add_command(label=self._t("action.wrap_lines"), command=self._wrap_text_dialog)
        text_menu.add_separator()
        text_menu.add_command(label=self._t("action.uppercase"), command=lambda: self._format_text("uppercase"))
        text_menu.add_command(label=self._t("action.lowercase"), command=lambda: self._format_text("lowercase"))
        text_menu.add_command(label=self._t("action.title_case"), command=lambda: self._format_text("title_case"))
        text_menu.add_separator()
        for alignment in ALIGNMENT_LABELS:
            text_menu.add_command(label=f"{self._t("field.alignment")}: {alignment}", command=lambda a=alignment: self._set_alignment(a))
        menubar.add_cascade(label=self._t("menu.text"), menu=text_menu)

        barcode_menu = tk.Menu(menubar, tearoff=False)
        barcode_menu.add_command(label=self._t("action.barcode_options"), accelerator="Ctrl+B", command=self._open_barcode_options)
        barcode_menu.add_command(label=self._t("action.use_barcode_from_label"), command=self._barcode_from_first_line)
        barcode_menu.add_command(label=self._t("action.toggle_code"), command=self._toggle_barcode)
        barcode_menu.add_separator()
        type_menu = tk.Menu(barcode_menu, tearoff=False)
        for barcode in BARCODE_TYPES.values():
            type_menu.add_command(label=barcode.label, command=lambda key=barcode.key: self._set_barcode_type(key))
        barcode_menu.add_cascade(label=self._t("menu.symbology"), menu=type_menu)
        position_menu = tk.Menu(barcode_menu, tearoff=False)
        for key in BARCODE_POSITION_KEYS:
            position_menu.add_command(label=_position_label(self.lang, key), command=lambda pos=key: self._set_barcode_position(pos))
        barcode_menu.add_cascade(label=self._t("field.position"), menu=position_menu)
        barcode_menu.add_separator()
        barcode_menu.add_command(label=self._t("action.disable_code"), command=lambda: (self.barcode_var.set(False), self._update_all()))
        menubar.add_cascade(label=self._t("menu.barcode"), menu=barcode_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label=self._t("action.batch"), accelerator="Ctrl+Shift+B", command=self._open_batch_window)
        tools_menu.add_separator()
        tools_menu.add_command(label=self._t("action.reset_layout"), command=self._reset_layout_options)
        menubar.add_cascade(label=self._t("menu.tools"), menu=tools_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label=self._t("action.show_zpl"), command=self._open_zpl_window)
        view_menu.add_command(label=self._t("action.refresh_preview"), accelerator="F5", command=self._update_all)
        menubar.add_cascade(label=self._t("menu.view"), menu=view_menu)

        settings_menu = tk.Menu(menubar, tearoff=False)
        language_menu = tk.Menu(settings_menu, tearoff=False)
        language_menu.add_command(label=self._t("language.german"), command=lambda: self._set_language("de"))
        language_menu.add_command(label=self._t("language.english"), command=lambda: self._set_language("en"))
        settings_menu.add_cascade(label=self._t("language.select_title"), menu=language_menu)
        settings_menu.add_command(label=self._t("action.save_settings"), command=self._save_all_settings)
        menubar.add_cascade(label=self._t("menu.settings"), menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=self._t("action.quick_guide"), command=self._show_quick_guide)
        help_menu.add_command(label=self._t("action.shortcuts"), command=self._show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label=self._t("action.about"), command=self._show_about)
        menubar.add_cascade(label=self._t("menu.help"), menu=help_menu)

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
            text=self._t("app.tagline"),
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
            text=self._t("action.refresh"),
            width=86,
            height=34,
            command=self._refresh_printers,
            **_secondary_button_style(),
        ).grid(row=0, column=1, padx=(0, 10), pady=10)

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        actions.grid_columnconfigure(0, weight=2)
        actions.grid_columnconfigure(1, weight=1)
        self.print_btn = ctk.CTkButton(
            actions,
            text=self._t("action.print_label"),
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COL_ACCENT,
            hover_color=COL_ACCENT_DARK,
            command=self._on_print,
        )
        self.print_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text=self._t("action.new"),
            height=42,
            command=self._reset_label,
            **_secondary_button_style(),
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
            command=self._clear_label_content,
            **_danger_button_style(),
        )
        self.clear_text_btn.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(text_header, text=self._t("panel.label_text"), font=ctk.CTkFont(size=14, weight="bold"), text_color=COL_TEXT).grid(row=0, column=1, sticky="w")
        self.text_counter_lbl = ctk.CTkLabel(text_header, text="", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.text_counter_lbl.grid(row=0, column=2, sticky="e")

        text_controls = ctk.CTkFrame(text_card, fg_color=COL_CARD_ALT, corner_radius=10)
        text_controls.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 8))
        text_controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(text_controls, text=self._t("panel.font"), text_color=COL_MUTED, font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=8)
        self.font_slider = ctk.CTkSlider(text_controls, from_=8, to=160, number_of_steps=152, variable=self.font_size_var, command=self._on_inline_font_size)
        self.font_slider.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        self.font_size_inline_lbl = ctk.CTkLabel(text_controls, text=str(self.font_size_var.get()), width=34, text_color=COL_TEXT)
        self.font_size_inline_lbl.grid(row=0, column=2, padx=(0, 8), pady=8)
        self.inline_alignment = ctk.CTkOptionMenu(text_controls, variable=self.alignment_var, values=ALIGNMENT_LABELS, width=105, height=28, command=lambda _: self._update_all())
        self.inline_alignment.grid(row=0, column=3, padx=(0, 8), pady=8)
        ctk.CTkCheckBox(text_controls, text=self._t("field.auto_fit"), variable=self.auto_fit_var, command=self._update_all).grid(row=0, column=4, padx=(0, 10), pady=8)

        quick_tools = ctk.CTkFrame(text_card, fg_color="transparent")
        quick_tools.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        for col in range(4):
            quick_tools.grid_columnconfigure(col, weight=1)
        ctk.CTkButton(quick_tools, text=self._t("panel.options"), height=28, font=ctk.CTkFont(size=11), command=self._open_text_options, **_secondary_button_style()).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text=self._t("panel.clean"), height=28, font=ctk.CTkFont(size=11), command=lambda: self._format_text("cleanup"), **_secondary_button_style()).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text=self._t("panel.wrap"), height=28, font=ctk.CTkFont(size=11), command=self._wrap_text_dialog, **_secondary_button_style()).grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ctk.CTkButton(quick_tools, text=self._t("panel.case"), height=28, font=ctk.CTkFont(size=11), command=lambda: self._format_text("uppercase"), **_secondary_button_style()).grid(row=0, column=3, sticky="ew")

        ctk.CTkLabel(
            text_card,
            text=self._t("panel.text_hint", max_lines=MAX_TEXT_LINES),
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

        layout_card = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        layout_card.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))
        layout_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(layout_card, text=self._t("panel.layout"), font=ctk.CTkFont(size=12, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(layout_card, text=self._t("panel.size"), font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=1, column=0, sticky="w", padx=(10, 6), pady=(4, 8))
        self.inline_size_var = tk.StringVar(value=self._size_label())
        self.inline_size_dd = ctk.CTkOptionMenu(layout_card, variable=self.inline_size_var, values=["57 x 19 mm", "57 x 17 mm", "62 x 29 mm", "100 x 50 mm", translate(self.lang, "layout_profile.custom")], width=118, height=28, command=self._on_inline_size)
        self.inline_size_dd.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(4, 8))
        ctk.CTkLabel(layout_card, text=self._t("panel.code_area"), font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(4, 8))
        self.inline_code_pos = ctk.CTkOptionMenu(layout_card, variable=self.barcode_pos_var, values=_position_labels(self.lang), width=132, height=28, command=lambda _: self._update_all())
        self.inline_code_pos.grid(row=1, column=3, sticky="ew", padx=(0, 10), pady=(4, 8))
        ctk.CTkLabel(layout_card, text=self._t("panel.code_size"), font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=2, column=0, sticky="w", padx=(10, 6), pady=(0, 10))
        self.inline_code_size = ctk.CTkEntry(layout_card, textvariable=self.barcode_height_var, width=78, height=28)
        self.inline_code_size.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(0, 10))
        self.inline_code_size.bind("<KeyRelease>", lambda _: self._update_all())
        ctk.CTkButton(layout_card, text=self._t("action.more"), height=28, command=self._open_label_setup, **_secondary_button_style()).grid(row=2, column=3, sticky="ew", padx=(0, 10), pady=(0, 10))
        ctk.CTkLabel(layout_card, text=self._t("panel.layout_profile"), font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=3, column=0, sticky="w", padx=(10, 6), pady=(0, 10))
        self.layout_profile_dd = ctk.CTkOptionMenu(
            layout_card,
            variable=self.layout_profile_var,
            values=_layout_profile_labels(self.lang),
            height=28,
            command=self._apply_layout_profile,
        )
        self.layout_profile_dd.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=(0, 10))

        template_card = ctk.CTkFrame(left, fg_color=COL_CARD, corner_radius=12, border_width=1, border_color=COL_BORDER)
        template_card.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 12))
        template_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(template_card, text=self._t("panel.templates"), font=ctk.CTkFont(size=12, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))
        self.template_var = tk.StringVar(value=self._t("template.choose"))
        self.template_dd = ctk.CTkOptionMenu(template_card, variable=self.template_var, values=self._template_names(), height=30, command=self._load_template)
        self.template_dd.grid(row=1, column=0, sticky="ew", padx=(10, 6), pady=(2, 10))
        ctk.CTkButton(template_card, text=self._t("action.save"), width=78, height=30, command=self._save_template, **_secondary_button_style()).grid(row=1, column=1, padx=(0, 6), pady=(2, 10))
        ctk.CTkButton(template_card, text=self._t("action.delete"), width=72, height=30, command=self._delete_template, **_danger_button_style()).grid(row=1, column=2, padx=(0, 10), pady=(2, 10))

    def _build_right_panel(self) -> None:
        right = ctk.CTkFrame(self, fg_color=COL_PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=self._t("panel.live_preview"), font=ctk.CTkFont(size=16, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w")
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
        ctk.CTkLabel(summary, text=self._t("panel.current_setup"), font=ctk.CTkFont(size=12, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        self.setup_summary_lbl = ctk.CTkLabel(summary, text="", justify="left", anchor="w", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.setup_summary_lbl.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 0))
        self.quality_lbl = ctk.CTkLabel(summary, text="", justify="left", anchor="w", font=ctk.CTkFont(size=11), text_color=COL_MUTED)
        self.quality_lbl.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

        footer = ctk.CTkFrame(right, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.preview_hint = ctk.CTkLabel(
            footer,
            text=self._t("panel.preview_tip"),
            font=ctk.CTkFont(size=11),
            text_color=COL_MUTED,
        )
        self.preview_hint.grid(row=0, column=0, sticky="w")


    def _apply_layout_profile(self, value: str) -> None:
        key = _layout_profile_key(self.lang, value)
        self.layout_profile_var.set(translate(self.lang, f"layout_profile.{key}"))
        if key == "text_only":
            self.barcode_var.set(False)
            self.barcode_text_var.set("")
            self.barcode_pos_var.set(_position_label(self.lang, "below"))
        elif key == "code_right":
            self.barcode_var.set(True)
            self.barcode_pos_var.set(_position_label(self.lang, "right"))
            self.barcode_height_var.set("120")
            if not self.barcode_text_var.get().strip():
                payload = " | ".join(line for line in self._get_text_lines() if line.strip())
                self.barcode_text_var.set(payload)
        elif key == "code_left":
            self.barcode_var.set(True)
            self.barcode_pos_var.set(_position_label(self.lang, "left"))
            self.barcode_height_var.set("120")
            if not self.barcode_text_var.get().strip():
                payload = " | ".join(line for line in self._get_text_lines() if line.strip())
                self.barcode_text_var.set(payload)
        elif key == "barcode_below":
            self.barcode_var.set(True)
            self.barcode_type_var.set(barcode_label("code128"))
            self.barcode_pos_var.set(_position_label(self.lang, "below"))
            self.barcode_height_var.set("48")
            if not self.barcode_text_var.get().strip():
                first_line = next((line for line in self._get_text_lines() if line.strip()), "")
                self.barcode_text_var.set(first_line)
        elif key == "code_above":
            self.barcode_var.set(True)
            self.barcode_pos_var.set(_position_label(self.lang, "above"))
            self.barcode_height_var.set("90")
            if not self.barcode_text_var.get().strip():
                payload = " | ".join(line for line in self._get_text_lines() if line.strip())
                self.barcode_text_var.set(payload)
        if hasattr(self, "inline_code_pos"):
            self.inline_code_pos.configure(values=_position_labels(self.lang))
        self._update_all()
        self._status(self._t("status.layout_profile_applied"), COL_SUCCESS)

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
        self.barcode_pos_var.set(_position_label(self.lang, s.get("barcode_pos", "below")))
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
        if hasattr(self, "inline_size_var"):
            self.inline_size_var.set(self._size_label())
        if hasattr(self, "inline_code_pos"):
            self.inline_code_pos.configure(values=_position_labels(self.lang))
        if hasattr(self, "layout_profile_dd"):
            self.layout_profile_dd.configure(values=_layout_profile_labels(self.lang))
            self.layout_profile_var.set(translate(self.lang, "layout_profile.custom"))

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
            barcode_pos=_position_key(self.barcode_pos_var.get()),
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
            self.preview_info.configure(text=self._t("message.input_error", error=exc))
            self.text_counter_lbl.configure(text="invalid")
            self.setup_summary_lbl.configure(text=self._t("message.invalid_input", error=exc))
            if hasattr(self, "quality_lbl"):
                self.quality_lbl.configure(text=self._t("message.fix_input"), text_color=COL_ERR)
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
            warnings.append(self._t("message.auto_fit", size=layout.fs))
        if not spec.has_text:
            warnings.append(self._t("message.no_text"))
        if spec.active_barcode and len(spec.barcode_text.strip()) > 32:
            warnings.append(self._t("message.long_code"))
        if len(spec.text_lines) >= MAX_TEXT_LINES:
            warnings.append(self._t("message.max_lines", max_lines=MAX_TEXT_LINES))
        if warnings:
            self.quality_lbl.configure(text=self._t("message.warning", warnings=" | ".join(warnings)), text_color=COL_WARN)
        else:
            self.quality_lbl.configure(text=self._t("message.ready_preview"), text_color=COL_MUTED)

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
        win = self._dialog(self._t("dialog.label_setup"), 480, 510)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        width_entry = self._dialog_entry(frame, 0, self._t("field.width"), self.width_var.get())
        height_entry = self._dialog_entry(frame, 1, self._t("field.height"), self.height_var.get())
        copies_entry = self._dialog_entry(frame, 2, self._t("field.copies"), self.copies_var.get())
        dpi_var = tk.StringVar(value=self.dpi_var.get())
        ctk.CTkLabel(frame, text=self._t("field.printer_dpi")).grid(row=3, column=0, sticky="w", padx=10, pady=8)
        ctk.CTkOptionMenu(frame, variable=dpi_var, values=list(DPI_OPTIONS.keys())).grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        border_var = tk.BooleanVar(value=self.border_var.get())
        inverted_var = tk.BooleanVar(value=self.inverted_var.get())
        ctk.CTkCheckBox(frame, text=self._t("field.draw_border"), variable=border_var).grid(row=4, column=1, sticky="w", padx=10, pady=8)
        ctk.CTkCheckBox(frame, text=self._t("field.inverted_label"), variable=inverted_var).grid(row=5, column=1, sticky="w", padx=10, pady=8)
        code_pos_var = tk.StringVar(value=self.barcode_pos_var.get())
        self._dialog_option(frame, 6, self._t("field.position"), code_pos_var, _position_labels(self.lang))
        code_size_entry = self._dialog_entry(frame, 7, self._t("field.code_size"), self.barcode_height_var.get())

        presets = ctk.CTkFrame(frame, fg_color="transparent")
        presets.grid(row=8, column=0, columnspan=2, sticky="ew", padx=10, pady=(6, 10))
        for col, (label, w, h) in enumerate([("57x19", 57, 19), ("57x17", 57, 17), ("62x29", 62, 29), ("100x50", 100, 50)]):
            presets.grid_columnconfigure(col, weight=1)
            ctk.CTkButton(presets, text=label, command=lambda ww=w, hh=h: (self._set_entry(width_entry, ww), self._set_entry(height_entry, hh)), **_secondary_button_style()).grid(row=0, column=col, sticky="ew", padx=3)

        def apply() -> None:
            self.width_var.set(width_entry.get())
            self.height_var.set(height_entry.get())
            self.copies_var.set(copies_entry.get())
            self.dpi_var.set(dpi_var.get())
            self.border_var.set(border_var.get())
            self.inverted_var.set(inverted_var.get())
            self.barcode_pos_var.set(code_pos_var.get())
            self.barcode_height_var.set(code_size_entry.get())
            if hasattr(self, "inline_code_pos"):
                self.inline_code_pos.configure(values=_position_labels(self.lang))
            self._update_all()
            win.destroy()

        self._dialog_buttons(frame, 9, apply, win.destroy)

    def _open_text_options(self, _=None) -> None:
        win = self._dialog(self._t("dialog.text_options"), 500, 520)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        font_size = ctk.CTkSlider(frame, from_=8, to=160, number_of_steps=152)
        font_size.set(int(self.font_size_var.get()))
        ctk.CTkLabel(frame, text=self._t("field.font_size")).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        font_size.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        font_size_lbl = ctk.CTkLabel(frame, text=str(int(font_size.get())), width=40)
        font_size_lbl.grid(row=0, column=2, padx=10, pady=8)
        font_size.configure(command=lambda value: font_size_lbl.configure(text=str(int(float(value)))))

        font_style_var = tk.StringVar(value=self.font_style_var.get())
        self._dialog_option(frame, 1, self._t("field.font_style"), font_style_var, FONT_STYLE_LABELS)
        alignment_var = tk.StringVar(value=self.alignment_var.get())
        self._dialog_option(frame, 2, self._t("field.alignment"), alignment_var, ALIGNMENT_LABELS)
        rotation_var = tk.StringVar(value=self.rotation_var.get())
        self._dialog_option(frame, 3, self._t("field.rotation"), rotation_var, ROTATION_LABELS)
        line_gap = self._dialog_entry(frame, 4, self._t("field.line_gap"), self.line_gap_var.get())
        offset_x = self._dialog_entry(frame, 5, self._t("field.offset_x"), self.offset_x_var.get())
        offset_y = self._dialog_entry(frame, 6, self._t("field.offset_y"), self.offset_y_var.get())
        auto_fit_var = tk.BooleanVar(value=self.auto_fit_var.get())
        ctk.CTkCheckBox(frame, text=self._t("field.auto_fit"), variable=auto_fit_var).grid(row=7, column=1, sticky="w", padx=10, pady=8)

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
        win = self._dialog(self._t("dialog.barcode_options"), 540, 520)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        enabled_var = tk.BooleanVar(value=self.barcode_var.get())
        type_var = tk.StringVar(value=self.barcode_type_var.get())
        content_entry = self._dialog_entry(frame, 2, self._t("field.payload"), self.barcode_text_var.get())
        position_var = tk.StringVar(value=self.barcode_pos_var.get())
        height_entry = self._dialog_entry(frame, 4, self._t("field.code_size"), self.barcode_height_var.get())
        mag_entry = self._dialog_entry(frame, 5, self._t("field.magnification"), self.barcode_magnification_var.get())
        show_text_var = tk.BooleanVar(value=self.barcode_show_text_var.get())

        ctk.CTkCheckBox(frame, text=self._t("field.print_code"), variable=enabled_var).grid(row=0, column=1, sticky="w", padx=10, pady=10)
        self._dialog_option(frame, 1, self._t("field.symbology"), type_var, BARCODE_TYPE_LABELS)
        self._dialog_option(frame, 3, self._t("field.position"), position_var, _position_labels(self.lang))
        ctk.CTkCheckBox(frame, text=self._t("field.show_human"), variable=show_text_var).grid(row=6, column=1, sticky="w", padx=10, pady=8)

        helper = ctk.CTkFrame(frame, fg_color="transparent")
        helper.grid(row=7, column=1, sticky="ew", padx=10, pady=(2, 8))
        helper.grid_columnconfigure(0, weight=1)
        helper.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(helper, text=self._t("field.use_first_line"), command=lambda: (content_entry.delete(0, "end"), content_entry.insert(0, self._get_text_lines()[0] if self._get_text_lines() else "")), **_secondary_button_style()).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(helper, text=self._t("field.use_all_text"), command=lambda: (content_entry.delete(0, "end"), content_entry.insert(0, " | ".join(line for line in self._get_text_lines() if line.strip()))), **_secondary_button_style()).grid(row=0, column=1, sticky="ew")

        note = ctk.CTkLabel(
            frame,
            text=self._t("help.supported_codes"),
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
        ctk.CTkButton(buttons, text=self._t("action.cancel"), command=cancel_command, **_secondary_button_style()).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(buttons, text=self._t("action.apply"), command=apply_command).grid(row=0, column=2)

    def _open_zpl_window(self, _=None) -> None:
        if self._zpl_window is not None and self._zpl_window.winfo_exists():
            self._zpl_window.focus()
            self._refresh_zpl_window()
            return
        win = ctk.CTkToplevel(self)
        win.title(self._t("dialog.generated_zpl"))
        win.geometry("760x520")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        win.protocol("WM_DELETE_WINDOW", self._close_zpl_window)
        self._zpl_window = win

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=self._t("dialog.generated_zpl"), font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text=self._t("action.copy"), width=86, command=self._copy_zpl).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(header, text=self._t("action.export_zpl_short"), width=104, command=self._export_zpl, **_secondary_button_style()).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(header, text=self._t("action.import_zpl_short"), width=104, command=self._import_zpl, **_secondary_button_style()).grid(row=0, column=3)

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
            self.barcode_pos_var.set(_position_label(self.lang, str(values["barcode_pos"])))
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
            preset = get_builtin_preset(name)
        except KeyError:
            self._status(self._t("message.unknown_preset"), COL_ERR)
            return
        if preset.fields:
            self._open_preset_input_dialog(name)
            return
        self._apply_setting_values(render_preset_settings(name))
        self.template_var.set(self._template_names()[0])
        self._status(self._t("status.layout_profile_applied"), COL_SUCCESS)

    def _open_preset_input_dialog(self, name: str) -> None:
        try:
            preset = get_builtin_preset(name)
        except KeyError:
            self._status(self._t("message.unknown_preset"), COL_ERR)
            return
        height = min(640, 230 + len(preset.fields) * 66)
        preset_key = _preset_i18n_key(preset.name)
        preset_title = _translated_or_fallback(self.lang, f"{preset_key}.name", preset.name)
        preset_description = _translated_or_fallback(self.lang, f"{preset_key}.description", preset.description)
        win = self._dialog(preset_title, 540, height)
        frame = ctk.CTkFrame(win, fg_color=COL_PANEL)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=preset_title, font=ctk.CTkFont(size=16, weight="bold"), text_color=COL_TEXT).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(frame, text=preset_description, justify="left", wraplength=470, font=ctk.CTkFont(size=11), text_color=COL_MUTED).grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 12))

        entries: dict[str, ctk.CTkEntry] = {}
        row = 2
        for field in preset.fields:
            field_label = _translated_or_fallback(self.lang, f"{preset_key}.field.{field.key}", field.label)
            field_help = _translated_or_fallback(self.lang, f"{preset_key}.field.{field.key}.help", field.help_text) if field.help_text else ""
            ctk.CTkLabel(frame, text=field_label).grid(row=row, column=0, sticky="w", padx=10, pady=(8, 2))
            entry = ctk.CTkEntry(frame)
            entry.insert(0, field.default)
            entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=(8, 2))
            entries[field.key] = entry
            row += 1
            if field_help:
                ctk.CTkLabel(frame, text=field_help, justify="left", wraplength=330, font=ctk.CTkFont(size=10), text_color=COL_MUTED).grid(row=row, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 4))
                row += 1

        def apply() -> None:
            field_values = {key: entry.get().strip() for key, entry in entries.items()}
            self._apply_setting_values(render_preset_settings(name, field_values))
            self.template_var.set(self._template_names()[0])
            self._status(self._t("status.layout_profile_applied"), COL_SUCCESS)
            win.destroy()

        self._dialog_buttons(frame, row, apply, win.destroy)

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
        self._status(self._t("status.text_updated"), COL_SUCCESS)

    def _wrap_text_dialog(self) -> None:
        value = simpledialog.askinteger(self._t("dialog.wrap_lines"), self._t("dialog.wrap_prompt"), parent=self, initialvalue=28, minvalue=4, maxvalue=80)
        if value is None:
            return
        try:
            lines = wrap_lines(self._get_text_lines(), value, max_lines=MAX_TEXT_LINES)
        except ValueError as exc:
            self._status(str(exc), COL_ERR)
            messagebox.showwarning(self._t("message.invalid_wrap_width"), str(exc), parent=self)
            return
        self._set_text_lines(list(lines))
        self._update_all()
        self._status(self._t("status.text_wrapped"), COL_SUCCESS)

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
        self._status(self._t("status.layout_reset"), COL_SUCCESS)

    def _open_batch_window(self, _=None) -> None:
        if self._batch_window is not None and self._batch_window.winfo_exists():
            self._batch_window.focus()
            return
        win = ctk.CTkToplevel(self)
        win.title(self._t("dialog.batch_labels"))
        win.geometry("740x560")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(2, weight=1)
        win.protocol("WM_DELETE_WINDOW", self._close_batch_window)
        self._batch_window = win

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=self._t("dialog.batch_labels"), font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w")
        self.batch_barcode_from_first_var = tk.BooleanVar(value=self.barcode_var.get())
        ctk.CTkCheckBox(header, text=self._t("batch.use_first_line"), variable=self.batch_barcode_from_first_var).grid(row=0, column=1, padx=(8, 0))

        hint = ctk.CTkLabel(
            win,
            text=self._t("batch.hint"),
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
        ctk.CTkButton(footer, text=self._t("action.copy_batch_zpl"), command=self._copy_batch_zpl).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(footer, text=self._t("action.export_zpl_short"), command=self._export_batch_zpl, **_secondary_button_style()).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(footer, text=self._t("action.close"), command=self._close_batch_window, **_secondary_button_style()).grid(row=0, column=3)
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
        self.batch_info_lbl.configure(text=self._t("batch.count", count=count, suffix="s" if self.lang == "en" and count != 1 else ("en" if self.lang == "de" and count != 1 else "")))

    def _batch_zpl(self) -> str:
        blocks = self._batch_blocks()
        if not blocks:
            raise LabelSpecError("Batch text does not contain any labels")
        return generate_batch_zpl(self._read_spec(), blocks, barcode_from_first_line=self.batch_barcode_from_first_var.get())

    def _copy_batch_zpl(self) -> None:
        try:
            zpl = self._batch_zpl()
        except LabelSpecError as exc:
            self._status(self._t("message.batch_blocked"), COL_ERR)
            messagebox.showwarning(self._t("message.batch_blocked"), str(exc), parent=self._batch_window or self)
            return
        self.clipboard_clear()
        self.clipboard_append(zpl)
        self._status(self._t("status.batch_copied"), COL_SUCCESS)

    def _export_batch_zpl(self) -> None:
        try:
            zpl = self._batch_zpl()
        except LabelSpecError as exc:
            self._status(self._t("message.batch_blocked"), COL_ERR)
            messagebox.showwarning(self._t("message.batch_blocked"), str(exc), parent=self._batch_window or self)
            return
        path = filedialog.asksaveasfilename(parent=self._batch_window or self, title=self._t("action.export_zpl"), defaultextension=".zpl", filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(zpl)
                file.write("\n")
        except OSError as exc:
            self._status(self._t("message.export_failed"), COL_ERR)
            messagebox.showerror(self._t("message.export_failed"), str(exc), parent=self._batch_window or self)
            return
        self._status(self._t("status.batch_exported"), COL_SUCCESS)

    # ---- actions -------------------------------------------------------------

    def _size_label(self) -> str:
        try:
            width = _short_number(float(str(self.width_var.get() or 57).replace(",", ".")))
            height = _short_number(float(str(self.height_var.get() or 19).replace(",", ".")))
        except (TypeError, ValueError):
            return translate(self.lang, "layout_profile.custom")
        label = f"{width} x {height} mm"
        return label if label in {"57 x 19 mm", "57 x 17 mm", "62 x 29 mm", "100 x 50 mm"} else translate(self.lang, "layout_profile.custom")

    def _on_inline_size(self, value: str) -> None:
        sizes = {"57 x 19 mm": (57, 19), "57 x 17 mm": (57, 17), "62 x 29 mm": (62, 29), "100 x 50 mm": (100, 50)}
        if value in sizes:
            self._set_size(*sizes[value])
        else:
            self._open_label_setup()

    def _set_barcode_position(self, position: str) -> None:
        self.barcode_pos_var.set(_position_label(self.lang, position))
        self._update_all()

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
        self._status(f"{self._t("field.symbology")}: {barcode_label(barcode_type)}", COL_SUCCESS)

    def _set_size(self, w, h) -> None:
        self.width_var.set(str(w))
        self.height_var.set(str(h))
        if hasattr(self, "inline_size_var"):
            self.inline_size_var.set(self._size_label())
        self._update_all()

    def _set_alignment(self, alignment: str) -> None:
        self.alignment_var.set(alignment)
        self._update_all()

    def _clear_text(self) -> None:
        self._clear_label_content()

    def _clear_label_content(self) -> None:
        self._set_text_lines([""])
        self.barcode_text_var.set("")
        self.barcode_var.set(False)
        self.template_var.set(self._template_names()[0])
        self._update_all()
        self._status(self._t("status.content_cleared"), COL_SUCCESS)

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
        self._status(self._t("status.new_ready"), COL_SUCCESS)

    def _on_print(self, _=None) -> None:
        printer = self.printer_var.get()
        if not printer or printer.startswith("(") or printer.startswith("Error") or printer.startswith("[Test mode"):
            self._status(self._t("message.no_printer_title"), COL_WARN)
            messagebox.showwarning(self._t("message.no_printer_title"), self._t("message.no_printer"))
            return
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            self._status(self._t("message.invalid_input", error=""), COL_ERR)
            messagebox.showwarning(self._t("message.invalid_input", error=""), str(exc))
            return
        if not spec.has_text:
            self._status(self._t("message.no_text_title"), COL_WARN)
            messagebox.showwarning(self._t("message.no_text_title"), self._t("message.no_text_body"))
            return
        try:
            send_zpl_to_printer(printer, spec.to_zpl())
        except RuntimeError as exc:
            self._status(self._t("message.print_error"), COL_ERR)
            messagebox.showerror(self._t("message.print_error"), str(exc))
            return
        except Exception as exc:
            self._status(self._t("message.error"), COL_ERR)
            messagebox.showerror(self._t("message.error"), str(exc))
            return
        label = spec.history_label()
        self._status(self._t("status.printed", label=label), COL_SUCCESS)
        self._autosave()

    def _refresh_printers(self) -> None:
        printers = get_printers()
        self.printer_dd.configure(values=printers)
        cur = self.printer_var.get()
        if cur not in printers and printers:
            self.printer_var.set(printers[0])
        self._status(self._t("status.printers_refreshed"), COL_SUCCESS)

    def _copy_zpl(self, _=None) -> None:
        try:
            zpl = self._build_zpl()
        except LabelSpecError as exc:
            self._status(self._t("message.invalid_input", error=""), COL_ERR)
            messagebox.showwarning(self._t("message.invalid_input", error=""), str(exc))
            return
        self.clipboard_clear()
        self.clipboard_append(zpl)
        self._status(self._t("status.zpl_copied"), COL_SUCCESS)

    def _export_zpl(self) -> None:
        try:
            zpl = self._build_zpl()
        except LabelSpecError as exc:
            self._status(self._t("message.invalid_input", error=""), COL_ERR)
            messagebox.showwarning(self._t("message.invalid_input", error=""), str(exc))
            return
        path = filedialog.asksaveasfilename(parent=self, title=self._t("action.export_zpl"), defaultextension=".zpl", filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(zpl)
                file.write("\n")
        except OSError as exc:
            self._status(self._t("message.export_failed"), COL_ERR)
            messagebox.showerror(self._t("message.export_failed"), str(exc))
            return
        self._status(self._t("status.zpl_exported"), COL_SUCCESS)

    def _import_zpl(self) -> None:
        path = filedialog.askopenfilename(parent=self, title=self._t("action.import_zpl"), filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                imported = parse_simple_zpl(file.read(), dpi=self._get_dpi())
        except OSError as exc:
            self._status(self._t("message.import_failed"), COL_ERR)
            messagebox.showerror(self._t("message.import_failed"), str(exc))
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
        self.barcode_pos_var.set(_position_label(self.lang, imported.barcode_pos))
        self.barcode_height_var.set(str(imported.barcode_height))
        self.barcode_show_text_var.set(imported.barcode_show_text)
        self.barcode_magnification_var.set(str(imported.barcode_magnification))
        self.font_style_var.set("A0  (smooth)" if imported.font_style == "A0" else "A  (Bitmap)")
        self.alignment_var.set(imported.alignment)
        self.rotation_var.set(imported.rotation)
        self.line_gap_var.set(str(imported.line_gap))
        self.barcode_text_var.set(imported.barcode_text)
        self._update_all()
        self._status(self._t("status.zpl_imported"), COL_SUCCESS)

    def _autosave(self) -> None:
        self.settings["printer"] = self.printer_var.get()
        save_settings(self.settings)

    def _persist_current_settings(self, show_errors: bool = True) -> bool:
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            if show_errors:
                self._status(self._t("message.invalid_input", error=""), COL_ERR)
                messagebox.showwarning(self._t("message.invalid_input", error=""), str(exc))
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
            self._status(self._t("status.settings_saved"), COL_SUCCESS)

    # ---- templates/history ---------------------------------------------------

    def _template_names(self) -> list[str]:
        names = list(self.settings.get("templates", {}).keys())
        return names if names else [self._t("template.none")]

    def _refresh_template_dropdown(self) -> None:
        self.template_dd.configure(values=self._template_names())

    def _save_template(self) -> None:
        name = simpledialog.askstring(self._t("action.save"), self._t("dialog.template_name"), parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        try:
            spec = self._read_spec()
        except LabelSpecError as exc:
            self._status(self._t("message.invalid_input", error=""), COL_ERR)
            messagebox.showwarning(self._t("message.invalid_input", error=""), str(exc))
            return
        self.settings.setdefault("templates", {})[name] = self._spec_to_settings(spec)
        save_settings(self.settings)
        self._refresh_template_dropdown()
        self.template_var.set(name)
        self._status(self._t("message.template_saved", name=name), COL_SUCCESS)

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
        self.barcode_pos_var.set(_position_label(self.lang, template.get("barcode_pos", "below")))
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
        self._status(self._t("message.template_loaded", name=name), COL_SUCCESS)

    def _delete_template(self) -> None:
        name = self.template_var.get()
        if name not in self.settings.get("templates", {}):
            return
        if messagebox.askyesno(self._t("message.delete_template_title"), self._t("message.delete_template_body", name=name), parent=self):
            del self.settings["templates"][name]
            save_settings(self.settings)
            self._refresh_template_dropdown()
            self.template_var.set(self._template_names()[0])
            self._status(self._t("message.template_deleted", name=name), COL_WARN)

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
        messagebox.showinfo(self._t("dialog.quick_guide"), self._t("guide.body"), parent=self)

    def _show_shortcuts(self) -> None:
        messagebox.showinfo(self._t("dialog.shortcuts"), self._t("shortcuts.body"), parent=self)

    def _show_about(self) -> None:
        messagebox.showinfo(self._t("dialog.about"), self._t("about.body"), parent=self)

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
