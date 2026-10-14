"""Read-only artifact probe. Run with wctl exec -T weppcloud python <path>."""
import csv
import hashlib
import json
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from wepppy.weppcloud.routes.gl_dashboard_flow_duration import _observed_status

root = Path('/wc1/runs/ti/tight-orthodontist')
paths = [root / 'observed/observed.csv', root / 'wepp/output/interchange/totalwatsed3.parquet']
hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
start = time.perf_counter()
observed = _observed_status(root)
elapsed = time.perf_counter() - start
assert observed['available'], observed
flows = sorted([float(row['flow']) * float(row['area']) / 1000 / 86400
                for row in observed['records'] if row['flow'] is not None], reverse=True)
assert hashes == {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
with tempfile.TemporaryDirectory() as tmp:
    sample = Path(tmp)
    (sample / 'observed').mkdir()
    source = sample / 'observed/observed.csv'
    with source.open('w') as out:
        writer = csv.writer(out)
        writer.writerow(['Date', 'Year', 'Month', 'Day', 'Julian', 'Streamflow (mm)'])
        day, end = date(1900, 1, 1), date(2000, 1, 1)
        while day < end:
            writer.writerow([day.isoformat(), day.year, day.month, day.day, day.timetuple().tm_yday - 1, 1.25])
            day += timedelta(days=1)
    area = sample / 'wepp/output/interchange/totalwatsed3.parquet'
    area.parent.mkdir(parents=True)
    pq.write_table(pa.table({'Area': [86400000.0]}), area)
    start = time.perf_counter()
    large = _observed_status(sample)
    large_elapsed = time.perf_counter() - start
    assert large['available']
    benchmark = {'records': len(large['records']), 'csvBytes': source.stat().st_size,
                 'jsonBytes': len(json.dumps(large)), 'seconds': large_elapsed}
print(json.dumps({'observed': observed,
                  'oracle': {'count': len(flows), 'maxFlow': flows[0], 'minFlow': flows[-1],
                             'firstProbability': 100 / (len(flows) + 1)},
                  'evidence': {'hashes': hashes, 'seconds': elapsed,
                               'jsonBytes': len(json.dumps(observed)), 'hundredYears': benchmark}}))
