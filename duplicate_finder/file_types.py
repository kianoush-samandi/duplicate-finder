"""Restricting a scan to certain kinds of files. No Tk code here."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FileCategory(Enum):
    """Ready-made choices; the user can also type extensions by hand."""

    DOCUMENTS = "documents"
    PDF = "pdf"
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIO = "audio"
    ARCHIVES = "archives"

    @property
    def extensions(self) -> frozenset[str]:
        return _CATEGORY_EXTENSIONS[self]


_CATEGORY_EXTENSIONS = {
    FileCategory.DOCUMENTS: frozenset({
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls", ".xlsx", ".ods",
        ".csv", ".ppt", ".pptx", ".odp", ".epub",
    }),
    FileCategory.PDF: frozenset({".pdf"}),
    FileCategory.IMAGES: frozenset({
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".svg",
        ".raw", ".cr2", ".nef", ".arw", ".dng",
    }),
    FileCategory.VIDEOS: frozenset({
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp",
    }),
    FileCategory.AUDIO: frozenset({
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".aiff",
    }),
    FileCategory.ARCHIVES: frozenset({
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso",
    }),
}

# Extensions may be separated by commas, semicolons or spaces: "pdf, .docx;txt".
_SEPARATORS = re.compile(r"[\s,;]+")


class NoExtensionsError(ValueError):
    """The text names no file extension."""


def parse_extensions(text: str) -> frozenset[str]:
    """Normalize typed extensions to lower case with a leading dot.

    ``"PDF, .docx *.txt"`` becomes ``{".pdf", ".docx", ".txt"}``.
    Raises NoExtensionsError if nothing usable is left.
    """
    extensions = frozenset(
        "." + word.lstrip("*.").lower()
        for word in _SEPARATORS.split(text)
        if word.lstrip("*.")
    )
    if not extensions:
        raise NoExtensionsError(text)
    return extensions


@dataclass(frozen=True)
class ExtensionFilter:
    """Accepts a path whose extension is one of ``extensions`` (case-insensitive)."""

    extensions: frozenset[str]

    def __call__(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions
