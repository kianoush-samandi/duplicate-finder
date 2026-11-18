"""UI message catalogs. Data only.

Keys are grouped by screen area. Placeholders use ``str.format`` syntax and
must be identical across languages (enforced by tests/test_i18n.py).
"""

from __future__ import annotations

from .i18n import Language

ENGLISH = {
    "app.title": "Duplicate Finder",
    "header.title": "Find Duplicate Files",
    "header.theme": "Theme:",
    "header.language": "Language:",
    "theme.system": "Windows default",
    "theme.light": "Light",
    "theme.dark": "Dark",

    "folder.label": "Folders to scan (duplicates are matched across all of them):",
    "folder.add": "Add folder…",
    "folder.remove": "Remove",
    "folder.dialog_title": "Choose a folder to scan",

    "options.shared_only": "Only files shared between folders",

    "scan.start": "Start scan",
    "scan.cancel": "Cancel",
    "scan.show_errors": "Show errors",

    "status.ready": "Add one or more folders and start the scan.",
    "status.scanning": "Scanning…",
    "status.cancelling": "Cancelling…",
    "status.cancelled": "Operation cancelled.",
    "status.failed": "The operation stopped because of an error.",
    "status.scan_done": (
        "Scan complete | {files:,} files | {groups:,} duplicate groups | "
        "Reclaimable: {size}"
    ),
    "status.scan_errors_suffix": " | {count:,} errors / inaccessible",
    "status.deleted_one": "Moved to the Recycle Bin: {path}",
    "status.progress_known": "{stage}: {done:,} of {total:,}",
    "status.progress_unknown": "{stage}: {done:,}",

    "stage.collecting": "Listing files",
    "stage.partial_hash": "Quick comparison (file beginnings)",
    "stage.full_hash": "Full content comparison",
    "stage.removing": "Moving duplicate copies",

    "tree.heading.item": "Group / File",
    "tree.heading.action": "Action",
    "tree.heading.size": "Size",
    "tree.heading.path": "Path (click to open)",
    "tree.group": "Group {number} ({count} files)",
    "tree.group_skipped_suffix": " — skipped",
    "tree.group_reclaimable": "Frees {size}",
    "tree.keep": "✔ Keep",
    "tree.remove": "✖ Remove",
    "tree.unchanged": "— Unchanged",

    "review.keep": "Keep only this copy (double-click)",
    "review.toggle_skip": "Skip / include group",
    "review.summary": "{count:,} files to remove | Reclaimable: {size}",

    "menu.open": "Open",
    "menu.show_in_folder": "Show in folder",
    "menu.keep": "Keep this copy",
    "menu.remove": "Mark for removal",
    "menu.delete": "Delete now (to Recycle Bin)…",

    "action.quarantine": "Move duplicates to quarantine…",
    "action.trash": "Move duplicates to Recycle Bin…",
    "quarantine.dialog_title": "Choose the quarantine folder",

    "footer.safety": (
        "Safe mode: scanning never changes any file. Before every move, both the kept "
        "copy and the duplicate are verified again. Files are never deleted outright: "
        "they go to a quarantine folder (with a restore manifest) or to the Recycle Bin."
    ),

    "error.no_folder.title": "No folder selected",
    "error.no_folder.body": (
        "You haven't added a folder yet.\n"
        "Please use “Add folder…” to choose the folders you want to scan."
    ),
    "error.folder_included.title": "Folder already included",
    "error.folder_included.body": (
        "This folder is already in the list, or inside a folder that is.\n"
        "It will be scanned anyway."
    ),
    "error.bad_folder.title": "Invalid path",
    "error.bad_folder.body": (
        "The path does not exist or is not a folder.\nPlease choose a valid folder."
    ),
    "error.bad_quarantine.body": (
        "The quarantine folder must not be inside a scanned folder, nor contain one."
    ),
    "error.scan_failed.title": "Scan error",
    "error.removal_failed.title": "Move error",

    "error.open_failed.title": "Cannot open file",
    "error.open_missing.body": (
        "This file no longer exists at:\n{path}\n\nIt may have been moved or deleted "
        "since the scan. Run the scan again to refresh the list."
    ),
    "error.open_failed.body": "The file could not be opened:\n{path}\n\n{detail}",
    "confirm.open_program.title": "Run this program?",
    "confirm.open_program.body": (
        "This file is a program or script, so opening it will run it:\n{path}\n\n"
        "Run it only if you trust it. Continue?"
    ),

    "confirm.delete_now.title": "Delete this file now?",
    "confirm.delete_now.body": (
        "This copy will be moved to the Recycle Bin right away:\n{path}\n\n"
        "It is first compared again with another identical copy, which stays in place. "
        "Continue?"
    ),

    "confirm.title": "Confirm removal",
    "confirm.lead.quarantine": "{count:,} duplicate files will be moved to:\n{folder}",
    "confirm.lead.trash": "{count:,} duplicate files will be moved to the Recycle Bin.",
    "confirm.details": (
        "Space freed: {size}\nCopies marked “Keep” will not be touched.\n\nContinue?"
    ),

    "result.title": "Result",
    "result.moved": "{count:,} files moved.",
    "result.failed_suffix": "\n{count:,} files could not be moved; details follow.",

    "dialog.scan_errors.title": "Scan errors",
    "dialog.failures.title": "Files that were not moved",
    "dialog.close": "Close",

    "issue.access_error": "{detail}",
    "issue.changed_during_scan": "changed while being scanned; skipped",
    "issue.missing": "missing, or no longer a regular file",
    "issue.size_changed": "size changed since the scan",
    "issue.content_changed": "content changed since the scan",
    "issue.hard_linked": "now a hard link to the kept copy",
    "issue.keeper_changed": "the kept copy changed or is missing; group skipped",
}

