"""Read-only cold/warm digest costs on the incident project's representative files."""
import json
import time
from pathlib import Path
from wepppy.nodb.mods.postfire_debris_flow.production import cached_digest, _digest_version
root = Path('/wc1/runs/th/thespian-cleanness')
paths = [root/'climate/wepp.cli', root/'dem/dem.tif']
paths += sorted(root.rglob('*.sqlite'))[:1]
if not paths[1].is_file():
    paths[1] = max(root.rglob('*.tif'), key=lambda p: p.stat().st_size)
results=[]
for path in paths:
    _digest_version.cache_clear()
    start=time.perf_counter(); checksum=cached_digest(path); cold=time.perf_counter()-start
    start=time.perf_counter()
    for _ in range(100):
        assert cached_digest(path)==checksum
    warm=(time.perf_counter()-start)/100
    results.append({'path':str(path),'bytes':path.stat().st_size,'cold_seconds':cold,
                    'warm_seconds_per_call':warm,'cache':str(_digest_version.cache_info())})
print(json.dumps(results,indent=2))
