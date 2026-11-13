# Persian Journalism Skills for AI

[فارسی](README.md)

A modular, tool-neutral collection for Persian editing, humanities translation, source verification, fact-checking, research synthesis, data analysis, visualization and data journalism, with a separate Iran context layer.

**Status: design foundation only. No installable skills, executable analysis tools, automated tests or distribution packages are shipped yet.** Documentation describes intended behavior, not demonstrated runtime support.

## Planned capabilities

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

See [catalog.yaml](catalog.yaml). Every skill is currently `planned`.

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

There are no installation commands yet. Adapters and self-contained packages will be added after implementation and acceptance tests.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and [SECURITY.md](SECURITY.md). Original project material is [MIT licensed](LICENSE); third-party material retains its own license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
