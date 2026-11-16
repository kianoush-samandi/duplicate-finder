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

## Install & run

Requires Python 3.9+.

```bash
git clone https://github.com/<USERNAME>/duplicate-finder.git
cd duplicate-finder
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -e ".[trash]"            # "trash" adds optional Recycle Bin support
python -m duplicate_finder
```

On Linux, Tkinter is a separate package: `sudo apt install python3-tk`.

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
├── formatting.py    # format_size
└── gui.py           # presentation only (Tkinter)
```

The core (`scanner`, `removal`, `review`) has no Tkinter dependency and reports problems as
structured `FileIssue` values rather than sentences, so it is testable on its own and every
message shown to the user can be translated.

## Adding a language

1. Add a member to `Language` in `i18n.py` (plus its native name, and add it to `_RTL_LANGUAGES` if it is right-to-left).
2. Add a catalog to `translations.py` and register it in `CATALOGS`.
3. Run `pytest` — the tests fail if any key or placeholder is missing.

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

نکته: روی لینوکس، Tk حروف فارسی را برعکس نمایش می‌دهد؛ روی ویندوز و macOS نمایش درست است.

## License

MIT — see [LICENSE](LICENSE).
