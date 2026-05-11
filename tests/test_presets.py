from zebra_label_tool.label_spec import LabelSpec
from zebra_label_tool.presets import BUILTIN_PRESET_NAMES, BUILTIN_PRESETS, preset_settings


def test_builtin_presets_are_valid_label_specs():
    assert BUILTIN_PRESETS
    for name in BUILTIN_PRESET_NAMES:
        settings = preset_settings(name)
        spec = LabelSpec.from_raw(lines=settings.get("text_lines", [""]), **{k: v for k, v in settings.items() if k != "text_lines"})
        assert spec.to_zpl().startswith("^XA")


def test_preset_settings_returns_copy():
    settings = preset_settings(BUILTIN_PRESET_NAMES[0])
    settings["width_mm"] = 999
    assert preset_settings(BUILTIN_PRESET_NAMES[0])["width_mm"] != 999
