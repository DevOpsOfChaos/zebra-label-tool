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
