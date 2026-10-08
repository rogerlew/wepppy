"""Live partial-year/calendar-boundary extraction with cache artifact readback."""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from wepppy.climates.prism.bulk_client import PrismBulkClient

HERE=Path(__file__).resolve().parent
client=PrismBulkClient()
checks=[]
for first,last in [('2019-12-31','2020-01-02'),('2026-10-01','2026-10-07')]:
    result=client.retrieve({'palouse':(-116.5,46.5)},first,last)
    frame=next(iter(result.frames.values()))
    assert frame.index.equals(pd.date_range(first,last,name='date'))
    reloaded=client.retrieve({'palouse':(-116.5,46.5)},first,last)
    pd.testing.assert_frame_equal(frame,next(iter(reloaded.frames.values())))
    assert all(ref['cache_hit'] for ref in reloaded.provenance)
    checks.append(dict(start=first,end=last,rows=len(frame),partitions=len(result.provenance),provenance=result.provenance,warm_provenance=reloaded.provenance))
repo=HERE.parents[3]
(HERE/'live-boundary-validation.json').write_text(json.dumps(dict(uid=os.getuid(),gid=os.getgid(),checks=checks,source_hashes={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'wepppy/climates/prism').glob('*bulk*.py')}),indent=2)+'\n')
print([(c['start'],c['end'],c['rows'],c['partitions']) for c in checks])
