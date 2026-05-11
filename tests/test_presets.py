from zebra_label_tool.label_spec import LabelSpec
from zebra_label_tool.presets import BUILTIN_PRESET_NAMES, BUILTIN_PRESETS, get_builtin_preset, preset_settings, render_preset_settings


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


def test_code_presets_have_user_fields():
    code_presets = [preset for preset in BUILTIN_PRESETS if preset.settings.get("barcode")]
    assert code_presets
    assert all(preset.fields for preset in code_presets)


def test_render_preset_settings_replaces_payload_and_text_placeholders():
    settings = render_preset_settings("Asset tag", {"asset_id": "ASSET-999", "location": "Lab"})
    assert settings["barcode_text"] == "ASSET-999"
    assert settings["text_lines"] == ["ASSET-999", "Lab"]


def test_wifi_preset_builds_standard_wifi_qr_payload():
    settings = render_preset_settings("Wi-Fi QR label", {"ssid": "MyNet", "security": "WPA", "password": "secret"})
    assert settings["barcode_type"] == "qr"
    assert settings["barcode_text"] == "WIFI:S:MyNet;T:WPA;P:secret;;"


def test_get_builtin_preset_exposes_field_metadata():
    preset = get_builtin_preset("QR device link")
    assert preset.needs_input is True
    assert {field.key for field in preset.fields} == {"device", "url"}
