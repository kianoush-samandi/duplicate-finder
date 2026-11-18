"""Tkinter front end. Presentation only: all decisions live in the core modules.

Language switching rebuilds the widget tree. Application state (scan
results, review plan, field contents, status) lives outside the widgets,
so a rebuild loses nothing and the layout can be mirrored for RTL languages.
"""

from __future__ import annotations

import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable, Optional

from .app_icon import apply_app_icon, register_windows_app_id
from .background import BackgroundTask
from .file_types import ExtensionFilter, FileCategory, NoExtensionsError, parse_extensions
from .file_opener import FileOpenError, is_launchable, open_file, reveal_file
from .formatting import format_size
from .i18n import Language, Translator
from .models import FileIssue, RemovalReport, ScanResult
from .progress import ProgressCallback, Stage
from .removal import QuarantineRemover, Remover, TrashRemover, remove_duplicates
from .result_order import SortField, ordered_group_indices
from .review import ReviewPlan
from .risk import RiskAssessor, RiskReason
from .scan_folders import FolderAlreadyIncludedError, ScanFolders
from .scanner import find_duplicates
from .settings import SettingsStore, default_settings_path
from .styling import ThemeManager, button_style, style_listbox, style_menu, style_text_widget
from .theme import ButtonRole, ThemeMode
from .validation import FolderNotSelectedError, NotAFolderError

# A status line is stored as a function of the translator, so it can be
# re-rendered in the new language after a switch.
StatusMessage = Callable[[Translator], str]

# (translation key, command, enabled); None stands for a separator.
MenuEntry = Optional[tuple[str, Callable[[], None], bool]]

_PATH_COLUMN = "path"
_LINK_HOVER_TAG = "path-link-hover"
_RISKY_TAG = "risky"
_MAX_LISTED_RISKY_FILES = 10  # more would not fit in a message box


def _message(key: str, **values) -> StatusMessage:
    return lambda t: t(key, **values)


@dataclass(frozen=True)
class ScanRequest:
    """What to scan and how; kept so the same scan can be repeated after a removal."""

    roots: tuple[Path, ...]
    file_filter: Optional[ExtensionFilter]
    shared_only: bool

    def run(self, report: ProgressCallback, cancel: threading.Event) -> ScanResult:
        return find_duplicates(*self.roots, file_filter=self.file_filter,
                               shared_only=self.shared_only,
                               on_progress=report, cancel_event=cancel)


