"""Window and taskbar icon. Cosmetic only: any failure here is ignored, never fatal."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICO_PATH = ASSETS_DIR / "icon.ico"  # multi-size, sharp at every Windows DPI
PNG_PATH = ASSETS_DIR / "icon.png"  # for platforms whose Tk cannot read .ico

# Without its own ID, Windows groups the app under python.exe and shows Python's icon
# on the taskbar. Format: Company.Product.SubProduct.Version.
# Public because the installer gives its shortcuts the same ID (tools/build_installer.py);
# otherwise a pinned shortcut and the running window appear as two taskbar buttons.
WINDOWS_APP_ID = "DuplicateFinder.DuplicateFinder.App.1"


def register_windows_app_id() -> None:
    """Give the process its own taskbar identity. Call before the first window is created."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass  # very old Windows: the taskbar falls back to python.exe's icon


def apply_app_icon(root: tk.Tk) -> None:
    """Set the icon on ``root`` and on every window (dialogs included) created later."""
    try:
        if sys.platform == "win32":
            root.iconbitmap(default=str(ICO_PATH))
        else:
            root.iconphoto(True, tk.PhotoImage(master=root, file=str(PNG_PATH)))
    except tk.TclError:
        pass  # missing or unreadable icon file: keep the default icon
