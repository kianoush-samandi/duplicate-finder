"""Spotting files that are risky to remove. No Tk code here.

A duplicate of a program, a system component or an application's own data
may still be in use: removing "the extra copy" can break that program or the
operating system. Such files are flagged so the GUI can list them apart and
ask for an explicit confirmation before they are removed.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path, PurePath
from typing import Iterable, Mapping

# Extensions the OS would *run* rather than display.
PROGRAM_SUFFIXES = frozenset({
    ".app", ".bat", ".cmd", ".com", ".command", ".desktop", ".exe", ".hta", ".jar",
    ".js", ".jse", ".lnk", ".msc", ".msi", ".pif", ".ps1", ".reg", ".scr", ".sh",
    ".vbe", ".vbs", ".wsf", ".wsh",
})

# Libraries, drivers and other parts of programs or of the OS itself.
SYSTEM_COMPONENT_SUFFIXES = frozenset({
    ".cat", ".cpl", ".dll", ".drv", ".dylib", ".efi", ".inf", ".ko", ".mui", ".ocx",
    ".so", ".sys",
})

_RISKY_SUFFIXES = PROGRAM_SUFFIXES | SYSTEM_COMPONENT_SUFFIXES

# Folders, wherever they are, that hold an application's or a tool's own data.
_APP_DATA_FOLDER_NAMES = frozenset({
    ".git", ".hg", ".svn", "$recycle.bin", "appdata", "system volume information",
})


class RiskReason(Enum):
    SYSTEM_FOLDER = "system_folder"  # inside an operating system or program folder
    APP_DATA = "app_data"  # inside application or version-control data
    PROGRAM_FILE = "program_file"  # a program, script, library or driver


def default_system_folders(
    platform: str = sys.platform, environ: Mapping[str, str] = os.environ
) -> tuple[Path, ...]:
    """Folders that belong to the operating system or installed programs."""
    if platform == "win32":
        variables = ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432",
                     "ProgramData")
        found = [environ[name] for name in variables if environ.get(name)]
        return tuple(Path(folder) for folder in found or [
            r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)", r"C:\ProgramData",
        ])
    if platform == "darwin":
        folders = ["/System", "/Library", "/Applications", "/usr", "/bin", "/sbin", "/opt"]
        return tuple(Path(folder) for folder in folders) + (Path.home() / "Library",)
    folders = ["/bin", "/boot", "/etc", "/lib", "/lib32", "/lib64", "/opt", "/sbin",
               "/snap", "/usr"]
    return tuple(Path(folder) for folder in folders)


class RiskAssessor:
    """Tells why removing a file may be risky.

    System folders are injectable so the rules can be tested on any platform.
    Folder comparisons ignore case, as Windows and macOS file systems do.
    """

    def __init__(self, system_folders: Iterable[PurePath] = ()) -> None:
        self._system_folders = tuple(_folded_parts(folder) for folder in system_folders)

    @classmethod
    def for_this_computer(cls) -> "RiskAssessor":
        return cls(default_system_folders())

    def reasons(self, path: PurePath) -> frozenset[RiskReason]:
        """Every reason that applies to ``path``; empty if it looks safe to remove."""
        parts = _folded_parts(path)
        found = set()
        if any(parts[:len(folder)] == folder for folder in self._system_folders):
            found.add(RiskReason.SYSTEM_FOLDER)
        if _APP_DATA_FOLDER_NAMES.intersection(parts[:-1]):
            found.add(RiskReason.APP_DATA)
        if path.suffix.lower() in _RISKY_SUFFIXES:
            found.add(RiskReason.PROGRAM_FILE)
        return frozenset(found)

    def risky_files(self, paths: Iterable[Path]) -> dict[Path, frozenset[RiskReason]]:
        """The risky ones among ``paths``, each with its reasons."""
        return {path: reasons for path in paths if (reasons := self.reasons(path))}


def _folded_parts(path: PurePath) -> tuple[str, ...]:
    return tuple(part.casefold() for part in path.parts)
