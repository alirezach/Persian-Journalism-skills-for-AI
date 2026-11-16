# Technical Persian editing

Source scope: the user-supplied Zolfaghari compilation, technical-editing section. The protection rules and conflict resolutions below are project adaptations; see [source decisions](source-decisions.md).

## Boundaries

A technical-only request permits unambiguous spelling, spacing and punctuation corrections. It does not permit lexical simplification, deleting repetitive arguments, rearranging paragraphs, changing register or silently correcting facts. Protect quotations and machine-readable spans before normalization. Never apply global character substitution to the whole document.

## Practical pass

1. **Letters and spacing:** in ordinary Persian prose, use Persian ی and ک. Correct a missing or extra space only when word boundaries are clear. Use ZWNJ where appropriate, such as می‌شود، نمی‌دانم، کتاب‌ها. Do not insert it into every compound mechanically. Preserve Arabic quotations, language-specific orthography and identifiers.
2. **Ezafe:** default house style is خانهٔ and دربارهٔ. Respect an explicitly requested consistent alternative such as خانه‌ی. In colloquial text, distinguish the copula ending from ezafe: کتابِ من is not کتابه من. Do not convert the whole text to colloquial forms to solve this.
3. **Spelling and names:** correct clear typos, not unfamiliar specialist vocabulary. Keep established names, citation spellings and historical variants unless the correct form is supplied or separately verified. Flag ambiguity rather than guessing between homophones.
4. **Punctuation:** use ، ؛ ؟ and «» where appropriate in Persian narrative. Normally no space before a punctuation mark and one after; no inner spaces immediately after an opening bracket or before its close. Preserve decimal notation, code, abbreviations and citation conventions. A comma must not detach the subject from its predicate without a real parenthetical construction.
5. **Sentence boundaries:** a period closes a complete sentence; a semicolon can connect closely related independent clauses; a colon introduces an actual explanation, quotation or list. Parentheses hold supplementary material. Do not add punctuation that changes the scope of negation, a condition or attribution. Under technical-only scope, flag an unclear sentence rather than rewriting it.
6. **Numbers and dates:** Persian digits may be used in ordinary prose according to house style, but retain values, precision, signs and units. Do not round, recalculate, infer a missing year or convert calendars. Keep version numbers, identifiers, URLs, formulas and statistical notation intact. Do not turn ۵۸٫۸ into حدود ۵۹.
7. **Abbreviations and mixed direction:** preserve the exact abbreviation and meaning. Avoid invisible-character tricks. If rendering is unavailable, describe a direction problem as needing a layout check rather than claiming it is fixed. Do not reorder formula symbols to make their visual appearance look Persian.
8. **References and document furniture:** follow the supplied citation style, retaining author, year, page and link. Keep footnote markers aligned with their content. Check consistency of headings, captions and numbering when the complete relevant material is present; report missing material rather than fabricating it. Language editing does not establish that a reference exists.

## Synthetic example

Ordinary prose input: «گزارش ها منتشر شد .»

Technical revision: «گزارش‌ها منتشر شد.»

This changes spacing only. Inside an exact quotation or a protected example of incorrect writing, preserve the original instead.

## Stop conditions

Keep and flag anything requiring factual research, an uncertain name correction, ambiguous word separation or an inaccessible figure/footnote. Do not claim to have checked PDF layout, fonts, tables or pagination from plain text alone. End by comparing all protected spans and numeric anchors with the input.
