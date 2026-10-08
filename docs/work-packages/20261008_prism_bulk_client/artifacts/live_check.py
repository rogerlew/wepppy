"""Run inside a Compose worker using its mounted PRISM_CACHE_DIR."""
import hashlib
import json
import os
from pathlib import Path
import time

import pandas as pd

from wepppy.climates.prism.bulk_client import PrismBulkClient, snap

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
points={'palouse':(-116.5,46.5),'sierra':(-119.5,37.7),'topanga':(-118.65872328468636,34.05536488765769)}
cell=snap(*points['palouse'])
points['palouse_alias']=(cell.center[0]+.001,cell.center[1]-.001)
client=PrismBulkClient()
start=time.monotonic()
a=client.retrieve(points,'2020-01-01','2020-12-31')
cold_seconds=time.monotonic()-start
start=time.monotonic()
b=client.retrieve(points,'2020-01-01','2020-12-31')
for name,frame in a.frames.items():
    pd.testing.assert_frame_equal(frame,b.frames[name])
    assert len(frame)==366 and pd.Timestamp('2020-02-29') in frame.index
assert a.locations['palouse']['cell']==a.locations['palouse_alias']['cell']
assert len(a.frames)==3 and all(ref['cache_hit'] for ref in b.provenance)
# The earlier recorded sample is independent source evidence, not a fabricated fixture.
prior=pd.read_csv(REPO/'docs/investigations/20261008_prism_800m_bulk/evidence/sample_2020.csv.gz',compression='gzip',skiprows=10)
for friendly in ['palouse','sierra']:
    expected=prior[prior.Name==friendly].iloc[:,5:].to_numpy()
    pd.testing.assert_frame_equal(pd.DataFrame(a.frames[a.locations[friendly]['cell']].to_numpy()),pd.DataFrame(expected),check_dtype=False)
umask=os.umask(0);os.umask(umask)
record=dict(uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),umask=oct(umask),
            configured_cache=os.environ['PRISM_CACHE_DIR'],resolved_cache=str(client.cache.root),
            cache_owner_uid=client.cache.root.stat().st_uid,cache_owner_gid=client.cache.root.stat().st_gid,
            cold_seconds=cold_seconds,warm_seconds=time.monotonic()-start,
            locations=a.locations,provenance=a.provenance,warm_provenance=b.provenance,
            cells=len(a.frames),days_per_cell=366,same_cell_alias=True,raw_dewpoint_preserved=any((f.tdmean<f.tmin).any() for f in a.frames.values()),
            cold_warm_values_equal=True,independent_prior_bulk_parity=True,
            source_hashes={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'wepppy/climates/prism').glob('*bulk*.py')},
            mountinfo=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if ' /wc1 ' in line])
(HERE/'live-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k in ['uid','gid','umask','configured_cache','cold_seconds','warm_seconds','cells','cold_warm_values_equal','independent_prior_bulk_parity']})
