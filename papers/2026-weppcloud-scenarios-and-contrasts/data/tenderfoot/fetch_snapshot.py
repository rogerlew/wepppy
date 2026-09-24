"""Read-only, targeted download of Tenderfoot model artifacts from wepp1."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
REMOTE = '/geodata/wc1/runs/an/animal-misgiving'
# Enumerate only known shallow directories; never traverse hillslope run trees.
REMOTE_SCRIPT = r'''
import sys, tarfile
from pathlib import Path
root = Path('/geodata/wc1/runs/an/animal-misgiving')
files = set()
metadata = ['omni.nodb','climate.nodb','wepp.nodb','disturbed.nodb','landuse.nodb','watershed.nodb','config-manifest.json']
runs = [root] + sorted((root/'_pups/omni/scenarios').iterdir()) + sorted((root/'_pups/omni/contrasts').iterdir())
for run in runs:
    for name in metadata:
        p = run/name
        if p.is_file(): files.add(p)
    directory = run/'wepp/output/interchange'
    for pattern in ['loss_pw0*.parquet','ebe_pw0.parquet','interchange_version.json','README.md']:
        files.update(directory.glob(pattern))
    for name in ['loss_pw0.txt','loss_pw0.out']:
        p = run/'wepp/output'/name
        if p.is_file(): files.add(p)
for directory in [root/'omni', root/'omni/contrasts']:
    files.update(p for p in directory.iterdir() if p.is_file())
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for p in sorted(files): archive.add(p, arcname=str(p.relative_to(root)), recursive=False)
'''

def main():
    raw = HERE/'raw'
    raw.mkdir(exist_ok=True)
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['ssh','wepp1','python3','-'], input=REMOTE_SCRIPT.encode(), stdout=stream, check=True)
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode='r:gz') as archive:
            archive.extractall(raw, filter='data')
    records = []
    for p in sorted(raw.rglob('*')):
        if p.is_file():
            records.append({'path':str(p.relative_to(raw)), 'bytes':p.stat().st_size,
                            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    manifest = {'downloaded_utc':datetime.now(timezone.utc).isoformat(), 'host':'wepp1',
                'source_path':REMOTE,'run_url':'https://wepp.cloud/weppcloud/runs/animal-misgiving/disturbed9002_wbt/',
                'files':records}
    (HERE/'snapshot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Snapshotted {len(records)} files, {sum(r["bytes"] for r in records):,} bytes')

if __name__ == '__main__':
    main()
