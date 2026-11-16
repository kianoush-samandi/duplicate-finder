"""Persisting user preferences (currently only the theme) between runs."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .theme import ThemeMode

APP_DIR_NAME = "DuplicateFinder"


@dataclass(frozen=True)
class Settings:
    theme_mode: ThemeMode = ThemeMode.SYSTEM


def default_settings_path() -> Path:
    """%APPDATA% on Windows, $XDG_CONFIG_HOME (or ~/.config) elsewhere."""
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_DIR_NAME / "settings.json"


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> Settings:
        """Return saved settings; defaults if the file is missing or corrupt."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return Settings(theme_mode=ThemeMode(data["theme_mode"]))
        except (OSError, ValueError, KeyError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"theme_mode": settings.theme_mode.value}, indent=2), encoding="utf-8"
        )
