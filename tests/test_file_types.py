from pathlib import Path

import pytest

from duplicate_finder.file_types import (
    ExtensionFilter,
    FileCategory,
    NoExtensionsError,
    parse_extensions,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("pdf", {".pdf"}),
        ("PDF, .docx;txt", {".pdf", ".docx", ".txt"}),
        ("  *.jpg   png ", {".jpg", ".png"}),
    ],
)
def test_typed_extensions_are_normalized(text, expected):
    assert parse_extensions(text) == expected


@pytest.mark.parametrize("text", ["", "  ", ", ;", "*. ."])
def test_text_without_extensions_is_rejected(text):
    with pytest.raises(NoExtensionsError):
        parse_extensions(text)


def test_extension_filter_ignores_case():
    accepts = ExtensionFilter(frozenset({".pdf"}))
    assert accepts(Path("report.PDF"))
    assert not accepts(Path("report.pdf.txt"))
    assert not accepts(Path("pdf"))


def test_every_category_has_normalized_extensions():
    for category in FileCategory:
        assert category.extensions
        assert all(ext.startswith(".") and ext == ext.lower() for ext in category.extensions)
