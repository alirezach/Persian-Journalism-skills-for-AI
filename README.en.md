# Persian Journalism Skills for AI

[فارسی](README.md)

A modular, tool-neutral collection for Persian editing, humanities translation, source verification, fact-checking, research synthesis, data analysis, visualization and data journalism, with a separate Iran context layer.

**Status: experimental editing package, `0.4.0-editing`.** [Persian editing 0.1.0](skills/persian-editing/README.md) now has three intervention levels and a standalone ZIP builder. Shared standards, record schemas, Persian profiles, working templates and the record validator remain available. The skill is model guidance, not an automatic text editor. Host installation and model behavior are untested; structural tests establish neither.

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

See [catalog.yaml](catalog.yaml). `persian-editing` is `experimental`; the other seven remain `planned`. Build its standalone ZIP with Python 3.10+ (standard library only):

```bash
python3 scripts/packaging/build-skill.py --output dist/persian-editing-0.1.0.zip
```

The output must not already exist. See the [packaging guide](scripts/packaging/README.md). Generated shared resources retain source hashes; source files remain canonical. No product-specific installation or adapter has been tested.

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
- [Eight working templates](templates/README.md): blank human forms, not completed reviews or automatic JSON exports.
- [Record validator](scripts/validation/README.md): one JSON record or an array; local schema and versioned-reference checks. It does not fetch sources, execute declared calculations or modify the input file.

With Node.js and the reviewed dependencies available, run from the repository root:

```bash
node scripts/validation/validate-records.cjs --input examples/records/synthetic-bundle.json
```

The example is entirely synthetic. Exit zero may include warnings and does not grant publication authority. The validator guide covers setup, stdin, unresolved-reference mode, limits and error codes.

All 231 local tests passed: 67 schema/regression, 88 validator/CLI, 23 profile/template, 16 editing-source/fixture contracts and 37 packager tests. Environment: Node.js v22.23.1, Ajv 6.15.0, js-yaml 4.3.2 and Python 3.12.13; existing dependencies only. Twelve synthetic editing cases are defined but have not been run on models. See the [evaluation record](docs/evaluations/persian-editing-0.1.0.md). Network installation, npm commands, CI, host installation, model behavior, visual rendering and comprehensive security audits remain untested. No complete transitive-dependency lockfile is supplied.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and [SECURITY.md](SECURITY.md). Original project material is [MIT licensed](LICENSE); third-party material retains its own license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
