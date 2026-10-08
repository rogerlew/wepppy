"""Parse the retained 500-cell leap-year payload with the production parser."""
from datetime import date
import gzip
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from wepppy.climates.prism._bulk_protocol import PrismCell, parse_bulk

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
source=REPO/'docs/investigations/20261008_prism_800m_bulk/evidence'
raw=gzip.decompress((source/'scale_500.csv.gz').read_bytes())
locations=json.loads((source/'scale_locations.json').read_text())
lookup={p['name']:PrismCell(p['row'],p['col']) for p in locations}
lines=raw.decode().splitlines(keepends=True)
# Change identifiers only: leave all original numeric/date tokens untouched.
adapted=''.join((lookup[line.split(',',1)[0]].id+','+line.split(',',1)[1]) if line.split(',',1)[0] in lookup else line for line in lines).encode()
started=time.perf_counter()
frames=parse_bulk(adapted,list(lookup.values()),date(2020,1,1),date(2020,12,31))
elapsed=time.perf_counter()-started
original=pd.read_csv(io.BytesIO(raw),skiprows=10)
for name,group in original.groupby('Name'):
    np.testing.assert_array_equal(frames[lookup[name].id].to_numpy(),group.iloc[:,5:].to_numpy())
record=dict(cells=len(frames),rows=sum(len(f) for f in frames.values()),production_parse_seconds=elapsed,previous_boolean_scan_seconds=8.22777012300503,all_values_equal=True,source_sha256=hashlib.sha256(raw).hexdigest(),adaptation='Native cell identifiers replace original batch-local names only; all date/numeric tokens unchanged.',scope='Offline parser scale/parity check, not a new upstream timing or live cache freshness claim')
assert record['cells']==500 and record['rows']==183000
(HERE/'scale-parser-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(record)
