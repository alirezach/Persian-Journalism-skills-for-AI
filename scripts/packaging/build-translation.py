#!/usr/bin/env python3
"""Build a translation archive with its explicitly configured lifecycle; Python 3.10+, standard library.
Trusted checkout required. No tests, model calls, installation or network access.
"""
import argparse
import hashlib
import io
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

NAME = 'humanities-translation'
PREFIX = 'skills/' + NAME + '/'
CONFIG = PREFIX + 'build-manifest.json'
MAX_FILE = 1024 * 1024
MAX_TOTAL = 4 * MAX_FILE
GENERATED = 'manifest.json'
MAPPING = {
    PREFIX + 'SKILL.md': 'SKILL.md',
    **{PREFIX + 'references/' + n + '.md': 'references/' + n + '.md'
       for n in ('terminology', 'fidelity', 'long-text', 'examples')},
    **{'standards/' + n + '.md': 'references/shared/' + n + '.md'
       for n in ('fidelity-and-uncertainty', 'privacy-and-source-protection', 'permissions-and-publication')},
    'profiles/locales/fa-IR.yaml': 'references/profiles/fa-IR.yaml',
    'profiles/house-style/default-fa.yaml': 'references/profiles/default-fa.yaml',
    'templates/translation-decisions.csv': 'templates/translation-decisions.csv',
    'LICENSE': 'LICENSE',
    PREFIX + 'package-README.md': 'README.md',
    PREFIX + 'package-NOTICES.md': 'THIRD_PARTY_NOTICES.md',
}
LINK = re.compile(r'\[[^\]\n]*\]\(([^)\n]*)\)')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    if not isinstance(value, str) or not value or any(c in value for c in '\\:%?#'):
        raise ValueError('Invalid path')
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('Invalid path characters')
    if PurePosixPath(value).is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Noncanonical path')
    return value


def read_source(root, name):
    p = root
    for part in canonical(name).split('/'):
        p = p / part
        if p.is_symlink():
            raise ValueError('Symlink source')
    if not stat.S_ISREG(p.stat().st_mode) or p.stat().st_size > MAX_FILE:
        raise ValueError('Nonregular or oversized source')
    data = p.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError('Oversized source')
    data.decode('utf-8', errors='strict')
    return data


def local_link(owner, link):
    if link.startswith(('https://', 'http://', '#')):
        return None
    path, marker, fragment = link.partition('#')
    if not path or any(c in path for c in '\\:%?') or any(c.isspace() for c in path):
        raise ValueError('Unsupported local link')
    if path.startswith('/'):
        raise ValueError('Absolute link')
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), path))
    canonical(resolved)
    return resolved, (marker + fragment if marker else '')


def check_syntax(text):
    # Only simple inline Markdown links; no HTML/reference links or title syntax.
    if re.search(r'^\s*\[[^\]]+\]:|\]\[|<(?:a|img)\b', text, re.M | re.I):
        raise ValueError('Unsupported Markdown links')
    if text.count('](') != len(LINK.findall(text)):
        raise ValueError('Unparsed Markdown link')


