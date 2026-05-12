from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"


def test_tauri_desktop_scaffold_files_exist() -> None:
    expected = [
        "package.json",
        "index.html",
        "tsconfig.json",
        "vite.config.ts",
        "src/main.ts",
        "src/styles.css",
        "src/domain.ts",
        "src/zpl.ts",
        "src/bridge.ts",
        "src-tauri/Cargo.toml",
        "src-tauri/tauri.conf.json",
        "src-tauri/src/lib.rs",
        "src-tauri/src/main.rs",
        "src-tauri/capabilities/default.json",
        "src-tauri/icons/icon.ico",
        "scripts/check-prereqs.mjs",
    ]
    missing = [path for path in expected if not (DESKTOP / path).is_file()]
    assert missing == []


def test_tauri_config_uses_repo_desktop_identity() -> None:
    config = json.loads((DESKTOP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    assert config["productName"] == "Zebra Label Tool"
    assert config["identifier"] == "dev.devopsofchaos.zebralabeltool"
    assert config["build"]["devUrl"] == "http://127.0.0.1:1420"
    assert config["app"]["windows"][0]["title"] == "Zebra Label Tool"


def test_tauri_frontend_has_mode_workflow_and_no_tkinter_coupling() -> None:
    main_ts = (DESKTOP / "src" / "main.ts").read_text(encoding="utf-8")
    assert "text_code" in main_ts
    assert "sequence_code" in main_ts
    assert "batch" in main_ts
    assert "customtkinter" not in main_ts.lower()
    assert "tkinter" not in main_ts.lower()


def test_tauri_backend_print_bridge_reuses_python_printing_backend() -> None:
    lib_rs = (DESKTOP / "src-tauri" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "zebra_label_tool.printing" in lib_rs
    assert "send_zpl_to_printer" in lib_rs
    assert "get_printers" in lib_rs


def test_tauri_config_has_windows_icon_and_compact_window_size() -> None:
    config = json.loads((DESKTOP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    window = config["app"]["windows"][0]
    assert window["minWidth"] <= 720
    assert window["width"] <= 1080
    assert config["bundle"]["icon"] == ["icons/icon.ico"]
    assert (DESKTOP / "src-tauri" / "icons" / "icon.ico").is_file()


def test_tauri_frontend_has_responsive_sequence_workflow() -> None:
    domain = (DESKTOP / "src" / "domain.ts").read_text(encoding="utf-8")
    main_ts = (DESKTOP / "src" / "main.ts").read_text(encoding="utf-8")
    zpl_ts = (DESKTOP / "src" / "zpl.ts").read_text(encoding="utf-8")
    css = (DESKTOP / "src" / "styles.css").read_text(encoding="utf-8")
    assert "SequenceKind = 'number' | 'letters'" in domain
    assert "barcodeTemplate" in domain
    assert 'data-seq-preset="letters"' in main_ts
    assert "letterStart" in main_ts
    assert "lettersToIndex" in zpl_ts
    assert "payloadForSequence" in zpl_ts
    assert "@media (max-width: 920px)" in css
    assert "@media (max-width: 620px)" in css


def test_tauri_package_has_doctor_script() -> None:
    package = json.loads((DESKTOP / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["doctor"] == "node scripts/check-prereqs.mjs"
    script = (DESKTOP / "scripts" / "check-prereqs.mjs").read_text(encoding="utf-8")
    assert "cargo" in script
    assert "icon.ico" in script
