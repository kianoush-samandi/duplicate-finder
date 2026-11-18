"""Applies a Palette to Tk/ttk widgets and keeps it in sync with the chosen mode.

Native ttk themes ("vista", "aqua") ignore custom colors, so the
cross-platform "clam" theme is used as the base for both light and dark.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .settings import SettingsStore
from .theme import ButtonColors, ButtonRole, Palette, ThemeMode, resolve_palette, system_prefers_dark

SYSTEM_POLL_MS = 2000  # how often "system" mode re-checks the OS setting

WidgetStyler = Callable[[Palette], None]


class ThemeManager:
    def __init__(
        self,
        root: tk.Tk,
        store: SettingsStore,
        prefers_dark: Callable[[], bool] = system_prefers_dark,
    ) -> None:
        self._root = root
        self._store = store
        self._prefers_dark = prefers_dark
        self._mode = store.load().theme_mode
        self._palette: Optional[Palette] = None
        # Plain tk widgets and extra windows are not covered by ttk.Style.
        self._extra_stylers: list[tuple[tk.Misc, WidgetStyler]] = []
        self._style = ttk.Style(root)
        self._style.theme_use("clam")

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def palette(self) -> Palette:
        return self._palette

    def start(self) -> None:
        self._refresh()
        self._root.after(SYSTEM_POLL_MS, self._poll_system_theme)

    def set_mode(self, mode: ThemeMode) -> None:
        self._mode = mode
        try:
            self._store.update(theme_mode=mode)
        except OSError:
            pass  # an unsaved preference is not worth interrupting the user
        self._refresh()

    def style_widget(self, widget: tk.Misc, styler: WidgetStyler) -> None:
        """Style ``widget`` now and again on every theme change, while it exists."""
        self._extra_stylers.append((widget, styler))
        styler(self._palette)

    def style_window(self, window: tk.Misc) -> None:
        """Background and (on Windows) title-bar color for a Toplevel."""
        self.style_widget(window, lambda palette: _style_window(window, palette))

    def _poll_system_theme(self) -> None:
        if self._mode is ThemeMode.SYSTEM:
            self._refresh()
        self._root.after(SYSTEM_POLL_MS, self._poll_system_theme)

    def _refresh(self) -> None:
        palette = resolve_palette(self._mode, self._prefers_dark)
        if palette == self._palette:
            return
        self._palette = palette
        _configure_ttk(self._style, palette)
        _style_window(self._root, palette)
        self._extra_stylers = [(w, s) for w, s in self._extra_stylers if _exists(w)]
        for _widget, styler in self._extra_stylers:
            styler(palette)


def button_style(role: ButtonRole) -> str:
    """The ttk style name for a button with ``role``."""
    return "TButton" if role is ButtonRole.NEUTRAL else f"{role.value.title()}.TButton"


def style_text_widget(text: tk.Text) -> WidgetStyler:
    def apply(palette: Palette) -> None:
        text.configure(
            background=palette.surface,
            foreground=palette.text,
            insertbackground=palette.text,
            selectbackground=palette.selection,
            selectforeground=palette.selection_text,
            highlightbackground=palette.border,
            highlightcolor=palette.accent,
        )

    return apply


def style_listbox(listbox: tk.Listbox) -> WidgetStyler:
    def apply(palette: Palette) -> None:
        listbox.configure(
            background=palette.surface,
            foreground=palette.text,
            selectbackground=palette.selection,
            selectforeground=palette.selection_text,
            disabledforeground=palette.disabled_text,
            highlightbackground=palette.border,
            highlightcolor=palette.accent,
        )

    return apply


def style_menu(menu: tk.Menu) -> WidgetStyler:
    def apply(palette: Palette) -> None:
        menu.configure(
            background=palette.surface,
            foreground=palette.text,
            activebackground=palette.selection,
            activeforeground=palette.selection_text,
            disabledforeground=palette.disabled_text,
            relief="flat",
            borderwidth=1,
        )

    return apply


def _configure_ttk(style: ttk.Style, p: Palette) -> None:
    style.configure(
        ".",
        background=p.background,
        foreground=p.text,
        fieldbackground=p.surface,
        bordercolor=p.border,
        lightcolor=p.background,
        darkcolor=p.background,
        troughcolor=p.surface,
        selectbackground=p.selection,
        selectforeground=p.selection_text,
        insertcolor=p.text,
        focuscolor=p.accent,
    )
    style.map(".", foreground=[("disabled", p.disabled_text)])

    style.configure("TButton", padding=(10, 4))
    for role in ButtonRole:
        _configure_button(style, button_style(role), p.button_colors(role), p)

    style.map(
        "TEntry",
        fieldbackground=[("disabled", p.background)],
        bordercolor=[("focus", p.accent)],
    )

    for toggle in ("TRadiobutton", "TCheckbutton"):
        style.configure(toggle, indicatorbackground=p.surface, indicatorforeground=p.text)
        style.map(
            toggle,
            background=[("active", p.background)],
            indicatorbackground=[("selected", p.accent), ("disabled", p.background)],
        )

    style.map(
        "TCombobox",
        fieldbackground=[("disabled", p.disabled_field), ("readonly", p.surface)],
        foreground=[("disabled", p.disabled_text)],
        bordercolor=[("disabled", p.disabled_field), ("focus", p.accent)],
        background=[("disabled", p.disabled_field)],
        arrowcolor=[("disabled", p.disabled_text)],
    )
    style.configure("TCombobox", arrowcolor=p.text, background=p.control)
    # The drop-down list is a plain Tk listbox, reached only through the option database.
    root = style.master
    for option, value in (("background", p.surface), ("foreground", p.text),
                          ("selectBackground", p.selection),
                          ("selectForeground", p.selection_text)):
        root.option_add(f"*TCombobox*Listbox.{option}", value)

    style.configure("Treeview", background=p.surface, fieldbackground=p.surface,
                    foreground=p.text)
    style.map(
        "Treeview",
        background=[("selected", p.selection)],
        foreground=[("selected", p.selection_text)],
    )
    style.configure("Treeview.Heading", background=p.control, relief="flat")
    style.map("Treeview.Heading", background=[("active", p.control_hover)])

    style.configure("TProgressbar", background=p.accent, lightcolor=p.accent,
                    darkcolor=p.accent)
    style.configure("TScrollbar", background=p.control, troughcolor=p.background,
                    arrowcolor=p.text)
    style.map("TScrollbar", background=[("active", p.control_hover)])

    style.configure("Hint.TLabel", foreground=p.muted_text)


def _configure_button(style: ttk.Style, name: str, colors: ButtonColors, p: Palette) -> None:
    """One look for every role; only the colors differ.

    A disabled button looks the same whatever its role, so a red button
    always means "this removes files, and you can press it now".
    """
    style.configure(name, background=colors.background, foreground=colors.text)
    style.map(
        name,
        background=[("disabled", p.background), ("pressed", colors.hover),
                    ("active", colors.hover)],
        foreground=[("disabled", p.disabled_text)],
        bordercolor=[("disabled", p.border), ("!disabled", colors.border)],
        lightcolor=[("disabled", p.background), ("!disabled", colors.background)],
        darkcolor=[("disabled", p.background), ("!disabled", colors.background)],
    )


def _style_window(window: tk.Misc, palette: Palette) -> None:
    window.configure(background=palette.background)
    _set_windows_title_bar_dark(window, palette.is_dark)


def _set_windows_title_bar_dark(window: tk.Misc, dark: bool) -> None:
    """Dark title bar on Windows 10 (1809+) / 11; a no-op elsewhere."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        # DWMWA_USE_IMMERSIVE_DARK_MODE is 20 on current builds, 19 on early ones.
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                break
    except (AttributeError, OSError):
        pass


def _exists(widget: tk.Misc) -> bool:
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False
