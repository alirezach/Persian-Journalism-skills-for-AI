# Orthography and mixed-script text

## Word boundaries

Distinguish the lexical word, a productive affix and independent syntactic words before joining or separating. Use ZWNJ where the selected style requires it: می‌شود، نمی‌دانم، کتاب‌ها، خانه‌ام. Do not insert it into every adjacent word or replace all spaces inside a compound. Established lexicalized compounds and accepted alternatives need a consistent dictionary/house-style decision, not a substring rule.

## Hamza, heh and ezafe

Preserve a meaningful hamza and distinguish original spelling, accepted variants and transcription. Do not erase hamza globally. Distinguish pronounced ه from silent final ه before attaching suffixes. The project default for ezafe after silent heh is خانهٔ; the compilation often uses خانه‌ی. A consistent explicitly requested alternative is not an error. In colloquial speech, test whether final ـه is the copula or an erroneous ezafe spelling: کتابِ من is not کتابه من. Do not rewrite an entire voice to solve a local spelling issue.

## Pronouns, copulas and suffixes

Check attached pronouns, written forms of copular verbs, plural and comparative endings against pronunciation, grammatical function and chosen style. Keep lexical exceptions such as established words distinct from productive affix rules. A spelling change must not change person, number or tense. Use diacritics only where they resolve a genuine ambiguity, are requested, or occur in protected material; do not vocalize ordinary prose mechanically.

## Character and display boundaries

Use Persian ی and ک in eligible Persian prose. Preserve Arabic passages, linguistic evidence, names as cited, URLs, email, code, versions, identifiers and formula strings. Preserve paragraph breaks and meaningful indentation. Never apply a whole-file replacement without excluding protected spans. Digits inside machine strings remain unchanged.

RTL text does not authorize reversing formulas, table data or code. Where the output format supports directional isolation, apply it only to a demonstrated display need and never inside an identifier. Do not assert that font shaping or PDF reading order was checked without viewing the actual output.

## Quotation exception

`quotation_policy.transcribed_fa_character_normalization.enabled` is off by default. A generic editing request به‌تنهایی آن را فعال نمی‌کند. Persian-looking text رونویسی‌بودن را ثابت نمی‌کند. Only explicit permission, confirmed Persian transcription, reviewed eligible spans and the narrow two-character mapping can enable the exception described in the quotation guide. Spacing and punctuation corrections remain outside that exception.
