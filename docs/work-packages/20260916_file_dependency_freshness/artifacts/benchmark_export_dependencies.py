"""Read-only actual manifest dependency working set; no source/controller writes."""
import json
from pathlib import Path
from time import perf_counter, sleep
from wepppy.all_your_base.file_digest import sha256_file, _digest, _observed_at

root = Path('/wc1/runs/th/thespian-cleanness')
manifest = root / 'export/features/artifacts/a41d267b33ad4105ac0fbc5142fd36a8/manifest.json'
entries = json.loads(manifest.read_text())['dependency_snapshot']['entries']
paths = sorted({root / entry['relpath'] for entry in entries if entry['exists']})
paths = [path for path in paths if path.is_file()]
records = {'root': str(root), 'entries': len(entries), 'unique_files': len(paths),
           'bytes': sum(path.stat().st_size for path in paths),
           'paths': [str(path.relative_to(root)) for path in paths]}
_digest.cache_clear()
_observed_at.cache_clear()
started = perf_counter()
for path in paths:
    sha256_file(path)
records['cold_hash_seconds'] = perf_counter() - started
sleep(1.01)
for path in paths:
    sha256_file(path)
before = _digest.cache_info()
started = perf_counter()
for _ in range(20):
    for path in paths:
        sha256_file(path)
records['settled_set_mean_seconds'] = (perf_counter() - started) / 20
records['settled_misses'] = _digest.cache_info().misses - before.misses
print(json.dumps(records, indent=2))
assert records['settled_misses'] == 0
