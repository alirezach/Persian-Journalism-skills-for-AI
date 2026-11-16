# Persian Journalism Skills for AI

[فارسی](README.md)

A modular, tool-neutral collection for Persian editing, humanities translation, source verification, fact-checking, research synthesis, data analysis, visualization and data journalism. Iran-specific requirements are documented separately; the planned contexts/iran/ and knowledge/ directories are not existing runtime resources.

**Status: experimental, `0.4.3-editing`.** [Persian editing 0.1.3](skills/persian-editing/README.md) includes an optional two-character mapping helper and exact candidate auditing. Permission, language and span classification remain caller responsibilities. Acceptance is incomplete and further testing has been stopped by the project owner. See the [release-status record](docs/evaluations/persian-editing-0.1.3-release-status.md); this is not a validated production release.

**Humanities translation 0.1.0 is also experimental.** Its [guidance and standalone package](skills/humanities-translation/README.md) were explicitly promoted by the project owner on 2026-11-15 for experimental use with output review, without running test suites, model evaluation or installation. The [promotion decision](docs/humanities-translation-0.1.0-experimental-decision.md) records limits and both archive hashes. The previous planned candidate and its historical coverage matrix are preserved. The project release identifier remains unchanged; no GitHub Release or tag was created.

## Capability map

| Skill | Responsibility |
|---|---|
| `persian-editing` | Improve prose at the requested intervention level without altering evidence or meaning. |
| `humanities-translation` | Translate meaning, terminology, voice and qualifications faithfully. |
| `source-verification` | Establish provenance, authenticity, context and evidentiary limits. |
| `fact-checking` | Investigate specific claims and document defensible assessments. |
| `research-synthesis` | Answer research questions through critical comparison of sources. |
| `data-analysis` | Produce reproducible transformations, calculations and findings. |
| `data-visualization` | Represent data honestly and accessibly. |
| `data-journalism` | Coordinate a reporting project without duplicating specialist procedures. |

See [catalog.yaml](catalog.yaml). `persian-editing` and `humanities-translation` are `experimental`; the other six remain `planned`. Experimental does not mean tested. Build their separate standalone ZIPs with Python 3.10+ (standard library only):

```bash
python3 scripts/packaging/build-skill.py --output dist/persian-editing-0.1.3.zip
python3 scripts/packaging/build-translation.py --output dist/humanities-translation-0.1.0-experimental.zip
```

The output must not already exist. See the [packaging guide](scripts/packaging/README.md). Generated shared resources retain source hashes; source files remain canonical. A separate private ClickUp adapter for editing received limited installation/readback checks. It is not shipped here and does not establish general host compatibility. Those checks do not transfer to translation.

## OpenCode bundle 0.1.0

The [OpenCode guide](docs/adapters/opencode.md) describes a generated project-local layout for all eight skills or an explicit subset. The wrapper calls the existing canonical builders, preserves their output resources, and places them under `.opencode/skills/<name>/`. It does not install or invoke OpenCode, modify AGENTS.md or host configuration, set credentials, or promote any skill.

```bash
python3 scripts/packaging/build-opencode.py --output dist/pjai-opencode-0.1.0.zip
python3 scripts/packaging/build-opencode.py --skills persian-editing data-analysis --output dist/pjai-opencode-0.1.0-selected.zip
python3 -m unittest discover -s tests -p 'test_opencode_build.py' -v
```

Extract to a new temporary directory first; inspect the manifest and conflicts before copying selected skill directories into a working project. Do not overwrite an existing skill blindly. Explicit invocation such as `@data-analysis` and actual reference access require a separate host check. Local files do not imply a local model or private processing.

See the [technical record](docs/evaluations/opencode-0.1.0-technical.md) for executed software/archive checks and unrun host/model checks. Earlier archives and their evidence remain frozen. Current shared-resource changes can change package hashes without changing the entry skill version; the bundle version, publication commit and actual hashes identify this output.