def prepare(root):
    root = Path(root).resolve(strict=True)
    raw = read_source(root, CONFIG)
    spec = json.loads(raw)
    if set(spec) != {'manifest_version', 'name', 'version', 'status', 'baseline_revision', 'files'}:
        raise ValueError('Invalid manifest fields')
    if spec['manifest_version'] != '1' or spec['name'] != NAME or spec['status'] not in ('planned', 'experimental'):
        raise ValueError('Unsupported package or status')
    if not isinstance(spec['version'], str) or not re.fullmatch(r'\d+\.\d+\.\d+', spec['version']):
        raise ValueError('Invalid version')
    if not isinstance(spec['baseline_revision'], str) or not re.fullmatch(r'[0-9a-f]{40}', spec['baseline_revision']):
        raise ValueError('Invalid baseline revision')
    rows = spec['files']
    if not isinstance(rows, list) or len(rows) != len(MAPPING):
        raise ValueError('Unexpected source count')
    mapping, folded = {}, set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'source', 'target', 'license'}:
            raise ValueError('Invalid file record')
        source, target = canonical(row['source']), canonical(row['target'])
        if source in mapping or target.casefold() in folded or target == GENERATED or row['license'] != 'MIT':
            raise ValueError('Duplicate path or unsupported license label')
        mapping[source] = target
        folded.add(target.casefold())
    if mapping != MAPPING:
        raise ValueError('Manifest differs from translation allowlist')
    files, records = {}, []
    total = 0
    for source, target in mapping.items():
        data = read_source(root, source)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('Package too large')
        if target == 'SKILL.md':
            text = data.decode('utf-8')
            if not text.startswith('---\n') or '\n---\n' not in text[4:]:
                raise ValueError('Missing front matter')
            front = text.split('---\n', 2)[1]
            if not re.search(r'^  status: "' + re.escape(spec['status']) + r'"$', front, re.M):
                raise ValueError('Entry status differs from configured lifecycle')
            if not re.search(r'^  version: "' + re.escape(spec['version']) + r'"$', front, re.M):
                raise ValueError('Entry version mismatch')
        rewrites = []
        if target.endswith('.md'):
            text = data.decode('utf-8')
            check_syntax(text)
            def replace(match):
                old = match.group(1)
                resolved = local_link(source, old)
                if resolved is None:
                    return match.group(0)
                ref, fragment = resolved
                if ref not in mapping:
                    raise ValueError('Source link outside package')
                new = posixpath.relpath(mapping[ref], posixpath.dirname(target) or '.') + fragment
                if new != old:
                    rewrites.append({'from': old, 'to': new})
                return match.group(0)[:match.start(1)-match.start(0)] + new + ')'
            out = LINK.sub(replace, text).encode('utf-8')
        else:
            out = data
        files[target] = out
        records.append({'source': source, 'target': target, 'license': 'MIT',
                        'source_sha256': digest(data), 'output_sha256': digest(out),
                        'link_rewrites': rewrites})
    # Resolve from each output file's own directory, including nested guides.
    for target, data in files.items():
        if target.endswith('.md'):
            for link in LINK.findall(data.decode('utf-8')):
                resolved = local_link(target, link)
                if resolved is not None and resolved[0] not in files:
                    raise ValueError('Unresolved output link')
    manifest = {'manifest_version': '1', 'name': NAME, 'version': spec['version'],
                'status': spec['status'],
                'artifact_stage': 'candidate' if spec['status'] == 'planned' else 'experimental',
                'baseline_revision': spec['baseline_revision'],
                'revision_scope': 'Baseline before this build; hashes identify actual inputs, not a claim all files came from that commit.',
                'source_config_sha256': digest(raw),
                'builder_sha256': digest(Path(__file__).read_bytes()),
                'files': sorted(records, key=lambda x: x['target']),
                'generated_files': [{'target': GENERATED, 'license': 'MIT', 'self_hash': 'not_recorded'}],
                'test_suites': 'not_run', 'model_evaluation': 'not_run', 'host_installation': 'not_run',
                'limitations': ['Trusted checkout only; not a sandbox or secret scanner.',
                                'Simple inline Markdown only; anchors and external URLs are not verified.',
                                'License labels record project provenance, not an independent legal audit.',
                                'Lifecycle is explicitly configured; ZIP creation alone does not authorize promotion or certify quality or compatibility.']}
    files[GENERATED] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_STORED) as archive:
        for target, data in sorted(files.items()):
            info = zipfile.ZipInfo(NAME + '/' + target, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buf.getvalue(), manifest


def build(root, output):
    data, manifest = prepare(root)
    output = Path(output)
    if output.suffix.lower() != '.zip':
        raise ValueError('ZIP destination required')
    for part in [output, *output.parents]:
        if part.is_symlink():
            raise ValueError('Symlink output')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(data)
    return {'name': NAME, 'version': manifest['version'], 'status': manifest['status'],
            'artifact_stage': manifest['artifact_stage'], 'build': 'completed', 'files': len(manifest['files']) + 1,
            'bytes': len(data), 'sha256': digest(data), 'test_suites': 'not_run',
            'model_evaluation': 'not_run', 'host_installation': 'not_run'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New ZIP path; existing files are not overwritten')
    args = parser.parse_args()
    try:
        print(json.dumps(build(Path(__file__).resolve().parents[2], args.output)))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'build': 'failed', 'error_type': type(exc).__name__,
                          'message': 'Check trusted sources, manifest, simple links and a new ZIP destination.'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
