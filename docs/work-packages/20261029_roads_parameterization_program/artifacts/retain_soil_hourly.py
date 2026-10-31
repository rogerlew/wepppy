"""Archive new soil/hourly executions and hash-verified four-cell readback."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tarfile

ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
HERE = Path(__file__).resolve().parent
DEST = Path('/wc1/runs/ro/roads-parameterization-program-20261031/soil-hourly-interaction-v1.tar.gz')
META = ROOT / 'retention-soil-hourly-v1'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    META.mkdir(exist_ok=False)
    evidence = ROOT / 'soil-hourly-evidence'; evidence.mkdir(exist_ok=False)
    for name in ('soil_hourly_interaction.py', 'analyze_soil_hourly.py',
                 'soil-hourly-interaction-v1-declaration.json', 'soil-hourly-interaction-v1-summary.json',
                 'soil-hourly-interaction-v1-analysis.json', 'soil-hourly-interaction-findings.md',
                 'plot_soil_hourly.py', 'soil-hourly-interaction-v1.png',
                 'soil-hourly-boundary-context-v1.json', 'candidate-ledger-v3.json',
                 'role_runtime_ablation.py', 'continuation.py', 'role_boundary_assessment.py',
                 'role-runtime-archive-v1.json', 'role-attribution-archive-v1.json'):
        shutil.copy2(HERE / name, evidence / name)
    for name in ('roads-soil-hourly-declare-v1.log', 'roads-soil-hourly-execution-v1.log', 'roads-soil-hourly-analysis-v1.log'):
        shutil.copy2(Path('/tmp') / name, evidence / name)
    manifest = {}
    for directory in (ROOT / 'soil-hourly-interaction-v1', evidence):
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
    shutil.copy2(META / 'receipt.json', HERE / 'soil-hourly-archive-v1.json')
    for name in ('receipt', 'manifest'):
        shutil.copy2(META / f'{name}.json', str(DEST) + f'.{name}.json')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
