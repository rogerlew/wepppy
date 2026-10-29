"""Submit an actual copied culvert archive; retain no browse or bearer credentials."""
import json
from pathlib import Path
import time
import redis
import requests
from rq.job import Job
from wepppy.weppcloud.utils.auth_tokens import issue_token
from wepppy.rq.webhook_tracking import WebhookStore
from wepppy.rq.webhook_dispatcher import inspect

connection = redis.Redis(host='redis', db=9)
store = WebhookStore(connection, 'disposable-workflow-acceptance')
issued = issue_token('culvert-batch-submit-90d', scopes=['culvert:batch:submit'],
                     audience='rq-engine', expires_in=5,
                     extra_claims={'token_class': 'service', 'service_groups': ['culverts']})
evidence = {'token_expires_at': issued['claims']['exp'], 'submitted_at': time.time()}
path = Path('/evidence/culvert_mixed_parallel_probe.json')
def retain():
    path.write_text(json.dumps(evidence, indent=2, default=str) + '\n')
with Path('/acceptance/culvert-mixed.zip').open('rb') as upload:
    response = requests.post('http://api:8050/api/culverts-wepp-batch/',
        headers={'Authorization': 'Bearer ' + issued['token'], 'Idempotency-Key': 'actual-culvert-expiry-10'},
        data={'webhook_url': 'https://webhook.test/ack'},
        files={'payload.zip': ('payload.zip', upload, 'application/zip')}, timeout=60)
payload = response.json()
evidence.update(http_status=response.status_code,
                response={key: value for key, value in payload.items() if key not in {'browse_token', 'browse_token_expires_at'}})
retain()
assert response.status_code in {200, 202}, 'Actual culvert admission failed; sanitized evidence retained'
root_id = payload['job_id']
batch = payload['culvert_batch_uuid']
for _ in range(1800):
    receipt = inspect(store, root_id)
    if receipt and receipt['state'] in {'delivered', 'exhausted', 'outcome_unavailable'}:
        break
    time.sleep(.5)
evidence['callback'] = inspect(store, root_id)
evidence['root_status'] = Job.fetch(root_id, connection=connection).get_status().value
summary = Path('/acceptance/culverts') / batch / 'batch_summary.json'
if summary.exists():
    evidence['batch_summary'] = json.loads(summary.read_text())
records = Path('/evidence/workflow_receiver.jsonl')
evidence['receiver'] = [json.loads(line) for line in records.read_text().splitlines()
                        if json.loads(json.loads(line)['body']).get('job_id') == root_id] if records.exists() else []
retain()
assert evidence['callback']['state'] == 'delivered', 'Culvert callback not delivered; inspect closure evidence'
assert evidence['receiver'] and evidence['receiver'][0]['received_at'] > evidence['token_expires_at']
assert summary.exists(), 'No actual domain summary was generated'
print('Actual culvert API, domain summary and post-expiry callback retained.')

# Explicit Option A acceptance, independent of the root job status.
event = json.loads(evidence['receiver'][0]['body'])
assert event['execution_status'] == 'finished'
assert evidence['batch_summary']['succeeded'] > 0 and evidence['batch_summary']['failed'] > 0
assert all(record['body'] == store.read(root_id)['event'] for record in evidence['receiver'])
