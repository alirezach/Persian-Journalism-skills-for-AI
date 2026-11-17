#!/usr/bin/env python3
"""Compatibility build command: emits persian-editing-and-ai-detox, never the retired ID."""
import argparse
import importlib.util
import json
from pathlib import Path


def builder():
    path = Path(__file__).with_name('build-persian-language-suite.py')
    spec = importlib.util.spec_from_file_location('language_suite_compat', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def build(root, output, format_name):
    return builder().build(root, output, 'persian-editing-and-ai-detox', format_name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--format', choices=['standalone', 'opencode'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(build(a.root, a.output, a.format), ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as e:
        p.exit(1, 'Build refused: '+str(e)+'\n')


if __name__ == '__main__':
    main()
