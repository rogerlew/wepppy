"""Read actual mixed-domain artifacts and the canonical live RQ hierarchy."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq
import redis
from rq.job import Job
from wepppy.rq.job_info import recursive_get_job_details
from wepppy.rq.webhook_tracking import WebhookStore

path = Path('/evidence/culvert_mixed_parallel_probe.json')
evidence = json.loads(path.read_text())
connection = redis.Redis(host='redis', db=9)
root_id = evidence['response']['job_id']
job = Job.fetch(root_id, connection=connection)
evidence['job_tree'] = recursive_get_job_details(job, connection, datetime.now(timezone.utc))
pending, statuses = [job], {}
while pending:
    current = pending.pop()
    if current.id in statuses:
        continue
    statuses[current.id] = current.get_status().value
    pending.extend(Job.fetch(value, connection=connection) for key, value in current.meta.items()
                   if key.startswith('jobs:') and isinstance(value, str))
evidence['job_states'] = statuses
batch = Path('/acceptance/culverts') / evidence['response']['culvert_batch_uuid']
state = json.loads((batch/'culverts_runner.nodb').read_text())['py/state']
evidence['domain_errors'] = {key: value.get('error', {}).get('type') for key, value in state['_runs'].items()
                             if value.get('status') == 'failed'}
evidence['model_artifacts'] = {}
for name, record in state['_runs'].items():
    if record.get('status') != 'success':
        continue
    for artifact in sorted((batch/'runs'/name/'wepp/output/interchange').glob('*.parquet')):
        table = pq.read_table(artifact)
        assert artifact.stat().st_mtime > evidence['submitted_at']
        evidence['model_artifacts'][str(artifact.relative_to(batch))] = {
            'rows': table.num_rows, 'columns': table.column_names,
            'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
store = WebhookStore(connection, 'disposable-workflow-acceptance')
receipt = store.read(root_id)
evidence['exact_persisted_event_bytes'] = all(r['body'] == receipt['event'] for r in evidence['receiver'])
assert len(statuses) == 38 and set(statuses.values()) == {'finished'}
assert len(evidence['domain_errors']) == 35 and set(evidence['domain_errors'].values()) == {'CulvertPointOutsideWatershedError'}
assert evidence['model_artifacts'] and any(a['rows'] > 0 for a in evidence['model_artifacts'].values())
assert evidence['exact_persisted_event_bytes'] and 'url' not in receipt
assert json.loads(receipt['event'])['execution_status'] == 'finished'
path.write_text(json.dumps(evidence, indent=2, default=str)+'\n')
print('38 finished RQ nodes, 35 caught domain failures, fresh successful-model parquet values and exact event bytes verified.')
