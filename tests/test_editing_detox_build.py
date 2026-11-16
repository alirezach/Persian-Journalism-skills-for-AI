"""Technical contracts only. No model execution or editorial-quality scoring."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/packaging/build-editing-detox.py'
spec = importlib.util.spec_from_file_location('editing_detox_builder', SCRIPT)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.root = self.work / 'repo'
        self.skill = self.root / 'skills' / b.NAME
        shutil.copytree(ROOT / 'skills' / b.NAME, self.skill)
        self.out = self.work / 'out.zip'

    def manifest(self):
        return json.loads((self.skill / b.MANIFEST).read_text())

    def save_manifest(self, value):
        (self.skill / b.MANIFEST).write_bytes(b.encode_json(value))

    def rehash(self, name):
        value = self.manifest()
        value['files'][name] = b.digest((self.skill / name).read_bytes())
        self.save_manifest(value)

    def refused(self):
        with self.assertRaises((ValueError, OSError)):
            b.build(self.root, self.out, 'standalone')
        self.assertFalse(self.out.exists())

    def test_both_layouts_and_hashes(self):
        for form in ('standalone', 'opencode'):
            with self.subTest(format=form):
                output = self.work / (form + '.zip')
                result = b.build(self.root, output, form)
                self.assertEqual(result['files'], 12)
                prefix = b.NAME + '/' if form == 'standalone' else '.opencode/skills/' + b.NAME + '/'
                with zipfile.ZipFile(output) as z:
                    self.assertIsNone(z.testzip())
                    record = json.loads(z.read('PACKAGE-MANIFEST.json'))
                    self.assertEqual(set(z.namelist()), set(record['files']) | {'PACKAGE-MANIFEST.json'})
                    self.assertEqual(record['format'], form)
                    self.assertEqual(record['status'], 'experimental')
                    for name, expected in record['files'].items():
                        self.assertEqual(b.digest(z.read(name)), expected)
                    for name, data in b.prepare(self.root).items():
                        self.assertEqual(z.read(prefix + name), data)
                    self.assertEqual(len(z.namelist()), len(set(z.namelist())))
                    for info in z.infolist():
                        self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(info.external_attr >> 16, 0o100644)

    def test_reproducible_both_formats(self):
        for form in ('standalone', 'opencode'):
            a, c = self.work / (form + '1.zip'), self.work / (form + '2.zip')
            b.build(self.root, a, form)
            b.build(self.root, c, form)
            self.assertEqual(a.read_bytes(), c.read_bytes())

    def test_existing_output_preserved(self):
        self.out.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            b.build(self.root, self.out, 'standalone')
        self.assertEqual(self.out.read_bytes(), b'keep')

    def test_output_symlink_refused(self):
        target = self.work / 'missing'
        self.out.symlink_to(target)
        with self.assertRaises(FileExistsError):
            b.build(self.root, self.out, 'standalone')
        self.assertFalse(target.exists())

    def test_missing_file(self):
        (self.skill / 'LICENSE').unlink()
        self.refused()

    def test_changed_input(self):
        (self.skill / 'README.md').write_text('changed')
        self.refused()

    def test_invalid_json(self):
        (self.skill / b.MANIFEST).write_text('{')
        self.refused()

    def test_duplicate_json_key(self):
        p = self.skill / b.MANIFEST
        p.write_text(p.read_text().replace('{', '{"name":"duplicate",', 1))
        self.refused()

    def test_invalid_manifest_shapes(self):
        original = self.manifest()
        for bad in ([], None, {'name': b.NAME}, dict(original, unexpected=True), dict(original, files=[])):
            with self.subTest(value=repr(bad)[:80]):
                self.save_manifest(bad)
                self.refused()

    def test_identity_rejected(self):
        original = self.manifest()
        for key, value in (('name', '../escape'), ('version', '9.0.0'), ('status', 'stable'), ('schema_version', True)):
            with self.subTest(key=key):
                self.save_manifest(dict(original, **{key: value}))
                self.refused()

    def test_extra_missing_and_unsafe_members(self):
        original = self.manifest()
        for name in ('../escape', '/absolute', 'C:\\escape', 'extra.md'):
            changed = json.loads(json.dumps(original))
            changed['files'][name] = 'a' * 64
            self.save_manifest(changed)
            self.refused()
        changed = json.loads(json.dumps(original))
        del changed['files']['LICENSE']
        self.save_manifest(changed)
        self.refused()

    def test_bad_hash_types(self):
        original = self.manifest()
        for value in (None, 12, 'no', 'A' * 64):
            changed = json.loads(json.dumps(original))
            changed['files']['LICENSE'] = value
            self.save_manifest(changed)
            self.refused()

    def test_invalid_utf8_and_nul(self):
        for raw in (b'\xff', b'a\x00b'):
            (self.skill / 'README.md').write_bytes(raw)
            self.rehash('README.md')
            self.refused()

    def test_oversized_file(self):
        (self.skill / 'README.md').write_bytes(b'x' * (b.LIMIT + 1))
        self.rehash('README.md')
        self.refused()

    def test_symlink_file(self):
        p = self.skill / 'LICENSE'
        p.unlink()
        p.symlink_to(ROOT / 'skills' / b.NAME / 'LICENSE')
        self.refused()

    def test_symlink_parent(self):
        refs = self.skill / 'references'
        moved = self.work / 'references'
        refs.rename(moved)
        refs.symlink_to(moved, target_is_directory=True)
        self.refused()

    def test_symlink_root(self):
        link = self.work / 'root-link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            b.prepare(link)

    def test_missing_local_link(self):
        p = self.skill / 'README.md'
        p.write_text(p.read_text() + '\n[broken](missing.md)\n')
        self.rehash('README.md')
        self.refused()

    def test_frontmatter_mismatch(self):
        p = self.skill / 'SKILL.md'
        p.write_text(p.read_text().replace('name: persian-editing-detox', 'name: other', 1))
        self.rehash('SKILL.md')
        self.refused()

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            b.build(self.root, self.out, 'other')
        self.assertFalse(self.out.exists())

    def test_unlisted_files_not_bundled(self):
        (self.skill / 'secret.txt').write_text('do not bundle')
        b.build(self.root, self.out, 'standalone')
        with zipfile.ZipFile(self.out) as z:
            self.assertFalse(any('secret' in name for name in z.namelist()))

    def test_cli(self):
        run = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), '--format', 'opencode', '--output', str(self.out)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['files'], 12)
        again = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), '--format', 'opencode', '--output', str(self.out)], capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)


if __name__ == '__main__':
    unittest.main()
