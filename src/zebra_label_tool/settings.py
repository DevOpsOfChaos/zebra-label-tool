"""Settings persistence for Zebra Label Tool."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .constants import DEFAULT_SETTINGS

APP_DIR_NAME = "zebra-label-tool"


def default_settings_path() -> Path:
    """Return the per-user settings file path."""
    override = os.environ.get("ZEBRA_LABEL_TOOL_SETTINGS")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME / "settings.json"


def merged_settings(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge loaded settings with defaults without mutating DEFAULT_SETTINGS."""
    result = DEFAULT_SETTINGS.copy()
    result["history"] = list(DEFAULT_SETTINGS.get("history", []))
    result["templates"] = dict(DEFAULT_SETTINGS.get("templates", {}))
    if isinstance(data, dict):
        result.update(data)
        result["history"] = list(data.get("history", result["history"]) or [])
        result["templates"] = dict(data.get("templates", result["templates"]) or {})
    return result


def load_settings(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load settings, falling back to defaults on missing or invalid files."""
    settings_path = Path(path) if path is not None else default_settings_path()
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            return merged_settings(data)
        except Exception:
            return merged_settings(None)
    return merged_settings(None)


def save_settings(settings: dict[str, Any], path: str | os.PathLike[str] | None = None) -> None:
    """Persist settings as readable JSON."""
    settings_path = Path(path) if path is not None else default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(merged_settings(settings), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
