"""Read exact generated inputs, model output values, reports and receiver bytes."""
import hashlib
import json
from pathlib import Path
import time
import pyarrow.parquet as pq
import redis
from wepppy.rq.webhook_tracking import WebhookStore
from wepppy.rq.webhook_dispatcher import inspect

root = Path('/acceptance/runs')
source = Path('/evidence/workflow_v6_probe.json')
evidence = json.loads(source.read_text())
store = WebhookStore(redis.Redis(host='redis', db=9), 'disposable-workflow-acceptance')
readback = {'comparisons': {}, 'delivery': {}}
base = root / 'ready-baseline'
for name in ('ready-healthy', 'ready-failing'):
    result = evidence[name]
    files = evidence['ready-baseline']['artifacts']
    comparison = {'exact_bytes': [], 'path_normalized_logs': [], 'parquet_values': [], 'mismatches': []}
    for relative in files:
        left, right = base / relative, root / name / relative
        if not right.exists():
            comparison['mismatches'].append(relative)
            continue
        if left.read_bytes() == right.read_bytes():
            comparison['exact_bytes'].append(relative)
        elif relative.endswith('.parquet'):
            a, b = pq.read_table(left), pq.read_table(right)
            # Physical row-group/compression/metadata layout is not model data.
            # Compare typed schema and exact row multisets, retaining duplicates.
            rows = lambda table: sorted(json.dumps(row, sort_keys=True, default=str) for row in table.to_pylist())
            if a.schema.equals(b.schema, check_metadata=True) and rows(a) == rows(b):
                comparison['parquet_values'].append({'path': relative, 'rows': a.num_rows,
                    'columns': a.column_names, 'values_sha256': hashlib.sha256('\n'.join(rows(a)).encode()).hexdigest()})
            else:
                comparison['mismatches'].append(relative)
        elif relative.endswith('.err') and left.read_text().replace(str(base), '<RUN>') == right.read_text().replace(str(root/name), '<RUN>'):
            comparison['path_normalized_logs'].append(relative)
        else:
            comparison['mismatches'].append(relative)
    comparison['fresh_files'] = len(result['fresh_artifacts'])
    readback['comparisons'][name] = comparison
    identifier = result['response']['job_id']
    for _ in range(400):
        receipt = inspect(store, identifier)
        if receipt['state'] in {'delivered', 'exhausted', 'outcome_unavailable'}:
            break
        time.sleep(.5)
    receipt = inspect(store, identifier)
    stored = store.read(identifier)
    receiver_path = Path('/evidence/workflow_receiver.jsonl')
    records = [json.loads(line) for line in receiver_path.read_text().splitlines()] if receiver_path.exists() else []
    records = [r for r in records if json.loads(r['body']).get('job_id') == identifier]
    readback['delivery'][name] = {'receipt': receipt, 'receiver': records,
        'exact_persisted_event_bytes': bool(records) and all(r['body'] == stored.get('event') for r in records),
        'after_token_expiry': bool(records) and min(r['received_at'] for r in records) > result['token_expiry_bound']}
Path('/evidence/workflow_readback_v6.json').write_text(json.dumps(readback, indent=2)+'\n')
assert all(not value['mismatches'] and value['fresh_files'] for value in readback['comparisons'].values())
assert readback['delivery']['ready-healthy']['receipt']['state'] == 'delivered'
assert readback['delivery']['ready-failing']['receipt']['state'] == 'exhausted'
assert all(value['exact_persisted_event_bytes'] and value['after_token_expiry'] for value in readback['delivery'].values())
print('Fresh model artifacts, exact callback bytes and token-expiry independence verified.')
