#!/usr/bin/env python3
"""Build six explicitly listed text-guidance candidates; Python 3.10+, stdlib only.

Trusted checkout required. Does not install, run a model, fetch URLs, promote a
lifecycle or execute bundled files. Existing destinations are never overwritten.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys
import zipfile

NAMES = frozenset((
    "source-verification", "fact-checking", "research-synthesis",
    "data-analysis", "data-visualization", "data-journalism",
))
MAX_FILE = 1024 * 1024
MAX_TOTAL = 4 * MAX_FILE
MAX_FILES = 96
REPOSITORY = "https://github.com/alirezach/Persian-Journalism-skills-for-AI"
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\n]*)\)")
KEYS = {"manifest_version", "name", "version", "status",
        "baseline_revision", "files", "external_references"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Empty or non-string path")
    if any(c in value for c in "\\:%?#") or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Unsupported path characters")
    if PurePosixPath(value).is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise ValueError("Noncanonical path")
    return value


def read_source(root, name):
    p = root
    for part in canonical(name).split("/"):
        p = p / part
        if p.is_symlink():
            raise ValueError("Symlink source")
    info = p.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
        raise ValueError("Nonregular or oversized source")
    data = p.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError("Oversized source")
    data.decode("utf-8", errors="strict")
    return data


def local_link(owner, link):
    if link.startswith(("https://", "http://", "#")):
        return None
    path, marker, fragment = link.partition("#")
    if not path or path.startswith("/") or any(c in path for c in "\\:%?"):
        raise ValueError("Unsupported local link")
    if any(c.isspace() or ord(c) < 32 for c in link):
        raise ValueError("Unsupported link characters")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), path))
    canonical(resolved)
    return resolved, marker + fragment if marker else ""


def simple_links(text):
    if re.search(r"^\s*\[[^\]]+\]:|\]\[|<(?:a|img)\b", text, re.M | re.I):
        raise ValueError("Unsupported Markdown link syntax")
    links = list(LINK.finditer(text))
    if text.count("](") != len(links):
        raise ValueError("Unparsed Markdown link")
    return links


def entry_metadata(text, spec):
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Missing frontmatter")
    front = text.split("---\n", 2)[1]
    for pattern in (
        r'^name: ' + re.escape(spec["name"]) + r'$',
        r'^license: MIT$',
        r'^metadata:$',
        r'^  version: "' + re.escape(spec["version"]) + r'"$',
        r'^  status: "planned"$',
        r'^  implementation: "source-only"$',
    ):
        if len(re.findall(pattern, front, re.M)) != 1:
            raise ValueError("Unsupported or inconsistent entry metadata")
    description = re.search(r"^description:\s*([^\n]*)\n((?:[ \t]+[^\n]*\n)*)", front, re.M)
    if not description:
        raise ValueError("Missing description")
    initial, continued = description.groups()
    value = continued.strip() if initial.strip() in (">-", ">", "|", "|-") else initial.strip()
    if not value or len(value) > 1024:
        raise ValueError("Invalid description")
    # Deliberately a narrow check of this project's frontmatter, not a general
    # YAML parser or the official Agent Skills validator.


def allowed_source(source, name):
    return (
        source == "LICENSE" or
        source.startswith(("standards/", "schemas/", "templates/")) or
        source in ("profiles/locales/fa-IR.yaml", "profiles/house-style/default-fa.yaml",
                   "docs/skill-boundaries.md", "docs/" + name + "-contract.md") or
        source.startswith("skills/" + name + "/") or
        source in ("skills/fact-checking/references/statistics.md",
                   "skills/fact-checking/references/quotations.md",
                   "skills/source-verification/references/evidence-types.md")
    )


def prepare(root, name):
    if name not in NAMES:
        raise ValueError("Unsupported skill")
    root = Path(root).resolve(strict=True)
    config = "skills/" + name + "/build-manifest.json"
    raw = read_source(root, config)
    spec = json.loads(raw)
    if not isinstance(spec, dict) or set(spec) != KEYS:
        raise ValueError("Invalid manifest fields")
    if spec["manifest_version"] != "1" or spec["name"] != name or spec["status"] != "planned":
        raise ValueError("Only explicitly configured planned candidates are supported")
    if not isinstance(spec["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", spec["version"]):
        raise ValueError("Invalid version")
    revision = spec["baseline_revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid baseline revision")
    rows = spec["files"]
    if not isinstance(rows, list) or not 4 <= len(rows) <= MAX_FILES:
        raise ValueError("Invalid source count")
    mapping, folded = {}, set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"source", "target", "license"}:
            raise ValueError("Invalid file entry")
        source, target = canonical(row["source"]), canonical(row["target"])
        if source in mapping or target.casefold() in folded or target.casefold() == "manifest.json":
            raise ValueError("Duplicate or reserved path")
        if not allowed_source(source, name) or row["license"] != "MIT":
            raise ValueError("Source outside allowed text areas or unsupported license")
        if source != "LICENSE" and PurePosixPath(source).suffix not in (".md", ".json", ".yaml", ".csv"):
            raise ValueError("Only text resources are packaged")
        if target != "LICENSE" and PurePosixPath(target).suffix not in (".md", ".json", ".yaml", ".csv"):
            raise ValueError("Only text resource targets are allowed")
        mapping[source] = target
        folded.add(target.casefold())
    for target in folded:
        if any("/".join(target.split("/")[:i]) in folded for i in range(1, len(target.split("/")))):
            raise ValueError("File/directory collision")
    required = {
        "skills/" + name + "/SKILL.md": "SKILL.md",
        "skills/" + name + "/package-README.md": "README.md",
        "skills/" + name + "/package-NOTICES.md": "THIRD_PARTY_NOTICES.md",
        "LICENSE": "LICENSE",
    }
    if any(mapping.get(k) != v for k, v in required.items()):
        raise ValueError("Missing required entry or package resource")
    external = spec["external_references"]
    if not isinstance(external, dict):
        raise ValueError("Invalid external references")
    for source, url in external.items():
        canonical(source)
        if source in mapping or url != REPOSITORY + "/blob/" + revision + "/" + source:
            raise ValueError("External reference must be an explicit baseline repository link")
    files, records, total, used_external = {}, [], 0, set()
    for source, target in mapping.items():
        data = read_source(root, source)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("Package too large")
        rewrites = []
        if target == "SKILL.md":
            entry_metadata(data.decode("utf-8"), spec)
        if target.endswith(".md"):
            text = data.decode("utf-8")
            simple_links(text)

            def replace(match):
                old = match.group(1)
                resolved = local_link(source, old)
                if resolved is None:
                    return match.group(0)
                ref, fragment = resolved
                if ref in mapping:
                    new = posixpath.relpath(mapping[ref], posixpath.dirname(target) or ".") + fragment
                elif ref in external:
                    new = external[ref] + fragment
                    used_external.add(ref)
                else:
                    raise ValueError("Unresolved source link: " + ref)
                if new != old:
                    rewrites.append({"from": old, "to": new, "external": ref in external})
                return match.group(0)[:match.start(1) - match.start(0)] + new + ")"

            out = LINK.sub(replace, text).encode("utf-8")
        else:
            out = data
        files[target] = out
        records.append({"source": source, "target": target, "license": "MIT",
                        "source_sha256": digest(data), "output_sha256": digest(out),
                        "link_rewrites": rewrites})
    if used_external != set(external):
        raise ValueError("Unused external-reference declaration")
    schema_ids = {}
    for target, data in files.items():
        if target.endswith(".schema.json"):
            document = json.loads(data)
            identifier = document.get("$id")
            if identifier:
                if identifier in schema_ids:
                    raise ValueError("Duplicate bundled schema identifier")
                schema_ids[identifier] = target
    for target, data in files.items():
        if target.endswith(".md"):
            for match in simple_links(data.decode("utf-8")):
                resolved = local_link(target, match.group(1))
                if resolved is not None and resolved[0] not in files:
                    raise ValueError("Unresolved output link")
        if target.endswith(".schema.json"):
            def walk(value):
                if isinstance(value, dict):
                    if "$ref" in value:
                        reference = value["$ref"]
                        if reference.startswith("urn:"):
                            if reference.partition("#")[0] not in schema_ids:
                                raise ValueError("Unresolved bundled schema URN")
                        else:
                            resolved = local_link(target, reference)
                            if resolved is not None and resolved[0] not in files:
                                raise ValueError("Unresolved schema reference")
                    for item in value.values():
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)
            walk(json.loads(data))
    manifest = {
        "manifest_version": "1", "name": name, "version": spec["version"],
        "status": "planned", "artifact_stage": "candidate",
        "baseline_revision": revision,
        "revision_scope": "Baseline before edits; file hashes identify actual inputs, not one common source commit.",
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "source_config_sha256": digest(raw),
        "files": sorted(records, key=lambda row: row["target"]),
        "external_references": external,
        "generated_files": [{"target": "manifest.json", "self_hash": "not_recorded"}],
        "operations_in_this_build": {"model_execution": False, "host_installation": False,
                                     "test_suite_execution": False, "network_fetches": False},
        "limitations": [
            "Trusted checkout only; not a security boundary, secret scanner or legal audit.",
            "Simple inline Markdown and this project's narrow frontmatter syntax only.",
            "Heading anchors and external URLs are not fetched or certified.",
            "External baseline links document collaborators or repository context, not installed dependencies.",
            "Bundled record schemas do not execute their validator or establish factual accuracy.",
            "Lifecycle promotion and host compatibility require separate decisions and evidence.",
        ],
    }
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for target, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name + "/" + target, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return buffer.getvalue(), manifest


def build(root, name, output):
    data, manifest = prepare(root, name)
    output = Path(output)
    if output.suffix.lower() != ".zip":
        raise ValueError("ZIP destination required")
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Symlink output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)
    return {"name": name, "version": manifest["version"], "status": "planned",
            "artifact_stage": "candidate", "build": "completed",
            "files": len(manifest["files"]) + 1, "bytes": len(data),
            "sha256": digest(data), "host_installation": "not_run",
            "model_execution": "not_run"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, choices=sorted(NAMES))
    parser.add_argument("--output", required=True, help="New ZIP destination")
    args = parser.parse_args()
    try:
        result = build(Path(__file__).resolve().parents[2], args.skill, args.output)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({"build": "failed", "error_type": type(exc).__name__,
                          "message": "Inspect trusted source, manifest, links and a fresh ZIP destination."}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
