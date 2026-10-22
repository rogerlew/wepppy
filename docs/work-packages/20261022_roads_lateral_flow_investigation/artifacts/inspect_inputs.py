"""Read-only inventory of the synced incident inputs; emits JSON to stdout."""
import hashlib
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq

root = Path(sys.argv[1] if len(sys.argv) > 1 else '/wc1/runs/cl/clogging-starch')
result = {'run_root': str(root), 'scopes': {}}
for scope, relative in [('baseline', 'wepp/output'), ('roads', 'wepp/roads/output')]:
    files = {}
    for name in ['totalwatsed3.parquet', 'H.wat.parquet', 'H.pass.parquet']:
        path = root / relative / 'interchange' / name
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        data = pq.read_table(path).to_pandas()
        item = {'path': str(path.relative_to(root)), 'sha256': digest.hexdigest(), 'rows': len(data)}
        if 'wepp_id' in data:
            item['wepp_ids'] = sorted(int(v) for v in data.wepp_id.unique())
        for column in ['Area', 'latqcc', 'Lateral Flow']:
            if column in data:
                item[column] = {'min': float(data[column].min()), 'max': float(data[column].max()), 'nulls': int(data[column].isna().sum())}
        if name == 'totalwatsed3.parquet':
            item['annual_sums_mm'] = data.groupby('year')[['Runoff', 'Baseflow', 'Lateral Flow']].sum().reset_index().to_dict('records')
        files[name] = item
    result['scopes'][scope] = files
print(json.dumps(result, indent=2))
