#!/usr/bin/env python3
"""Opt-in two-character mapping in caller-reviewed Unicode code-point spans.

Python 3.10+, standard library only. No network, inference, file writes, general
Unicode normalization, or independent verification of permission/language.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

VERSION = "0.1.3"
MAX_BYTES = 1048576
MAX_CHARS = 100000
MAX_SPANS = 1000
MAX_REPORTED_CHANGES = 1000
MAX_JSON_DEPTH = 16
MAPPINGS = {"\u064a": "\u06cc", "\u0643": "\u06a9"}
AUTHORIZATIONS = {"explicit-task-permission", "explicitly-selected-enabled-profile"}
REQUIRED = {"request_version", "source", "authorization",
            "confirmed_persian_transcription", "scope_reviewed",
            "eligible_spans", "protected_spans"}
LIMITATIONS = [
    "Permission, language and semantic span classification are caller assertions.",
    "Automatic guards recognize only backticks and conventional URL/email syntax.",
    "Not a semantic editor, language detector, host-install test or publication authorization."
]


class RequestError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_value(value):
    if not isinstance(value, str) or len(value) > MAX_CHARS or "\x00" in value:
        raise RequestError("invalid_text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise RequestError("invalid_unicode")
    return value


def decode_request(data):
    if len(data) > MAX_BYTES:
        raise RequestError("input_too_large")
    depth = 0
    in_string = False
    escaped = False
    for byte in data:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                in_string = False
        elif byte == 34:
            in_string = True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise RequestError("json_too_deep")
        elif byte in (93, 125):
            depth -= 1

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RequestError("duplicate_json_key")
            result[key] = value
        return result

    def constant(_):
        raise RequestError("nonfinite_json_value")

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise RequestError("nonfinite_json_value")
        return result

    try:
        return json.loads(data.decode("utf-8", errors="strict"),
                          object_pairs_hook=pairs, parse_constant=constant,
                          parse_float=number)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise RequestError("invalid_json") from None


def spans(value, source):
    if not isinstance(value, list) or len(value) > MAX_SPANS:
        raise RequestError("invalid_spans")
    result = []
    for span in value:
        if not isinstance(span, dict) or set(span) != {"start", "end", "text"}:
            raise RequestError("invalid_span_fields")
        start, end = span["start"], span["end"]
        if type(start) is not int or type(end) is not int:
            raise RequestError("invalid_span_offset")
        if not 0 <= start < end <= len(source):
            raise RequestError("span_out_of_range")
        if not isinstance(span["text"], str) or source[start:end] != span["text"]:
            raise RequestError("span_text_mismatch")
        result.append((start, end))
    result.sort()
    if any(left[1] > right[0] for left, right in zip(result, result[1:])):
        raise RequestError("overlapping_spans")
    return result


def diff_record(original, actual):
    """Positional differences, not an edit-distance alignment after insertions."""
    count = 0
    records = []
    for position in range(max(len(original), len(actual))):
        before = original[position] if position < len(original) else None
        after = actual[position] if position < len(actual) else None
        if before != after:
            count += 1
            if len(records) < MAX_REPORTED_CHANGES:
                records.append({"position": position, "from": before, "to": after})
    return {"count": count, "changes": records,
            "truncated": count > len(records),
            "comparison": "Unicode-code-point-position; not edit-distance"}


def transform(request):
    if not isinstance(request, dict) or not REQUIRED <= set(request):
        raise RequestError("missing_request_fields")
    if set(request) - REQUIRED - {"candidate"}:
        raise RequestError("unknown_request_fields")
    if request["request_version"] != "1":
        raise RequestError("unsupported_request_version")
    if not isinstance(request["authorization"], str) or request["authorization"] not in AUTHORIZATIONS:
        raise RequestError("permission_required")
    if request["confirmed_persian_transcription"] is not True:
        raise RequestError("confirmed_transcription_required")
    if request["scope_reviewed"] is not True:
        raise RequestError("reviewed_scope_required")
    source = text_value(request["source"])
    eligible = spans(request["eligible_spans"], source)
    protected = spans(request["protected_spans"], source)
    mask = bytearray(len(source))
    for start, end in eligible:
        mask[start:end] = b"\x01" * (end - start)
    if any(any(mask[start:end]) for start, end in protected):
        raise RequestError("eligible_protected_overlap")
    # Deliberately conservative guards, not an exhaustive protected-text parser.
    if any(mask[i] for i, char in enumerate(source) if char == "`"):
        raise RequestError("machine_syntax_in_eligible_span")
    opening = None
    for marker in re.finditer(r"`+", source):
        if opening is None:
            opening = marker
        elif len(marker.group()) == len(opening.group()):
            if any(mask[opening.start():marker.end()]):
                raise RequestError("machine_syntax_in_eligible_span")
            opening = None
    if opening is not None:
        raise RequestError("unbalanced_backticks")
    guards = [
        r"(?:https?://|www\.)[^\s<>]+",
        r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+",
    ]
    for pattern in guards:
        for match in re.finditer(pattern, source, flags=re.DOTALL):
            if any(mask[match.start():match.end()]):
                raise RequestError("machine_syntax_in_eligible_span")
    output = "".join(MAPPINGS.get(char, char) if mask[i] else char
                     for i, char in enumerate(source))
    intended = diff_record(source, output)
    counts = {char: sum(mask[i] and c == char for i, c in enumerate(source))
              for char in MAPPINGS}
    note = None
    if intended["count"]:
        note = ("یادداشت ویرایشی: در بخش‌های مجاز رونویسی، "
                f"{counts['ي']} نویسهٔ «ي» به «ی» و {counts['ك']} نویسهٔ «ك» به «ک» تبدیل شد؛ "
                "سایر نویسه‌ها، از جمله فاصله‌ها، نشانه‌ها و عددها، عیناً حفظ شدند.")
    result = {
        "tool_version": VERSION,
        "operation": "audit" if "candidate" in request else "normalize",
        "source_sha256": digest(source),
        "expected_sha256": digest(output),
        "scope_is_caller_assertion": True,
        "limitations": list(LIMITATIONS),
        "original_text": source,
        "permitted_diff": intended,
        "mapping_counts": counts,
    }
    if "candidate" in request:
        candidate = text_value(request["candidate"])
        valid = candidate == output
        result.update({
            "status": "audit_pass" if valid else "audit_fail",
            "accepted": valid,
            "candidate_sha256": digest(candidate),
            "actual_diff": diff_record(source, candidate),
            "mismatch_from_expected": diff_record(output, candidate),
            "text": candidate if valid else None,
            "note": note if valid else None,
        })
    else:
        result.update({"status": "normalized" if intended["count"] else "unchanged",
                       "accepted": True, "text": output, "note": note,
                       "actual_diff": intended})
    return result


def read_input(name):
    if name == "-":
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        if "://" in name or name.startswith("file:"):
            raise RequestError("local_file_required")
        path = Path(name)
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise RequestError("symlink_input_rejected")
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise RequestError("invalid_input_file")
        with path.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    return decode_request(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Explicit local JSON request, or - for stdin")
    args = parser.parse_args()
    try:
        result = transform(read_input(args.input))
        # ASCII JSON keeps arbitrary valid Unicode safe on non-UTF-8 terminals.
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
        return 0 if result["accepted"] else 1
    except RequestError as error:
        print(json.dumps({"status": "invalid_request", "error_code": error.code}), file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print(json.dumps({"status": "invalid_request", "error_code": "input_error"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
