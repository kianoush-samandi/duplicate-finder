"""Language selection and message lookup. No Tk code here.

Adding a language = adding a ``Language`` member and a catalog in
``translations.py``; nothing else changes (Open/Closed).
"""

from __future__ import annotations

from enum import Enum


class Language(Enum):
    ENGLISH = "en"
    PERSIAN = "fa"

    @property
    def native_name(self) -> str:
        """Shown untranslated, so users can always find their own language."""
        return _NATIVE_NAMES[self]

    @property
    def is_rtl(self) -> bool:
        return self in _RTL_LANGUAGES


DEFAULT_LANGUAGE = Language.ENGLISH

_NATIVE_NAMES = {Language.ENGLISH: "English", Language.PERSIAN: "فارسی"}
_RTL_LANGUAGES = {Language.PERSIAN}


class Translator:
    """Looks up a message by key and fills in its placeholders.

    A key missing from a translation falls back to English, so an incomplete
    catalog degrades gracefully instead of crashing the UI.
    """

    def __init__(self, language: Language) -> None:
        from .translations import CATALOGS  # data module; imported lazily to avoid a cycle

        self.language = language
        self._catalog = CATALOGS[language]
        self._fallback = CATALOGS[DEFAULT_LANGUAGE]

    def __call__(self, key: str, **values: object) -> str:
        template = self._catalog.get(key) or self._fallback[key]
        return template.format(**values)
