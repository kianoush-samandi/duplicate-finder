# Duplicate Finder

A desktop tool (Python + Tkinter) that finds duplicate files and safely removes the extra copies — **only after you approve**.
Available in **English** (default) and **Persian (فارسی)**, with light and dark themes.

[فارسی](#فارسی)

## Features

- **Fast three-stage comparison:** size → hash of the first 64 KiB → full BLAKE2b hash. Most non-duplicates are discarded without being read in full.
- **You choose the copy to keep** in each group (double-click), and can **skip** any group.
- **Safe removal:**
  - The copy you keep is re-verified first; if it changed or disappeared, the whole group is left untouched.
  - Every duplicate is re-hashed right before it is moved.
  - Nothing is deleted outright: files go to a **quarantine folder** (with a `manifest.jsonl` for restoring) or to the system **Recycle Bin**.
- Hard links, symlinks and Windows junctions are handled correctly; empty files are ignored.
- Scanning and removal run in the background — the window never freezes, and both can be **cancelled**.
- Access errors are never hidden; they can be reviewed in a separate window.
- **Themes:** Light, Dark, or *Windows default*, which follows Windows' app mode live.
- **Languages:** English or Persian, switchable at any time without losing your results; the layout is mirrored for right-to-left.

Theme and language choices are saved to `%APPDATA%\DuplicateFinder\settings.json` (Windows) or `~/.config/DuplicateFinder/settings.json`.

## Download

**Windows 10/11 (64-bit):** [⬇ Download DuplicateFinder-Setup.exe](https://github.com/kianoush-samandi/duplicate-finder/releases/latest/download/DuplicateFinder-Setup.exe)

The link always points to the latest release; no Python needed. Older versions and release
notes are on the [Releases page](https://github.com/kianoush-samandi/duplicate-finder/releases).

## Run from source

Python 3.9+:

```bash
git clone https://github.com/kianoush-samandi/duplicate-finder.git
cd duplicate-finder
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -e ".[trash]"            # "trash" adds optional Recycle Bin support
python -m duplicate_finder
```

On Linux, Tkinter is a separate package: `sudo apt install python3-tk`.

## Building the Windows installer

The installer is built in two steps by one command: PyInstaller bundles the app with its own
Python runtime (so users do not need Python), then Inno Setup packages that folder.

Requirements: 64-bit Windows, 64-bit Python, and [Inno Setup 7.1+](https://jrsoftware.org/isdl.php).

```bash
pip install -e ".[trash]" pyinstaller
python tools/build_icons.py          # only if duplicate_finder/assets/icon.ico is missing
python tools/build_installer.py      # add --iscc PATH if ISCC.exe is not found automatically
```

The result is `dist/installer/DuplicateFinder-Setup.exe`. The version comes from
`duplicate_finder.__version__`; it is shown in the installer and in the file's properties.
The file name has no version on purpose, so the download link above never needs updating.

To publish it, create a release whose tag matches the version and attach the installer
(the [GitHub CLI](https://cli.github.com/) is shown; the Releases page works too):

```bash
gh release create v0.4.0 dist/installer/DuplicateFinder-Setup.exe --generate-notes
```

What the installer does:

- Installs **per user** by default (no administrator prompt); "all users" can still be chosen.
- English and Persian wizards, chosen from the Windows language; light/dark follows Windows.
- Optional Start-menu shortcut (on by default) and desktop shortcut (off by default), both with the same taskbar ID as the app, so a pinned icon and the running window stay one taskbar button.
- Upgrades in place and closes a running copy first; on uninstall it asks whether to remove your settings. Quarantine folders are never touched.

Do not compile `packaging/installer.iss` on its own: `tools/build_installer.py` passes it the
version, paths and IDs taken from the app's code, so each is defined in one place only.

## Project structure

```
duplicate_finder/
├── models.py        # immutable data: DuplicateGroup, ScanResult, Selection, FileIssue, …
├── hashing.py       # partial_digest / full_digest
├── scanner.py       # find_duplicates — pure logic, no GUI, never modifies files
├── removal.py       # Remover strategies (Quarantine / Trash) + verified remove_duplicates
├── review.py        # ReviewPlan — the user's choices (kept copy, skipped groups)
├── progress.py      # throttled progress reporting + cancellation, shared by all operations
├── background.py    # runs work off the Tk thread and hands results back safely
├── validation.py    # user-input validation (e.g. empty / invalid folder)
├── i18n.py          # Language, Translator (with English fallback)
├── translations.py  # message catalogs — data only
├── theme.py         # ThemeMode, palettes, Windows dark-mode detection — no Tk
├── settings.py      # persisted preferences (JSON)
├── styling.py       # ThemeManager — applies palettes to ttk, follows the OS setting
├── app_icon.py      # window/taskbar icon and the Windows taskbar ID
├── formatting.py    # format_size
└── gui.py           # presentation only (Tkinter)
packaging/
├── installer.iss    # Inno Setup script
├── launcher.py      # PyInstaller entry point
└── languages/Farsi.isl  # Persian installer text (from the Inno Setup project)
tools/
├── build_icons.py      # SVG masters → icon.ico / icon.png
└── build_installer.py  # PyInstaller + Inno Setup → Setup.exe
```

The core (`scanner`, `removal`, `review`) has no Tkinter dependency and reports problems as
structured `FileIssue` values rather than sentences, so it is testable on its own and every
message shown to the user can be translated.

## Adding a language

1. Add a member to `Language` in `i18n.py` (plus its native name, and add it to `_RTL_LANGUAGES` if it is right-to-left).
2. Add a catalog to `translations.py` and register it in `CATALOGS`.
3. Run `pytest` — the tests fail if any key or placeholder is missing.
4. For the installer, add the language to `[Languages]` and `[CustomMessages]` in `packaging/installer.iss`.

## Restoring from quarantine

Each line of `manifest.jsonl` records one move:

```json
{"moved_at": "2026-11-15T20:00:00+00:00", "original": "/path/a.txt", "quarantined": "/q/a.txt"}
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Known limitations

- On **Linux**, Tk does not shape right-to-left text, so Persian appears with reversed letters. Windows and macOS render it correctly.
- *Windows default* theme reads the OS setting on Windows only; elsewhere it falls back to Light (manual choice works everywhere).
- The cross-platform `clam` ttk theme is used (native `vista` ignores custom colors), so buttons look slightly different from native Windows controls.

## فارسی

ابزاری برای پیدا کردن فایل‌های تکراری و حذف امن نسخه‌های اضافه، فقط پس از تأیید کاربر. زبان پیش‌فرض انگلیسی است و از بالای پنجره (بخش **Language**) می‌توانید زبان را به **فارسی** تغییر دهید. انتخاب شما ذخیره می‌شود و نتایج اسکن هنگام تغییر زبان از بین نمی‌رود.

**دانلود برای ویندوز ۱۰ و ۱۱ (۶۴ بیتی):** [⬇ دریافت DuplicateFinder-Setup.exe](https://github.com/kianoush-samandi/duplicate-finder/releases/latest/download/DuplicateFinder-Setup.exe) — همیشه آخرین نسخه را دانلود می‌کند و به پایتون نیازی ندارد. برای ساختن نصب‌کننده، بخش «Building the Windows installer» را ببینید.

نکته: روی لینوکس، Tk حروف فارسی را برعکس نمایش می‌دهد؛ روی ویندوز و macOS نمایش درست است.

## License

MIT — see [LICENSE](LICENSE).
