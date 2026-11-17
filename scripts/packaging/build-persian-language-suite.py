#!/usr/bin/env python3
"""Deterministic Persian language packages. Trusted checkout; no install/network/model calls."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import zipfile

VERSIONS = {'persian-editing': '0.2.0', 'persian-ai-detox': '0.1.0', 'persian-editing-and-ai-detox': '0.2.0'}
DETOX_FILES = {'SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'} | {
    'references/' + n + '.md' for n in ('register-and-voice', 'pattern-catalog', 'academic-and-evidence-sensitive', 'structure-and-rhythm', 'workflow-and-quality', 'source-decisions', 'acceptance-cases')}
OWN_FILES = {'SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'}
MAX_TOTAL = 8 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('Duplicate JSON key')
        out[k] = v
    return out


def module(root):
    name = Path(root) / 'scripts/packaging/build-skill.py'
    if any(p.is_symlink() for p in (name, *name.parents)):
        raise ValueError('Symlink builder')
    spec = importlib.util.spec_from_file_location('canonical_editing_builder', name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def safe_read(builder, root, path):
    data = builder.read_source(root, path)
    if b'\0' in data:
        raise ValueError('NUL in text source')
    return data


def identity(data, name):
    text = data.decode('utf-8')
    front = re.match(r'^---\n([\s\S]*?)\n---\n', text)
    if not front:
        raise ValueError('Missing frontmatter')
    for key, value in [('name', name), ('version', VERSIONS[name]), ('status', 'experimental')]:
        hits = re.findall(r'^\s*' + key + r':\s*[\"\x27]?([^\"\x27\n]+?)[\"\x27]?\s*$', front[1], re.M)
        if hits != [value]:
            raise ValueError('Identity mismatch: ' + key)


def manifest(files, name, **extra):
    return {'schema_version': 1, 'name': name, 'version': VERSIONS[name], 'status': 'experimental',
            'files': {n: sha(d) for n, d in sorted(files.items())},
            'manifest_excludes_itself': True, **extra}


def prepare(root, name):
    if name not in VERSIONS:
        raise ValueError('Unknown skill')
    root = Path(root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Symlink root')
    b = module(root)
    if name == 'persian-editing':
        raw, m = b.prepare(root)
        if m['version'] != VERSIONS[name]:
            raise ValueError('Editing version mismatch')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            files = {n[len(name)+1:]: z.read(n) for n in z.namelist()}
        identity(files['SKILL.md'], name)
        return files
    base = 'skills/' + name + '/'
    config_raw = safe_read(b, root, base + 'build-manifest.json')
    config = json.loads(config_raw, object_pairs_hook=unique)
    if not isinstance(config, dict) or config.get('name') != name or config.get('version') != VERSIONS[name] or config.get('status') != 'experimental' or type(config.get('schema_version')) is not int or config['schema_version'] != 1:
        raise ValueError('Invalid configuration identity')
    if name == 'persian-ai-detox':
        if set(config) != {'schema_version', 'name', 'version', 'status', 'files'} or not isinstance(config['files'], dict) or set(config['files']) != DETOX_FILES:
            raise ValueError('Invalid detox allowlist')
        files = {}
        for n, expected in config['files'].items():
            data = safe_read(b, root, base + n)
            if not isinstance(expected, str) or sha(data) != expected:
                raise ValueError('Detox hash mismatch: ' + n)
            files[n] = data
        files['build-manifest.json'] = config_raw
        identity(files['SKILL.md'], name)
        b.link_check(files)
        files['PACKAGE-MANIFEST.json'] = encoded(manifest(files, name))
        return files
    expected_components = {k: VERSIONS[k] for k in ('persian-editing', 'persian-ai-detox')}
    expected_rewrites = {'../'+k+'/SKILL.md': 'components/'+k+'/INSTRUCTIONS.md' for k in expected_components}
    if set(config) != {'schema_version', 'name', 'version', 'status', 'components', 'files', 'entry_rewrites'} or config['components'] != expected_components or config['entry_rewrites'] != expected_rewrites or not isinstance(config['files'], list) or len(config['files']) != 4 or set(config['files']) != OWN_FILES:
        raise ValueError('Invalid combined contract')
    files = {n: safe_read(b, root, base + n) for n in config['files']}
    files['build-manifest.json'] = config_raw
    identity(files['SKILL.md'], name)
    entry = files['SKILL.md'].decode()
    for old, new in expected_rewrites.items():
        anchor = '](' + old + ')'
        if entry.count(anchor) != 1:
            raise ValueError('Missing or ambiguous component link')
        entry = entry.replace(anchor, '](' + new + ')')
    files['SKILL.md'] = entry.encode()
    components = {}
    for component in expected_components:
        payload = prepare(root, component)
        mapping = []
        for original, data in sorted(payload.items()):
            target = 'components/' + component + '/' + ('INSTRUCTIONS.md' if original == 'SKILL.md' else original)
            if target in files:
                raise ValueError('Component collision')
            files[target] = data
            mapping.append({'original': original, 'target': target, 'sha256': sha(data)})
        components[component] = {'version': VERSIONS[component], 'files': mapping, 'entry_rename_only': True}
    # Component links were checked in their own roots before embedding. Outer links resolve here.
    b.link_check({n: d for n, d in files.items() if not n.startswith('components/')} | {n: b'' for n in files if n.startswith('components/')})
    if any(n.endswith('/SKILL.md') for n in files):
        raise ValueError('Nested discoverable skill entry')
    files['PACKAGE-MANIFEST.json'] = encoded(manifest(files, name, components=components,
        component_paths='relative to each component root; original manifests retained as provenance',
        source_entry_sha256=sha(safe_read(b, root, base+'SKILL.md')), entry_rewrites=expected_rewrites))
    return files


def archive(members):
    if len(members) > 512 or sum(map(len, members.values())) > MAX_TOTAL:
        raise ValueError('Archive limit exceeded')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_STORED) as z:
        for n, d in sorted(members.items()):
            if not n or n.startswith('/') or '\\' in n or ':' in n or any(x in ('', '.', '..') for x in n.split('/')):
                raise ValueError('Unsafe archive path')
            item = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)); item.create_system = 3
            item.external_attr = 0o100644 << 16
            z.writestr(item, d)
    return buf.getvalue()


def build(root, output, skill='all', format_name='opencode'):
    if format_name not in ('standalone', 'opencode') or (skill == 'all' and format_name != 'opencode'):
        raise ValueError('Choose one skill for standalone or all for OpenCode')
    names = list(VERSIONS) if skill == 'all' else [skill]
    members = {}; packages = {}
    for name in names:
        data = prepare(root, name)
        prefix = ('.opencode/skills/' if format_name == 'opencode' else '') + name + '/'
        members.update({prefix+n: d for n, d in data.items()})
        packages[name] = {'version': VERSIONS[name], 'files': len(data)}
    if format_name == 'opencode':
        members['START-HERE-fa.md'] = ('# مجموعهٔ فارسی\n\nنام‌ها: '+ '، '.join(names) +'\n\nمهارت متناسب با درخواست را انتخاب کنید؛ سه مسیر را هم‌زمان روی یک متن اجرا نکنید. پوشهٔ .opencode ممکن است مخفی باشد. پیش از جایگزینی، نسخهٔ نصب‌شده و تغییرات محلی را بررسی کنید. نصب، آزمون مدل و اجرای میزبان انجام نشده است.\n').encode()
        members['BUNDLE-MANIFEST.json'] = encoded({'schema_version': 1, 'suite_version': '0.1.0', 'packages': packages, 'files': {n: sha(d) for n,d in sorted(members.items())}, 'manifest_excludes_itself': True})
    raw = archive(members)
    out = Path(output)
    if out.suffix.lower() != '.zip' or any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('Invalid output path')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as f:
        f.write(raw)
    return {'files': len(members), 'bytes': len(raw), 'sha256': sha(raw), 'packages': packages, 'format': format_name}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill', choices=['all', *VERSIONS], default='all')
    p.add_argument('--format', choices=['standalone', 'opencode'], default='opencode')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--root', default=Path(__file__).resolve().parents[2], type=Path)
    a = p.parse_args()
    try:
        print(json.dumps(build(a.root, a.output, a.skill, a.format), ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as e:
        p.exit(1, 'Build refused: '+str(e)+'\n')


if __name__ == '__main__':
    main()
