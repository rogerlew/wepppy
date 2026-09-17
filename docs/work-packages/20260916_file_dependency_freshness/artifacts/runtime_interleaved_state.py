"""Read-only two-project state/cache observation under the service identity."""
import json
from pathlib import Path
import statistics
import time

from wepppy.nodb.mods.postfire_debris_flow import production as p

roots = [Path('/wc1/runs/qa/qa-freshness-runtime-7e24c8d1'),
         Path('/wc1/batch/qa-omni-native-20260917-a61f3e/runs/qa-omni-native-20260917-a61f3e-grizzly')]
rows = []
for root in roots:
    started = time.perf_counter()
    state = p.get_state(root, 'config', model='M3', frequency='cli', reconcile=False)
    rows.append({'root': str(root), 'first_seconds': time.perf_counter()-started,
                 'freshness': state['freshness'], 'warm_seconds': []})
time.sleep(1.1)
for root in roots:
    p.get_state(root, 'config', model='M3', frequency='cli', reconcile=False)
before = p._digest_version.cache_info()
original = p._digest_version.__wrapped__
uncached = []


def observed(path, version, **kwargs):
    uncached.append({'path': str(path), 'size': version[2]})
    return original(path, version, **kwargs)


p._digest_version.__wrapped__ = observed
try:
    for _ in range(30):
        for root, row in zip(roots, rows):
            started = time.perf_counter()
            p.get_state(root, 'config', model='M3', frequency='cli', reconcile=False)
            row['warm_seconds'].append(time.perf_counter()-started)
finally:
    p._digest_version.__wrapped__ = original
after = p._digest_version.cache_info()
for row in rows:
    row['warm_mean_seconds'] = statistics.mean(row['warm_seconds'])
result = {'projects': rows, 'cache_before': before._asdict(), 'cache_after': after._asdict(),
          'warm_cache_misses': after.misses-before.misses, 'warm_uncached_payloads': uncached,
          'scope': 'Same geography, independent ordinary copies on /wc1 NFS, one service process; no cross-host coherence claim.'}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
assert after.misses == before.misses and not uncached, result
print(json.dumps(result, indent=2))
