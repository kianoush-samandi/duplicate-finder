# Duplicate Finder

ابزاری دسکتاپ (Python + Tkinter) برای پیدا کردن فایل‌های تکراری و حذف امن نسخه‌های اضافه، **فقط پس از تأیید کاربر**.

A desktop tool to find duplicate files and safely remove extra copies — only after you approve.

## ویژگی‌ها

- **مقایسه‌ی سه‌مرحله‌ای سریع:** حجم ← هش ۶۴ کیلوبایت اول ← هش کامل (BLAKE2b). بیشتر فایل‌های غیرتکراری بدون خواندن کامل کنار گذاشته می‌شوند.
- **انتخاب نسخه‌ی ماندنی** در هر گروه (دابل‌کلیک) و امکان **رد کردن** هر گروه.
- **حذف امن:**
  - نسخه‌ی نگه‌داشته‌شده پیش از هر کاری دوباره بررسی می‌شود؛ اگر تغییر کرده یا حذف شده باشد، کل گروه دست نمی‌خورد.
  - هر نسخه‌ی تکراری درست پیش از انتقال دوباره هش می‌شود.
  - هیچ فایلی مستقیماً پاک نمی‌شود: یا به **پوشه‌ی قرنطینه** می‌رود (همراه با `manifest.jsonl` برای بازگردانی) یا به **سطل بازیافت** سیستم.
- هاردلینک‌ها، symlinkها و junctionهای ویندوز درست مدیریت می‌شوند؛ فایل‌های خالی نادیده گرفته می‌شوند.
- اسکن و انتقال در پس‌زمینه اجرا می‌شوند؛ رابط کاربری قفل نمی‌شود و عملیات قابل **لغو** است.
- خطاهای دسترسی پنهان نمی‌شوند و در پنجره‌ای جدا قابل مشاهده‌اند.
- **تم روشن و تیره:** انتخاب دستی، یا «پیش‌فرض ویندوز» که تنظیم ویندوز (Settings ← Personalization ← Colors) را دنبال می‌کند و هنگام تغییر آن، بدون نیاز به اجرای دوباره، خودش عوض می‌شود. انتخاب کاربر ذخیره می‌شود.

## نصب و اجرا

نیازمندی: Python 3.9 یا جدیدتر.

```bash
git clone https://github.com/<USERNAME>/duplicate-finder.git
cd duplicate-finder
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -e ".[trash]"            # trash = پشتیبانی از سطل بازیافت (اختیاری)
python -m duplicate_finder
```

روی لینوکس Tkinter جداگانه نصب می‌شود: `sudo apt install python3-tk`

## ساختار پروژه

```
duplicate_finder/
├── models.py      # داده‌های تغییرناپذیر: DuplicateGroup, ScanResult, Selection, RemovalReport
├── hashing.py     # partial_digest / full_digest
├── scanner.py     # find_duplicates — منطق خالص، بدون GUI و بدون تغییر فایل
├── removal.py     # Remover (Quarantine / Trash) + remove_duplicates با بازبینی ایمنی
├── review.py      # ReviewPlan — تصمیم‌های کاربر (نسخه‌ی ماندنی، گروه‌های ردشده)
├── progress.py    # گزارش پیشرفت (throttled) و لغو — مشترک برای همه‌ی عملیات‌ها
├── background.py  # اجرای کار در ترد جدا و برگرداندن نتیجه به ترد Tk
├── formatting.py  # format_size
├── validation.py  # اعتبارسنجی ورودی کاربر (مثلاً پوشه‌ی خالی/نامعتبر)
├── theme.py       # ThemeMode، پالت‌های رنگ، تشخیص حالت تیره‌ی ویندوز — بدون Tk
├── settings.py    # ذخیره‌ی تنظیمات کاربر (JSON)
├── styling.py     # ThemeManager — اعمال پالت روی ttk و دنبال کردن تنظیم سیستم
└── gui.py         # فقط نمایش (Tkinter)
```

تنظیمات در `%APPDATA%\DuplicateFinder\settings.json` (ویندوز) یا `~/.config/DuplicateFinder/settings.json` ذخیره می‌شوند.

هسته (`scanner`, `removal`, `review`) هیچ وابستگی‌ای به Tkinter ندارد؛ بنابراین مستقلاً تست می‌شود و می‌توان روی آن رابط دیگری (مثلاً CLI) ساخت.

## بازگردانی از قرنطینه

هر خط `manifest.jsonl` یک انتقال را ثبت می‌کند:

```json
{"moved_at": "2026-11-15T20:00:00+00:00", "original": "/path/a.txt", "quarantined": "/q/a.txt"}
```

## تست

```bash
pip install -e ".[dev]"
pytest
```

## محدودیت‌های شناخته‌شده

- روی **لینوکس**، Tk متن فارسی را راست‌به‌چپ و با اتصال حروف صحیح نمایش نمی‌دهد (محدودیت خود Tk روی X11). روی ویندوز و macOS نمایش درست است.
- گزینه‌ی «پیش‌فرض ویندوز» فقط روی ویندوز تنظیم سیستم را می‌خواند؛ روی سیستم‌عامل‌های دیگر تم روشن در نظر گرفته می‌شود (انتخاب دستی همه‌جا کار می‌کند).
- برای اینکه رنگ‌های سفارشی اعمال شوند، تم پایه‌ی `clam` به‌جای `vista` استفاده می‌شود؛ ظاهر دکمه‌ها کمی با ظاهر بومی ویندوز فرق دارد.

## License

MIT — see [LICENSE](LICENSE).
