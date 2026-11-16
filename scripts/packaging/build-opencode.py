#!/usr/bin/env python3
"""Build an OpenCode layout, never install or invoke OpenCode.
Python 3.10+, stdlib. Existing trusted repository builders remain canonical.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

CONFIG = "adapters/opencode/bundle.json"
NAMES = (
    "persian-editing", "humanities-translation", "source-verification",
    "fact-checking", "research-synthesis", "data-analysis",
    "data-visualization", "data-journalism",
)
BUILDERS = {
    name: "scripts/packaging/" + (
        "build-skill.py" if name == "persian-editing" else
        "build-translation.py" if name == "humanities-translation" else
        "build-candidates.py"
    ) for name in NAMES
}
MAX_FILE = 1024 * 1024
MAX_PACKAGE = 8 * MAX_FILE
MAX_TOTAL = 32 * MAX_FILE
MAX_FILES = 512
ROOT = ".opencode/skills"
MANIFEST = "BUNDLE-MANIFEST.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    if not isinstance(value, str) or not value or any(c in value for c in "\\:%?#"):
        raise ValueError("Invalid relative path")
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Invalid path characters")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(p in ("", ".", "..") for p in parts):
        raise ValueError("Noncanonical path")
    for part in parts:
        if part.endswith(".") or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part):
            raise ValueError("Nonportable path component")
    return value


def read_source(root, relative):
    p = root
    for part in canonical(relative).split("/"):
        p = p / part
        if p.is_symlink():
            raise ValueError("Symlink source")
    if not stat.S_ISREG(p.stat().st_mode) or p.stat().st_size > MAX_FILE:
        raise ValueError("Nonregular or oversized source")
    data = p.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError("Oversized source")
    data.decode("utf-8")
    return data


def configuration(root):
    raw = read_source(root, CONFIG)
    cfg = json.loads(raw)
    if set(cfg) != {"schema_version", "bundle_version", "host", "skill_root", "skills"}:
        raise ValueError("Unexpected bundle configuration")
    if cfg["schema_version"] != "1" or cfg["host"] != "opencode" or cfg["skill_root"] != ROOT:
        raise ValueError("Unsupported bundle target")
    if not isinstance(cfg["bundle_version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", cfg["bundle_version"]):
        raise ValueError("Invalid bundle version")
    rows = cfg["skills"]
    if not isinstance(rows, list) or len(rows) != len(NAMES):
        raise ValueError("Unexpected skill inventory")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "version", "status"}:
            raise ValueError("Invalid skill record")
        if not isinstance(row["name"], str) or row["name"] not in NAMES or row["name"] in seen:
            raise ValueError("Unknown or duplicate skill")
        if not isinstance(row["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", row["version"]):
            raise ValueError("Invalid skill version")
        if row["status"] not in ("planned", "experimental"):
            raise ValueError("Lifecycle promotion is outside this adapter")
        seen.add(row["name"])
    return raw, cfg


def run_builder(root, name):
    # Fixed local Python modules from a trusted checkout, not user plugins.
    # Importing this code is not a security or sandbox boundary.
    path = root / BUILDERS[name]
    spec = importlib.util.spec_from_file_location("_pjai_" + name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        if name in ("persian-editing", "humanities-translation"):
            data, _ = module.prepare(root)
        else:
            data, _ = module.prepare(root, name)
        return data
    finally:
        sys.dont_write_bytecode = previous


def inspect_package(data, row):
    if not isinstance(data, bytes) or len(data) > MAX_PACKAGE:
        raise ValueError("Oversized or invalid package")
    files, folded, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if not 1 <= len(infos) <= MAX_FILES:
            raise ValueError("Invalid package entry count")
        for info in infos:
            full = canonical(info.filename)
            prefix = row["name"] + "/"
            if not full.startswith(prefix) or info.is_dir():
                raise ValueError("Unexpected package root or directory entry")
            target = canonical(full[len(prefix):])
            mode = info.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG) or info.flag_bits & 1:
                raise ValueError("Nonregular or encrypted entry")
            if target.casefold() in folded or info.file_size > MAX_FILE:
                raise ValueError("Duplicate or oversized entry")
            total += info.file_size
            if total > MAX_PACKAGE:
                raise ValueError("Package expansion limit")
            content = archive.read(info)
            content.decode("utf-8")
            files[target] = content
            folded.add(target.casefold())
    for target in files:
        for parent in PurePosixPath(target).parents:
            if str(parent).casefold() in folded:
                raise ValueError("File/directory collision")
    entry = files.get("SKILL.md", b"").decode("utf-8")
    front = re.match(r"\A---\n(.*?)\n---(?:\n|$)", entry, re.S)
    if front is None:
        raise ValueError("Missing skill frontmatter")
    for key, value, indent in (("name", row["name"], ""), ("version", row["version"], "  "), ("status", row["status"], "  ")):
        # Repository's bounded format, not a general YAML parser.
        values = re.findall(r"^" + indent + key + r": (?:\"([^\"\n]+)\"|([^\s\"\n]+))$", front[1], re.M)
        if len(values) != 1 or (values[0][0] or values[0][1]) != value:
            raise ValueError("Skill metadata differs from bundle configuration")
    if len(re.findall(r"^description: .+\S$", front[1], re.M)) != 1:
        raise ValueError("Missing discoverable description")
    manifest_name = "PACKAGE-MANIFEST.json" if row["name"] == "persian-editing" else "manifest.json"
    manifest = json.loads(files[manifest_name])
    if not isinstance(manifest, dict) or manifest.get("name") != row["name"] or manifest.get("version") != row["version"]:
        raise ValueError("Package manifest identity mismatch")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Invalid package manifest file list")
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("output_sha256"), str):
            raise ValueError("Invalid package manifest record")
        canonical(record.get("target"))
        if not re.fullmatch(r"[0-9a-f]{64}", record["output_sha256"]):
            raise ValueError("Invalid package output hash")
    targets = [record["target"] for record in records]
    if len(set(targets)) != len(targets) or set(files) != set(targets) | {manifest_name}:
        raise ValueError("Package manifest inventory mismatch")
    if not {"SKILL.md", "LICENSE"} <= set(files):
        raise ValueError("Missing skill entry or license")
    for record in records:
        if digest(files[record["target"]]) != record["output_sha256"]:
            raise ValueError("Package output hash mismatch")
    return files


def start_here(cfg, selected):
    names = "، ".join(selected)
    return (
        "# بستهٔ پروژه‌ای OpenCode\n\n"
        f"نسخهٔ بسته: {cfg['bundle_version']}\n\n"
        f"مهارت‌های انتخاب‌شده: {names}\n\n"
        "این آرشیو چیدمان فایل‌های مهارت را آماده می‌کند؛ نصب یا اجرای OpenCode نیست.\n\n"
        "۱. آرشیو را ابتدا در پوشهٔ موقت استخراج و BUNDLE-MANIFEST.json را بررسی کنید.\n"
        "۲. پوشه‌های مهارت زیر .opencode/skills را به همان مسیر در پروژهٔ کاری منتقل کنید. "
        "اگر پوشهٔ هم‌نام وجود دارد، توقف کنید؛ ابتدا نسخهٔ قبلی را جدا نگه دارید و تغییرها را بررسی کنید.\n"
        "۳. فایل SKILL.md باید مستقیماً در پوشهٔ هر مهارت باشد. پوشهٔ مخفی .opencode را از قلم نیندازید.\n"
        "۴. در OpenCode مهارت را با @ و شناسهٔ آن صریح فراخوانی کنید. "
        "ابتدا فقط خواندن یک مرجع را بخواهید و رد اجرای میزبان را بررسی کنید.\n\n"
        "تنظیمات، AGENTS.md، مدل، کلید API و permission کاربر با این بسته تغییر نمی‌کنند. "
        "منع نوشتن، اجرای shell و انتقال بیرونی را در میزبان جدا اعمال کنید؛ متن درخواست مرز امنیتی نیست. "
        "مدل ابری ممکن است دادهٔ خوانده‌شده را دریافت کند حتی اگر فایل مهارت محلی باشد.\n\n"
        "وضعیت planned/experimental حفظ شده است؛ OpenCode الزاماً این برچسب‌ها را مانع فعال‌سازی نمی‌داند. "
        "بستهٔ جدید ممکن است منابع مشترک اصلاح‌شده داشته باشد؛ هش آن جایگزین شواهد بسته‌های تاریخی نیست. "
        "هیچ اجرای مدل، نصب میزبان، پذیرش رفتاری یا ارتقای وضعیت با ساخت این آرشیو انجام نمی‌شود.\n\n"
        "بازگشت نسخه: پوشه‌های قبلی را با انتخاب صریح و پس از پشتیبان‌گیری برگردانید؛ "
        "حذف این فایل‌ها سوابق گفتگو یا دادهٔ ارسال‌شده به سرویس مدل را حذف نمی‌کند.\n\n"
        "راهنمای رسمی: https://opencode.ai/docs/skills/\n"
    ).encode("utf-8")


def prepare(root, selected=None):
    root = Path(root).resolve(strict=True)
    raw, cfg = configuration(root)
    chosen = list(NAMES) if selected is None else list(selected)
    if not chosen or len(set(chosen)) != len(chosen) or any(n not in NAMES for n in chosen):
        raise ValueError("Unknown, empty or duplicate selection")
    chosen.sort()
    rows = {row["name"]: row for row in cfg["skills"]}
    files, packages, builders = {}, [], {}
    for name in chosen:
        builder = BUILDERS[name]
        builders[builder] = digest(read_source(root, builder))
        data = run_builder(root, name)
        contents = inspect_package(data, rows[name])
        for target, content in contents.items():
            files[ROOT + "/" + name + "/" + target] = content
        packages.append({**rows[name], "package_sha256": digest(data),
                         "files": len(contents), "bytes": len(data)})
    files["START-HERE-fa.md"] = start_here(cfg, chosen)
    if len(files) + 1 > MAX_FILES or sum(map(len, files.values())) > MAX_TOTAL:
        raise ValueError("Bundle limit exceeded")
    manifest = {
        "schema_version": "1", "bundle_version": cfg["bundle_version"],
        "target": ROOT, "config_sha256": digest(raw),
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "package_builders": builders, "packages": packages,
        "files": [{"path": name, "bytes": len(data), "sha256": digest(data)}
                  for name, data in sorted(files.items())],
        "generated_manifest": {"path": MANIFEST, "self_hash": "not_recorded"},
        "host_installation": "not_run", "host_execution": "not_run",
        "behavioral_evaluation": "not_run", "lifecycle_promoted": False,
        "limitations": [
            "Trusted checkout and local builder code required; not a sandbox or secret scanner.",
            "No installer, overwrite, credentials, AGENTS/config mutation, network or OpenCode invocation.",
            "Package-local checks inherit each canonical builder's documented link-resolution rules.",
            "No external URL, fragment, host permission, model-quality or cross-platform certification.",
            "Source/output hashes identify these inputs; historical archive evidence is not inherited.",
        ],
    }
    files[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    return buffer.getvalue(), manifest


def build(root, output, selected=None):
    output = Path(output)
    if output.suffix.lower() != ".zip":
        raise ValueError("ZIP destination required")
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Symlink output")
    if output.exists():
        raise ValueError("Output already exists")
    data, manifest = prepare(root, selected)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)
    return {"build": "completed", "bundle_version": manifest["bundle_version"],
            "skills": len(manifest["packages"]), "files": len(manifest["files"]) + 1,
            "bytes": len(data), "sha256": digest(data),
            "host_installation": "not_run", "host_execution": "not_run",
            "behavioral_evaluation": "not_run"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New ZIP path; never overwritten")
    parser.add_argument("--skills", nargs="+", choices=NAMES, help="Selected skills; default all eight")
    args = parser.parse_args()
    try:
        print(json.dumps(build(Path(__file__).resolve().parents[2], args.output, args.skills)))
        return 0
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        print(json.dumps({"build": "failed", "error_type": type(exc).__name__,
                          "message": "Check trusted inputs, selection, package metadata and a new ZIP destination."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
