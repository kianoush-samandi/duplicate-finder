"""Tkinter front end. Presentation only: all decisions live in the core modules."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable, Optional

from .background import BackgroundTask
from .formatting import format_size
from .models import RemovalReport, ScanResult
from .progress import Stage
from .removal import QuarantineRemover, Remover, TrashRemover, remove_duplicates
from .review import ReviewPlan
from .scanner import find_duplicates
from .settings import SettingsStore, default_settings_path
from .styling import ThemeManager, style_text_widget
from .theme import ThemeMode
from .validation import FolderNotSelectedError, NotAFolderError, parse_scan_folder

APP_TITLE = "Duplicate Finder"

THEME_LABELS = {
    ThemeMode.SYSTEM: "پیش‌فرض ویندوز",
    ThemeMode.LIGHT: "روشن",
    ThemeMode.DARK: "تیره",
}

STAGE_LABELS = {
    Stage.COLLECTING: "در حال فهرست کردن فایل‌ها",
    Stage.PARTIAL_HASH: "مقایسه‌ی سریع (ابتدای فایل‌ها)",
    Stage.FULL_HASH: "مقایسه‌ی کامل محتوا",
    Stage.REMOVING: "در حال انتقال نسخه‌های تکراری",
}

KEEP_LABEL = "✔ نگه‌داشته می‌شود"
REMOVE_LABEL = "✖ حذف می‌شود"
SKIPPED_LABEL = "— بدون تغییر"


class DuplicateFinderApp:
    def __init__(self, root: tk.Tk, theme: ThemeManager) -> None:
        self.root = root
        self._theme = theme
        self.root.title(APP_TITLE)
        self.root.geometry("980x680")
        self.root.minsize(780, 520)

        self._task: Optional[BackgroundTask] = None
        self._scan_result: Optional[ScanResult] = None
        self._plan: Optional[ReviewPlan] = None
        self._group_item_ids: list[str] = []
        # tree item id -> (group index, file path or None for the group row)
        self._item_targets: dict[str, tuple[int, Optional[Path]]] = {}

        self._build_ui()
        self._update_controls()

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        self._build_header(main)
        self._build_folder_row(main)
        self._build_scan_row(main)

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 6))
        self.status_var = tk.StringVar(value="یک پوشه انتخاب کنید و اسکن را شروع کنید.")
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(0, 6))

        self._build_tree(main)
        self._build_review_row(main)
        self._build_action_row(main)

        ttk.Label(
            main,
            text=(
                "حالت امن: اسکن هیچ فایلی را تغییر نمی‌دهد. پیش از هر انتقال، هم نسخه‌ی "
                "نگه‌داشته‌شده و هم نسخه‌ی تکراری دوباره بررسی می‌شوند. فایل‌ها هرگز "
                "مستقیماً پاک نمی‌شوند: به قرنطینه (با فهرست بازگردانی) یا سطل بازیافت می‌روند."
            ),
            wraplength=940,
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(8, 0))

    def _build_header(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 10))

        title_font = tkfont.nametofont("TkDefaultFont").copy()
        title_font.configure(size=16, weight="bold")
        ttk.Label(row, text="پیدا کردن فایل‌های تکراری", font=title_font).pack(side="left")

        self.theme_var = tk.StringVar(value=self._theme.mode.value)
        for mode in reversed(ThemeMode):  # packed right-to-left
            ttk.Radiobutton(
                row,
                text=THEME_LABELS[mode],
                value=mode.value,
                variable=self.theme_var,
                command=self._on_theme_selected,
            ).pack(side="right", padx=(8, 0))
        ttk.Label(row, text="تم:").pack(side="right")

    def _on_theme_selected(self) -> None:
        self._theme.set_mode(ThemeMode(self.theme_var.get()))

    def _build_folder_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text="پوشه موردنظر:").pack(side="left")
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(row, textvariable=self.folder_var)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.browse_button = ttk.Button(row, text="انتخاب پوشه", command=self._choose_folder)
        self.browse_button.pack(side="left")

    def _build_scan_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=10)
        self.scan_button = ttk.Button(row, text="شروع اسکن", command=self._on_scan_clicked)
        self.scan_button.pack(side="left")
        self.errors_button = ttk.Button(row, text="نمایش خطاها", command=self._show_scan_errors)
        self.errors_button.pack(side="left", padx=8)

    def _build_tree(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            frame, columns=("action", "size", "path"), show="tree headings", selectmode="browse"
        )
        for column, text, width, anchor in (
            ("#0", "گروه / فایل", 260, "w"),
            ("action", "وضعیت", 170, "w"),
            ("size", "حجم", 100, "e"),
            ("path", "مسیر", 460, "w"),
        ):
            self.tree.heading(column, text=text)
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
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        self.keep_button = ttk.Button(
            row, text="نگه‌داشتن این نسخه (دابل‌کلیک)", command=self._keep_selected_file
        )
        self.keep_button.pack(side="left")
        self.skip_button = ttk.Button(
            row, text="رد کردن / گنجاندن گروه", command=self._toggle_selected_group
        )
        self.skip_button.pack(side="left", padx=8)
        self.plan_var = tk.StringVar()
        ttk.Label(row, textvariable=self.plan_var).pack(side="left", padx=8)

    def _build_action_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        self.quarantine_button = ttk.Button(
            row, text="انتقال تکراری‌ها به قرنطینه…", command=self._remove_to_quarantine
        )
        self.quarantine_button.pack(side="left")
        self.trash_button = ttk.Button(
            row, text="انتقال تکراری‌ها به سطل بازیافت…", command=self._remove_to_trash
        )
        self.trash_button.pack(side="left", padx=8)

    # ------------------------------------------------------------ control state

    @property
    def _busy(self) -> bool:
        return self._task is not None

    def _update_controls(self) -> None:
        idle = "disabled" if self._busy else "normal"
        self.browse_button.configure(state=idle)
        self.folder_entry.configure(state=idle)
        self.scan_button.configure(text="لغو" if self._busy else "شروع اسکن")

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

        if self._plan is None:
            self.plan_var.set("")
        else:
            self.plan_var.set(
                f"{self._plan.files_to_remove_count:,} فایل برای حذف | "
                f"فضای آزادشونده: {format_size(self._plan.reclaimable_bytes)}"
            )

    # ------------------------------------------------------------------ scanning

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="انتخاب پوشه برای اسکن")
        if selected:
            self.folder_var.set(selected)

    def _on_scan_clicked(self) -> None:
        if self._busy:
            self._task.cancel()
            self.status_var.set("در حال لغو…")
            return
        try:
            folder = parse_scan_folder(self.folder_var.get())
        except FolderNotSelectedError:
            messagebox.showerror(
                "پوشه‌ای انتخاب نشده",
                "هنوز پوشه‌ای انتخاب نکرده‌اید.\n"
                "لطفاً با دکمه‌ی «انتخاب پوشه» پوشه‌ای را که می‌خواهید بررسی شود انتخاب کنید.",
            )
            return
        except NotAFolderError:
            messagebox.showerror(
                "مسیر نامعتبر",
                "مسیر واردشده وجود ندارد یا یک پوشه نیست.\nلطفاً یک پوشه‌ی معتبر انتخاب کنید.",
            )
            return
        self._start_scan(folder)

    def _start_scan(self, root: Path) -> None:
        self._set_results(None)
        self.status_var.set("در حال اسکن…")
        self._run_task(
            lambda report, cancel: find_duplicates(root, on_progress=report, cancel_event=cancel),
            on_success=self._on_scan_finished,
            failure_title="خطا در اسکن",
        )

    def _on_scan_finished(self, result: ScanResult) -> None:
        self._set_results(result)
        summary = (
            f"اسکن تمام شد | {result.total_files:,} فایل | "
            f"{len(result.groups):,} گروه تکراری | "
            f"فضای قابل آزادسازی: {format_size(result.reclaimable_bytes)}"
        )
        if result.errors:
            summary += f" | {len(result.errors):,} خطا/عدم دسترسی"
        self.status_var.set(summary)

    def _show_scan_errors(self) -> None:
        if self._scan_result:
            self._show_text_dialog("خطاهای اسکن", self._scan_result.errors)

    # ------------------------------------------------------------------ results

    def _set_results(self, result: Optional[ScanResult]) -> None:
        self._scan_result = result
        self._plan = ReviewPlan(result.groups) if result else None
        self.tree.delete(*self.tree.get_children())
        self._group_item_ids.clear()
        self._item_targets.clear()

        if result:
            for index, group in enumerate(result.groups):
                group_id = self.tree.insert("", "end", open=True)
                self._group_item_ids.append(group_id)
                self._item_targets[group_id] = (index, None)
                for path in group.files:
                    file_id = self.tree.insert(group_id, "end")
                    self._item_targets[file_id] = (index, path)
                self._render_group(index)
        self._update_controls()

    def _render_group(self, index: int) -> None:
        group = self._plan.groups[index]
        skipped = self._plan.is_skipped(index)
        keeper = self._plan.keeper(index)
        group_id = self._group_item_ids[index]

        title = f"گروه {index + 1} ({len(group.files)} فایل)"
        self.tree.item(
            group_id,
            text=title + (" — رد شده" if skipped else ""),
            values=(
                "" if skipped else f"آزاد می‌شود: {format_size(group.reclaimable_bytes)}",
                format_size(group.size),
                "",
            ),
        )
        for file_id in self.tree.get_children(group_id):
            _, path = self._item_targets[file_id]
            if skipped:
                action = SKIPPED_LABEL
            else:
                action = KEEP_LABEL if path == keeper else REMOVE_LABEL
            self.tree.item(
                file_id, text=path.name, values=(action, format_size(group.size), str(path))
            )

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
        folder = filedialog.askdirectory(title="پوشه‌ی قرنطینه را انتخاب کنید")
        if not folder:
            return
        try:
            remover = QuarantineRemover(Path(folder), self._scan_result.root)
        except ValueError:
            messagebox.showerror(
                "مسیر نامعتبر",
                "پوشه‌ی قرنطینه نباید داخل پوشه‌ی اسکن‌شده باشد و نباید آن را در بر بگیرد.",
            )
            return
        self._confirm_and_remove(remover, f"به این پوشه منتقل می‌شوند:\n{remover.quarantine_dir}")

    def _remove_to_trash(self) -> None:
        self._confirm_and_remove(TrashRemover(), "به سطل بازیافت سیستم منتقل می‌شوند.")

    def _confirm_and_remove(self, remover: Remover, destination_text: str) -> None:
        plan = self._plan
        confirmed = messagebox.askyesno(
            "تأیید حذف",
            f"{plan.files_to_remove_count:,} فایل تکراری {destination_text}\n\n"
            f"فضای آزادشونده: {format_size(plan.reclaimable_bytes)}\n"
            "نسخه‌های علامت‌خورده با «نگه‌داشته می‌شود» دست نمی‌خورند.\n\nادامه می‌دهید؟",
            icon="warning",
        )
        if not confirmed:
            return
        selections = plan.selections()
        self._run_task(
            lambda report, cancel: remove_duplicates(
                selections, remover, on_progress=report, cancel_event=cancel
            ),
            on_success=self._on_removal_finished,
            failure_title="خطا در انتقال",
        )

    def _on_removal_finished(self, report: RemovalReport) -> None:
        message = f"{len(report.removed):,} فایل منتقل شد."
        if report.failures:
            message += f"\n{len(report.failures):,} فایل منتقل نشد؛ جزئیات در پنجره‌ی بعدی."
        messagebox.showinfo("نتیجه", message)
        if report.failures:
            self._show_text_dialog("فایل‌هایی که منتقل نشدند", report.failures)
        self._start_scan(self._scan_result.root)  # refresh with the same root

    # ---------------------------------------------------------- task plumbing

    def _run_task(
        self, work: Callable, *, on_success: Callable, failure_title: str
    ) -> None:
        def finish(handler: Callable) -> Callable:
            def wrapped(*args) -> None:
                self._task = None
                self.progress.stop()
                self.progress.configure(mode="determinate", value=0)
                handler(*args)
                self._update_controls()

            return wrapped

        def on_error(exc: BaseException) -> None:
            self.status_var.set("عملیات با خطا متوقف شد.")
            messagebox.showerror(failure_title, str(exc))

        self._task = BackgroundTask(
            self.root,
            work,
            on_progress=self._on_progress,
            on_success=finish(on_success),
            on_error=finish(on_error),
            on_cancelled=finish(lambda: self.status_var.set("عملیات لغو شد.")),
        )
        self._update_controls()
        self._task.start()

    def _on_progress(self, stage: Stage, done: int, total: int) -> None:
        label = STAGE_LABELS[stage]
        if total:
            self.progress.stop()
            self.progress.configure(mode="determinate", maximum=total, value=done)
            self.status_var.set(f"{label}: {done:,} از {total:,}")
        else:
            if str(self.progress.cget("mode")) != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start(10)
            self.status_var.set(f"{label}: {done:,}")


    def _show_text_dialog(self, title: str, lines) -> None:
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

        ttk.Button(dialog, text="بستن", command=dialog.destroy).pack(side="bottom", pady=6)
        yscroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)


def _state(enabled: bool) -> str:
    return "normal" if enabled else "disabled"


def main() -> None:
    root = tk.Tk()
    theme = ThemeManager(root, SettingsStore(default_settings_path()))
    theme.start()
    DuplicateFinderApp(root, theme)
    root.mainloop()


if __name__ == "__main__":
    main()
