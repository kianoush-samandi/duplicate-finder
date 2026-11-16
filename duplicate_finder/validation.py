"""Validation of user input, kept free of GUI code so it can be unit-tested."""

from __future__ import annotations

from pathlib import Path


class FolderNotSelectedError(ValueError):
    """The folder field is empty."""


class NotAFolderError(ValueError):
    """The entered path does not exist or is not a folder."""


def parse_scan_folder(text: str) -> Path:
    """Turn the folder field's text into an absolute folder path.

    An empty field must be rejected explicitly: ``Path("")`` means the
    current working directory, which would silently scan the app's own folder.
    """
    cleaned = text.strip()
    if not cleaned:
        raise FolderNotSelectedError()
    path = Path(cleaned).expanduser()
    if not path.is_dir():
        raise NotAFolderError(cleaned)
    return path.resolve()
