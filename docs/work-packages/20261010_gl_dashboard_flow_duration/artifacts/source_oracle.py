"""Read-only oracle for the retained eighty-five-synthetic integration fixture.

Run with wctl exec weppcloud python <this-file>; paths are container paths.
The actual network/translator independently established channel128/element412.
"""
import hashlib
import json
from pathlib import Path

import duckdb

base = Path('/wc1/runs/ei/eighty-five-synthetic')
output = {'hillslope': [], 'outlet': []}
for scenario in ['', '_pups/omni/scenarios/undisturbed']:
    root = base / scenario
    for key, filename, expression, channel_filter in [
        ('hillslope', 'totalwatsed3', '"Streamflow"*"Area"/1000/86400', ''),
        ('outlet', 'chanwb', '"Outflow (m^3)"/86400', ' AND "Chan_ID"=128 AND "Elmt_ID"=412'),
    ]:
        path = root / f'wepp/output/interchange/{filename}.parquet'
        count, minimum, maximum = duckdb.sql(f'''
            SELECT count(*), min({expression}), max({expression})
            FROM read_parquet('{path}') WHERE year >= 1982 {channel_filter}
        ''').fetchone()
        output[key].append({'scenario': scenario, 'count': count, 'min': minimum,
                            'max': maximum, 'source': str(path),
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
artifact = Path('/workdir/wepppy/docs/work-packages/20261010_gl_dashboard_flow_duration/artifacts/source_oracle.json')
artifact.write_text(json.dumps(output, indent=2) + '\n')
print('Wrote direct-source oracle for four owned daily datasets')
