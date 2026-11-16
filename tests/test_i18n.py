import string

import pytest

from duplicate_finder.i18n import DEFAULT_LANGUAGE, Language, Translator
from duplicate_finder.models import IssueKind
from duplicate_finder.progress import Stage
from duplicate_finder.settings import Settings, SettingsStore
from duplicate_finder.theme import ThemeMode
from duplicate_finder.translations import CATALOGS


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_english_is_the_default_language():
    assert DEFAULT_LANGUAGE is Language.ENGLISH
    assert Settings().language is Language.ENGLISH


@pytest.mark.parametrize("language", list(Language))
def test_every_language_has_a_complete_catalog(language):
    assert set(CATALOGS[language]) == set(CATALOGS[Language.ENGLISH])


@pytest.mark.parametrize("language", list(Language))
def test_placeholders_match_english(language):
    english = CATALOGS[Language.ENGLISH]
    for key, template in CATALOGS[language].items():
        assert _placeholders(template) == _placeholders(english[key]), key


def test_every_issue_kind_and_stage_has_a_message():
    keys = set(CATALOGS[Language.ENGLISH])
    assert {f"issue.{kind.value}" for kind in IssueKind} <= keys
    assert {f"stage.{stage.value}" for stage in Stage} <= keys
    assert {f"theme.{mode.value}" for mode in ThemeMode} <= keys


def test_translator_formats_placeholders():
    t = Translator(Language.ENGLISH)
    assert t("result.moved", count=1234) == "1,234 files moved."
    assert t("result.moved", count=2) != Translator(Language.PERSIAN)("result.moved", count=2)


def test_missing_translation_falls_back_to_english(monkeypatch):
    monkeypatch.delitem(CATALOGS[Language.PERSIAN], "dialog.close")
    assert Translator(Language.PERSIAN)("dialog.close") == "Close"


def test_only_persian_is_right_to_left():
    assert Language.PERSIAN.is_rtl and not Language.ENGLISH.is_rtl


def test_updating_one_setting_keeps_the_other(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.update(language=Language.PERSIAN)
    store.update(theme_mode=ThemeMode.DARK)

    assert store.load() == Settings(theme_mode=ThemeMode.DARK, language=Language.PERSIAN)


def test_invalid_language_keeps_valid_theme(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme_mode": "dark", "language": "klingon"}', encoding="utf-8")

    assert SettingsStore(path).load() == Settings(theme_mode=ThemeMode.DARK)
