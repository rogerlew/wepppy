"""Retain exact correction, build identity and validation receipts without secrets."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path('/workdir/hbp-schema2-calendar-selection-20261021')
NATIVE = Path('/workdir/wepp-forest')
PACKAGE = Path(__file__).resolve().parent
BASE = Path('/wc1/holdouts/watershed-channel-routing-closure-20261021/instrumented-source')


def receipt(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def main():
    files = ['fpm-src/hillslope_binary_pass_reader.f90', 'src/hbp_mode2_bridge.f90', 'src/wshred.for',
             'fpm-test/ps05_mode2_direct_reader_tests.f90',
             'docs/contracts/watershed-hillslope-pass-reader-contract.md',
             'docs/specs/source/hbp_mode2_bridge_spec.md']
    patches = []
    old_root = ROOT / 'pre-fix-files'
    for name in files:
        old = old_root / name
        old.parent.mkdir(parents=True, exist_ok=True)
        if (BASE / name).exists():
            old.write_bytes((BASE / name).read_bytes())
        elif name.startswith('docs/specs/'):
            old.write_bytes(b'')
        else:
            old.write_bytes(subprocess.check_output(['git', '-C', str(NATIVE), 'show', 'HEAD:' + name]))
        result = subprocess.run(['diff', '-u', '--label', 'a/' + name, '--label', 'b/' + name,
                                 str(old), str(NATIVE / name)], capture_output=True, check=False)
        assert result.returncode in [0, 1]
        patches.append(result.stdout)
    (PACKAGE / 'reader-fix.patch').write_bytes(b''.join(patches))
    source = ROOT / 'candidate-source'
    # Assert the runtime source equals reviewed source; tests/docs are outside make.
    for name in files[:3]:
        assert (source / name).read_bytes() == (NATIVE / name).read_bytes()
    manifest = {str(p.relative_to(source)): receipt(p) for folder in ['src', 'fpm-src']
                for p in sorted((source / folder).rglob('*')) if p.is_file()
                and (p.suffix.lower() in ['.f90', '.for', '.inc', '.c', '.h'] or p.name.lower().startswith('makefile'))}
    manifest_path = ROOT / 'candidate-source-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    data = {'retained_root': str(ROOT), 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_head': subprocess.check_output(['git', '-C', str(NATIVE), 'rev-parse', 'HEAD'], text=True).strip(),
            'compiler': subprocess.check_output(['/usr/bin/gfortran', '--version'], text=True).splitlines()[0],
            'build_command': "make FC=/usr/bin/gfortran LDFLAGS='-mcmodel=medium -no-pie -lz' wepp wepp_hill",
            'flags_source': str(source / 'src/makefile'), 'source_manifest': receipt(manifest_path),
            'baseline': str(BASE), 'correction': receipt(PACKAGE / 'reader-fix.patch'),
            'binaries': [receipt(source / 'src' / name) for name in ['wepp', 'wepp_hill']],
            'initial_repository_snapshots': [receipt(p) for p in sorted(ROOT.glob('*-baseline.txt'))],
            'validation_logs': [receipt(p) for p in sorted(ROOT.glob('*.log'))],
            'replay_manifests': [receipt(ROOT / mode / case / name) for mode in ['off', 'on']
                                 for case in ['single', 'upper60', 'real']
                                 for name in ['input_manifest.json', 'execution.json']],
            'diagnostics': [receipt(p) for p in sorted((ROOT / 'on').glob('*/*'))
                            if p.is_file() and (p.name.endswith('.observe.log') or p.name.startswith('channel_'))],
            'validation_receipts': [receipt(p) for p in sorted(PACKAGE.glob('*-validation.json'))],
            'release': 'local build only; no release, vendoring or deployment'}
    (PACKAGE / 'provenance.json').write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
