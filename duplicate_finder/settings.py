"""Persisting user preferences (theme and language) between runs."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from .i18n import DEFAULT_LANGUAGE, Language
from .theme import ThemeMode

APP_DIR_NAME = "DuplicateFinder"


@dataclass(frozen=True)
class Settings:
    theme_mode: ThemeMode = ThemeMode.SYSTEM
    language: Language = DEFAULT_LANGUAGE


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
        """Return saved settings; each invalid or missing field gets its default."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Settings()
        if not isinstance(data, dict):
            return Settings()
        defaults = Settings()
        return Settings(
            theme_mode=_parse_enum(ThemeMode, data.get("theme_mode"), defaults.theme_mode),
            language=_parse_enum(Language, data.get("language"), defaults.language),
        )

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"theme_mode": settings.theme_mode.value, "language": settings.language.value}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update(self, **changes) -> Settings:
        """Change some fields and keep the rest, so saving the theme never
        resets the language (and vice versa)."""
        settings = replace(self.load(), **changes)
        self.save(settings)
        return settings


def _parse_enum(enum_type, raw, default):
    try:
        return enum_type(raw)
    except ValueError:
        return default
