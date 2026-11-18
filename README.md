# اسکیل‌های پژوهش و روزنامه‌نگاری فارسی

[English](README.en.md)

مجموعه‌ای مستقل و ماژولار برای ویرایش فارسی، ترجمهٔ علوم انسانی، بررسی منبع، راستی‌آزمایی و کار با داده. هر مهارت دامنه و محدودیت خودش را دارد؛ وجود دستور یا بسته، به معنی کیفیت تأییدشدهٔ خروجی مدل نیست.

## وضعیت امروز

به‌روزرسانی مستندات: ۱۸ نوامبر ۲۰۲۶. بازطراحی سه‌مهارتی با [PR شمارهٔ ۱](https://github.com/alirezach/Persian-Journalism-skills-for-AI/pull/1) در ۱۷ نوامبر در `main` ادغام شد. شناسهٔ پروژه `0.4.3-editing` است؛ این به‌روزرسانی نسخهٔ تازه یا Release/tag ایجاد نمی‌کند.

- کاتالوگ **۱۰ مهارت** دارد: چهار مهارت `experimental` و شش مهارت `planned`.
- بستهٔ OpenCode نسخهٔ **0.2.0** همان هشت مهارت اصلی را دارد؛ فقط ویرایش آن به 0.2.0 رسیده است.
- مجموعهٔ فارسی نسخهٔ **0.1.0** سه مهارت ویرایش، دیتاکس و ترکیبی را جداگانه ارائه می‌کند. بستهٔ ده‌مهارتی یکپارچه ادعا نمی‌شود.
- روی نسخهٔ ادغام‌شده، **۴۵۵ کنترل فنی مستقل موفق و صفر شکست** ثبت شد. این نتیجه پذیرش رفتاری، نصب میزبان یا گواهی امنیت نیست. [گزارش اجرا](docs/evaluations/main-full-tests-2026-11-17.md)

## کدام مهارت؟

| نیاز | مهارت | نسخه | وضعیت |
|---|---|---|---|
| ویراستاری فنی و زبانی، بدون دیتاکس خودکار | [persian-editing](skills/persian-editing/README.md) | 0.2.0 | experimental |
| اصلاح نثر قالبی با حفظ معنا و صدا | [persian-ai-detox](skills/persian-ai-detox/README.md) | 0.1.0 | experimental |
| ویرایش و دیتاکس در یک بسته با دو جزء کامل | [persian-editing-and-ai-detox](skills/persian-editing-and-ai-detox/README.md) | 0.2.0 | experimental |
| ترجمهٔ علوم انسانی و سیاست‌گذاری | [humanities-translation](skills/humanities-translation/README.md) | 0.1.0 | experimental |
| هویت، منشأ و اصالت مدرک | [source-verification](skills/source-verification/README.md) | 0.1.1 | planned |
| بررسی ادعای مشخص | [fact-checking](skills/fact-checking/README.md) | 0.1.1 | planned |
| مقایسه و ترکیب پژوهش‌ها | [research-synthesis](skills/research-synthesis/README.md) | 0.1.1 | planned |
| آماده‌سازی و تحلیل داده | [data-analysis](skills/data-analysis/README.md) | 0.1.1 | planned |
| جدول، نمودار و نقشه | [data-visualization](skills/data-visualization/README.md) | 0.1.1 | planned |
| هماهنگی پروندهٔ دیتاژورنالیسم | [data-journalism](skills/data-journalism/README.md) | 0.1.1 | planned |

برای یک متن، فقط مسیر لازم را انتخاب کنید؛ بستهٔ ترکیبی نیاز به نصب دو مهارت همسایه ندارد. شش مهارت planned منابع متنی و ZIP نامزد دارند، اما پذیرش عملی ندارند. [کاتالوگ](catalog.yaml) مرجع نسخه و محدودیت‌هاست.

## ساخت و نصب انتخابی

از ریشهٔ مخزن، با Python 3.10+ و کتابخانهٔ استاندارد، برای بستهٔ ترکیبی در چیدمان OpenCode:

```bash
python3 scripts/packaging/build-persian-language-suite.py --skill persian-editing-and-ai-detox --format opencode --output dist/persian-editing-and-ai-detox-0.2.0-opencode.zip
```

برای هر سه مهارت فارسی یا همان هشت مهارت اصلی:

```bash
python3 scripts/packaging/build-persian-language-suite.py --output dist/pjai-persian-language-suite-0.1.0-opencode.zip
python3 scripts/packaging/build-opencode.py --output dist/pjai-opencode-0.2.0.zip
```

فایل مقصد باید تازه باشد. نصب خودکار انجام نمی‌شود: ZIP را در پوشهٔ موقت باز کنید، manifest و تعارض با نصب قبلی را بررسی کنید و فقط پوشهٔ مهارت انتخاب‌شده را به `.opencode/skills/` پروژهٔ مقصد منتقل کنید. پوشهٔ موجود را بدون پشتیبان و تصمیم صریح بازنویسی نکنید. سپس شناسایی مهارت و خواندن منابعش را در نسخهٔ میزبان خود بررسی کنید؛ ساخت ZIP شاهد موفقیت این مرحله نیست.

برای بستهٔ مستقل، انتخاب‌های بیشتر و مهاجرت از نام قدیمی، [راهنمای مجموعهٔ فارسی](docs/persian-language-suite.md) و [راهنمای بسته‌بندی](scripts/packaging/README.md) را ببینید. برای ترجمه از سازندهٔ مستقل استفاده کنید:

```bash
python3 scripts/packaging/build-translation.py --output dist/humanities-translation-0.1.0-experimental.zip
```

## بررسی فنی

با Node.js 20+، وابستگی‌های پروژه و Python، دو فرمان زیر با هم همهٔ مجموعه‌آزمون‌های فعلی را پوشش می‌دهند:

```bash
npm test
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`npm test` به‌تنهایی ۲۹۷ کنترل دارد و ۱۵۸ کنترل بسته‌بندی دیگر را اجرا نمی‌کند. اجرای دوم ۲۳۲ آزمون Python دارد که ۷۴ مورد آن تکرار آزمون تبدیل نویسهٔ فرمان نخست است؛ مجموع بدون تکرار ۴۵۵ است. هنوز فرمان یکپارچهٔ تازه، CI یا فایل قفل کامل وابستگی‌ها اضافه نشده است. [راهبرد آزمون و روش آماده‌سازی](docs/testing-strategy.md)

## محدودیت‌ها و منابع

- خروجی مدل نیاز به بازبینی دارد. نه `experimental` یعنی `tested`، نه ساخت بسته یعنی اجرای موفق مهارت.
- متن، عدد، نقل‌قول، انتساب و عدم‌قطعیت باید حفظ شوند؛ ویرایش و ترجمه مجوز اصلاح خودکار واقعیت یا انتشار نیستند.
- مبنای ویرایش، گردآوری ارسالی منتسب به ذوالفقاری است؛ اصل کتاب مقابله نشده است. دیتاکس از نسخهٔ مشخص persian-writing با اعلان MIT اقتباس شده است.
- آزمون رفتاری نسخه‌های جدید، سازگاری واقعی میزبان، نمایش RTL و ممیزی امنیتی جامع تأیید نشده‌اند. گزارش‌های قدیمی به نسخهٔ جدید منتقل نمی‌شوند.
- فایل محلی به معنی پردازش خصوصی یا مدل محلی نیست. دادهٔ محرمانه و اطلاعات منابع را وارد مخزن عمومی نکنید.

[اعلان منابع ثالث](THIRD_PARTY_NOTICES.md) و اعلان داخل هر بسته، [مجوز MIT](LICENSE)، [امنیت](SECURITY.md) و [مشارکت](CONTRIBUTING.md) را بخوانید. راهنمای توسعه در [AGENTS.md](AGENTS.md) است؛ نصب آن روی پروژهٔ کاربر لازم نیست.

## مستندات و تاریخچه

- [معماری](docs/architecture.md)، [مرز مهارت‌ها](docs/skill-boundaries.md)، [سازگاری](docs/compatibility.md) و [الزامات ایران](docs/iran-requirements.md)
- [پروفایل‌ها](profiles/README.md)، [الگوهای کاری](templates/README.md) و [اعتبارسنج رکوردها](scripts/validation/README.md)
- [نقشهٔ راه جاری](docs/roadmap.md) و [تغییرنامه](CHANGELOG.md)
- [آرشیو کامل معرفی فارسی پیش از این اصلاح](docs/history/readme-fa-before-2026-11-18.md) و [آرشیو انگلیسی](docs/history/readme-en-before-2026-11-18.md)

تاریخچه حذف یا خلاصه نشده است؛ وضعیت جاری از آن جدا شده است. این پروژه با کمک GPT-6 Astra توسعه یافته و از [persian-writing](https://github.com/ali2000hos/persian-writing) و [claude-skills-journalism](https://github.com/jamditis/claude-skills-journalism) الهام گرفته است. نقش مدل و محدودیت استقلال ارزیابی‌ها در سوابق باقی است.
