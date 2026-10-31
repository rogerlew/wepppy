"""Archive restriction provenance, 52-case flag control and all native failures."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tarfile

ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
HERE = Path(__file__).resolve().parent
DEST = Path('/wc1/runs/ro/roads-parameterization-program-20261031/restriction-boundary-v1.tar.gz')
META = ROOT / 'retention-restriction-boundary-v1'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    META.mkdir(exist_ok=False)
    evidence = ROOT / 'restriction-boundary-evidence'; evidence.mkdir(exist_ok=False)
    for name in ('restriction_provenance.py', 'restriction-provenance-v1.json',
                 'restriction-source-retention-v1.json', 'no_detected_boundary.py',
                 'analyze_no_detected_boundary.py', 'restriction-provenance-findings.md',
                 'no-detected-boundary-v1-declaration.json', 'no-detected-boundary-v1-summary.json',
                 'no-detected-boundary-v1-analysis.json', 'no-detected-boundary-v1-failures.json',
                 'candidate-ledger-v4.json', 'role_runtime_ablation.py', 'continuation.py',
                 'role_boundary_assessment.py', 'soil-hourly-archive-v1.json'):
        shutil.copy2(HERE / name, evidence / name)
    for name in ('roads-restriction-provenance-v1.log', 'roads-restriction-provenance-v2.log',
                 'roads-no-detected-declare-v1.log', 'roads-no-detected-declare-v2.log',
                 'roads-no-detected-execution-v1.log', 'roads-no-detected-analysis-v1.log'):
        shutil.copy2(Path('/tmp') / name, evidence / name)
    manifest = {}
    for directory in (ROOT / 'no-detected-boundary-v1', ROOT / 'restriction-provenance-inputs', evidence):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                assert not path.is_symlink(), path
                manifest[str(path.relative_to(ROOT))] = digest(path)
    (META / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (META / 'files.txt').write_text('\n'.join(manifest) + '\n')
    DEST.parent.mkdir(parents=True, exist_ok=True); assert not DEST.exists()
    subprocess.run(['tar', '-I', 'pigz -p 4 -1', '-cf', str(DEST), '--verbatim-files-from',
                    '-T', str(META / 'files.txt')], cwd=ROOT, check=True)
    count = size = 0
    with tarfile.open(DEST, 'r|gz') as archive:
        for member in archive:
            assert member.isfile() and member.name in manifest
            assert hashlib.file_digest(archive.extractfile(member), 'sha256').hexdigest() == manifest[member.name]
            count += 1; size += member.size
    assert count == len(manifest)
    receipt = dict(archive=str(DEST), sha256=digest(DEST), bytes=DEST.stat().st_size,
                   files=count, uncompressed_bytes=size, all_members_verified=True,
                   manifest_sha256=digest(META / 'manifest.json'))
    (META / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    shutil.copy2(META / 'receipt.json', HERE / 'restriction-boundary-archive-v1.json')
    for name in ('receipt', 'manifest'):
        shutil.copy2(META / f'{name}.json', str(DEST) + f'.{name}.json')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
