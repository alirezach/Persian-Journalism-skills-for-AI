#!/usr/bin/env python3
"""Build only the allowlisted Persian editing package. Python 3.10+, stdlib only.
Trusted checkout/configuration required; not a secret scanner or host validator.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

CONFIG = 'skills/persian-editing/build-manifest.json'
MAX_FILE = 1024 * 1024
MAX_TOTAL = 4 * MAX_FILE
HELPER = 'scripts/editing/normalize_transcribed_fa.py'
HELPER_TARGET = 'scripts/normalize_transcribed_fa.py'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Invalid relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('Non-canonical relative path')
    return p


def read_source(root, name):
    p = root
    for part in relative(name).parts:
        p = p / part
        if p.is_symlink():
            raise ValueError('Symlink sources are not supported')
    if not p.is_file() or p.stat().st_size > MAX_FILE:
        raise ValueError('Missing, nonregular or oversized source')
    data = p.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError('Oversized source')
    data.decode('utf-8', errors='strict')
    return data


def link_check(files):
    # Supported syntax is deliberately small: inline Markdown links without
    # spaces/parentheses in targets. Not a general Markdown or HTML validator.
    for name, data in files.items():
        if not name.endswith('.md'):
            continue
        text = data.decode('utf-8')
        if re.search(r'^\s*\[[^\]]+\]:|\]\[|<(?:a|img)\b', text, re.M | re.I):
            raise ValueError('Unsupported link syntax')
        for target in re.findall(r'\[[^\]]*\]\(([^)\n]*)\)', text):
            if target.startswith(('https://', 'http://', '#')):
                continue
            target = target.split('#', 1)[0]
            relative(target)
            # Agent Skills resource paths are relative to the skill root.
            if target not in files:
                raise ValueError('Missing package-local resource')


def prepare(root):
    root = Path(root).resolve(strict=True)
    raw = read_source(root, CONFIG)
    spec = json.loads(raw)
    if set(spec) != {'manifest_version','name','version','files','entry_rewrites'}:
        raise ValueError('Invalid manifest fields')
    if spec['manifest_version'] != '1' or spec['name'] != 'persian-editing':
        raise ValueError('Unsupported package')
    if not re.fullmatch(r'\d+\.\d+\.\d+', spec['version']):
        raise ValueError('Invalid package version')
    rows = spec['files']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise ValueError('Invalid file count')
    files, records, sources, folded = {}, [], set(), set()
    total = 0
    for row in rows:
        if not isinstance(row,dict) or set(row) != {'source','target'}:
            raise ValueError('Invalid mapping')
        source, target = row['source'], row['target']
        relative(source); relative(target)
        if target == 'PACKAGE-MANIFEST.json' or target.casefold() in folded or source in sources:
            raise ValueError('Duplicate or reserved path')
        if not (source.startswith(('skills/persian-editing/','standards/','profiles/locales/','profiles/house-style/')) or source in ('LICENSE','THIRD_PARTY_NOTICES.md',HELPER)):
            raise ValueError('Source outside supported public areas')
        if not (source.endswith(('.md','.yaml')) or source in ('LICENSE',HELPER)):
            raise ValueError('Unsupported source type')
        if source == HELPER and target != HELPER_TARGET:
            raise ValueError('Unexpected helper destination')
        if target == HELPER_TARGET and source != HELPER:
            raise ValueError('Unexpected helper source')
        data = read_source(root,source)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('Package input too large')
        files[target] = data; sources.add(source); folded.add(target.casefold())
        records.append({'source':source,'target':target,'source_sha256':digest(data)})
    if not {'SKILL.md','LICENSE','THIRD_PARTY_NOTICES.md'} <= files.keys():
        raise ValueError('Missing entry or notices')
    rewrites = spec['entry_rewrites']
    if not isinstance(rewrites,dict):
        raise ValueError('Invalid rewrites')
    entry = files['SKILL.md'].decode('utf-8')
    for old, new in rewrites.items():
        if not isinstance(old,str) or not old.startswith('../../') or new not in files:
            raise ValueError('Invalid resource rewrite')
        mapped = [(x['source'],x['target']) for x in rows]
        if (old[6:],new) not in mapped:
            raise ValueError('Rewrite does not match mapping')
        anchor = ']('+old+')'
        if entry.count(anchor) != 1:
            raise ValueError('Rewrite anchor missing or ambiguous')
        entry = entry.replace(anchor, ']('+new+')')
    files['SKILL.md'] = entry.encode('utf-8')
    link_check(files)
    for item in records:
        item['output_sha256'] = digest(files[item['target']])
    manifest = {'manifest_version':'1','name':spec['name'],'version':spec['version'],
                'source_config_sha256':digest(raw),
                'builder_sha256':digest(Path(__file__).read_bytes()),
                'files':sorted(records,key=lambda x:x['target']),
                'limitations':['No host installation or model evaluation implied',
                                'Hashes identify content, not trust or publication authority']}
    files['PACKAGE-MANIFEST.json'] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo('persian-editing/'+name, (1980,1,1,0,0,0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info,data)
    return buf.getvalue(), manifest


def build(root, output):
    data, manifest = prepare(root)
    output = Path(output)
    if output.suffix.lower() != '.zip':
        raise ValueError('Output must be a ZIP path')
    # Reject symlink destination components. This is not a race-proof sandbox.
    for part in [output, *output.parents]:
        if part.is_symlink():
            raise ValueError('Symlink outputs are not supported')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:  # never replace existing output
        stream.write(data)
    return {'status':'built','name':manifest['name'],'version':manifest['version'],
            'files':len(manifest['files'])+1,'bytes':len(data),'sha256':digest(data),
            'model_evaluation':'not_run','host_compatibility':'not_tested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='New .zip file; existing outputs are never overwritten')
    args = parser.parse_args()
    try:
        report = build(Path(__file__).resolve().parents[2],args.output)
        print(json.dumps(report))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'status':'build_error','error_type':type(exc).__name__,
                          'message':'Check the manifest, UTF-8 sources, resource links and a new writable ZIP destination.'}),file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
