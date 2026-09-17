"""Read-only representative multi-year input hashing; no locks or model mutation."""
import json
from pathlib import Path
from time import perf_counter
from wepppy.nodb._derived_build import file_signature

root = Path('/wc1/runs/ol/old-fluorosis')
paths = sorted((root / 'rap').glob('_rap_v3_*.tif'))
paths += sorted(root.glob('watershed/subwta.tif'))
paths += sorted(root.glob('watershed/mofe.tif'))
assert paths
measurements = []
for _ in range(2):
    started = perf_counter()
    signatures = [file_signature(path) for path in paths]
    measurements.append(perf_counter() - started)
print(json.dumps({'root': str(root), 'files': len(paths),
                  'paths': [str(path.relative_to(root)) for path in paths],
                  'bytes': sum(record[2] for record in signatures),
                  'signature_pass_seconds': measurements,
                  'hash_lock_budget_seconds': 10,
                  'within_budget': max(measurements) < 10,
                  'scope': 'main-file hash cost, no actual lock acquired; native processing excluded'}, indent=2))
