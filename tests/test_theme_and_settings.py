import sys

import pytest

from duplicate_finder.settings import Settings, SettingsStore
from duplicate_finder.theme import (
    ButtonRole,
    DARK_PALETTE,
    LIGHT_PALETTE,
    ThemeMode,
    resolve_palette,
    system_prefers_dark,
)


@pytest.mark.parametrize(
    "mode, system_dark, expected",
    [
        (ThemeMode.SYSTEM, True, DARK_PALETTE),
        (ThemeMode.SYSTEM, False, LIGHT_PALETTE),
        (ThemeMode.LIGHT, True, LIGHT_PALETTE),  # manual choice overrides the OS
        (ThemeMode.DARK, False, DARK_PALETTE),
    ],
)
def test_resolve_palette(mode, system_dark, expected):
    assert resolve_palette(mode, lambda: system_dark) is expected


def test_manual_modes_do_not_query_the_os():
    def fail():
        raise AssertionError("OS should not be queried")

    resolve_palette(ThemeMode.DARK, fail)
    resolve_palette(ThemeMode.LIGHT, fail)


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows fallback")
def test_non_windows_falls_back_to_light():
    assert system_prefers_dark() is False


def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "nested" / "settings.json")
    store.save(Settings(theme_mode=ThemeMode.DARK))

    assert store.load().theme_mode is ThemeMode.DARK


@pytest.mark.parametrize(
    "content", ["", "not json", "[]", '{"theme_mode": "purple"}', '{"other": 1}']
)
def test_corrupt_settings_fall_back_to_system(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")

    assert SettingsStore(path).load().theme_mode is ThemeMode.SYSTEM


def test_missing_settings_default_to_system(tmp_path):
    assert SettingsStore(tmp_path / "none.json").load() == Settings()


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


WCAG_AA = 4.5
PALETTES = [LIGHT_PALETTE, DARK_PALETTE]


@pytest.mark.parametrize("palette", PALETTES)
@pytest.mark.parametrize("role", list(ButtonRole))
def test_button_text_is_readable_in_every_state(palette, role):
    colors = palette.button_colors(role)
    assert _contrast(colors.text, colors.background) >= WCAG_AA
    assert _contrast(colors.text, colors.hover) >= WCAG_AA


@pytest.mark.parametrize("palette", PALETTES)
def test_button_roles_look_different(palette):
    backgrounds = {palette.button_colors(role).background for role in ButtonRole}
    assert len(backgrounds) == len(ButtonRole)


@pytest.mark.parametrize("palette", PALETTES)
def test_warning_text_is_readable(palette):
    assert _contrast(palette.warning, palette.surface) >= WCAG_AA


@pytest.mark.parametrize("palette", PALETTES)
def test_disabled_fields_stand_apart_from_enabled_ones(palette):
    assert _contrast(palette.surface, palette.disabled_field) >= 1.25