The three stale structural suites were repaired before this adapter work: 68 checks passed across those three suites, not the whole repository. Template documentation is not counted as a working form, and editing checks no longer depend on the lifecycle count of unrelated skills.

The other six skills already have source-only 0.1.1 planned candidates. Their 40 historical builder-unit tests and archive integrity checks do not establish behavioral acceptance. Eighteen prepared scenarios remain unrun. No new GitHub Release or tag is created by this adapter.

## Design commitments

- Separate language, geography, methodology and personal house style.
- Persian-language work does not automatically activate Iran-specific rules.
- Preserve originals, uncertainty, attribution and the distinction between translation and factual correction.
- Evaluate evidence beyond institutional authority; copied reports do not constitute independent corroboration.
- Keep sensitive data and source identities outside this public repository.
- Disclose actual tool use and verification coverage. No fabricated checks, interviews or citations.
- Publish compatibility evidence per environment; reading Markdown is not proof of runtime compatibility.
- Optimize for better writing and auditable reporting, not AI-detector evasion.

## Documentation

The design documents are currently in Persian:

- [Architecture](docs/architecture.md)
- [Skill boundaries](docs/skill-boundaries.md)
- [Iran requirements](docs/iran-requirements.md)
- [Compatibility](docs/compatibility.md)
- [Testing strategy](docs/testing-strategy.md)
- [Roadmap](docs/roadmap.md)

## Available tooling

- [Persian profiles](profiles/README.md): declarative locale and replaceable house-style guidance, not a text-rewriting engine or automatic Iran-context selector.
- [Eleven working templates](templates/README.md): blank human forms, not completed reviews or automatic JSON exports.
- [Record validator](scripts/validation/README.md): one JSON record or an array; local schema and versioned-reference checks. It does not fetch sources, execute declared calculations or modify the input file.

With Node.js and the reviewed dependencies available, run from the repository root:

```bash
node scripts/validation/validate-records.cjs --input examples/records/synthetic-bundle.json
```

The example is entirely synthetic. Exit zero may include warnings and does not grant publication authority. The validator guide covers setup, stdin, unresolved-reference mode, limits and error codes.

The following historical counts concern editing and its supporting infrastructure, not translation. Only build-time controls and archive integrity comparison were performed for translation; no project test suites, model evaluation or host installation were run.

The frozen pre-release candidate had 338 recorded passing local technical checks; no new suite was run for these release-status edits: 67 schema/regression, 88 validator/CLI, 32 profile/template, 20 editing-source/fixture checks, 16 editorial-source contracts, 41 packager tests and 74 transcription-helper tests. See the [0.1.3 report](docs/evaluations/persian-editing-0.1.3.md). The two previously failed quotation outputs remain rejected by the new audit; historical responses were not repaired or replaced.

The [supplementary 0.1.2 record](docs/evaluations/persian-editing-0.1.2-astra-opus-2026-11-14.md) distinguishes earlier unknown-model comparisons from the later open-book Astra retest and returned Opus review. Eight responses received 47 applicable pass labels, with one minor issue and incomplete blinding; this is not a general success rate or proof of a repaired skill. Identity relies on runtime declarations, not provider request metadata.

Environment of earlier checks: Node.js v22.23.1, Ajv 6.15.0, js-yaml 4.3.2 and Python 3.12.13. A later native record declared GPT-6 Astra and met its reported with-skill conditions, while a baseline was invalidated by additional editing guidance. No valid paired native baseline, independent provider verification, complete context isolation or human review was established. Network installation, npm commands, CI, visual rendering and comprehensive security audits remain untested. No complete transitive-dependency lockfile is supplied. See the release-status record for the partial host evidence and the decision to stop further tests.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and [SECURITY.md](SECURITY.md). Original project material is [MIT licensed](LICENSE); third-party material retains its own license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the [translation package notices](skills/humanities-translation/package-NOTICES.md). Exact editorial source URLs were added from existing records, without redistributing their articles or conducting a new license or web review.
