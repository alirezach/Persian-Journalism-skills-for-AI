---
name: persian-editing-and-ai-detox
description: "ویرایش فارسی و دیتاکس در یک بستهٔ کامل؛ برای انجام هر دو کار یا انتخاب یکی از دو مسیر با حفظ معنا و شواهد."
license: MIT
metadata:
  version: "0.2.0"
  status: "experimental"
  language: "fa"
---

## Choose the requested work

This package contains the full editing and full detox components, not abbreviated substitutes. For an expressly combined request use both. For editing-only load only the editing component; for detox-only load only detox. An ambiguous request to edit remains conservative language editing, not automatic detox or creative rewriting. Do not run three competing skills on the same text.

- [Complete Persian editing component](../persian-editing/SKILL.md): technical proofreading and professional language editing, including the complete detailed Zolfaghari-derived modules, quotation protocol, profiles and optional helper.
- [Complete Persian AI detox component](../persian-ai-detox/SKILL.md): register, the full T1-T18 catalog, academic constraints, structural patterns, quality checks, source decisions and unrun scenarios.

In a built package, the two links point to local components. Each component's resource paths are relative to its own component directory, not the outer combined root. Read the component entry and every applicable module it requires; this routing page is not a replacement for them. Full components are bundled even when the current request needs only some modules. Installation of sibling skills or network access is not required to read them.

## Combined execution

1. Establish requested scope, audience, register and protected spans using both components' contracts. Preserve an original.
2. Apply contextual detox and local language editing without changing the author's substantive position, inventing evidence or removing meaningful qualifiers. Shared checks need not be performed redundantly.
3. Finish with the editing component's technical pass. The detox component's limits on full proofreading do not block this explicitly requested combined pass.
4. Compare with the original claim by claim and protected span by protected span. Check source comparability; retain legitimate contrasts and report consequential unclear comparisons without rewriting the author's reasoning.
5. Deliver one coherent edited text, not two conflicting versions. Add only necessary notes. If text-only is explicit, preserve unresolved passages and omit routine notes rather than silently resolving them.

Fidelity, explicit scope, protected spans and source privacy outrank stylistic preferences. Neither component authorizes factual correction, free rewriting, summarization, source research or publication implicitly. Do not invent an intermediate causal bridge to connect their outputs. Preserve the narrow quotation-normalization consent and evidence requirements; component packaging is not permission to execute the helper.

## Completeness and limits

The build manifest identifies exact component versions and complete embedded-file mappings. Component payload bytes, including their complete instructions and references, are checked against the standalone builds. Internal entry files are named INSTRUCTIONS.md to avoid advertising nested duplicate skills; their content is not summarized. Historical manifests remain provenance with explicit entry-path mapping in the outer manifest.

The former persian-editing-detox name is retired after verified replacement. Historical ZIPs are not modified. This new version remains experimental; packaging tests do not prove behavioral quality, successful host discovery or independent review.
