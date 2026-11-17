"""Compatibility CLI contracts; core guards live in test_persian_language_suite.py."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
WRAPPER=ROOT/'scripts/packaging/build-editing-detox.py'
spec=importlib.util.spec_from_file_location('compat',WRAPPER)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
NEW='persian-editing-and-ai-detox'
class CompatibilityTests(unittest.TestCase):
    def test_standalone_new_name_only(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'a.zip';b.build(ROOT,out,'standalone')
            with zipfile.ZipFile(out) as z:
                self.assertTrue(all(n.startswith(NEW+'/') for n in z.namelist()))
                self.assertEqual(len(z.namelist()),45)
    def test_opencode_new_entry_only(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'a.zip';b.build(ROOT,out,'opencode')
            with zipfile.ZipFile(out) as z:
                self.assertEqual([n for n in z.namelist() if n.endswith('/SKILL.md')],['.opencode/skills/'+NEW+'/SKILL.md'])
    def test_same_bytes_as_canonical(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a.zip';c=Path(t)/'c.zip'
            b.build(ROOT,a,'standalone');b.builder().build(ROOT,c,NEW,'standalone')
            self.assertEqual(a.read_bytes(),c.read_bytes())
    def test_cli_help(self):
        p=subprocess.run([sys.executable,str(WRAPPER),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0);self.assertIn('--format',p.stdout)
    def test_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'a.zip';cmd=[sys.executable,str(WRAPPER),'--format','standalone','--output',str(out)]
            p=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
            before=out.read_bytes();p=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertEqual(before,out.read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
