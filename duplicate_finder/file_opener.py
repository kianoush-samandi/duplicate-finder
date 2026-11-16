"""Hands a file to the operating system's default application. No Tk code here."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Extensions the OS would *run* rather than display. Clicking one of these in
# a duplicate list is rarely meant as "execute it", so the GUI asks first.
_LAUNCHABLE_SUFFIXES = frozenset({
    ".app", ".bat", ".cmd", ".com", ".command", ".desktop", ".exe", ".hta", ".jar",
    ".js", ".jse", ".lnk", ".msc", ".msi", ".pif", ".ps1", ".reg", ".scr", ".sh",
    ".vbe", ".vbs", ".wsf", ".wsh",
})


class FileOpenError(OSError):
    """The file exists, but the operating system could not open it."""


def is_launchable(path: Path) -> bool:
    """True if opening ``path`` would run a program instead of showing a document."""
    return path.suffix.lower() in _LAUNCHABLE_SUFFIXES


def open_file(path: Path, platform: str = sys.platform) -> None:
    """Open ``path`` with its default application without waiting for it.

    Raises FileNotFoundError if the file is gone (e.g. moved since the scan)
    and FileOpenError if the OS refuses to open it.
    """
    if not path.is_file():
        raise FileNotFoundError(str(path))
    try:
        if platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]  # Windows only
        else:
            subprocess.Popen(
                open_command(path, platform),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # the viewer must outlive this app
            )
    except OSError as exc:
        raise FileOpenError(str(exc)) from exc


def open_command(path: Path, platform: str) -> list[str]:
    """Argument list for non-Windows platforms; no shell, so any file name is safe."""
    opener = "open" if platform == "darwin" else "xdg-open"
    return [opener, str(path)]
