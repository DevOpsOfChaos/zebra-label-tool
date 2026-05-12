from pathlib import Path

APP_SOURCE = Path(__file__).resolve().parents[1] / "src" / "zebra_label_tool" / "app.py"


def _source() -> str:
    return APP_SOURCE.read_text(encoding="utf-8")


def test_enter_is_not_bound_to_printing_at_app_level():
    source = _source()
    assert 'self.bind("<Return>", lambda e: self._on_print())' not in source
    assert 'accelerator="Enter"' not in source
    assert 'self.text_box.bind("<Return>", self._text_box_return)' in source


def test_print_shortcut_is_explicit_ctrl_p():
    source = _source()
    assert 'self.bind("<Control-p>", lambda e: self._on_print())' in source
    assert 'accelerator="Ctrl+P"' in source


def test_text_editing_shortcuts_are_not_stolen_for_zpl():
    source = _source()
    assert 'self.bind("<Control-c>", lambda e: self._copy_zpl())' not in source
    assert 'self.bind("<Control-z>", lambda e: self._open_zpl_window())' not in source
    assert 'accelerator="Ctrl+C"' not in source
    assert 'accelerator="Ctrl+Z"' not in source


def test_main_action_row_has_no_duplicate_parent_argument():
    source = _source()
    assert 'ctk.CTkButton(\n            actions,\n            actions,' not in source


def test_clear_x_resets_label_content_and_barcode():
    source = _source()
    assert "command=self._clear_label_content" in source
    assert "def _clear_label_content" in source
    assert 'self.barcode_text_var.set("")' in source
    assert "self.barcode_var.set(False)" in source
    assert "self.template_var.set(self._template_names()[0])" in source


def test_builtin_presets_with_fields_open_dialog():
    source = _source()
    assert "def _open_preset_input_dialog" in source
    assert "render_preset_settings(name, field_values)" in source


def test_secondary_buttons_do_not_reuse_card_or_soft_background_colors():
    source = _source()
    forbidden = ("fg_color=COL_CARD", "fg_color=COL_SOFT", "fg_color=COL_PANEL", "fg_color=COL_BG")
    lines = source.splitlines()
    for idx, line in enumerate(lines):
        if "CTkButton" not in line:
            continue
        call_lines = []
        for following in lines[idx : idx + 20]:
            call_lines.append(following)
            if ").grid" in following or following.strip() == ")":
                break
        call_source = "\n".join(call_lines)
        assert not any(fragment in call_source for fragment in forbidden)
    assert "def _secondary_button_style" in source
    assert "COL_BUTTON" in source


def test_layout_profile_control_is_available_in_main_gui():
    source = _source()
    assert "self.layout_profile_dd" in source
    assert "def _apply_layout_profile" in source
    assert "layout_profile.code_right" in source


def test_number_sequence_tool_is_menu_based_and_shortcut_visible():
    source = _source()
    assert "def _open_number_sequence_window" in source
    assert 'accelerator="Ctrl+Shift+N"' in source
    assert "action.number_sequence" in source
    assert "generate_number_sequence_zpl" in source


def test_number_sequence_tool_uses_visible_button_styles():
    source = _source()
    assert "sequence.copy_zpl" in source
    assert "sequence.export" in source
    assert "COL_CARD" in source  # cards are allowed for frames, not buttons; contrast test covers buttons.
