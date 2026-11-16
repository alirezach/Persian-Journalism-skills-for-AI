"""Synthetic adapter checks, not OpenCode execution or skill acceptance."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("opencode_builder", REPO / "scripts/packaging/build-opencode.py")
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)


def package(row, edit=None, extra=None):
    name = row["name"]
    files = {
        "SKILL.md": (f'---\nname: {name}\ndescription: Synthetic fixture only\nmetadata:\n  version: "{row["version"]}"\n  status: "{row["status"]}"\n---\nRead references/example.md.\n').encode(),
        "LICENSE": b"Synthetic license fixture\n",
        "references/example.md": b"Synthetic reference only\n",
    }
    if edit:
        edit(files)
    mn = "PACKAGE-MANIFEST.json" if name == "persian-editing" else "manifest.json"
    manifest = {"name": name, "version": row["version"], "files": [
        {"source": "fixture/" + target, "target": target, "source_sha256": B.digest(data), "output_sha256": B.digest(data)}
        for target, data in files.items()]}
    files[mn] = json.dumps(manifest).encode()
    if extra:
        extra(files)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for target, data in files.items():
            info = zipfile.ZipInfo(name + "/" + target)
            info.external_attr = (stat.S_IFLNK | 0o777 if target == "symlink" else 0o100644) << 16
            z.writestr(info, data)
    return buf.getvalue()


class OpenCodeBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.cfg = json.loads((REPO / B.CONFIG).read_text())
        self.write_cfg()
        for name in set(B.BUILDERS.values()):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# trusted synthetic fixture; mocked builder\n")
        self.row = copy.deepcopy(self.cfg["skills"][0])
        self.mock = mock.patch.object(B, "run_builder", side_effect=self.fake_builder).start()
        self.addCleanup(mock.patch.stopall)

    def write_cfg(self):
        p = self.root / B.CONFIG
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.cfg))

    def fake_builder(self, root, name):
        return package(next(r for r in self.cfg["skills"] if r["name"] == name))

    def test_all_eight_layouts(self):
        data, m = B.prepare(self.root)
        self.assertEqual(len(m["packages"]), 8)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in B.NAMES:
                self.assertIn(B.ROOT + "/" + name + "/SKILL.md", z.namelist())
            self.assertEqual(z.testzip(), None)
            self.assertNotIn("AGENTS.md", z.namelist())
            self.assertNotIn("opencode.json", z.namelist())

    def test_selection_only_calls_selected_builder(self):
        _, m = B.prepare(self.root, ["data-analysis"])
        self.assertEqual([r["name"] for r in m["packages"]], ["data-analysis"])
        self.mock.assert_called_once_with(self.root, "data-analysis")

    def test_deterministic_order(self):
        self.assertEqual(B.prepare(self.root, list(B.NAMES))[0], B.prepare(self.root, list(reversed(B.NAMES)))[0])

    def test_manifest_hashes_and_fixed_zip_metadata(self):
        data, m = B.prepare(self.root)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(len(z.namelist()), len(m["files"]) + 1)
            for r in m["files"]:
                self.assertEqual(B.digest(z.read(r["path"])), r["sha256"])
                self.assertEqual(len(z.read(r["path"])), r["bytes"])
            for info in z.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_no_host_or_quality_claim(self):
        _, m = B.prepare(self.root)
        self.assertFalse(m["lifecycle_promoted"])
        for key in ("host_installation", "host_execution", "behavioral_evaluation"):
            self.assertEqual(m[key], "not_run")

    def test_write_new_zip_and_no_overwrite(self):
        out = self.root / "output.zip"
        r = B.build(self.root, out, ["data-analysis"])
        before = out.read_bytes()
        self.assertEqual(r["sha256"], B.digest(before))
        with self.assertRaises(ValueError):
            B.build(self.root, out)
        self.assertEqual(out.read_bytes(), before)

    def test_wrong_output_extension(self):
        with self.assertRaises(ValueError):
            B.build(self.root, self.root / "output.txt")

    def test_symlink_output_parent(self):
        (self.root / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            B.build(self.root, self.root / "link/output.zip")

    def test_failed_build_does_not_create_output(self):
        out = self.root / "missing/output.zip"
        self.mock.side_effect = ValueError("fixture")
        with self.assertRaises(ValueError):
            B.build(self.root, out)
        self.assertFalse(out.exists())

    def test_invalid_selections(self):
        for names in ([], ["unknown"], ["data-analysis", "data-analysis"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                B.prepare(self.root, names)

    def test_unexpected_configuration_field(self):
        self.cfg["command"] = "not allowed"
        self.write_cfg()
        with self.assertRaises(ValueError):
            B.prepare(self.root)

    def test_wrong_target(self):
        self.cfg["skill_root"] = "../outside"
        self.write_cfg()
        with self.assertRaises(ValueError):
            B.prepare(self.root)

    def test_duplicate_config_skill(self):
        self.cfg["skills"][1] = self.cfg["skills"][0]
        self.write_cfg()
        with self.assertRaises(ValueError):
            B.prepare(self.root)

    def test_no_implicit_lifecycle_promotion(self):
        self.cfg["skills"][0]["status"] = "tested"
        self.write_cfg()
        with self.assertRaises(ValueError):
            B.prepare(self.root)

    def test_symlink_builder_is_rejected(self):
        p = self.root / B.BUILDERS["persian-editing"]
        p.unlink()
        p.symlink_to(self.root / B.CONFIG)
        with self.assertRaises(ValueError):
            B.prepare(self.root, ["persian-editing"])

    def test_canonical_paths(self):
        for target in ("../x", "/x", "a//b", "a/./b", "a\\b", "a:b", "a b", "NUL.txt", "x."):
            with self.subTest(target=target), self.assertRaises(ValueError):
                B.canonical(target)

    def test_valid_package_inspection(self):
        self.assertIn("SKILL.md", B.inspect_package(package(self.row), self.row))

    def test_metadata_version_mismatch(self):
        other = {**self.row, "version": "99.0.0"}
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row), other)

    def test_missing_description(self):
        def edit(files):
            files["SKILL.md"] = files["SKILL.md"].replace(b"description: Synthetic fixture only\n", b"")
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, edit=edit), self.row)

    def test_missing_entry(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, edit=lambda f: f.pop("SKILL.md")), self.row)

    def test_missing_license(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, edit=lambda f: f.pop("LICENSE")), self.row)

    def test_traversal_member(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"../outside": b"bad"})), self.row)

    def test_casefold_collision(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"license": b"bad"})), self.row)

    def test_file_directory_collision(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"references": b"bad"})), self.row)

    def test_symlink_member(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"symlink": b"outside"})), self.row)

    def test_untracked_file(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"untracked.md": b"bad"})), self.row)

    def test_output_hash_mismatch(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row, extra=lambda f: f.update({"LICENSE": b"modified"})), self.row)

    def test_invalid_utf8(self):
        with self.assertRaises(UnicodeError):
            B.inspect_package(package(self.row, edit=lambda f: f.update({"LICENSE": b"\xff"})), self.row)

    def test_entry_size_limit(self):
        data = package(self.row)
        with mock.patch.object(B, "MAX_FILE", 1), self.assertRaises(ValueError):
            B.inspect_package(data, self.row)

    def test_archive_size_limit(self):
        data = package(self.row)
        with mock.patch.object(B, "MAX_PACKAGE", len(data) - 1), self.assertRaises(ValueError):
            B.inspect_package(data, self.row)

    def test_entry_count_limit(self):
        with mock.patch.object(B, "MAX_FILES", 1), self.assertRaises(ValueError):
            B.inspect_package(package(self.row), self.row)

    def test_bundle_size_limit(self):
        with mock.patch.object(B, "MAX_TOTAL", 1), self.assertRaises(ValueError):
            B.prepare(self.root)

    def test_wrong_package_root(self):
        with self.assertRaises(ValueError):
            B.inspect_package(package(self.row), {**self.row, "name": "data-analysis"})

    def test_malformed_manifest_object(self):
        for value in (None, [], "invalid", {"name": self.row["name"]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                B.inspect_package(package(self.row, extra=lambda f: f.update({"PACKAGE-MANIFEST.json": json.dumps(value).encode()})), self.row)

    def test_malformed_manifest_records(self):
        for value in (None, [], [None], [{"target": "../bad", "output_sha256": "0" * 64}], [{"target": "LICENSE", "output_sha256": "invalid"}]):
            def edit(files):
                manifest = json.loads(files["PACKAGE-MANIFEST.json"])
                manifest["files"] = value
                files["PACKAGE-MANIFEST.json"] = json.dumps(manifest).encode()
            with self.subTest(value=value), self.assertRaises(ValueError):
                B.inspect_package(package(self.row, extra=edit), self.row)


if __name__ == "__main__":
    unittest.main()