class DuplicateFinderApp:
    def __init__(self, root: tk.Tk, theme: ThemeManager, store: SettingsStore,
                 risk: RiskAssessor) -> None:
        self.root = root
        self._theme = theme
        self._store = store
        self._risk = risk
        self._t = Translator(store.load().language)
        self.root.geometry("1040x760")
        self.root.minsize(840, 600)

        # State that must survive a UI rebuild.
        self._task: Optional[BackgroundTask] = None
        self._folders = ScanFolders()
        self._scan_request: Optional[ScanRequest] = None
        self._scan_result: Optional[ScanResult] = None
        self._plan: Optional[ReviewPlan] = None
        self._risky_files: dict[Path, frozenset[RiskReason]] = {}
        self._status: StatusMessage = _message("status.ready")
        self.shared_only_var = tk.BooleanVar(value=False)
        self.type_filter_var = tk.BooleanVar(value=False)
        self.file_types_var = tk.StringVar()
        # A ready-made category picked from the list, or None for typed extensions.
        # Kept apart from the text so the label can be re-translated on a rebuild.
        self._file_category: Optional[FileCategory] = FileCategory.DOCUMENTS
        self._sort_field = SortField.SIZE
        self._sort_descending = True
        self.status_var = tk.StringVar()
        self.plan_var = tk.StringVar()
        self.theme_var = tk.StringVar(value=theme.mode.value)
        self.language_var = tk.StringVar(value=self._t.language.value)

        # Widget bookkeeping, recreated by every rebuild.
        self._main: Optional[ttk.Frame] = None
        self._language_buttons: list[ttk.Radiobutton] = []
        self._group_item_ids: dict[int, str] = {}  # plan group index -> tree item
        self._group_numbers: dict[int, int] = {}  # plan group index -> number shown
        self._item_targets: dict[str, tuple[int, Optional[Path]]] = {}
        self._hovered_link: Optional[str] = None

        self._rebuild()

    # ------------------------------------------------------------ language

    def _on_language_selected(self) -> None:
        language = Language(self.language_var.get())
        if self._busy or language is self._t.language:
            return
        try:
            self._store.update(language=language)
        except OSError:
            pass  # an unsaved preference is not worth interrupting the user
        self._t = Translator(language)
        self._rebuild()

    def _rebuild(self) -> None:
        if self._main is not None:
            self._main.destroy()
        self._build_ui()
        self._populate_tree()
        self._render_status()
        self._update_controls()

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        t = self._t
        self._rtl = rtl = t.language.is_rtl
        # Mirrored layout for right-to-left languages.
        self._start, self._end = ("right", "left") if rtl else ("left", "right")
        self._anchor = "e" if rtl else "w"
        self._justify = "right" if rtl else "left"
        self.root.title(t("app.title"))

        self._main = main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        self._build_header(main)
        self._build_folder_list(main)
        self._build_type_filter_row(main)
        self._build_scan_row(main)

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 6))
        ttk.Label(main, textvariable=self.status_var, justify=self._justify).pack(
            anchor=self._anchor, pady=(0, 6)
        )

        self._build_sort_row(main)
        self._build_tree(main)
        self._build_review_row(main)
        self._build_action_row(main)

        ttk.Label(
            main,
            text=t("footer.safety"),
            wraplength=960,
            justify=self._justify,
            style="Hint.TLabel",
        ).pack(anchor=self._anchor, pady=(8, 0))

    def _build_header(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 10))

        title_font = tkfont.nametofont("TkDefaultFont").copy()
        title_font.configure(size=16, weight="bold")
        ttk.Label(row, text=t("header.title"), font=title_font).pack(side=self._start)

        preferences = ttk.Frame(row)
        preferences.pack(side=self._end)

        ttk.Label(preferences, text=t("header.language")).pack(side=self._start)
        self._language_buttons = [
            self._radio(preferences, language.native_name, language.value,
                        self.language_var, self._on_language_selected)
            for language in Language
        ]
        ttk.Label(preferences, text=t("header.theme")).pack(side=self._start, padx=(16, 0))
        for mode in ThemeMode:
            self._radio(preferences, t(f"theme.{mode.value}"), mode.value,
                        self.theme_var, self._on_theme_selected)

    def _start_gap(self, size: int) -> tuple[int, int]:
        """Horizontal padding on the start side only (left in LTR, right in RTL)."""
        return (0, size) if self._rtl else (size, 0)

    def _radio(self, parent, text, value, variable, command) -> ttk.Radiobutton:
        button = ttk.Radiobutton(parent, text=text, value=value, variable=variable,
                                 command=command)
        button.pack(side=self._start, padx=4)
        return button

    def _on_theme_selected(self) -> None:
        self._theme.set_mode(ThemeMode(self.theme_var.get()))

    def _build_folder_list(self, parent: ttk.Frame) -> None:
        t = self._t
        ttk.Label(parent, text=t("folder.label")).pack(anchor=self._anchor)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(4, 0))

        buttons = ttk.Frame(row)
        buttons.pack(side=self._end, fill="y", padx=self._start_gap(8))
        self.add_folder_button = ttk.Button(buttons, text=t("folder.add"),
                                            command=self._add_folder)
        self.add_folder_button.pack(fill="x")
        self.remove_folder_button = ttk.Button(buttons, text=t("folder.remove"),
                                               command=self._remove_selected_folder)
        self.remove_folder_button.pack(fill="x", pady=(4, 0))

        # Paths are always left-to-right, even in an RTL layout.
        self.folder_list = tk.Listbox(row, height=3, activestyle="none", relief="flat",
                                      highlightthickness=1, exportselection=False)
        self._theme.style_widget(self.folder_list, style_listbox(self.folder_list))
        yscroll = ttk.Scrollbar(row, orient="vertical", command=self.folder_list.yview)
        self.folder_list.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side=self._end, fill="y")
        self.folder_list.pack(side=self._start, fill="both", expand=True)
        self.folder_list.bind("<<ListboxSelect>>", lambda _event: self._update_controls())
        self.folder_list.bind("<Delete>", lambda _event: self._remove_selected_folder())
        self._render_folders()

        self.shared_only_check = ttk.Checkbutton(
            parent, text=t("options.shared_only"), variable=self.shared_only_var
        )
        self.shared_only_check.pack(anchor=self._anchor, pady=(4, 0))

    def _build_type_filter_row(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        self.type_filter_check = ttk.Checkbutton(
            row, text=t("options.filter_types"), variable=self.type_filter_var,
            command=self._update_controls,
        )
        self.type_filter_check.pack(side=self._start)
        self.file_types_box = ttk.Combobox(
            row, textvariable=self.file_types_var, width=42,
            values=[self._category_label(category) for category in FileCategory],
        )
        self.file_types_box.pack(side=self._start, padx=8)
        self.file_types_box.bind("<<ComboboxSelected>>", self._on_file_category_selected)
        self.file_types_box.bind("<Key>", self._on_file_types_typed)
        if self._file_category is not None:
            self.file_types_var.set(self._category_label(self._file_category))
        ttk.Label(row, text=t("options.filter_types_hint"), style="Hint.TLabel").pack(
            side=self._start
        )

    def _category_label(self, category: FileCategory) -> str:
        extensions = ", ".join(sorted(ext.lstrip(".") for ext in category.extensions))
        return self._t("filetype.label", name=self._t(f"filetype.{category.value}"),
                       extensions=extensions)

    def _on_file_category_selected(self, _event: tk.Event) -> None:
        self._file_category = list(FileCategory)[self.file_types_box.current()]

    def _on_file_types_typed(self, event: tk.Event) -> None:
        if event.char or event.keysym in ("BackSpace", "Delete"):
            self._file_category = None  # the text is now the user's own list

    def _chosen_file_filter(self) -> Optional[ExtensionFilter]:
        """The filter for the next scan; raises NoExtensionsError for an empty list."""
        if not self.type_filter_var.get():
            return None
        if self._file_category is not None:
            return ExtensionFilter(self._file_category.extensions)
        return ExtensionFilter(parse_extensions(self.file_types_var.get()))

    def _build_scan_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=10)
        self.scan_button = ttk.Button(row, command=self._on_scan_clicked)
        self.scan_button.pack(side=self._start)
        self.errors_button = ttk.Button(row, text=self._t("scan.show_errors"),
                                        command=self._show_scan_errors)
        self.errors_button.pack(side=self._start, padx=8)

    def _build_sort_row(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 6))
        ttk.Label(row, text=t("sort.label")).pack(side=self._start)
        self.sort_field_box = self._readonly_combobox(
            row, [t(f"sort.field.{field.value}") for field in SortField],
            list(SortField).index(self._sort_field),
        )
        self.sort_order_box = self._readonly_combobox(
            row, [t("sort.descending"), t("sort.ascending")], 0 if self._sort_descending else 1,
        )

    def _readonly_combobox(self, parent: ttk.Frame, values: list[str],
                           current: int) -> ttk.Combobox:
        box = ttk.Combobox(parent, values=values, state="readonly",
                           width=max(len(value) for value in values) + 2)
        box.current(current)
        box.pack(side=self._start, padx=self._start_gap(8))
        box.bind("<<ComboboxSelected>>", self._on_sort_changed)
        return box

    def _on_sort_changed(self, _event: tk.Event) -> None:
        self._sort_field = list(SortField)[self.sort_field_box.current()]
        self._sort_descending = self.sort_order_box.current() == 0
        self._populate_tree()
        self._update_controls()

    def _build_tree(self, parent: ttk.Frame) -> None:
        t = self._t
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            frame, columns=("action", "size", _PATH_COLUMN), show="tree headings",
            selectmode="browse",
        )
        for column, key, width, anchor in (
            ("#0", "tree.heading.item", 320, self._anchor),
            ("action", "tree.heading.action", 190, self._anchor),
            ("size", "tree.heading.size", 100, "e"),
            (_PATH_COLUMN, "tree.heading.path", 380, "w"),  # paths are always left-to-right
        ):
            self.tree.heading(column, text=t(key), anchor=anchor)
            self.tree.column(column, width=width, minwidth=80, anchor=anchor)

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._update_controls())
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self._bind_path_links()
        self._bind_file_menu()

    # A ttk.Treeview cannot style a single cell, so the path "link" is a row
    # tag (accent color + underline) applied while the pointer is over the
    # path cell, plus a hand cursor. A click on that cell opens the file.

    def _bind_path_links(self) -> None:
        link_font = tkfont.nametofont("TkDefaultFont").copy()
        link_font.configure(underline=True)
        self._link_font = link_font  # Tk fonts vanish once garbage-collected
        self._hovered_link = None
        self._theme.style_widget(self.tree, lambda palette: (
            self.tree.tag_configure(_RISKY_TAG, foreground=palette.warning),
            # Configured last, so it wins over the risky color while hovered.
            self.tree.tag_configure(_LINK_HOVER_TAG, foreground=palette.accent,
                                    font=link_font),
        ))

        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", lambda _event: self._set_hovered_link(None))
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Return>", lambda _event: self._open_path(self._selected_target()[1]))

    def _path_link_at(self, x: int, y: int) -> Optional[str]:
        """The file row whose path cell is under (x, y), if any."""
        if self.tree.identify_region(x, y) != "cell":
            return None
        if self.tree.column(self.tree.identify_column(x), "id") != _PATH_COLUMN:
            return None
        item = self.tree.identify_row(y)
        _, path = self._item_targets.get(item, (None, None))
        return item if path is not None else None

    def _on_tree_motion(self, event: tk.Event) -> None:
        self._set_hovered_link(self._path_link_at(event.x, event.y))

    def _set_hovered_link(self, item: Optional[str]) -> None:
        if item == self._hovered_link:
            return
        if self._hovered_link is not None and self.tree.exists(self._hovered_link):
            self.tree.item(self._hovered_link, tags=self._row_tags(self._hovered_link))
        if item is not None:
            self.tree.item(item, tags=self._row_tags(item) + (_LINK_HOVER_TAG,))
        self.tree.configure(cursor="hand2" if item is not None else "")
        self._hovered_link = item

    def _on_tree_click(self, event: tk.Event) -> None:
        item = self._path_link_at(event.x, event.y)
        if item is not None:
            self._open_path(self._item_targets[item][1])

    def _on_tree_double_click(self, event: tk.Event) -> None:
        # The first click of a double-click on a path has already opened the
        # file; choosing the keeper there as well would be a surprise.
        if self._path_link_at(event.x, event.y) is None:
            self._keep_selected_file()

    def _open_path(self, path: Optional[Path]) -> None:
        if path is None or self._busy:  # never lock a file that is being moved
            return
        t = self._t
        if is_launchable(path) and not messagebox.askyesno(
            t("confirm.open_program.title"), t("confirm.open_program.body", path=path),
            icon="warning",
        ):
            return
        self._hand_to_os(open_file, path)

    def _reveal_path(self, path: Path) -> None:
        self._hand_to_os(reveal_file, path)

    def _hand_to_os(self, action: Callable[[Path], None], path: Path) -> None:
        t = self._t
        try:
            action(path)
        except FileNotFoundError:
            messagebox.showerror(t("error.open_failed.title"),
                                 t("error.open_missing.body", path=path))
        except FileOpenError as exc:
            messagebox.showerror(t("error.open_failed.title"),
                                 t("error.open_failed.body", path=path, detail=exc))

    # ------------------------------------------------------------ file menu

    def _bind_file_menu(self) -> None:
        self._file_menu = tk.Menu(self.tree, tearoff=False)
        self._theme.style_widget(self._file_menu, style_menu(self._file_menu))
        for sequence in _context_menu_sequences(self.root):
            self.tree.bind(sequence, self._on_tree_context_menu)
        self.tree.bind("<Shift-F10>", lambda _event: self._show_file_menu_at_selection())

    def _on_tree_context_menu(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if self._item_targets.get(item, (None, None))[1] is not None:
            self._show_file_menu(item, event.x_root, event.y_root)

    def _show_file_menu_at_selection(self) -> None:
        selection = self.tree.selection()
        if not selection or self._item_targets.get(selection[0], (None, None))[1] is None:
            return
        x, y, _width, height = self.tree.bbox(selection[0], _PATH_COLUMN) or (0, 0, 0, 0)
        self._show_file_menu(selection[0], self.tree.winfo_rootx() + x,
                             self.tree.winfo_rooty() + y + height)

    def _show_file_menu(self, item: str, x_root: int, y_root: int) -> None:
        self.tree.selection_set(item)  # menu actions work on the selected file
        self.tree.focus(item)
        self._file_menu.delete(0, "end")
        for entry in self._file_menu_entries(*self._item_targets[item]):
            if entry is None:
                self._file_menu.add_separator()
            else:
                key, command, enabled = entry
                self._file_menu.add_command(label=self._t(key), command=command,
                                            state=_state(enabled))
        try:
            self._file_menu.tk_popup(x_root, y_root)
        finally:
            self._file_menu.grab_release()

    def _file_menu_entries(self, group_index: int, path: Path) -> list[MenuEntry]:
        plan, idle = self._plan, not self._busy
        kept = plan.is_kept(group_index, path)
        return [
            ("menu.open", lambda: self._open_path(path), idle),
            ("menu.show_in_folder", lambda: self._reveal_path(path), True),
            None,
            ("menu.keep", lambda: self._change_selected_file(ReviewPlan.keep),
             idle and not kept),
            ("menu.remove", lambda: self._change_selected_file(ReviewPlan.mark_for_removal),
             idle and kept and plan.can_mark_for_removal(group_index, path)),
            None,
            ("menu.delete", lambda: self._delete_now(group_index, path),
             idle and TrashRemover.is_available()),
        ]

    def _build_review_row(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        self.keep_button = ttk.Button(row, text=t("review.keep"),
                                      command=self._keep_selected_file)
        self.keep_button.pack(side=self._start)
        self.skip_button = ttk.Button(row, text=t("review.toggle_skip"),
                                      command=self._toggle_selected_group)
        self.skip_button.pack(side=self._start, padx=8)
        ttk.Label(row, textvariable=self.plan_var).pack(side=self._start, padx=8)

    def _build_action_row(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        removes_files = button_style(ButtonRole.DESTRUCTIVE)
        self.quarantine_button = ttk.Button(row, text=t("action.quarantine"),
                                            command=self._remove_to_quarantine,
                                            style=removes_files)
        self.quarantine_button.pack(side=self._start)
        self.trash_button = ttk.Button(row, text=t("action.trash"),
                                       command=self._remove_to_trash, style=removes_files)
        self.trash_button.pack(side=self._start, padx=8)

    # ------------------------------------------------------------ control state

    @property
    def _busy(self) -> bool:
        return self._task is not None

    def _update_controls(self) -> None:
        t = self._t
        idle = _state(not self._busy)
        self.add_folder_button.configure(state=idle)
        self.folder_list.configure(state=idle)
        self.remove_folder_button.configure(
            state=_state(not self._busy and bool(self.folder_list.curselection()))
        )
        self.shared_only_check.configure(state=_state(not self._busy and len(self._folders) > 1))
        self.type_filter_check.configure(state=idle)
        self.file_types_box.configure(
            state=_state(not self._busy and self.type_filter_var.get())
        )
        for button in self._language_buttons:  # a rebuild mid-task is not worth the risk
            button.configure(state=idle)
        # While busy the button cancels, which is not the main next step.
        self.scan_button.configure(
            text=t("scan.cancel" if self._busy else "scan.start"),
            style=button_style(ButtonRole.NEUTRAL if self._busy else ButtonRole.PRIMARY),
        )

        has_errors = bool(self._scan_result and self._scan_result.errors)
        self.errors_button.configure(state=_state(not self._busy and has_errors))

        group_index, path = self._selected_target()
        can_review = not self._busy and group_index is not None
        self.keep_button.configure(state=_state(can_review and path is not None))
        self.skip_button.configure(state=_state(can_review))

        can_remove = (
            not self._busy and self._plan is not None and self._plan.files_to_remove_count > 0
        )
        self.quarantine_button.configure(state=_state(can_remove))
        self.trash_button.configure(state=_state(can_remove and TrashRemover.is_available()))

        self.plan_var.set(
            ""
            if self._plan is None
            else t("review.summary", count=self._plan.files_to_remove_count,
                   size=format_size(self._plan.reclaimable_bytes))
        )

    def _set_status(self, message: StatusMessage) -> None:
        self._status = message
        self._render_status()

    def _render_status(self) -> None:
        self.status_var.set(self._status(self._t))

    # ------------------------------------------------------------------ scanning

    def _add_folder(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder.dialog_title"))
        if not selected:
            return
        try:
            self._folders.add(selected)
        except NotAFolderError:
            self._show_error("error.bad_folder.title", "error.bad_folder.body")
            return
        except FolderAlreadyIncludedError:
            self._show_error("error.folder_included.title", "error.folder_included.body")
            return
        self._render_folders()
        self._update_controls()

    def _remove_selected_folder(self) -> None:
        selection = self.folder_list.curselection()
        if self._busy or not selection:
            return
        self._folders.remove(selection[0])
        self._render_folders()
        self._update_controls()

    def _render_folders(self) -> None:
        self.folder_list.delete(0, "end")
        for folder in self._folders.folders:
            self.folder_list.insert("end", str(folder))

    def _on_scan_clicked(self) -> None:
        if self._busy:
            self._task.cancel()
            self._set_status(_message("status.cancelling"))
            return
        try:
            roots = self._folders.require_any()
        except FolderNotSelectedError:
            self._show_error("error.no_folder.title", "error.no_folder.body")
            return
        try:
            file_filter = self._chosen_file_filter()
        except NoExtensionsError:
            self._show_error("error.no_extensions.title", "error.no_extensions.body")
            return
        shared_only = len(roots) > 1 and self.shared_only_var.get()
        self._start_scan(ScanRequest(roots, file_filter, shared_only))

    def _start_scan(self, request: ScanRequest) -> None:
        self._scan_request = request
        self._set_results(None)
        self._set_status(_message("status.scanning"))
        self._run_task(
            request.run,
            on_success=self._on_scan_finished,
            failure_title_key="error.scan_failed.title",
        )

    def _on_scan_finished(self, result: ScanResult) -> None:
        self._set_results(result)

        def summary(t: Translator) -> str:
            text = t("status.scan_done", files=result.total_files, groups=len(result.groups),
                     size=format_size(result.reclaimable_bytes))
            if result.errors:
                text += t("status.scan_errors_suffix", count=len(result.errors))
            return text

        self._set_status(summary)

    def _show_scan_errors(self) -> None:
        if self._scan_result:
            self._show_issues("dialog.scan_errors.title", self._scan_result.errors)

    # ------------------------------------------------------------------ results

    def _set_results(self, result: Optional[ScanResult]) -> None:
        self._scan_result = result
        self._plan = ReviewPlan(result.groups) if result else None
        self._risky_files = self._risk.risky_files(
            path for group in (result.groups if result else ()) for path in group.files
        )
        self._populate_tree()
        self._update_controls()

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._group_item_ids.clear()
        self._item_targets.clear()
        self._set_hovered_link(None)
        self._group_numbers.clear()
        if self._plan is None:
            return
        order = ordered_group_indices(self._plan.groups, self._sort_field,
                                      self._sort_descending)
        risky = [index for index in order if self._is_risky_group(index)]
        if not risky:
            self._insert_groups("", order, first_number=1)
            return
        # Risky groups get a section of their own, listed first, so they are
        # reviewed together and never mistaken for ordinary duplicates.
        others = [index for index in order if not self._is_risky_group(index)]
        sections = (("tree.section.risky", risky, (_RISKY_TAG,)),
                    ("tree.section.other", others, ()))
        number = 1
        for key, indices, tags in sections:
            if indices:
                section_id = self.tree.insert("", "end", open=True, tags=tags,
                                              text=self._t(key, count=len(indices)))
                self._insert_groups(section_id, indices, first_number=number)
                number += len(indices)

    def _insert_groups(self, parent: str, indices: list[int], first_number: int) -> None:
        groups = self._plan.groups
        for number, index in enumerate(indices, start=first_number):
            group_id = self.tree.insert(parent, "end", open=True)
            self._group_item_ids[index] = group_id
            self._group_numbers[index] = number
            self._item_targets[group_id] = (index, None)
            for path in groups[index].files:
                self._item_targets[self.tree.insert(group_id, "end")] = (index, path)
            self._render_group(index)

    def _is_risky_group(self, index: int) -> bool:
        return any(path in self._risky_files for path in self._plan.groups[index].files)

    def _row_tags(self, item: str) -> tuple[str, ...]:
        _, path = self._item_targets.get(item, (None, None))
        return (_RISKY_TAG,) if path in self._risky_files else ()

    def _file_label(self, path: Path) -> str:
        reasons = self._risky_files.get(path)
        if not reasons:
            return path.name
        return self._t("tree.risky_file", name=path.name,
                       reasons=self._describe_reasons(reasons))

    def _describe_reasons(self, reasons: frozenset[RiskReason]) -> str:
        ordered = [reason for reason in RiskReason if reason in reasons]  # stable order
        return self._t("risk.separator").join(self._t(f"risk.{r.value}") for r in ordered)

    def _render_group(self, index: int) -> None:
        t = self._t
        group = self._plan.groups[index]
        skipped = self._plan.is_skipped(index)
        group_id = self._group_item_ids[index]
        size = format_size(group.size)

        title = t("tree.group", number=self._group_numbers[index], count=len(group.files))
        if skipped:
            title += t("tree.group_skipped_suffix")
        reclaimable = "" if skipped else t(
            "tree.group_reclaimable",
            size=format_size(self._plan.selection(index).reclaimable_bytes),
        )
        self.tree.item(group_id, text=title, values=(reclaimable, size, ""))

        for file_id in self.tree.get_children(group_id):
            _, path = self._item_targets[file_id]
            if skipped:
                action = t("tree.unchanged")
            else:
                action = t("tree.keep" if self._plan.is_kept(index, path) else "tree.remove")
            self.tree.item(file_id, text=self._file_label(path),
                           values=(action, size, str(path)), tags=self._row_tags(file_id))

    def _selected_target(self) -> tuple[Optional[int], Optional[Path]]:
        selection = self.tree.selection()
        if not selection or self._plan is None:
            return None, None
        return self._item_targets.get(selection[0], (None, None))

    def _keep_selected_file(self) -> None:
        self._change_selected_file(ReviewPlan.keep_only)

    def _change_selected_file(self, change: Callable[[ReviewPlan, int, Path], None]) -> None:
        group_index, path = self._selected_target()
        if self._busy or path is None:
            return
        change(self._plan, group_index, path)
        self._render_group(group_index)
        self._update_controls()

    def _toggle_selected_group(self) -> None:
        group_index, _ = self._selected_target()
        if self._busy or group_index is None:
            return
        self._plan.toggle_skipped(group_index)
        self._render_group(group_index)
        self._update_controls()

    # ------------------------------------------------------------------ removal

    def _remove_to_quarantine(self) -> None:
        folder = filedialog.askdirectory(title=self._t("quarantine.dialog_title"))
        if not folder:
            return
        try:
            remover = QuarantineRemover(Path(folder), self._scan_result.roots)
        except ValueError:
            self._show_error("error.bad_folder.title", "error.bad_quarantine.body")
            return
        lead = self._t("confirm.lead.quarantine", count=self._plan.files_to_remove_count,
                       folder=remover.quarantine_dir)
        self._confirm_and_remove(remover, lead)

    def _remove_to_trash(self) -> None:
        lead = self._t("confirm.lead.trash", count=self._plan.files_to_remove_count)
        self._confirm_and_remove(TrashRemover(), lead)

    def _confirm_and_remove(self, remover: Remover, lead: str) -> None:
        t = self._t
        selections = self._plan.selections()
        to_remove = [path for selection in selections for path in selection.files_to_remove]
        if not self._confirm_risky_removal(to_remove):
            return
        details = t("confirm.details", size=format_size(self._plan.reclaimable_bytes))
        if not messagebox.askyesno(t("confirm.title"), f"{lead}\n\n{details}", icon="warning"):
            return
        self._run_task(
            lambda report, cancel: remove_duplicates(
                selections, remover, on_progress=report, cancel_event=cancel
            ),
            on_success=self._on_removal_finished,
            failure_title_key="error.removal_failed.title",
        )

    def _delete_now(self, group_index: int, path: Path) -> None:
        t = self._t
        if not self._confirm_risky_removal([path]):
            return
        if not messagebox.askyesno(t("confirm.delete_now.title"),
                                   t("confirm.delete_now.body", path=path), icon="warning"):
            return
        selection = self._plan.single_removal(group_index, path)
        self._run_task(
            lambda report, cancel: remove_duplicates(
                [selection], TrashRemover(), on_progress=report, cancel_event=cancel
            ),
            on_success=lambda report: self._on_delete_now_finished(group_index, path, report),
            failure_title_key="error.removal_failed.title",
        )

    def _confirm_risky_removal(self, paths: list[Path]) -> bool:
        """Warn before risky files are removed; True if there are none or the user agrees.

        This comes on top of the usual confirmation and defaults to "No", so a
        hurried Enter cannot remove a program or system file.
        """
        risky = [path for path in paths if path in self._risky_files]
        if not risky:
            return True
        t = self._t
        lines = [t("confirm.risky.item", path=path,
                   reasons=self._describe_reasons(self._risky_files[path]))
                 for path in risky[:_MAX_LISTED_RISKY_FILES]]
        if len(risky) > _MAX_LISTED_RISKY_FILES:
            lines.append(t("confirm.risky.more", count=len(risky) - _MAX_LISTED_RISKY_FILES))
        body = t("confirm.risky.body", count=len(risky), files="\n".join(lines))
        return messagebox.askyesno(t("confirm.risky.title"), body, icon="warning",
                                   default="no")

    def _on_delete_now_finished(self, group_index: int, path: Path,
                                report: RemovalReport) -> None:
        if not report.removed:
            self._show_issues("dialog.failures.title", report.failures)
            return
        self._plan.forget(group_index, path)
        self._populate_tree()  # the group may be gone, which shifts the others
        self._set_status(_message("status.deleted_one", path=path))

    def _on_removal_finished(self, report: RemovalReport) -> None:
        t = self._t
        message = t("result.moved", count=len(report.removed))
        if report.failures:
            message += t("result.failed_suffix", count=len(report.failures))
        messagebox.showinfo(t("result.title"), message)
        if report.failures:
            self._show_issues("dialog.failures.title", report.failures)
        self._start_scan(self._scan_request)  # refresh with the same folders and options

    # ---------------------------------------------------------- task plumbing

    def _run_task(self, work: Callable, *, on_success: Callable, failure_title_key: str) -> None:
        def finish(handler: Callable) -> Callable:
            def wrapped(*args) -> None:
                self._task = None
                self.progress.stop()
                self.progress.configure(mode="determinate", value=0)
                handler(*args)
                self._update_controls()

            return wrapped

        def on_error(exc: BaseException) -> None:
            self._set_status(_message("status.failed"))
            messagebox.showerror(self._t(failure_title_key), str(exc))

        self._task = BackgroundTask(
            self.root,
            work,
            on_progress=self._on_progress,
            on_success=finish(on_success),
            on_error=finish(on_error),
            on_cancelled=finish(lambda: self._set_status(_message("status.cancelled"))),
        )
        self._update_controls()
        self._task.start()

    def _on_progress(self, stage: Stage, done: int, total: int) -> None:
        if total:
            self.progress.stop()
            self.progress.configure(mode="determinate", maximum=total, value=done)
            self._set_status(lambda t: t("status.progress_known", stage=t(f"stage.{stage.value}"),
                                         done=done, total=total))
        else:
            if str(self.progress.cget("mode")) != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start(10)
            self._set_status(lambda t: t("status.progress_unknown",
                                         stage=t(f"stage.{stage.value}"), done=done))

    # ------------------------------------------------------------------ dialogs

    def _show_error(self, title_key: str, body_key: str) -> None:
        messagebox.showerror(self._t(title_key), self._t(body_key))

    def _describe_issue(self, issue: FileIssue) -> str:
        return f"{issue.path}: {self._t(f'issue.{issue.kind.value}', detail=issue.detail)}"

    def _show_issues(self, title_key: str, issues) -> None:
        self._show_text_dialog(self._t(title_key), [self._describe_issue(i) for i in issues])

    def _show_text_dialog(self, title: str, lines: list[str]) -> None:
        """Read-only scrollable list; used for both scan errors and removal failures."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("760x380")
        dialog.transient(self.root)
        self._theme.style_window(dialog)

        text = tk.Text(dialog, wrap="none", relief="flat", highlightthickness=1)
        self._theme.style_widget(text, style_text_widget(text))
        yscroll = ttk.Scrollbar(dialog, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=yscroll.set)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")

        ttk.Button(dialog, text=self._t("dialog.close"), command=dialog.destroy).pack(
            side="bottom", pady=6
        )
        yscroll.pack(side=self._end, fill="y")
        text.pack(fill="both", expand=True)


def _state(enabled: bool) -> str:
    return "normal" if enabled else "disabled"


def _context_menu_sequences(root: tk.Misc) -> tuple[str, ...]:
    """Right-click is Button-3 on Windows/Linux but Button-2 (or Ctrl+click) on macOS."""
    if root.tk.call("tk", "windowingsystem") == "aqua":
        return ("<Button-2>", "<Control-Button-1>")
    return ("<Button-3>",)


def main() -> None:
    register_windows_app_id()  # must precede the first window
    root = tk.Tk()
    apply_app_icon(root)
    store = SettingsStore(default_settings_path())
    theme = ThemeManager(root, store)
    theme.start()
    DuplicateFinderApp(root, theme, store, RiskAssessor.for_this_computer())
    root.mainloop()


if __name__ == "__main__":
    main()
