"""Read-only executable and large-file performance with settled cache admission."""
import json
from pathlib import Path
from time import perf_counter, sleep
from wepppy.all_your_base.file_digest import sha256_file, _digest, _observed_at

records = []
for path in [Path('/workdir/wepppy/wepp_runner/bin/wepp_260803'),
             Path('/wc1/runs/th/thespian-cleanness/dem/dem.tif'),
             Path('/wc1/runs/th/thespian-cleanness/export/features/artifacts/a41d267b33ad4105ac0fbc5142fd36a8/features_export.gdb.zip')]:
    _digest.cache_clear()
    _observed_at.cache_clear()
    started = perf_counter()
    sha256_file(path)
    cold = perf_counter() - started
    sleep(1.01)
    sha256_file(path)
    before = _digest.cache_info()
    started = perf_counter()
    for _ in range(100):
        sha256_file(path)
    mean = (perf_counter() - started) / 100
    after = _digest.cache_info()
    records.append({'path': str(path), 'bytes': path.stat().st_size,
                    'cold_seconds': cold, 'settled_mean_seconds': mean,
                    'settled_misses': after.misses - before.misses})
print(json.dumps(records, indent=2))
assert all(record['settled_mean_seconds'] < .001 and record['settled_misses'] == 0 for record in records)
