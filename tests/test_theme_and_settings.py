import sys

import pytest

from duplicate_finder.settings import Settings, SettingsStore
from duplicate_finder.theme import (
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
