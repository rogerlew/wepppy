"""Read-only identity gate for the exact native sources used by response u2."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.repo = args.repo.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    base = args.repo / 'out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4'
    reuse_path = base / 'attempt-u2/binary-reuse.json'
    reuse = json.loads(reuse_path.read_text())
    receipts = {str(reuse_path.relative_to(args.repo)): sha(reuse_path)}
    for name, expected in reuse['origin_bindings'].items():
        path = Path(name).resolve()
        assert sha(path) == expected, name
        receipts[str(path.relative_to(args.repo))] = expected
    build_path = base / 'attempt-u1/build-receipt.json'
    build = json.loads(build_path.read_text())
    src = base / 'attempt-u1/build/src'
    before = {}
    for name, expected in build['postbuild_inventory'].items():
        path = src / name
        stat = path.stat()
        actual = sha(path)
        assert actual == expected, name
        before[name] = {'sha256': actual, 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    assert sha(src / 'wepp') == reuse['binary_sha256'] == build['binary_sha256']
    relevant = ['input.for', 'tilage.for', 'scon.for', 'infile.for', 'covcal.for',
                'decomp.for', 'soil.for', 'infpar.for', 'frcfac.for', 'shears.for',
                'contin.for', 'rngint.for', 'patrib.for']
    selected = {n: before[n] for n in relevant}
    active_hits = {}
    # Fixed-form comment cards excluded; this is an index, not a Fortran parser.
    for path in sorted(src.glob('*.for')):
        for lineno, line in enumerate(path.read_text(errors='strict').splitlines(), 1):
            if line and line[0] in 'cC*!':
                continue
            lower = line.lower()
            for variable in ('rfg(', 'rfg1(', 'rfg2(', 'rokcov(', 'roki(', 'rokr('):
                if variable in lower:
                    active_hits.setdefault(variable, []).append({'file': path.name, 'line': lineno})
    for name, saved in before.items():
        path = src / name
        stat = path.stat()
        assert saved == {'sha256': sha(path), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}, name
    result = {'status': 'PASS', 'binary_sha256': reuse['binary_sha256'],
              'build_root': str(src.relative_to(args.repo)),
              'postbuild_members_verified': len(before),
              'all_verified_members_nonmutated': True, 'receipt_bindings': receipts,
              'relevant_sources': selected, 'active_reference_index': active_hits,
              'limits': 'Source identity and static consumer evidence; no new model execution or runtime branch observation.'}
    (args.out / 'source-identity.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
