"""Tkinter front end. Presentation only: all decisions live in the core modules.

Language switching rebuilds the widget tree. Application state (scan
results, review plan, field contents, status) lives outside the widgets,
so a rebuild loses nothing and the layout can be mirrored for RTL languages.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable, Optional

from .background import BackgroundTask
from .formatting import format_size
from .i18n import Language, Translator
from .models import FileIssue, RemovalReport, ScanResult
from .progress import Stage
from .removal import QuarantineRemover, Remover, TrashRemover, remove_duplicates
from .review import ReviewPlan
from .scanner import find_duplicates
from .settings import SettingsStore, default_settings_path
from .styling import ThemeManager, style_text_widget
from .theme import ThemeMode
from .validation import FolderNotSelectedError, NotAFolderError, parse_scan_folder

# A status line is stored as a function of the translator, so it can be
# re-rendered in the new language after a switch.
StatusMessage = Callable[[Translator], str]


def _message(key: str, **values) -> StatusMessage:
    return lambda t: t(key, **values)


class DuplicateFinderApp:
    def __init__(self, root: tk.Tk, theme: ThemeManager, store: SettingsStore) -> None:
        self.root = root
        self._theme = theme
        self._store = store
        self._t = Translator(store.load().language)
        self.root.geometry("1000x680")
        self.root.minsize(800, 520)

        # State that must survive a UI rebuild.
        self._task: Optional[BackgroundTask] = None
        self._scan_result: Optional[ScanResult] = None
        self._plan: Optional[ReviewPlan] = None
        self._status: StatusMessage = _message("status.ready")
        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.plan_var = tk.StringVar()
        self.theme_var = tk.StringVar(value=theme.mode.value)
        self.language_var = tk.StringVar(value=self._t.language.value)

        # Widget bookkeeping, recreated by every rebuild.
        self._main: Optional[ttk.Frame] = None
        self._language_buttons: list[ttk.Radiobutton] = []
        self._group_item_ids: list[str] = []
        self._item_targets: dict[str, tuple[int, Optional[Path]]] = {}

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
        rtl = t.language.is_rtl
        # Mirrored layout for right-to-left languages.
        self._start, self._end = ("right", "left") if rtl else ("left", "right")
        self._anchor = "e" if rtl else "w"
        self._justify = "right" if rtl else "left"
        self.root.title(t("app.title"))

        self._main = main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        self._build_header(main)
        self._build_folder_row(main)
        self._build_scan_row(main)

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 6))
        ttk.Label(main, textvariable=self.status_var, justify=self._justify).pack(
            anchor=self._anchor, pady=(0, 6)
        )

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

    def _radio(self, parent, text, value, variable, command) -> ttk.Radiobutton:
        button = ttk.Radiobutton(parent, text=text, value=value, variable=variable,
                                 command=command)
        button.pack(side=self._start, padx=4)
        return button

    def _on_theme_selected(self) -> None:
        self._theme.set_mode(ThemeMode(self.theme_var.get()))

    def _build_folder_row(self, parent: ttk.Frame) -> None:
        t = self._t
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text=t("folder.label")).pack(side=self._start)
        self.folder_entry = ttk.Entry(row, textvariable=self.folder_var)
        self.folder_entry.pack(side=self._start, fill="x", expand=True, padx=8)
        self.browse_button = ttk.Button(row, text=t("folder.browse"),
                                        command=self._choose_folder)
        self.browse_button.pack(side=self._start)

    def _build_scan_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=10)
        self.scan_button = ttk.Button(row, command=self._on_scan_clicked)
        self.scan_button.pack(side=self._start)
        self.errors_button = ttk.Button(row, text=self._t("scan.show_errors"),
                                        command=self._show_scan_errors)
        self.errors_button.pack(side=self._start, padx=8)

    def _build_tree(self, parent: ttk.Frame) -> None:
        t = self._t
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            frame, columns=("action", "size", "path"), show="tree headings", selectmode="browse"
        )
        for column, key, width, anchor in (
            ("#0", "tree.heading.item", 260, self._anchor),
            ("action", "tree.heading.action", 190, self._anchor),
            ("size", "tree.heading.size", 100, "e"),
            ("path", "tree.heading.path", 440, "w"),  # paths are always left-to-right
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
        self.tree.bind("<Double-1>", lambda _event: self._keep_selected_file())

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
        self.quarantine_button = ttk.Button(row, text=t("action.quarantine"),
                                            command=self._remove_to_quarantine)
        self.quarantine_button.pack(side=self._start)
        self.trash_button = ttk.Button(row, text=t("action.trash"),
                                       command=self._remove_to_trash)
        self.trash_button.pack(side=self._start, padx=8)

    # ------------------------------------------------------------ control state

    @property
    def _busy(self) -> bool:
        return self._task is not None

    def _update_controls(self) -> None:
        t = self._t
        idle = _state(not self._busy)
        self.browse_button.configure(state=idle)
        self.folder_entry.configure(state=idle)
        for button in self._language_buttons:  # a rebuild mid-task is not worth the risk
            button.configure(state=idle)
        self.scan_button.configure(text=t("scan.cancel" if self._busy else "scan.start"))

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

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder.dialog_title"))
        if selected:
            self.folder_var.set(selected)

    def _on_scan_clicked(self) -> None:
        if self._busy:
            self._task.cancel()
            self._set_status(_message("status.cancelling"))
            return
        try:
            folder = parse_scan_folder(self.folder_var.get())
        except FolderNotSelectedError:
            self._show_error("error.no_folder.title", "error.no_folder.body")
            return
        except NotAFolderError:
            self._show_error("error.bad_folder.title", "error.bad_folder.body")
            return
        self._start_scan(folder)

    def _start_scan(self, root: Path) -> None:
        self._set_results(None)
        self._set_status(_message("status.scanning"))
        self._run_task(
            lambda report, cancel: find_duplicates(root, on_progress=report, cancel_event=cancel),
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
        self._populate_tree()
        self._update_controls()

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._group_item_ids.clear()
        self._item_targets.clear()
        if self._plan is None:
            return
        for index, group in enumerate(self._plan.groups):
            group_id = self.tree.insert("", "end", open=True)
            self._group_item_ids.append(group_id)
            self._item_targets[group_id] = (index, None)
            for path in group.files:
                self._item_targets[self.tree.insert(group_id, "end")] = (index, path)
            self._render_group(index)

    def _render_group(self, index: int) -> None:
        t = self._t
        group = self._plan.groups[index]
        skipped = self._plan.is_skipped(index)
        keeper = self._plan.keeper(index)
        group_id = self._group_item_ids[index]
        size = format_size(group.size)

        title = t("tree.group", number=index + 1, count=len(group.files))
        if skipped:
            title += t("tree.group_skipped_suffix")
        reclaimable = "" if skipped else t(
            "tree.group_reclaimable", size=format_size(group.reclaimable_bytes)
        )
        self.tree.item(group_id, text=title, values=(reclaimable, size, ""))

        for file_id in self.tree.get_children(group_id):
            _, path = self._item_targets[file_id]
            if skipped:
                action = t("tree.unchanged")
            else:
                action = t("tree.keep" if path == keeper else "tree.remove")
            self.tree.item(file_id, text=path.name, values=(action, size, str(path)))

    def _selected_target(self) -> tuple[Optional[int], Optional[Path]]:
        selection = self.tree.selection()
        if not selection or self._plan is None:
            return None, None
        return self._item_targets.get(selection[0], (None, None))

    def _keep_selected_file(self) -> None:
        group_index, path = self._selected_target()
        if self._busy or group_index is None or path is None:
            return
        self._plan.set_keeper(group_index, path)
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
            remover = QuarantineRemover(Path(folder), self._scan_result.root)
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
        details = t("confirm.details", size=format_size(self._plan.reclaimable_bytes))
        if not messagebox.askyesno(t("confirm.title"), f"{lead}\n\n{details}", icon="warning"):
            return
        selections = self._plan.selections()
        self._run_task(
            lambda report, cancel: remove_duplicates(
                selections, remover, on_progress=report, cancel_event=cancel
            ),
            on_success=self._on_removal_finished,
            failure_title_key="error.removal_failed.title",
        )

    def _on_removal_finished(self, report: RemovalReport) -> None:
        t = self._t
        message = t("result.moved", count=len(report.removed))
        if report.failures:
            message += t("result.failed_suffix", count=len(report.failures))
        messagebox.showinfo(t("result.title"), message)
        if report.failures:
            self._show_issues("dialog.failures.title", report.failures)
        self._start_scan(self._scan_result.root)  # refresh with the same root

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


def main() -> None:
    root = tk.Tk()
    store = SettingsStore(default_settings_path())
    theme = ThemeManager(root, store)
    theme.start()
    DuplicateFinderApp(root, theme, store)
    root.mainloop()


if __name__ == "__main__":
    main()
