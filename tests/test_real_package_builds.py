"""Build real repository packages through their CLIs, without mocks or model calls.

Outputs and modified negative-case checkouts live only in temporary directories.
Counts are unittest methods; candidate skills each get a separate method.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit, unquote
import zipfile
import posixpath

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ('source-verification', 'fact-checking', 'research-synthesis',
              'data-analysis', 'data-visualization', 'data-journalism')
LANGUAGE = ('persian-editing', 'persian-ai-detox', 'persian-editing-and-ai-detox')
ORIGINAL = ('persian-editing', 'humanities-translation', *CANDIDATES)
LINK = re.compile(r'\[[^\]\n]*\]\(([^)\n]+)\)')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def command(repo, builder, output, *options):
    return [sys.executable, str(repo / 'scripts' / 'packaging' / builder),
            '--output', str(output), *options]

class RealPackageBuilds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='pjai-real-builds-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        cls.built = {}
        for name in ORIGINAL:
            builder = 'build-skill.py' if name == 'persian-editing' else (
                'build-translation.py' if name == 'humanities-translation' else 'build-candidates.py')
            options = [] if name not in CANDIDATES else ['--skill', name]
            cls.build(name, builder, options)
        for name in LANGUAGE:
            cls.build('language-'+name, 'build-persian-language-suite.py',
                      ['--skill', name, '--format', 'standalone'])
        cls.build('eight', 'build-opencode.py', [])
        cls.build('selected-eight', 'build-opencode.py', ['--skills', 'humanities-translation', 'data-analysis'])
        cls.build('language-suite', 'build-persian-language-suite.py', [])
        cls.build('selected-language', 'build-persian-language-suite.py', ['--skill', LANGUAGE[-1]])
        cls.build('legacy-standalone', 'build-editing-detox.py', ['--format', 'standalone'])
        cls.build('legacy-opencode', 'build-editing-detox.py', ['--format', 'opencode'])

    @classmethod
    def build(cls, key, builder, options):
        output = cls.work / (key+'.zip')
        args = command(ROOT, builder, output, *options)
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=60,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        if result.returncode:
            raise AssertionError(f'{key} real build failed: {result.stdout}\n{result.stderr}')
        receipt = json.loads(result.stdout)
        raw = output.read_bytes()
        if receipt['sha256'] != digest(raw):
            raise AssertionError('Receipt hash differs from actual ZIP: '+key)
        if receipt['bytes'] != len(raw):
            raise AssertionError('Receipt size differs from actual ZIP: '+key)
        with zipfile.ZipFile(output) as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                raise AssertionError('Duplicate archive members: '+key)
            for info in z.infolist():
                p = PurePosixPath(info.filename)
                if p.is_absolute() or any(x in ('', '.', '..') for x in info.filename.split('/')) or '\\' in info.filename or ':' in info.filename:
                    raise AssertionError('Unsafe archive path: '+info.filename)
                if info.date_time != (1980,1,1,0,0,0) or (info.external_attr >> 16) != 0o100644:
                    raise AssertionError('Unexpected deterministic ZIP metadata: '+info.filename)
            members = {name:z.read(name) for name in names}
        if receipt['files'] != len(members):
            raise AssertionError('Receipt count differs from ZIP: '+key)
        cls.built[key] = {'builder':builder, 'options':options, 'receipt':receipt,
                          'raw':raw, 'members':members, 'path':output}
        return cls.built[key]

    def package(self, key, name):
        members = self.built[key]['members'];prefix = name+'/'
        self.assertTrue(all(p.startswith(prefix) for p in members))
        return {p[len(prefix):]:d for p,d in members.items()}

    def check_local_links(self, members, skill_root=False):
        for source, data in members.items():
            if not source.endswith('.md'): continue
            for link in LINK.findall(data.decode('utf-8')):
                url = urlsplit(link)
                if url.scheme or not url.path: continue
                base = '' if skill_root else posixpath.dirname(source)
                target = posixpath.normpath(posixpath.join(base, unquote(url.path)))
                self.assertTrue(target in members, f'{source}: unresolved local link {link}')

    def check_source_manifest(self, name, generated):
        members = self.package(name, name)
        manifest = json.loads(members[generated])
        config_path = ROOT/'skills'/name/'build-manifest.json'
        config = json.loads(config_path.read_text())
        self.assertEqual(manifest['name'], name)
        self.assertEqual(manifest['version'], config['version'])
        if 'status' in config:self.assertEqual(manifest['status'], config['status'])
        self.assertEqual(manifest['source_config_sha256'], digest(config_path.read_bytes()))
        builder = ROOT/'scripts'/'packaging'/self.built[name]['builder']
        self.assertEqual(manifest['builder_sha256'], digest(builder.read_bytes()))
        records = manifest['files']
        self.assertEqual(set(members), {x['target'] for x in records}|{generated})
        for row in records:
            self.assertEqual(row['source_sha256'], digest((ROOT/row['source']).read_bytes()))
            self.assertEqual(row['output_sha256'], digest(members[row['target']]))
        self.check_local_links(members, skill_root=(name == 'persian-editing'))
        return members, manifest

    def test_translation_real_sources_manifest_and_links(self):
        _, manifest = self.check_source_manifest('humanities-translation', 'manifest.json')
        self.assertEqual(manifest['model_evaluation'], 'not_run')
        self.assertEqual(manifest['host_installation'], 'not_run')

    def test_editing_canonical_and_language_route_are_identical(self):
        self.check_source_manifest('persian-editing','PACKAGE-MANIFEST.json')
        self.assertEqual(self.built['persian-editing']['raw'],self.built['language-persian-editing']['raw'])

    def test_detox_real_sources_and_allowlist(self):
        name='persian-ai-detox';members=self.package('language-'+name,name)
        config_raw=(ROOT/'skills'/name/'build-manifest.json').read_bytes()
        config=json.loads(config_raw)
        self.assertEqual(set(members),set(config['files'])|{'build-manifest.json','PACKAGE-MANIFEST.json'})
        for target,sha in config['files'].items():
            self.assertEqual(members[target],(ROOT/'skills'/name/target).read_bytes())
            self.assertEqual(digest(members[target]),sha)
        self.assertEqual(members['build-manifest.json'],config_raw)
        # Detox explicitly resolves resources from the skill root, not guide directories.
        self.check_local_links(members, skill_root=True)

    def test_combined_embeds_both_complete_payloads_without_discoverable_entries(self):
        name=LANGUAGE[-1];combined=self.package('language-'+name,name)
        manifest=json.loads(combined['PACKAGE-MANIFEST.json'])
        for component in LANGUAGE[:2]:
            original=self.package('language-'+component,component)
            prefix='components/'+component+'/'
            embedded={p[len(prefix):]:d for p,d in combined.items() if p.startswith(prefix)}
            expected={('INSTRUCTIONS.md' if p=='SKILL.md' else p):d for p,d in original.items()}
            self.assertEqual(embedded,expected)
            for row in manifest['components'][component]['files']:
                self.assertEqual(digest(combined[row['target']]),row['sha256'])
        self.assertFalse(any(p.endswith('/SKILL.md') for p in combined))

    def check_bundle(self,key,names,standalone_keys):
        members=self.built[key]['members'];manifest=json.loads(members['BUNDLE-MANIFEST.json'])
        declared=manifest['packages']
        self.assertEqual(set(declared) if isinstance(declared,dict) else {p['name'] for p in declared},set(names))
        expected_entries={'.opencode/skills/'+n+'/SKILL.md' for n in names}
        self.assertEqual({p for p in members if p.endswith('/SKILL.md')},expected_entries)
        for name in names:
            prefix='.opencode/skills/'+name+'/'
            embedded={p[len(prefix):]:d for p,d in members.items() if p.startswith(prefix)}
            expected=self.package(standalone_keys[name],name)
            self.assertEqual(embedded,expected)
        declarations=manifest['files']
        hashes=declarations if isinstance(declarations,dict) else {p['path']:p['sha256'] for p in declarations}
        self.assertEqual(set(hashes),set(members)-{'BUNDLE-MANIFEST.json'})
        for p,sha in hashes.items():self.assertEqual(digest(members[p]),sha)

    def test_eight_skill_bundle_uses_real_canonical_builders(self):
        self.check_bundle('eight',ORIGINAL,{n:n for n in ORIGINAL})
        m=json.loads(self.built['eight']['members']['BUNDLE-MANIFEST.json'])
        self.assertEqual(m['host_execution'],'not_run');self.assertFalse(m['lifecycle_promoted'])

    def test_selected_eight_bundle_contains_only_requested_skills(self):
        names=('humanities-translation','data-analysis')
        self.check_bundle('selected-eight',names,{n:n for n in names})

    def test_three_skill_bundle_matches_real_standalone_payloads(self):
        self.check_bundle('language-suite',LANGUAGE,{n:'language-'+n for n in LANGUAGE})

    def test_selected_language_bundle_contains_only_combined(self):
        name=LANGUAGE[-1];self.check_bundle('selected-language',[name],{name:'language-'+name})

    def test_legacy_standalone_command_matches_canonical(self):
        self.assertEqual(self.built['legacy-standalone']['raw'],self.built['language-'+LANGUAGE[-1]]['raw'])

    def test_legacy_opencode_command_matches_canonical(self):
        self.assertEqual(self.built['legacy-opencode']['raw'],self.built['selected-language']['raw'])

    def test_all_real_build_routes_are_byte_reproducible(self):
        for key,item in list(self.built.items()):
            with self.subTest(route=key):
                output=self.work/(key+'-repeat.zip')
                result=subprocess.run(command(ROOT,item['builder'],output,*item['options']),
                    cwd=ROOT,capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                self.assertEqual(output.read_bytes(),item['raw'])

    def test_current_skill_inventory_is_covered(self):
        entries={p.parent.name for p in (ROOT/'skills').glob('*/SKILL.md')}
        self.assertEqual(entries,set(ORIGINAL)|set(LANGUAGE))

    def test_translation_refuses_to_overwrite_output(self):
        output=self.work/'existing.zip';output.write_bytes(b'keep existing user bytes')
        result=subprocess.run(command(ROOT,'build-translation.py',output),cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(output.read_bytes(),b'keep existing user bytes')

    def translation_negative(self, change):
        with tempfile.TemporaryDirectory(prefix='pjai-translation-negative-') as temp:
            copy=Path(temp)/'repo'
            shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('.git','node_modules','__pycache__','dist','build'))
            change(copy)
            output=Path(temp)/'rejected.zip'
            result=subprocess.run(command(copy,'build-translation.py',output),cwd=copy,capture_output=True,text=True,timeout=60)
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse(output.exists())

    def test_translation_missing_real_input_fails_without_archive(self):
        self.translation_negative(lambda r:(r/'skills/humanities-translation/references/fidelity.md').unlink())

    def test_translation_unmapped_resource_fails_without_archive(self):
        def change(repo):
            p=repo/'skills/humanities-translation/references/fidelity.md'
            p.write_text(p.read_text()+'\n[Missing](not-in-the-package.md)\n')
        self.translation_negative(change)

for candidate in CANDIDATES:
    def test_candidate(self, name=candidate):
        _,manifest=self.check_source_manifest(name,'manifest.json')
        self.assertEqual(manifest['status'],'planned')
        self.assertFalse(manifest['operations_in_this_build']['host_installation'])
        self.assertFalse(manifest['operations_in_this_build']['model_execution'])
    setattr(RealPackageBuilds,'test_candidate_'+candidate.replace('-','_'),test_candidate)

if __name__ == '__main__':
    unittest.main(verbosity=2)
