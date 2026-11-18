"""Recognizing the operating system's recycle bin / trash folders. No Tk code here.

Files in the trash were already removed by the user, so they are not
compared with the rest of the disk: they would show up as "duplicates" of
the very copies that were kept.
"""

from __future__ import annotations

from pathlib import PurePath

_TRASH_FOLDER_NAMES = frozenset({
    "$recycle.bin",  # Windows Vista and later, one per drive
    "recycler",  # Windows XP (NTFS)
    "recycled",  # Windows 9x / FAT drives
    ".trash",  # macOS, the user's own
    ".trashes",  # macOS, one per external volume
})
_TRASH_FOLDER_PREFIX = ".trash-"  # freedesktop.org (Linux), one per drive: .Trash-1000


def is_trash_folder(path: PurePath) -> bool:
    name = path.name.casefold()
    if name in _TRASH_FOLDER_NAMES or name.startswith(_TRASH_FOLDER_PREFIX):
        return True
    # freedesktop.org home trash: ~/.local/share/Trash
    return name == "trash" and [p.casefold() for p in path.parts[-3:-1]] == [".local", "share"]
