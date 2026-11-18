# Persian Journalism Skills for AI

[فارسی](README.md)

Independent, modular guidance for Persian editing, humanities translation, source verification, fact-checking and data journalism. Each skill has its own scope and limits. A source file or package is not proof of model-output quality.

## Current status

Documentation updated: **2026-11-18**. The three-skill language refactor was merged into `main` on 2026-11-17 through [PR #1](https://github.com/alirezach/Persian-Journalism-skills-for-AI/pull/1). The project identifier remains `0.4.3-editing`; this documentation update does not create a version, Release or tag.

- The catalog contains **10 skills: four experimental and six planned**.
- OpenCode bundle **0.2.0** contains the original eight skills, with editing updated to 0.2.0.
- Persian language suite **0.1.0** separately provides editing, detox and the combined skill. There is no claimed unified ten-skill bundle.
- The merged snapshot passed **455 unique technical checks, zero failures**. This is not model acceptance, host installation or a security certification. [Recorded test run](docs/evaluations/main-full-tests-2026-11-17.md)

## Choose a skill

| Need | Skill | Version | Status |
|---|---|---|---|
| Technical and language editing, without automatic detox | [persian-editing](skills/persian-editing/README.md) | 0.2.0 | experimental |
| Address formulaic prose while preserving meaning and voice | [persian-ai-detox](skills/persian-ai-detox/README.md) | 0.1.0 | experimental |
| Editing and detox in one package with both full components | [persian-editing-and-ai-detox](skills/persian-editing-and-ai-detox/README.md) | 0.2.0 | experimental |
| Humanities and policy translation | [humanities-translation](skills/humanities-translation/README.md) | 0.1.0 | experimental |
| Evidence identity, provenance and authenticity | [source-verification](skills/source-verification/README.md) | 0.1.1 | planned |
| Investigate a specific claim | [fact-checking](skills/fact-checking/README.md) | 0.1.1 | planned |
| Compare and synthesize research | [research-synthesis](skills/research-synthesis/README.md) | 0.1.1 | planned |
| Prepare and analyze data | [data-analysis](skills/data-analysis/README.md) | 0.1.1 | planned |
| Tables, charts and maps | [data-visualization](skills/data-visualization/README.md) | 0.1.1 | planned |
| Coordinate a data-journalism project | [data-journalism](skills/data-journalism/README.md) | 0.1.1 | planned |

Choose only the route needed for a text. The combined package does not require the two sibling skills to be installed. The six planned skills have text guidance and candidate ZIPs, not operational acceptance. [catalog.yaml](catalog.yaml) records versions and limitations.

## Build and install selectively

From the repository root, with Python 3.10+ and its standard library, build the combined skill in OpenCode layout:

```bash
python3 scripts/packaging/build-persian-language-suite.py --skill persian-editing-and-ai-detox --format opencode --output dist/persian-editing-and-ai-detox-0.2.0-opencode.zip
```

For all three Persian language skills, or the original eight skills:

```bash
python3 scripts/packaging/build-persian-language-suite.py --output dist/pjai-persian-language-suite-0.1.0-opencode.zip
python3 scripts/packaging/build-opencode.py --output dist/pjai-opencode-0.2.0.zip
```

The output file must not already exist. No automatic installation occurs: extract into a temporary directory, inspect the manifest and conflicts, then copy only the selected skill directory into the destination project's `.opencode/skills/`. Do not overwrite an existing installation without a backup and an explicit decision. Verify discovery and reference loading in your actual host version; ZIP creation does not establish this.

See the [Persian language suite guide](docs/persian-language-suite.md) and [packaging guide](scripts/packaging/README.md) for standalone packages, other selections and migration. Translation has its own builder:

```bash
python3 scripts/packaging/build-translation.py --output dist/humanities-translation-0.1.0-experimental.zip
```

## Technical checks

With Node.js 20+, project dependencies and Python available, these commands together cover all current test modules:

```bash
npm test
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`npm test` alone runs 297 checks and omits 158 packaging checks. Python discovery runs 232 tests, including 74 normalization tests already run by npm: the unique total is 455. No new unified command, CI workflow or complete dependency lockfile is added by this documentation update. [Testing strategy and environment setup](docs/testing-strategy.md)

## Limits and sources

- Review model output. Experimental is not tested; packaging is not successful skill execution.
- Preserve meaning, quantities, quotations, attribution and uncertainty. Editing and translation do not implicitly authorize factual correction or publication.
- Editing adapts the supplied Zolfaghari compilation; the original book was not inspected. Detox adapts a pinned persian-writing revision with its MIT notice.
- New-version model behavior, real host compatibility, RTL rendering and comprehensive security acceptance remain unverified. Historical results do not transfer to new versions.
- Local files do not imply local-model or private processing. Keep confidential data and source identities outside the public repository.

Read the [third-party notices](THIRD_PARTY_NOTICES.md) and notices inside each package, [MIT license](LICENSE), [security policy](SECURITY.md) and [contribution guide](CONTRIBUTING.md). [AGENTS.md](AGENTS.md) guides repository development; installing it into a user's project is not required.

## Documentation and history

- [Architecture](docs/architecture.md), [skill boundaries](docs/skill-boundaries.md), [compatibility](docs/compatibility.md) and [Iran requirements](docs/iran-requirements.md)
- [Profiles](profiles/README.md), [working templates](templates/README.md) and [record validator](scripts/validation/README.md)
- [Current roadmap](docs/roadmap.md) and [changelog](CHANGELOG.md)
- [Complete previous English README](docs/history/readme-en-before-2026-11-18.md) and [Persian README archive](docs/history/readme-fa-before-2026-11-18.md)

History was preserved, not shortened; it is separate from current guidance. The project was developed with GPT-6 Astra, with inspiration from [persian-writing](https://github.com/ali2000hos/persian-writing) and [claude-skills-journalism](https://github.com/jamditis/claude-skills-journalism). Historical records retain model provenance and limits on evaluation independence.
