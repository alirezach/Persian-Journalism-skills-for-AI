# Synthetic editorial examples and test prompts

These examples illustrate decisions; they are not outputs from model evaluation and do not establish acceptance. Direct quotations and identifiers remain protected unless the stated narrow exception is authorized.

1. Spacing: ordinary prose «گزارش ها منتشر شد .» becomes «گزارش‌ها منتشر شد.» No content is added.
2. Local syntax: «این بخش به بررسی روش می‌پردازد» can become «این بخش روش را بررسی می‌کند». The method itself is not supplied or changed.
3. Event stage: «سه دستگاه در معرض فروش قرار گرفت، اما هنوز فروخته نشده است» must retain both offering and non-sale. Do not shorten to «سه دستگاه فروخته شد».
4. Unknown agency: «تصمیم گرفته شد» does not authorize adding «مدیر تصمیم گرفت». Keep or query the agent.
5. Quantities: «حدود ۵۸٫۸ درصد در این نمونه» keeps حدود، precision and sample scope. No rounding or generalization.
6. Statistics: «تفاوت معناداری مشاهده نشد» stays a non-significant result, not equivalence.
7. Source comparison: a claim about احساس کنترل and a claim about احساس امنیت do not establish disagreement by themselves. Keep the author's interpretation and flag the exact comparison issue, unless text-only output is explicitly required.
8. Protected error: an exact quote «اين متن است .» stays exact. یادداشت ویرایشی: نویسه و فاصلهٔ مشکوک در نقل‌قول حفظ شد؛ اصلاح آن به اجازه و تعیین نوع منبع نیاز دارد.
9. Optional transcription normalization, with explicit permission and reviewed eligible spans: «كار گروهي را پي مي گيريم.» becomes «کار گروهی را پی می گیریم.» Only ي/ك change; spaces, punctuation and all other characters remain. Do not introduce ZWNJ in this exception. Without reliable comparison, retain the original and report that conversion was not completed.
10. Text-only: keep an unresolved name or competing total unchanged rather than silently selecting a preferred answer. No extra note if the user explicitly prohibited it.
11. Valid variant: retain an accepted spelling consistently unless a selected house style requires another. Do not declare the alternative universally wrong.
12. Correct text: a precise, grammatical academic sentence with a passive or three-item classification can remain unchanged.

## Three prepared prompts, not run

- «فقط ویرایش فنی کن؛ نقل‌قول و شناسهٔ فایل دست‌نخورده بمانند.» Check scope and exact spans.
- «این بند دانشگاهی را ویرایش زبانی کن؛ قیدها، نفی و درصدها حفظ شوند.» Check local correction without factual change.
- «این متن را فقط ویرایش کن؛ اگر دو منبع قابل‌مقایسه نیستند، جدا یادداشت کن.» Include both ambiguous-comparison and legitimate-contrast controls; check that the editor neither resolves the argument nor adds generic warnings.

Historical rewrite fixtures remain historical evidence, not requirements to reintroduce free rewriting into version 0.2.0. New behavioral execution needs separate authorization and recorded actual outputs.
