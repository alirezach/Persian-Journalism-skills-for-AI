#!/usr/bin/env python3
"""Build one self-contained experimental skill; no network, install or model calls."""
import argparse
import hashlib
import io
import json
import posixpath
import re
import stat
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

NAME = 'persian-editing-detox'
VERSION = '0.1.0'
STATUS = 'experimental'
FILES = (
    'LICENSE', 'README.md', 'SKILL.md', 'THIRD_PARTY_NOTICES.md',
    'references/acceptance-cases.md', 'references/ai-detox.md',
    'references/language-editing.md', 'references/source-decisions.md',
    'references/technical-editing.md',
)
LIMIT = 65536
TOTAL_LIMIT = 262144
MANIFEST = 'build-manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_file(root, relative):
    current = root
    for part in relative.split('/'):
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink input: ' + relative)
    if not stat.S_ISREG(current.stat().st_mode):
        raise ValueError('Not a regular file: ' + relative)
    if current.stat().st_size > LIMIT:
        raise ValueError('Oversized input: ' + relative)
    data = current.read_bytes()
    if len(data) > LIMIT or b'\x00' in data:
        raise ValueError('Invalid input size or NUL: ' + relative)
    data.decode('utf-8')
    return data


def check_links(payload):
    for name, data in payload.items():
        if not name.endswith('.md'):
            continue
        for target in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', data.decode('utf-8')):
            parsed = urlsplit(target)
            if parsed.scheme in ('https', 'http', 'mailto'):
                continue
            if parsed.scheme or parsed.netloc:
                raise ValueError('Unsupported link: ' + target)
            path = unquote(parsed.path)
            if not path:
                continue
            destination = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
            if '\\' in path or destination.startswith('/') or destination not in payload:
                raise ValueError('Missing or unsafe local link: ' + name + ' -> ' + target)


def prepare(root):
    root = Path(root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Symlink repository root')
    base = 'skills/' + NAME + '/'
    manifest_bytes = read_file(root, base + MANIFEST)
    manifest = json.loads(manifest_bytes.decode('utf-8'), object_pairs_hook=unique_object)
    expected_keys = {'schema_version', 'name', 'version', 'status', 'files'}
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise ValueError('Invalid manifest fields')
    if (type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['name'] != NAME or manifest['version'] != VERSION
            or manifest['status'] != STATUS):
        raise ValueError('Invalid package identity')
    hashes = manifest['files']
    if not isinstance(hashes, dict) or set(hashes) != set(FILES):
        raise ValueError('Manifest must contain the exact allowed files')
    payload = {}
    for name in FILES:
        expected = hashes[name]
        if not isinstance(expected, str) or re.fullmatch(r'[0-9a-f]{64}', expected) is None:
            raise ValueError('Invalid SHA-256: ' + name)
        data = read_file(root, base + name)
        if digest(data) != expected:
            raise ValueError('Hash mismatch: ' + name)
        payload[name] = data
    payload[MANIFEST] = manifest_bytes
    if sum(map(len, payload.values())) > TOTAL_LIMIT:
        raise ValueError('Package size limit exceeded')
    text = payload['SKILL.md'].decode('utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError('Missing skill frontmatter')
    front = {line.strip() for line in text.split('\n---\n', 1)[0].splitlines()}
    for required in ('name: ' + NAME, 'version: "' + VERSION + '"', 'status: ' + STATUS):
        if required not in front:
            raise ValueError('Skill metadata mismatch')
    check_links(payload)
    return payload


def build(root, output, format_name):
    if format_name not in ('standalone', 'opencode'):
        raise ValueError('Unsupported package format')
    payload = prepare(root)
    prefix = NAME + '/' if format_name == 'standalone' else '.opencode/skills/' + NAME + '/'
    members = {prefix + name: data for name, data in payload.items()}
    start = (
        '# بستهٔ ویرایش و دیتاکس فارسی\n\n'
        'نسخهٔ ۰.۱.۰، آزمایشی. [راهنما](' + prefix + 'README.md) و '
        '[دستور اصلی](' + prefix + 'SKILL.md).\n\n'
        'پیش از کپی، مقصد موجود را بررسی کنید؛ هیچ فایل یا تنظیمی را خودکار بازنویسی نکنید. '
        'این بسته نصب‌کننده ندارد. در OpenCode پوشهٔ مخفی .opencode را نیز بررسی کنید. '
        'بارگذاری و مجوزها به میزبان بستگی دارند؛ آزمون رفتاری و اجرای واقعی این مهارت انجام نشده‌اند.\n'
    )
    members['START-HERE-fa.md'] = start.encode('utf-8')
    check_links(members)
    members['PACKAGE-MANIFEST.json'] = encode_json({
        'schema_version': 1, 'name': NAME, 'version': VERSION, 'status': STATUS,
        'format': format_name,
        'files': {name: digest(data) for name, data in sorted(members.items())},
        'manifest_excludes_itself': True,
    })
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(members.items()):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = (stat.S_IFREG | 0o644) << 16
            item.compress_type = zipfile.ZIP_STORED
            archive.writestr(item, data)
    result = buffer.getvalue()
    output = Path(output)
    # Exclusive creation refuses existing files and symlinks, including dangling ones.
    with output.open('xb') as handle:
        handle.write(result)
    return {'format': format_name, 'files': len(members), 'bytes': len(result), 'sha256': digest(result)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--format', required=True, choices=('standalone', 'opencode'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.root, args.output, args.format)
    except (OSError, ValueError) as error:
        parser.exit(1, 'Build refused: ' + str(error) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
