from zebra_label_tool.i18n import SUPPORTED_LANGUAGES, normalize_language, translate


def test_i18n_supports_english_and_german():
    assert "en" in SUPPORTED_LANGUAGES
    assert "de" in SUPPORTED_LANGUAGES
    assert translate("de", "menu.settings") == "Einstellungen"
    assert translate("de", "action.clean_whitespace") == "Leerzeichen bereinigen"
    assert translate("de", "layout_profile.code_right") == "Code rechts + Text links"
    assert translate("de", "preset.asset_tag.name") == "Inventaretikett"
    assert translate("de", "preset.qr_device_link.field.url") == "QR-URL / Inhalt"
    assert translate("en", "panel.label_text") == "Label text"


def test_i18n_falls_back_to_english_for_unknown_language():
    assert normalize_language("fr") == "en"
    assert translate("fr", "menu.file") == "File"
