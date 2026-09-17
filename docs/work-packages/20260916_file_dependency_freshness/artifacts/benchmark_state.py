"""Read-only whole-working-set source/state cost; no acceptance rewriting."""
import json
import time
from pathlib import Path
from wepppy.nodb.mods.postfire_debris_flow import production as p
root=Path('/wc1/runs/th/thespian-cleanness')
start=time.perf_counter()
first=p.get_state(root, 'disturbed9002_wbt', model='M3', reconcile=False)
cold=time.perf_counter()-start
time.sleep(1.01)  # Measure settled admission separately from the observation interval.
p.get_state(root, 'disturbed9002_wbt', model='M3', reconcile=False)
cache_before=p._digest_version.cache_info()
start=time.perf_counter()
for _ in range(100):
    p.get_state(root, 'disturbed9002_wbt', model='M3', reconcile=False)
warm=(time.perf_counter()-start)/100
cache_after=p._digest_version.cache_info()
print(json.dumps({'cold_state_seconds':cold,'warm_state_seconds':warm,
                  'cache_before':cache_before._asdict(),'cache_after':cache_after._asdict(),
                  'warm_misses':cache_after.misses-cache_before.misses,
                  'legacy_freshness':first['freshness']},indent=2))
