from zebra_label_tool.settings import load_settings, save_settings


def test_load_missing_settings_returns_defaults(tmp_path):
    settings = load_settings(tmp_path / "missing.json")
    assert settings["dpi"] == 300
    assert settings["templates"] == {}


def test_save_and_load_settings_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    save_settings({"dpi": 203, "history": ["x"], "templates": {"A": {"width_mm": 57}}}, path)
    loaded = load_settings(path)
    assert loaded["dpi"] == 203
    assert loaded["history"] == ["x"]
    assert loaded["templates"]["A"]["width_mm"] == 57


def test_load_invalid_settings_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    settings = load_settings(path)
    assert settings["width_mm"] == 57
