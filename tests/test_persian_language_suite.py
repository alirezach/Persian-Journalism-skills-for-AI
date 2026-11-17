"""Technical package contracts only; no model, network or host execution."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('suite_builder', ROOT/'scripts/packaging/build-persian-language-suite.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
COMBINED = 'persian-editing-and-ai-detox'
DETOX = 'persian-ai-detox'


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)/'repo'
        self.root.mkdir()
        paths = set()
        cfg = json.loads((ROOT/'skills/persian-editing/build-manifest.json').read_text())
        paths.update(r['source'] for r in cfg['files'])
        paths.add('skills/persian-editing/build-manifest.json')
        paths.add('scripts/packaging/build-skill.py')
        for name in (DETOX, COMBINED):
            paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'skills'/name).rglob('*') if p.is_file())
        for path in paths:
            dest = self.root/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/path, dest)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, name):
        return self.root/'skills'/name/'build-manifest.json'

    def change_config(self, name, fn):
        path = self.config(name)
        data = json.loads(path.read_text())
        fn(data)
        path.write_text(json.dumps(data))

    def bad(self, name=COMBINED):
        with self.assertRaises((ValueError, OSError, TypeError, KeyError)):
            b.prepare(self.root, name)

    def test_complete_component_bytes(self):
        combined = b.prepare(self.root, COMBINED)
        outer = json.loads(combined['PACKAGE-MANIFEST.json'])
        for name in ('persian-editing', DETOX):
            expected = b.prepare(self.root, name)
            mappings = outer['components'][name]['files']
            self.assertEqual(set(expected), {r['original'] for r in mappings})
            self.assertEqual(len(expected), len(mappings))
            for row in mappings:
                self.assertEqual(combined[row['target']], expected[row['original']])
                self.assertEqual(row['sha256'], b.sha(expected[row['original']]))

    def test_single_discoverable_entry(self):
        files = b.prepare(self.root, COMBINED)
        self.assertEqual([n for n in files if n.endswith('SKILL.md')], ['SKILL.md'])
        for name in ('persian-editing', DETOX):
            self.assertIn('components/'+name+'/INSTRUCTIONS.md', files)

    def test_package_counts(self):
        for name, count in [('persian-editing',26), (DETOX,13), (COMBINED,45)]:
            self.assertEqual(len(b.prepare(self.root,name)), count)

    def test_manifest_hashes(self):
        for name in (DETOX, COMBINED):
            files=b.prepare(self.root,name)
            manifest=json.loads(files['PACKAGE-MANIFEST.json'])
            self.assertEqual(set(manifest['files']),set(files)-{'PACKAGE-MANIFEST.json'})
            for path, digest in manifest['files'].items():
                self.assertEqual(digest,b.sha(files[path]))

    def test_deterministic_build(self):
        a=Path(self.tmp.name)/'a.zip'; c=Path(self.tmp.name)/'c.zip'
        b.build(self.root,a); b.build(self.root,c)
        self.assertEqual(a.read_bytes(),c.read_bytes())

    def test_suite_layout_and_manifest(self):
        out=Path(self.tmp.name)/'a.zip'
        report=b.build(self.root,out)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(len(z.namelist()),86)
            self.assertIsNone(z.testzip())
            m=json.loads(z.read('BUNDLE-MANIFEST.json'))
            self.assertEqual(set(m['packages']),set(b.VERSIONS))
            self.assertEqual(set(m['files']),set(z.namelist())-{'BUNDLE-MANIFEST.json'})
            for n,digest in m['files'].items():
                self.assertEqual(digest,b.sha(z.read(n)))
            entries=[n for n in z.namelist() if n.endswith('/SKILL.md')]
            self.assertEqual(len(entries),3)
            self.assertTrue(all(n.startswith('.opencode/skills/') for n in entries))
            self.assertTrue(all(i.date_time==(1980,1,1,0,0,0) for i in z.infolist()))
        self.assertEqual(report['sha256'],b.sha(out.read_bytes()))

    def test_single_standalone(self):
        out=Path(self.tmp.name)/'a.zip'
        b.build(self.root,out,DETOX,'standalone')
        with zipfile.ZipFile(out) as z:
            self.assertTrue(all(n.startswith(DETOX+'/') for n in z.namelist()))

    def test_existing_output_preserved(self):
        out=Path(self.tmp.name)/'a.zip';out.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):b.build(self.root,out)
        self.assertEqual(out.read_bytes(),b'keep')

    def test_no_source_mutation(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        b.prepare(self.root,COMBINED)
        self.assertTrue(all(p.read_bytes()==d for p,d in before.items()))

    def test_unknown_skill(self):
        self.bad('other')

    def test_invalid_format(self):
        with self.assertRaises(ValueError):b.build(self.root,Path(self.tmp.name)/'a.zip',DETOX,'unknown')

    def test_all_standalone_rejected(self):
        with self.assertRaises(ValueError):b.build(self.root,Path(self.tmp.name)/'a.zip','all','standalone')

    def test_wrong_extension(self):
        with self.assertRaises(ValueError):b.build(self.root,Path(self.tmp.name)/'a.txt')

    def test_no_output_on_missing_input(self):
        (self.root/'skills'/DETOX/'LICENSE').unlink()
        out=Path(self.tmp.name)/'a.zip'
        with self.assertRaises(ValueError):b.build(self.root,out)
        self.assertFalse(out.exists())

    def test_detox_hash_tamper(self):
        path=self.root/'skills'/DETOX/'references/pattern-catalog.md'
        path.write_text(path.read_text()+'\nchanged\n')
        self.bad(DETOX)

    def test_detox_allowlist(self):
        self.change_config(DETOX,lambda d:d['files'].update({'../../private.txt':'x'}))
        self.bad(DETOX)

    def test_detox_missing_reference(self):
        self.change_config(DETOX,lambda d:d['files'].pop('references/register-and-voice.md'))
        self.bad(DETOX)

    def test_unknown_config_field(self):
        self.change_config(COMBINED,lambda d:d.update({'execute':'not-permitted'}))
        self.bad()

    def test_wrong_component_version(self):
        self.change_config(COMBINED,lambda d:d['components'].update({'persian-editing':'0.1.3'}))
        self.bad()

    def test_missing_component(self):
        self.change_config(COMBINED,lambda d:d['components'].pop(DETOX))
        self.bad()

    def test_unsafe_component_rewrite(self):
        self.change_config(COMBINED,lambda d:d['entry_rewrites'].update({'../'+DETOX+'/SKILL.md':'../../outside'}))
        self.bad()

    def test_identity_mismatch(self):
        path=self.root/'skills'/COMBINED/'SKILL.md'
        path.write_text(path.read_text().replace('version: "0.2.0"','version: "9.9.9"'))
        self.bad()

    def test_duplicate_json_key(self):
        path=self.config(DETOX)
        path.write_text(path.read_text().replace('"files":','"name":"bad","files":',1))
        self.bad(DETOX)

    def test_broken_local_link(self):
        path=self.root/'skills'/COMBINED/'SKILL.md'
        path.write_text(path.read_text()+'\n[bad](missing.md)\n')
        self.bad()

    def test_ambiguous_entry_anchor(self):
        path=self.root/'skills'/COMBINED/'SKILL.md'
        path.write_text(path.read_text()+'\n[duplicate](../persian-ai-detox/SKILL.md)\n')
        self.bad()

    def test_source_symlink(self):
        path=self.root/'skills'/DETOX/'LICENSE'
        path.unlink();path.symlink_to(ROOT/'LICENSE')
        self.bad()

    def test_root_symlink(self):
        link=Path(self.tmp.name)/'link';link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):b.prepare(link,COMBINED)

    def test_output_parent_symlink(self):
        real=Path(self.tmp.name)/'real';real.mkdir()
        link=Path(self.tmp.name)/'link';link.symlink_to(real,target_is_directory=True)
        with self.assertRaises(ValueError):b.build(self.root,link/'a.zip')
        self.assertFalse((real/'a.zip').exists())

    def test_archive_path_guards(self):
        for name in ('/x','../x','a/../x','a\\x','a//x'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):b.archive({name:b'x'})

    def test_archive_limits(self):
        with self.assertRaises(ValueError):b.archive({str(i):b'' for i in range(513)})
        with self.assertRaises(ValueError):b.archive({'a':b'x'*(b.MAX_TOTAL+1)})

    def test_no_unlisted_file(self):
        (self.root/'skills'/DETOX/'private.txt').write_text('synthetic-secret-marker')
        self.assertNotIn('private.txt',b.prepare(self.root,DETOX))

    def test_nul_and_utf8_rejected(self):
        path=self.root/'skills'/DETOX/'README.md'
        for raw in (b'x\0y', b'\xff'):
            path.write_bytes(raw)
            self.change_config(DETOX,lambda d:d['files'].update({'README.md':b.sha(raw)}))
            self.bad(DETOX)

    def test_oversized_input(self):
        path=self.root/'skills'/DETOX/'README.md'
        raw=b'x'*(1024*1024+1);path.write_bytes(raw)
        self.change_config(DETOX,lambda d:d['files'].update({'README.md':b.sha(raw)}))
        self.bad(DETOX)

    def test_manifest_shapes(self):
        path=self.config(DETOX)
        for value in ([],None,{'schema_version':True}):
            path.write_text(json.dumps(value));self.bad(DETOX)

    def test_bad_hash_types(self):
        for value in (None,12,'A'*64):
            self.change_config(DETOX,lambda d:d['files'].update({'LICENSE':value}))
            self.bad(DETOX)

    def test_symlink_reference_parent(self):
        path=self.root/'skills'/DETOX/'references'
        moved=Path(self.tmp.name)/'moved';path.rename(moved)
        path.symlink_to(moved,target_is_directory=True)
        self.bad(DETOX)

    def test_builder_parent_symlink(self):
        path=self.root/'scripts'
        moved=Path(self.tmp.name)/'moved';path.rename(moved)
        path.symlink_to(moved,target_is_directory=True)
        self.bad()


if __name__=='__main__':
    unittest.main(verbosity=2)
