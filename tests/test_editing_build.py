"""Deterministic packager tests only. No model calls or network."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/packaging/build-skill.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'repo';self.root.mkdir()
        self.cfg=json.loads((ROOT/b.CONFIG).read_text())
        for row in self.cfg['files']+[{'source':b.CONFIG}]:
            p=self.root/row['source'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['source'],p)
    def tearDown(self):self.tmp.cleanup()
    def save(self): (self.root/b.CONFIG).write_text(json.dumps(self.cfg))
    def bad(self):
        self.save()
        with self.assertRaises((ValueError,OSError,TypeError,KeyError)):b.prepare(self.root)
    def test_reproducible_bytes(self):self.assertEqual(b.prepare(self.root)[0],b.prepare(self.root)[0])
    def test_hashes_and_standalone_resources(self):
        data,m=b.prepare(self.root)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            files={n.removeprefix('persian-editing/'):z.read(n) for n in z.namelist()}
            self.assertEqual(len(files),26);b.link_check(files)
            self.assertNotIn(b'../../',files['SKILL.md'])
            for row in m['files']:
                self.assertEqual(row['output_sha256'],b.digest(files[row['target']]))
                self.assertEqual(row['source_sha256'],b.digest((self.root/row['source']).read_bytes()))
    def test_source_unchanged(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()};b.prepare(self.root)
        self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_output_report(self):
        out=Path(self.tmp.name)/'a.zip';report=b.build(self.root,out)
        self.assertEqual(report['sha256'],b.digest(out.read_bytes()));self.assertEqual(report['files'],26)
    def test_existing_output_preserved(self):
        out=Path(self.tmp.name)/'a.zip';out.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):b.build(self.root,out)
        self.assertEqual(out.read_bytes(),b'keep')
    def test_missing_source(self): (self.root/'LICENSE').unlink();self.bad()
    def test_absolute_source(self):self.cfg['files'][0]['source']='/tmp/private.md';self.bad()
    def test_traversal_source(self):self.cfg['files'][0]['source']='standards/../private.md';self.bad()
    def test_absolute_target(self):self.cfg['files'][0]['target']='/SKILL.md';self.bad()
    def test_traversal_target(self):self.cfg['files'][0]['target']='../SKILL.md';self.bad()
    def test_windows_target(self):self.cfg['files'][0]['target']='C:\\SKILL.md';self.bad()
    def test_duplicate_target(self):self.cfg['files'][1]['target']='SKILL.md';self.bad()
    def test_case_collision(self):self.cfg['files'][1]['target']='skill.md';self.bad()
    def test_duplicate_source(self):self.cfg['files'][1]['source']=self.cfg['files'][0]['source'];self.bad()
    def test_reserved_manifest(self):self.cfg['files'][1]['target']='PACKAGE-MANIFEST.json';self.bad()
    def test_private_source(self):self.cfg['files'][1]['source']='profiles/local/private.md';self.bad()
    def test_missing_license(self):self.cfg['files']=[r for r in self.cfg['files'] if r['source']!='LICENSE'];self.bad()
    def test_source_symlink(self):
        p=self.root/'LICENSE';p.unlink();p.symlink_to(ROOT/'LICENSE');self.bad()
    def test_directory_symlink(self):
        shutil.rmtree(self.root/'standards');(self.root/'standards').symlink_to(ROOT/'standards',target_is_directory=True);self.bad()
    def test_output_symlink(self):
        real=Path(self.tmp.name)/'real';real.mkdir();link=Path(self.tmp.name)/'link';link.symlink_to(real,target_is_directory=True)
        with self.assertRaises(ValueError):b.build(self.root,link/'a.zip')
        self.assertFalse((real/'a.zip').exists())
    def test_other_python_source_rejected(self):
        other=self.root/'skills/persian-editing/other.py';other.write_text('print(1)')
        self.cfg['files'].append({'source':'skills/persian-editing/other.py','target':'other.py'});self.bad()
    def test_helper_destination_rejected(self):
        next(r for r in self.cfg['files'] if r['source']==b.HELPER)['target']='other.py';self.bad()
    def test_helper_source_spoof_rejected(self):
        next(r for r in self.cfg['files'] if r['source']==b.HELPER)['source']='LICENSE';self.bad()
    def test_packaged_helper_runs_without_repository(self):
        data,_=b.prepare(self.root);dest=Path(self.tmp.name)/'standalone'
        with zipfile.ZipFile(io.BytesIO(data)) as z:z.extractall(dest)
        request={'request_version':'1','source':'يك كار','authorization':'explicit-task-permission','confirmed_persian_transcription':True,'scope_reviewed':True,'eligible_spans':[{'start':0,'end':6,'text':'يك كار'}],'protected_spans':[]}
        script=dest/'persian-editing/scripts/normalize_transcribed_fa.py'
        p=subprocess.run([sys.executable,str(script),'-'],input=json.dumps(request),text=True,capture_output=True,cwd=dest)
        self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout)
        self.assertEqual(result['text'],'یک کار');self.assertEqual(result['original_text'],'يك كار')
    def test_large_file(self):(self.root/'LICENSE').write_bytes(b'x'*(b.MAX_FILE+1));self.bad()
    def test_total_limit(self):
        for row in self.cfg['files'][:5]:(self.root/row['source']).write_bytes(b'x'*b.MAX_FILE)
        self.bad()
    def test_invalid_utf8(self):(self.root/'LICENSE').write_bytes(b'\xff');self.bad()
    def test_nonregular_source(self):p=self.root/'LICENSE';p.unlink();p.mkdir();self.bad()
    def test_rewrite_missing_anchor(self):self.cfg['entry_rewrites']['../../standards/missing.md']='LICENSE';self.bad()
    def test_broken_link(self):
        p=self.root/'skills/persian-editing/SKILL.md';p.write_text(p.read_text()+'\n[missing](references/missing.md)\n');self.bad()
    def test_unsupported_reference_link(self):
        p=self.root/'skills/persian-editing/SKILL.md';p.write_text(p.read_text()+'\n[x][ref]\n[ref]: other.md\n');self.bad()
    def test_extra_private_file_excluded(self):
        (self.root/'private.txt').write_text('synthetic-marker-not-a-secret')
        self.assertNotIn(b'synthetic-marker-not-a-secret',b.prepare(self.root)[0])
    def test_config_fields_closed(self):self.cfg['execute']='nothing';self.bad()
    def test_bad_version(self):self.cfg['version']='../../bad';self.bad()
    def test_bad_name(self):self.cfg['name']='other';self.bad()
    def test_empty_files(self):self.cfg['files']=[];self.bad()
    def test_too_many_files(self):self.cfg['files']*=3;self.bad()
    def test_no_output_on_bad_input(self):
        (self.root/'LICENSE').unlink();out=Path(self.tmp.name)/'fail.zip'
        with self.assertRaises(ValueError):b.build(self.root,out)
        self.assertFalse(out.exists())
    def test_zip_extension(self):
        with self.assertRaises(ValueError):b.build(self.root,Path(self.tmp.name)/'a.txt')
    def test_cli_help(self):
        p=subprocess.run([sys.executable,str(ROOT/'scripts/packaging/build-skill.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0);self.assertIn('--output',p.stdout)
    def test_cli_success_and_failure(self):
        out=Path(self.tmp.name)/'cli.zip';cmd=[sys.executable,str(ROOT/'scripts/packaging/build-skill.py'),'--output',str(out)]
        p=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['status'],'built')
        p=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertEqual(json.loads(p.stderr)['status'],'build_error')

if __name__=='__main__':unittest.main(verbosity=2)
