"""Focused candidate-builder tests; synthetic temp inputs, no model or network."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE = Path(__file__).resolve().parents[1] / "scripts/packaging/build-candidates.py"
spec = importlib.util.spec_from_file_location("candidate_builder", MODULE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CandidateBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.name = "data-analysis"
        self.prefix = "skills/" + self.name + "/"
        self.config = {
            "manifest_version": "1", "name": self.name, "version": "0.1.1",
            "status": "planned", "baseline_revision": "a" * 40,
            "files": [
                {"source": self.prefix + "SKILL.md", "target": "SKILL.md", "license": "MIT"},
                {"source": self.prefix + "package-README.md", "target": "README.md", "license": "MIT"},
                {"source": self.prefix + "package-NOTICES.md", "target": "THIRD_PARTY_NOTICES.md", "license": "MIT"},
                {"source": "LICENSE", "target": "LICENSE", "license": "MIT"},
            ], "external_references": {},
        }
        self.entry = (
            '---\nname: data-analysis\ndescription: >-\n  تحلیل دادهٔ نمونه\n'
            'license: MIT\nmetadata:\n  version: "0.1.1"\n  status: "planned"\n'
            '  language: "fa"\n  implementation: "source-only"\n---\n\n'
            'منبعِ مصنوعی؛ شاهد ارزیابی مدل نیست.\n'
        )
        self.put(self.prefix + "SKILL.md", self.entry)
        self.put(self.prefix + "package-README.md", "# Synthetic package\n")
        self.put(self.prefix + "package-NOTICES.md", "# Synthetic notices\n")
        self.put("LICENSE", "Synthetic license fixture, not a legal conclusion.\n")
        self.save()

    def put(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    def save(self):
        self.put(self.prefix + "build-manifest.json", json.dumps(self.config))

    def prepare(self):
        self.save()
        return builder.prepare(self.root, self.name)

    def reject(self):
        with self.assertRaises((ValueError, OSError, TypeError, KeyError)):
            self.prepare()

    def add(self, source, target, text="Resource\n"):
        self.put(source, text)
        self.config["files"].append({"source": source, "target": target, "license": "MIT"})

    def test_deterministic_bytes(self):
        self.assertEqual(self.prepare()[0], self.prepare()[0])

    def test_utf8_and_hashes(self):
        data, manifest = self.prepare()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.read(self.name + "/SKILL.md").decode(), self.entry)
            for record in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read(self.name + "/" + record["target"])).hexdigest(),
                                 record["output_sha256"])
            self.assertEqual(len(archive.namelist()), 5)

    def test_archive_metadata(self):
        data, _ = self.prepare()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.external_attr >> 16, 0o100644)
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_source_unchanged(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.prepare()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_no_overwrite(self):
        self.save()
        output = self.root / "candidate.zip"
        result = builder.build(self.root, self.name, output)
        self.assertEqual(result["status"], "planned")
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            builder.build(self.root, self.name, output)
        self.assertEqual(output.read_bytes(), original)

    def test_wrong_output_suffix(self):
        with self.assertRaises(ValueError):
            builder.build(self.root, self.name, self.root / "candidate.txt")

    def test_output_symlink(self):
        real = self.root / "real"
        real.mkdir()
        (self.root / "alias").symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError):
            builder.build(self.root, self.name, self.root / "alias/candidate.zip")

    def test_unknown_name(self):
        with self.assertRaises(ValueError):
            builder.prepare(self.root, "persian-editing")

    def test_lifecycle_not_promoted(self):
        self.config["status"] = "experimental"
        self.reject()

    def test_version_mismatch(self):
        self.config["version"] = "0.1.2"
        self.reject()

    def test_invalid_version(self):
        self.config["version"] = "../bad"
        self.reject()

    def test_invalid_baseline(self):
        self.config["baseline_revision"] = "main"
        self.reject()

    def test_extra_manifest_field(self):
        self.config["run"] = "forbidden"
        self.reject()

    def test_missing_required_entry(self):
        self.config["files"][0]["target"] = "ENTRY.md"
        self.reject()

    def test_missing_description(self):
        self.put(self.prefix + "SKILL.md", self.entry.replace("description: >-\n  تحلیل دادهٔ نمونه\n", ""))
        self.reject()

    def test_invalid_metadata_status(self):
        self.put(self.prefix + "SKILL.md", self.entry.replace('"planned"', '"experimental"'))
        self.reject()

    def test_duplicate_source(self):
        row = copy.deepcopy(self.config["files"][0])
        row["target"] = "other.md"
        self.config["files"].append(row)
        self.reject()

    def test_casefold_collision(self):
        self.add(self.prefix + "other.md", "readme.MD")
        self.reject()

    def test_directory_collision(self):
        self.add(self.prefix + "other.md", "README.md/other.md")
        self.reject()

    def test_reserved_manifest_target(self):
        self.add(self.prefix + "other.json", "manifest.json", "{}")
        self.reject()

    def test_path_traversal(self):
        self.config["files"][0]["source"] = "../SKILL.md"
        self.reject()

    def test_absolute_target(self):
        self.config["files"][0]["target"] = "/SKILL.md"
        self.reject()

    def test_backslash_path(self):
        self.config["files"][0]["source"] = "skills\\data-analysis\\SKILL.md"
        self.reject()

    def test_disallowed_source(self):
        self.add("private/secret.md", "secret.md")
        self.reject()

    def test_executable_source(self):
        self.add(self.prefix + "script.py", "script.md")
        self.reject()

    def test_executable_target(self):
        self.add(self.prefix + "other.md", "script.py")
        self.reject()

    def test_symlink_source(self):
        source = self.root / (self.prefix + "SKILL.md")
        source.unlink()
        source.symlink_to(self.root / "LICENSE")
        self.reject()

    def test_oversize_source(self):
        (self.root / "LICENSE").write_bytes(b"x" * (builder.MAX_FILE + 1))
        self.reject()

    def test_invalid_utf8(self):
        (self.root / "LICENSE").write_bytes(b"\xff")
        self.reject()

    def test_missing_file(self):
        (self.root / "LICENSE").unlink()
        self.reject()

    def test_unresolved_link(self):
        self.put(self.prefix + "package-README.md", "[missing](missing.md)\n")
        self.reject()

    def test_reference_link_syntax(self):
        self.put(self.prefix + "package-README.md", "[x][ref]\n[ref]: target.md\n")
        self.reject()

    def test_nested_link_rewrite(self):
        self.add("standards/fidelity-and-uncertainty.md", "references/shared/fidelity.md")
        self.add(self.prefix + "references/guide.md", "references/guide.md",
                 "[rule](../../../standards/fidelity-and-uncertainty.md)\n")
        data, _ = self.prepare()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.read(self.name + "/references/guide.md").decode(),
                             "[rule](shared/fidelity.md)\n")

    def test_explicit_external_collaborator(self):
        source = "skills/fact-checking/SKILL.md"
        url = builder.REPOSITORY + "/blob/" + "a" * 40 + "/" + source
        self.config["external_references"][source] = url
        self.put(self.prefix + "package-README.md", "[role](../fact-checking/SKILL.md)\n")
        data, manifest = self.prepare()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.read(self.name + "/README.md").decode(), "[role](" + url + ")\n")
        self.assertFalse(manifest["operations_in_this_build"]["host_installation"])

    def test_unapproved_external_destination(self):
        self.config["external_references"]["some.md"] = "https://example.com"
        self.reject()

    def test_unused_external_reference(self):
        source = "unused.md"
        self.config["external_references"][source] = builder.REPOSITORY + "/blob/" + "a" * 40 + "/" + source
        self.reject()

    def test_schema_ref_resolution(self):
        self.add("schemas/a.schema.json", "schemas/a.schema.json", '{"$ref":"b.schema.json#/x"}')
        self.reject()
        self.add("schemas/b.schema.json", "schemas/b.schema.json", '{"x":{}}')
        self.assertTrue(self.prepare()[0])

    def test_bundled_schema_urn(self):
        self.add("schemas/a.schema.json", "schemas/a.schema.json",
                 '{"$id":"urn:test:a","$ref":"urn:test:b#/definitions/x"}')
        self.reject()
        self.add("schemas/b.schema.json", "schemas/b.schema.json",
                 '{"$id":"urn:test:b","definitions":{"x":{}}}')
        self.assertTrue(self.prepare()[0])

    def test_duplicate_schema_id(self):
        self.add("schemas/a.schema.json", "schemas/a.schema.json", '{"$id":"urn:test:same"}')
        self.add("schemas/b.schema.json", "schemas/b.schema.json", '{"$id":"urn:test:same"}')
        self.reject()

    def test_all_six_names(self):
        for name in sorted(builder.NAMES):
            with self.subTest(name=name):
                original_prefix = self.prefix
                self.name = name
                self.prefix = "skills/" + name + "/"
                self.config["name"] = name
                for row in self.config["files"]:
                    if row["source"].startswith(original_prefix):
                        row["source"] = self.prefix + row["source"][len(original_prefix):]
                self.put(self.prefix + "SKILL.md", self.entry.replace("name: data-analysis", "name: " + name))
                self.put(self.prefix + "package-README.md", "# Fixture\n")
                self.put(self.prefix + "package-NOTICES.md", "# Fixture\n")
                self.assertEqual(self.prepare()[1]["name"], name)


if __name__ == "__main__":
    unittest.main()
