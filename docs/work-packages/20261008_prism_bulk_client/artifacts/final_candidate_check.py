"""Fresh short-interval check of the final source candidate in the real worker."""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from wepppy.climates.prism.bulk_client import PrismBulkClient

here=Path(__file__).resolve().parent
repo=here.parents[3]
client=PrismBulkClient()
points={'palouse':(-116.5,46.5),'alias':(-116.499,46.501)}
a=client.retrieve(points,'2020-01-21','2020-01-30')
b=client.retrieve(points,'2020-01-21','2020-01-30')
assert len(a.frames)==1 and len(next(iter(a.frames.values())))==10
pd.testing.assert_frame_equal(next(iter(a.frames.values())),next(iter(b.frames.values())))
assert all(p['cache_hit'] for p in b.provenance)
record=dict(uid=os.getuid(),gid=os.getgid(),configured_cache=os.environ['PRISM_CACHE_DIR'],
            first_provenance=a.provenance,warm_provenance=b.provenance,source_hashes={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'wepppy/climates/prism').glob('*bulk*.py')},identical=True,days=10,unique_cells=1)
(here/'final-candidate-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print({'first_cache_hits':sum(p['cache_hit'] for p in a.provenance),'warm_cache_hits':sum(p['cache_hit'] for p in b.provenance),'days':10,'identical':True})
