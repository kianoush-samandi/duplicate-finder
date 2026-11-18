"""Hands a file to the operating system: open it, or show it in its folder. No Tk code here."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Union

from .risk import PROGRAM_SUFFIXES

Command = Union[str, list[str]]


class FileOpenError(OSError):
    """The file exists, but the operating system could not open or show it."""


def is_launchable(path: Path) -> bool:
    """True if opening ``path`` would run a program instead of showing a document.

    Clicking one in a duplicate list is rarely meant as "execute it", so the GUI asks first.
    """
    return path.suffix.lower() in PROGRAM_SUFFIXES


def open_file(path: Path, platform: str = sys.platform) -> None:
    """Open ``path`` with its default application without waiting for it.

    Raises FileNotFoundError if the file is gone (e.g. moved since the scan)
    and FileOpenError if the OS refuses to open it.
    """
    _require_file(path)
    if platform == "win32":
        _guarded(lambda: os.startfile(path))  # type: ignore[attr-defined]  # Windows only
    else:
        _launch(open_command(path, platform))


def reveal_file(path: Path, platform: str = sys.platform) -> None:
    """Show ``path`` in the system file manager, selected where the OS allows it.

    Raises the same errors as ``open_file``.
    """
    _require_file(path)
    _launch(reveal_command(path, platform))


def open_command(path: Path, platform: str) -> list[str]:
    """Argument list for non-Windows platforms; no shell, so any file name is safe."""
    opener = "open" if platform == "darwin" else "xdg-open"
    return [opener, str(path)]


def reveal_command(path: Path, platform: str) -> Command:
    if platform == "win32":
        # Explorer parses its own command line and needs exactly this quoting;
        # Windows paths cannot contain '"', so the path cannot break out of it.
        return f'explorer /select,"{path}"'
    if platform == "darwin":
        return ["open", "-R", str(path)]
    # Linux file managers share no "select this file" option: open the folder.
    return ["xdg-open", str(path.parent)]


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(str(path))


def _launch(command: Command) -> None:
    _guarded(lambda: subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # the viewer must outlive this app
    ))


def _guarded(action: Callable[[], object]) -> None:
    try:
        action()
    except OSError as exc:
        raise FileOpenError(str(exc)) from exc
