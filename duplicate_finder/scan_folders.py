"""The set of folders the user chose to scan together. No Tk code here."""

from __future__ import annotations

from pathlib import Path

from .validation import FolderNotSelectedError, parse_scan_folder


class FolderAlreadyIncludedError(ValueError):
    """The folder is already in the list, or inside a folder that is."""


class ScanFolders:
    """An ordered list of folders that never overlap.

    Overlapping folders would make the scanner walk the same files twice, so
    adding a folder that is already covered is rejected, and adding a parent
    of listed folders replaces them.
    """

    def __init__(self) -> None:
        self._folders: list[Path] = []

    @property
    def folders(self) -> tuple[Path, ...]:
        return tuple(self._folders)

    def __len__(self) -> int:
        return len(self._folders)

    def add(self, text: str) -> Path:
        """Validate ``text`` as a folder path and add it; returns the added folder.

        Raises the errors of ``parse_scan_folder`` and FolderAlreadyIncludedError.
        """
        folder = parse_scan_folder(text)
        if any(folder.is_relative_to(existing) for existing in self._folders):
            raise FolderAlreadyIncludedError(str(folder))
        self._folders = [old for old in self._folders if not old.is_relative_to(folder)]
        self._folders.append(folder)
        return folder

    def remove(self, index: int) -> None:
        del self._folders[index]

    def require_any(self) -> tuple[Path, ...]:
        """The folders to scan; raises FolderNotSelectedError if there are none."""
        if not self._folders:
            raise FolderNotSelectedError()
        return self.folders
