# Sources and adaptation decisions

## Two sources, distinct roles

### Persian detox

Repository: https://github.com/ali2000hos/persian-writing

Pinned commit: `75fcdf313fab65d6d205500ca50f9cb52db25783`; entry version 1.4.0.

Read and used:

- [SKILL.md](https://github.com/ali2000hos/persian-writing/blob/75fcdf313fab65d6d205500ca50f9cb52db25783/SKILL.md), blob `5c32841a2748371740b4c574cff38a069630d3b4`.
- [writing-style.md](https://github.com/ali2000hos/persian-writing/blob/75fcdf313fab65d6d205500ca50f9cb52db25783/references/writing-style.md), blob `7ec421ef2903446d5ff9ef098dde084840435b4b`: register, T1-T18, exceptions and rhythm.
- [academic.md](https://github.com/ali2000hos/persian-writing/blob/75fcdf313fab65d6d205500ca50f9cb52db25783/references/academic.md), blob `92e77a210a93ed0e345785ceb8a10c26ccc85b66`: academic register and source fidelity.
- [LICENSE](https://github.com/ali2000hos/persian-writing/blob/75fcdf313fab65d6d205500ca50f9cb52db25783/LICENSE), blob `9404273b4567eb3761d4e25f2e78fdef86eb3cd2`.

These files were read; this is not a claim to have audited the complete upstream repository. Upstream fonts, dictionaries, scripts, SEO and document-production modules are not included or required.

### Persian editing

User-provided file: `Persian_Editing_Principles_Zolfaghari.md`.

192,452 bytes; 1,749 lines; SHA-256 `621fab1ba6d6c52f5a97021178f0f62103422691b4527a7ed02f520bae3ab208`.

The compilation attributes its principles to Hassan Zolfaghari, راهنمای ویراستاری و درست‌نویسی, Elm, Tehran, 1387. The original book was not inspected. The attachment preface says missing or damaged examples were reconstructed and some original tables were unavailable. Therefore its examples are not treated as verified verbatim quotations from the book. The attachment itself is not redistributed.

Coverage of the supplied compilation:

- Lines 27-116: editing scope and responsibility.
- 118-452: punctuation.
- 453-770: orthography, spelling and names.
- 771-897: transcription, numbers, dates, formulas and abbreviations.
- 897-1034: references and preparation of a written work.
- 1035-1420: register and lexical choices.
- 1420-1688: grammar and sentence structure.
- 1690-1749: suggested equivalents and the compiler's final checklist.

These are navigation ranges in the supplied file, not book page references. Selected principles are paraphrased, not reproduced exhaustively. New examples in this package are synthetic illustrations, not source quotations or test results.

## Decisions that override mechanical copying

1. Upstream bans become contextual checks. Formality, passive voice, a three-item list and an isolated phrase do not prove machine authorship.
2. Upstream examples that strengthen a claim or introduce unsupported numbers, projects or citations are excluded. Specificity cannot come from invented facts.
3. Scientific hedges, negation, uncertainty and attribution override brevity or positive-wording preferences. Unknown actors remain unknown.
4. Offering something for sale is not selling it. Lexical and syntactic shortening must retain event status, aspect and modality.
5. Project house style defaults to خانهٔ, not the compilation's خانه‌ی; explicit consistent user style can override this preference.
6. Exact quotations, identifiers, code and URLs are protected. Character normalization is limited to eligible prose.
7. No unverified detector-study statistics are imported. No detector-evasion guarantee is made.
8. Ordinary editing defaults to conservative language editing. Technical-only and broad rewriting are explicit scopes.
9. AI-detox instructions are not attributed to Zolfaghari. Protection protocols, routing and packaging are project integration work.

Jamditis/claude-skills-journalism was read for comparison during research, but is not a direct adapted-content source for this package. Its English-specific substitution and formatting rules are not imported.

## Provenance and limits

Created with GPT-6 Astra for the Persian-Journalism-skills-for-AI project. Technical packaging checks are not independent editorial evaluation or model acceptance. Three [behavioral scenarios](acceptance-cases.md) are prepared and unrun. The owner's report that an earlier OpenCode bundle worked is not runtime evidence for this new skill.

See [third-party notices](../THIRD_PARTY_NOTICES.md) for the complete upstream MIT notice and the distinction between licensed repository material and the unbundled book compilation.
