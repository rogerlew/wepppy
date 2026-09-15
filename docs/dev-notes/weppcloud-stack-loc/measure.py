"""Measure tracked working-tree text with ocloc, independent of language support.

Run from any directory: python3 measure.py --root ~/src --output snapshot.json
All buckets use nonblank physical lines (including comments/docstrings).
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

REPOS = ['wepppy', 'wepppyo3', 'peridot', 'weppcloud-wbt', 'rosetta',
         'wepp-forest', 'wepp-forest-revegetation', 'wepppy-win-bootstrap',
         'topaz', 'jimf-cligen532']
SOURCE = {
    'Python': 'py pyi', 'JavaScript': 'js cjs mjs jsx',
    'TypeScript': 'ts tsx', 'Rust': 'rs', 'Fortran': 'f for f90 f95 f03 f08 inc',
    'C/C++': 'c h cc cpp cxx hpp hxx', 'Go': 'go', 'R': 'r',
    'Shell': 'sh bash zsh', 'PowerShell': 'ps1 psm1 psd1',
    'Batch': 'bat cmd', 'Perl': 'pl pm', 'SQL': 'sql',
    'HTML/CSS/templates': 'html htm css scss sass less j2 jinja jinja2 mako',
    'Visual Basic': 'bas frm vbs vb', 'LaTeX support': 'sty bst',
    'Literate reports': 'rmd qmd', 'LLVM IR': 'll',
}
EXTENSIONS = {'.' + ext: lang for lang, extensions in SOURCE.items()
              for ext in extensions.split()}
SKIP_DIRS = {'target', 'node_modules', '.venv', 'venv', '__pycache__', '.git'}
DOC_EXTENSIONS = {'.md', '.rst', '.tex', '.org'}
CONFIG_EXTENSIONS = {'.json', '.jsonl', '.yaml', '.yml', '.toml', '.ini',
                     '.cfg', '.conf', '.xml', '.env', '.service', '.timer'}
BUCKETS = ['Agents', 'README', 'End-user', 'Specs/contracts/standards',
           'UI docs', 'Work packages', 'Other docs']


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def doc_bucket(path):
    name = path.name.lower()
    parts = {p.lower() for p in path.parts}
    if name in {'agents.md', 'agents.rst', 'agents.txt'}:
        return 'Agents'
    if re.match(r'^readme(?:\.|$)', name):
        return 'README'
    if re.match(r'^enduser(?:\.|$)', name):
        return 'End-user'
    if parts & {'work-packages', 'mini-work-packages'}:
        return 'Work packages'
    if 'ui-docs' in parts:
        return 'UI docs'
    if (parts & {'schemas', 'standards', 'adrs', 'contracts', 'specifications'}
            or re.search(r'specification|contract|^adr[-_]', name)):
        return 'Specs/contracts/standards'
    return 'Other docs'


def classify(path, prefix):
    name = path.name.lower()
    ext = path.suffix.lower()
    if ext in DOC_EXTENSIONS or re.match(r'^(readme|enduser|agents)(\.|$)', name):
        return 'docs', doc_bucket(path)
    if name.startswith(('makefile', 'dockerfile')) or name == 'gnumakefile':
        return 'source', 'Build recipes'
    if ext == '.cls':
        return 'source', 'Visual Basic' if b'Attribute VB_' in prefix else 'LaTeX support'
    if ext == '.sql' and b'SQL Dump' in prefix:
        return 'config', 'SQL data dump'
    if ext in EXTENSIONS:
        return 'source', EXTENSIONS[ext]
    if ext == '.ipynb':
        return 'notebook', 'Notebook code'
    if prefix.startswith(b'#!'):
        return 'source', 'Extensionless/other scripts'
    if ext in CONFIG_EXTENSIONS:
        return 'config', 'Configuration/structured text'
    return None


def measure(root):
    result = {'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
              'tracked_worktree_dirty': bool(git(root, 'diff', 'HEAD', '--name-only'))}
    files = sorted(set(git(root, 'ls-files', '-z').decode().split('\0')) - {''})
    groups = defaultdict(list)
    exclusions = Counter()
    digest = hashlib.sha256()
    for name in files:
        rel = Path(name)
        path = root / rel
        if (set(rel.parts) & SKIP_DIRS
                or name == 'docs/weppcloud-stack.md'
                or name.startswith('docs/dev-notes/weppcloud-stack-loc/')):
            exclusions['build/cache or measurement files'] += 1
            continue
        if path.is_symlink() or not path.is_file():
            exclusions['symlink or absent file'] += 1
            continue
        with path.open('rb') as stream:
            prefix = stream.read(512)
        category = classify(rel, prefix)
        if category is None:
            exclusions['data/assets/binaries/other formats'] += 1
            continue
        data = path.read_bytes()
        if b'\0' in data:
            exclusions['binary content'] += 1
            continue
        # Keep notebook code and narrative, never serialized outputs or metadata.
        if category[0] == 'notebook':
            notebook = json.loads(data)
            for cell_type, group in [('code', ('source', 'Notebook code')),
                                     ('markdown', ('docs', 'Other docs'))]:
                cells = [''.join(c.get('source', [])) for c in notebook['cells']
                         if c['cell_type'] == cell_type]
                if cells:
                    groups[group].append((name, '\n'.join(cells).encode()))
        else:
            groups[category].append((name, data))
        digest.update(name.encode() + b'\0' + data + b'\0')
    result['selected_content_sha256'] = digest.hexdigest()
    result['excluded_files'] = dict(exclusions)
    for kind in ['docs', 'source', 'config']:
        result[kind] = {}
    with tempfile.TemporaryDirectory(prefix='stack-loc-') as temporary:
        for index, ((kind, bucket), entries) in enumerate(sorted(groups.items())):
            staging = Path(temporary) / str(index)
            staging.mkdir()
            expected_nonblank = 0
            for i, (_, data) in enumerate(entries):
                # Text staging bypasses ocloc's incomplete language recognition.
                (staging / f'{i}.txt').write_bytes(data)
                expected_nonblank += sum(bool(line.strip()) for line in data.splitlines())
            raw = json.loads(subprocess.check_output(['ocloc', str(staging), '--json']))
            totals = raw['totals']
            nonblank = totals['total'] - totals['blank']
            assert totals['files'] == len(entries), (root, bucket, totals, len(entries))
            assert nonblank == expected_nonblank, (root, bucket, nonblank, expected_nonblank)
            result[kind][bucket] = {'files': len(entries), 'nonblank': nonblank,
                                    'total': totals['total'], 'blank': totals['blank']}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'tool': subprocess.check_output(['ocloc', '--version']).decode().strip(),
              'metric': 'Nonblank physical lines, including comments/docstrings',
              'repositories': {}}
    for repo in REPOS:
        result['repositories'][repo] = measure(args.root / repo)
        print(repo, 'measured', flush=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
