"""Theme model: modes, color palettes and OS dark-mode detection. No Tk code here."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ThemeMode(Enum):
    SYSTEM = "system"  # follow the Windows "app mode" setting, live
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class Palette:
    is_dark: bool
    background: str
    surface: str  # input fields, lists
    text: str
    muted_text: str
    disabled_text: str
    border: str
    control: str  # buttons, headings
    control_hover: str
    accent: str
    selection: str
    selection_text: str


LIGHT_PALETTE = Palette(
    is_dark=False,
    background="#f3f3f3",
    surface="#ffffff",
    text="#1b1b1b",
    muted_text="#5c5c5c",
    disabled_text="#a0a0a0",
    border="#c9c9c9",
    control="#fbfbfb",
    control_hover="#e6f0fa",
    accent="#0067c0",
    selection="#cce4f7",
    selection_text="#1b1b1b",
)

DARK_PALETTE = Palette(
    is_dark=True,
    background="#202020",
    surface="#2b2b2b",
    text="#f0f0f0",
    muted_text="#a6a6a6",
    disabled_text="#6b6b6b",
    border="#3f3f3f",
    control="#2d2d2d",
    control_hover="#3a3a3a",
    accent="#4cc2ff",
    selection="#1f4f78",
    selection_text="#ffffff",
)

_PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def system_prefers_dark() -> bool:
    """True if Windows is set to dark mode for apps; False elsewhere or on error."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY) as key:
            apps_use_light_theme, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return False  # key missing on old Windows versions: they are light-only
    return apps_use_light_theme == 0


def resolve_palette(
    mode: ThemeMode, prefers_dark: Callable[[], bool] = system_prefers_dark
) -> Palette:
    """Pick the palette for ``mode``; ``prefers_dark`` is injectable for tests."""
    if mode is ThemeMode.SYSTEM:
        return DARK_PALETTE if prefers_dark() else LIGHT_PALETTE
    return DARK_PALETTE if mode is ThemeMode.DARK else LIGHT_PALETTE
