"""Read-only pre-repair snapshot and canonical archive content verification."""
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RUNS = 'ventilated-gag equestrian-bonheur tactful-aging incorporate-cerebrum choice-feminist neoliberal-dictate acetic-surprise uncrowned-bolt'.split()
run = sys.argv[1]
assert run in RUNS
root = Path('/wc1/runs') / run[:2] / run

def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()

if len(sys.argv) == 2:
    paths = set()
    for pattern in ('*.nodb', '*.log', 'landuse/*', 'soils/*', 'disturbed/*', 'wepp/runs/*',
                    'wepp/output/interchange/*', 'watershed/hillslopes.parquet'):
        paths.update(p for p in root.glob(pattern) if p.is_file())
    manifest = {}
    for p in sorted(paths):
        with p.open('rb') as stream:
            sha = digest(stream)
        manifest[str(p.relative_to(root))] = {'sha256': sha, 'size': p.stat().st_size,
                                           'mtime': p.stat().st_mtime}
    states = {name: json.loads((root / (name + '.nodb')).read_text())['py/state']
              for name in ('landuse', 'soils', 'wepp', 'disturbed')}
    print(json.dumps({'runid': run, 'captured_at': datetime.now(timezone.utc).isoformat(),
                      'states': states, 'manifest': manifest}, indent=2))
else:
    snapshot = json.loads(Path(sys.argv[2]).read_text())
    archive = root / 'archives' / sys.argv[3]
    assert archive.parent == root / 'archives' and archive.suffix == '.zip'
    checked = 0
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
        pre_repair_public_marker = 'PUBLIC' in names
        for relative, entry in snapshot['manifest'].items():
            # Archive operations update their own logs/receipt; scientific files
            # and state must still match the snapshot taken before the rebuild.
            if relative.endswith('.log'):
                continue
            assert relative in names, relative
            with z.open(relative) as stream:
                assert digest(stream) == entry['sha256'], relative
            checked += 1
    with archive.open('rb') as stream:
        sha = digest(stream)
    print(json.dumps({'runid': run, 'archive': str(archive), 'sha256': sha,
                      'verified_members': checked, 'size': archive.stat().st_size,
                      'pre_repair_public_marker': pre_repair_public_marker,
                      'current_public_marker': (root / 'PUBLIC').exists()}))