PERSIAN = {
    "app.title": "یابنده‌ی فایل‌های تکراری",
    "header.title": "پیدا کردن فایل‌های تکراری",
    "header.theme": "تم:",
    "header.language": "زبان:",
    "theme.system": "پیش‌فرض ویندوز",
    "theme.light": "روشن",
    "theme.dark": "تیره",

    "folder.label": "پوشه‌های موردنظر (فایل‌های تکراری بین همه‌ی آن‌ها پیدا می‌شوند):",
    "folder.add": "افزودن پوشه…",
    "folder.remove": "حذف از فهرست",
    "folder.dialog_title": "انتخاب پوشه برای اسکن",

    "options.shared_only": "فقط فایل‌های مشترک بین پوشه‌ها",

    "scan.start": "شروع اسکن",
    "scan.cancel": "لغو",
    "scan.show_errors": "نمایش خطاها",

    "status.ready": "یک یا چند پوشه اضافه کنید و اسکن را شروع کنید.",
    "status.scanning": "در حال اسکن…",
    "status.cancelling": "در حال لغو…",
    "status.cancelled": "عملیات لغو شد.",
    "status.failed": "عملیات با خطا متوقف شد.",
    "status.scan_done": (
        "اسکن تمام شد | {files:,} فایل | {groups:,} گروه تکراری | "
        "فضای قابل آزادسازی: {size}"
    ),
    "status.scan_errors_suffix": " | {count:,} خطا/عدم دسترسی",
    "status.deleted_one": "به سطل بازیافت منتقل شد: {path}",
    "status.progress_known": "{stage}: {done:,} از {total:,}",
    "status.progress_unknown": "{stage}: {done:,}",

    "stage.collecting": "در حال فهرست کردن فایل‌ها",
    "stage.partial_hash": "مقایسه‌ی سریع (ابتدای فایل‌ها)",
    "stage.full_hash": "مقایسه‌ی کامل محتوا",
    "stage.removing": "در حال انتقال نسخه‌های تکراری",

    "tree.heading.item": "گروه / فایل",
    "tree.heading.action": "وضعیت",
    "tree.heading.size": "حجم",
    "tree.heading.path": "مسیر (برای باز کردن کلیک کنید)",
    "tree.group": "گروه {number} ({count} فایل)",
    "tree.group_skipped_suffix": " — رد شده",
    "tree.group_reclaimable": "آزاد می‌شود: {size}",
    "tree.keep": "✔ نگه‌داشته می‌شود",
    "tree.remove": "✖ حذف می‌شود",
    "tree.unchanged": "— بدون تغییر",

    "review.keep": "فقط این نسخه نگه‌داشته شود (دابل‌کلیک)",
    "review.toggle_skip": "رد کردن / گنجاندن گروه",
    "review.summary": "{count:,} فایل برای حذف | فضای آزادشونده: {size}",

    "menu.open": "باز کردن",
    "menu.show_in_folder": "نمایش در پوشه",
    "menu.keep": "نگه‌داشتن این نسخه",
    "menu.remove": "علامت‌گذاری برای حذف",
    "menu.delete": "حذف فوری (انتقال به سطل بازیافت)…",

    "action.quarantine": "انتقال تکراری‌ها به قرنطینه…",
    "action.trash": "انتقال تکراری‌ها به سطل بازیافت…",
    "quarantine.dialog_title": "پوشه‌ی قرنطینه را انتخاب کنید",

    "footer.safety": (
        "حالت امن: اسکن هیچ فایلی را تغییر نمی‌دهد. پیش از هر انتقال، هم نسخه‌ی "
        "نگه‌داشته‌شده و هم نسخه‌ی تکراری دوباره بررسی می‌شوند. فایل‌ها هرگز مستقیماً "
        "پاک نمی‌شوند: به قرنطینه (با فهرست بازگردانی) یا سطل بازیافت می‌روند."
    ),

    "error.no_folder.title": "پوشه‌ای انتخاب نشده",
    "error.no_folder.body": (
        "هنوز پوشه‌ای اضافه نکرده‌اید.\n"
        "لطفاً با دکمه‌ی «افزودن پوشه…» پوشه‌هایی را که می‌خواهید بررسی شوند انتخاب کنید."
    ),
    "error.folder_included.title": "پوشه از قبل در فهرست است",
    "error.folder_included.body": (
        "این پوشه یا خودش در فهرست هست یا داخل پوشه‌ای از فهرست قرار دارد.\n"
        "در هر صورت اسکن خواهد شد."
    ),
    "error.bad_folder.title": "مسیر نامعتبر",
    "error.bad_folder.body": (
        "مسیر واردشده وجود ندارد یا یک پوشه نیست.\nلطفاً یک پوشه‌ی معتبر انتخاب کنید."
    ),
    "error.bad_quarantine.body": (
        "پوشه‌ی قرنطینه نباید داخل یکی از پوشه‌های اسکن‌شده باشد و نباید یکی از آن‌ها را در بر بگیرد."
    ),
    "error.scan_failed.title": "خطا در اسکن",
    "error.removal_failed.title": "خطا در انتقال",

    "error.open_failed.title": "باز کردن فایل ممکن نیست",
    "error.open_missing.body": (
        "این فایل دیگر در این مسیر وجود ندارد:\n{path}\n\nممکن است پس از اسکن جابه‌جا "
        "یا حذف شده باشد. برای به‌روز شدن فهرست، دوباره اسکن کنید."
    ),
    "error.open_failed.body": "فایل باز نشد:\n{path}\n\n{detail}",
    "confirm.open_program.title": "این برنامه اجرا شود؟",
    "confirm.open_program.body": (
        "این فایل یک برنامه یا اسکریپت است و باز کردن آن یعنی اجرای آن:\n{path}\n\n"
        "فقط اگر به آن اطمینان دارید اجرایش کنید. ادامه می‌دهید؟"
    ),

    "confirm.delete_now.title": "این فایل همین حالا حذف شود؟",
    "confirm.delete_now.body": (
        "این نسخه بلافاصله به سطل بازیافت منتقل می‌شود:\n{path}\n\n"
        "پیش از آن دوباره با یک نسخه‌ی یکسان دیگر مقایسه می‌شود که سر جایش می‌ماند. "
        "ادامه می‌دهید؟"
    ),

    "confirm.title": "تأیید حذف",
    "confirm.lead.quarantine": "{count:,} فایل تکراری به این پوشه منتقل می‌شوند:\n{folder}",
    "confirm.lead.trash": "{count:,} فایل تکراری به سطل بازیافت سیستم منتقل می‌شوند.",
    "confirm.details": (
        "فضای آزادشونده: {size}\nنسخه‌های علامت‌خورده با «نگه‌داشته می‌شود» دست "
        "نمی‌خورند.\n\nادامه می‌دهید؟"
    ),

    "result.title": "نتیجه",
    "result.moved": "{count:,} فایل منتقل شد.",
    "result.failed_suffix": "\n{count:,} فایل منتقل نشد؛ جزئیات در پنجره‌ی بعدی.",

    "dialog.scan_errors.title": "خطاهای اسکن",
    "dialog.failures.title": "فایل‌هایی که منتقل نشدند",
    "dialog.close": "بستن",

    "issue.access_error": "{detail}",
    "issue.changed_during_scan": "هنگام اسکن تغییر کرد؛ نادیده گرفته شد",
    "issue.missing": "وجود ندارد یا دیگر یک فایل عادی نیست",
    "issue.size_changed": "حجم فایل پس از اسکن تغییر کرده است",
    "issue.content_changed": "محتوای فایل پس از اسکن تغییر کرده است",
    "issue.hard_linked": "اکنون هاردلینکی به نسخه‌ی نگه‌داشته‌شده است",
    "issue.keeper_changed": "نسخه‌ی نگه‌داشته‌شده تغییر کرده یا وجود ندارد؛ گروه رد شد",
}

CATALOGS = {Language.ENGLISH: ENGLISH, Language.PERSIAN: PERSIAN}
