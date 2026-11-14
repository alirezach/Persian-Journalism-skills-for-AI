"""Deterministic code tests only. No model generation or model grading."""
import copy
import hashlib
import importlib.util
import json
import random
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/editing/normalize_transcribed_fa.py"
spec = importlib.util.spec_from_file_location("transcribed_fa", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
FIXTURE = json.loads((ROOT/"tests/fixtures/transcription-normalization-0.1.3.json").read_text())


def request(source="يك كار"):
    return {"request_version":"1", "source":source,
            "authorization":"explicit-task-permission",
            "confirmed_persian_transcription":True, "scope_reviewed":True,
            "eligible_spans":[{"start":0,"end":len(source),"text":source}] if source else [],
            "protected_spans":[]}


class TransformTests(unittest.TestCase):
    def reject(self, req, code=None):
        with self.assertRaises(tool.RequestError) as cm:
            tool.transform(req)
        if code:
            self.assertEqual(cm.exception.code, code)

    def test_two_mappings_complete(self):
        result=tool.transform(request())
        self.assertEqual(result["text"],"یک کار")
        self.assertEqual(result["mapping_counts"],{"ي":1,"ك":2})

    def test_no_op_has_no_note(self):
        result=tool.transform(request("یک کار"))
        self.assertEqual(result["status"],"unchanged");self.assertIsNone(result["note"])

    def test_empty_text(self):
        result=tool.transform(request(""))
        self.assertEqual(result["text"],"");self.assertIsNone(result["note"])

    def test_input_object_unchanged(self):
        req=request();before=copy.deepcopy(req);tool.transform(req);self.assertEqual(req,before)

    def test_original_and_hash_retained(self):
        result=tool.transform(request())
        self.assertEqual(result["original_text"],"يك كار")
        self.assertEqual(result["source_sha256"],hashlib.sha256("يك كار".encode()).hexdigest())

    def test_missing_permission(self):
        req=request();del req["authorization"];self.reject(req)

    def test_false_permission(self):
        req=request();req["authorization"]="none";self.reject(req,"permission_required")

    def test_permission_wrong_type(self):
        req=request();req["authorization"]={};self.reject(req,"permission_required")

    def test_transcription_not_confirmed(self):
        req=request();req["confirmed_persian_transcription"]=False;self.reject(req)

    def test_truthy_not_boolean_confirmation(self):
        req=request();req["confirmed_persian_transcription"]=1;self.reject(req)

    def test_scope_not_reviewed(self):
        req=request();req["scope_reviewed"]=False;self.reject(req)

    def test_unknown_fields_rejected(self):
        req=request();req["execute"]="do nothing";self.reject(req,"unknown_request_fields")

    def test_wrong_version_rejected(self):
        req=request();req["request_version"]="2";self.reject(req)

    def test_non_object_rejected(self):
        self.reject([])

    def test_wrong_source_type(self):
        req=request();req["source"]=4;self.reject(req)

    def test_nul_rejected(self):
        self.reject(request("ي\x00ك"))

    def test_surrogate_rejected(self):
        self.reject(request("\ud800ي"),"invalid_unicode")

    def test_large_text_rejected(self):
        self.reject(request("ي"*(tool.MAX_CHARS+1)))

    def test_bad_span_text(self):
        req=request();req["eligible_spans"][0]["text"]="wrong";self.reject(req,"span_text_mismatch")

    def test_boolean_offset_rejected(self):
        req=request();req["eligible_spans"][0]["start"]=False;self.reject(req,"invalid_span_offset")

    def test_negative_offset_rejected(self):
        req=request();req["eligible_spans"][0]["start"]=-1;self.reject(req)

    def test_empty_span_rejected(self):
        req=request();req["eligible_spans"][0]={"start":0,"end":0,"text":""};self.reject(req)

    def test_byte_offsets_rejected(self):
        req=request();req["eligible_spans"][0]["end"]=len(req["source"].encode());self.reject(req)

    def test_utf16_offsets_rejected(self):
        req=request("😀يك");req["eligible_spans"][0]={"start":2,"end":4,"text":"يك"};self.reject(req)

    def test_extra_span_field_rejected(self):
        req=request();req["eligible_spans"][0]["instruction"]="ignored";self.reject(req)

    def test_duplicate_eligible_spans_rejected(self):
        req=request();req["eligible_spans"]*=2;self.reject(req,"overlapping_spans")

    def test_protected_overlap_rejected(self):
        req=request();req["protected_spans"]=copy.deepcopy(req["eligible_spans"])
        self.reject(req,"eligible_protected_overlap")

    def test_too_many_spans(self):
        req=request();req["eligible_spans"]*=tool.MAX_SPANS+1;self.reject(req)

    def test_whole_backtick_identifier_rejected(self):
        self.reject(request("`case_يك_A`"),"machine_syntax_in_eligible_span")

    def test_inside_backtick_identifier_rejected(self):
        req=request("`يك`");req["eligible_spans"]=[{"start":1,"end":3,"text":"يك"}];self.reject(req)

    def test_unbalanced_backticks_rejected(self):
        req=request("`يك");req["eligible_spans"]=[{"start":1,"end":3,"text":"يك"}]
        self.reject(req,"unbalanced_backticks")

    def test_fenced_identifier_rejected(self):
        req=request("```يك```");req["eligible_spans"]=[{"start":3,"end":5,"text":"يك"}];self.reject(req)

    def test_url_guard(self):
        self.reject(request("https://example.org/يك"))

    def test_email_guard(self):
        self.reject(request("يك@example.org"))

    def test_selected_profile_authority(self):
        req=request();req["authorization"]="explicitly-selected-enabled-profile"
        self.assertEqual(tool.transform(req)["text"],"یک کار")

    def test_audit_exact_candidate(self):
        req=request();req["candidate"]="یک کار"
        result=tool.transform(req);self.assertEqual(result["status"],"audit_pass")

    def test_failed_audit_has_no_success_note_or_text(self):
        req=request();req["candidate"]="یک‌کار";result=tool.transform(req)
        self.assertFalse(result["accepted"]);self.assertIsNone(result["note"]);self.assertIsNone(result["text"])

    def test_candidate_spacing_mutation_rejected(self):
        req=request();req["candidate"]="یک  کار";self.assertFalse(tool.transform(req)["accepted"])

    def test_candidate_digit_mutation_rejected(self):
        req=request("يك 12");req["candidate"]="یک ۱۲";self.assertFalse(tool.transform(req)["accepted"])

    def test_candidate_punctuation_mutation_rejected(self):
        req=request("يك؛");req["candidate"]="یک،";self.assertFalse(tool.transform(req)["accepted"])

    def test_candidate_word_mutation_rejected(self):
        req=request();req["candidate"]="یک بار";self.assertFalse(tool.transform(req)["accepted"])

    def test_candidate_deletion_rejected(self):
        req=request();req["candidate"]="یک";self.assertFalse(tool.transform(req)["accepted"])

    def test_incomplete_mapping_rejected(self):
        req=request();req["candidate"]="یک كار";self.assertFalse(tool.transform(req)["accepted"])

    def test_no_automatic_general_normalization(self):
        result=tool.transform(request("ي ا\u0654 ﷲ ﻙ"))
        self.assertEqual(result["text"],"ی ا\u0654 ﷲ ﻙ")

    def test_zero_eligible_preserves_all(self):
        req=request("هذا كتاب مفيد");req["eligible_spans"]=[]
        self.assertEqual(tool.transform(req)["text"],req["source"])

    def test_scope_is_not_independently_verified(self):
        # An incorrect language declaration can still cause a wrong-scope change.
        # This exposes a limitation rather than certifying Arabic safety.
        result=tool.transform(request("هذا كتاب مفيد"))
        self.assertTrue(result["scope_is_caller_assertion"])
        self.assertNotEqual(result["text"],result["original_text"])
        self.assertTrue(any("caller assertions" in x for x in result["limitations"]))

    def test_report_truncation_explicit(self):
        result=tool.transform(request("ي"*(tool.MAX_REPORTED_CHANGES+1)))
        self.assertTrue(result["actual_diff"]["truncated"])
        self.assertEqual(result["actual_diff"]["count"],tool.MAX_REPORTED_CHANGES+1)

    def test_randomized_allowed_mapping_and_stability(self):
        randomizer=random.Random(1313)
        chars=list("يكیك abc 12۱۲؛،\n\t\u200c\u200f😀ا\u0654")
        for _ in range(200):
            source="".join(randomizer.choices(chars,k=100))
            result=tool.transform(request(source))
            expected=source.replace("ي","ی").replace("ك","ک")
            self.assertEqual(result["text"],expected)
            self.assertEqual(tool.transform(request(expected))["text"],expected)
            self.assertEqual(len(source),len(expected))


class InputAndCliTests(unittest.TestCase):
    def invoke(self, data, args=None):
        return subprocess.run([sys.executable,str(SCRIPT),*(args or ["-"])],
                              input=data,capture_output=True)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(tool.RequestError):tool.decode_request(b'{"source":"x","source":"y"}')

    def test_nonfinite_json_rejected(self):
        for raw in [b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e9999}']:
            with self.assertRaises(tool.RequestError):tool.decode_request(raw)

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(tool.RequestError):tool.decode_request(b'\xff')

    def test_oversized_json_rejected(self):
        with self.assertRaises(tool.RequestError):tool.decode_request(b' '*(tool.MAX_BYTES+1))

    def test_deep_json_rejected(self):
        with self.assertRaises(tool.RequestError):tool.decode_request(b'['*2000+b']'*2000)

    def test_depth_guard_ignores_brackets_inside_strings(self):
        req=request('ي ' + '['*100 + '"\\\\' + ']'*100)
        self.assertEqual(tool.decode_request(json.dumps(req).encode()),req)

    def test_stdin_normalize(self):
        p=self.invoke(json.dumps(request(),ensure_ascii=False).encode())
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)["text"],"یک کار")

    def test_audit_failure_exit_one(self):
        req=request();req["candidate"]="wrong";p=self.invoke(json.dumps(req).encode())
        self.assertEqual(p.returncode,1);self.assertEqual(json.loads(p.stdout)["status"],"audit_fail")

    def test_invalid_request_does_not_echo_source(self):
        req=request("PRIVATE-SYNTHETIC-MARKER");req["authorization"]="none"
        p=self.invoke(json.dumps(req).encode());self.assertEqual(p.returncode,2)
        self.assertNotIn(b"PRIVATE-SYNTHETIC-MARKER",p.stdout+p.stderr)

    def test_input_file_not_modified(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"source.json";data=json.dumps(request()).encode();p.write_bytes(data)
            result=self.invoke(b"",[str(p)]);self.assertEqual(result.returncode,0)
            self.assertEqual(p.read_bytes(),data);self.assertEqual(len(list(Path(t).iterdir())),1)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"source.json";p.write_text(json.dumps(request()))
            link=Path(t)/"link.json";link.symlink_to(p)
            self.assertEqual(self.invoke(b"",[str(link)]).returncode,2)

    def test_remote_input_rejected(self):
        self.assertEqual(self.invoke(b"",["https://example.org/input.json"]).returncode,2)

    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.invoke(b"",[str(Path(t)/"missing")]).returncode,2)

    def test_help(self):
        self.assertEqual(self.invoke(b"",["--help"]).returncode,0)


class FrozenRegressionTests(unittest.TestCase):
    pass


def make_fixture_test(case):
    def check(self):
        result=tool.transform(copy.deepcopy(case["request"]))
        self.assertEqual(result["status"],case["expected_status"])
        self.assertEqual(result["accepted"],case["accepted"])
        self.assertEqual(result["text"],case["expected_text"])
        if not case["accepted"]:
            self.assertIsNone(result["note"])
        if "historical_response_sha256" in case:
            self.assertEqual(hashlib.sha256(case["historical_response"].encode()).hexdigest(),
                             case["historical_response_sha256"])
    return check


for case in FIXTURE["cases"]:
    setattr(FrozenRegressionTests, "test_"+case["id"], make_fixture_test(case))

if __name__ == "__main__":
    unittest.main(verbosity=2)
