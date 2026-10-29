"""Actual HTTP submission and live RQ tree evidence on disposable project copies."""
import hashlib
import json
import os
from pathlib import Path
import time
from datetime import datetime

import redis
import requests
from rq import Queue, Worker
from rq.job import Job
from wepppy.nodb.core import Ron
from wepppy.weppcloud.utils.auth_tokens import issue_token
from wepppy.rq.webhook_tracking import WebhookStore
from wepppy.rq.webhook_dispatcher import inspect
from wepppy.rq.job_info import recursive_get_job_details

connection = redis.Redis(host='redis', db=9)
store = WebhookStore(connection, 'disposable-workflow-acceptance')
evidence = {'provenance': {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
                           'umask': oct(os.umask(0o22)), 'rq': __import__('rq').__version__,
                           'source': 'disposable copies; source mounts read-only; isolated Redis and network'}}
for _ in range(60):
    workers = Worker.all(connection=connection)
    counts = {queue: sum(queue in worker.queue_names() for worker in workers)
              for queue in ('default', 'batch')}
    if counts == {'default': 6, 'batch': 4}:
        break
    time.sleep(.5)
else:
    raise RuntimeError('Canonical six-default/four-batch worker pools did not become ready')
evidence['provenance']['worker_counts'] = counts


def retain():
    Path('/evidence/workflow_v6_probe.json').write_text(json.dumps(evidence, indent=2, default=str) + '\n')


def token(runid, ttl=5):
    return issue_token('culvert-batch-submit-90d', scopes=['rq:enqueue', 'rq:status', 'culvert:batch:submit'],
                       runs=[runid], audience='rq-engine', expires_in=ttl,
                       extra_claims={'token_class': 'service', 'service_groups': ['culverts']})['token']


def tree(job_id):
    job = Job.fetch(job_id, connection=connection)
    details = recursive_get_job_details(job, connection, datetime.utcnow())
    statuses = {}
    pending = [job]
    while pending:
        item = pending.pop()
        if item.id in statuses:
            continue
        statuses[item.id] = item.get_status().value
        for key, value in item.meta.items():
            if key.startswith('jobs:') and isinstance(value, str):
                pending.append(Job.fetch(value, connection=connection))
    return details, statuses


def artifacts(name):
    root = Path('/acceptance/runs') / name
    manifest = {}
    for folder in ('wepp/runs', 'wepp/output', 'wepp/stats'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_file():
                manifest[str(path.relative_to(root))] = {'bytes': path.stat().st_size,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mtime': path.stat().st_mtime}
    return manifest


for _ in range(60):
    try:
        if requests.get('http://api:8050/openapi.json', timeout=2).status_code == 200:
            break
    except requests.ConnectionError:
        time.sleep(1)
else:
    raise RuntimeError('Disposable API did not become ready')

for name, callback in [('ready-baseline', None), ('ready-healthy', 'https://webhook.test/ack'), ('ready-failing', 'https://webhook.test/failure')]:
    runid = 'profile;;tmp;;' + name
    config = Ron.getInstance('/acceptance/runs/' + name).config_stem
    before = artifacts(name)
    issued_at = time.time()
    headers = {'Authorization': 'Bearer ' + token(runid, ttl=5)}
    if callback:
        headers['Idempotency-Key'] = 'workflow-acceptance-v6-' + name
    response = requests.post(f'http://api:8050/api/runs/{runid}/{config}/run-wepp',
                             headers=headers, json={'webhook_url': callback} if callback else {}, timeout=60)
    result = {'submitted_at': issued_at, 'token_expiry_bound': issued_at + 5, 'http_status': response.status_code, 'response': response.json()}
    evidence[name] = result
    retain()
    if response.status_code != 200:
        raise RuntimeError('Actual WEPP admission failed; see sanitized evidence')
    job_id = response.json()['job_id']
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        details, statuses = tree(job_id)
        if statuses and not set(statuses.values()) & {'queued', 'started', 'scheduled'}:
            result['job_states'] = statuses
            result['job_tree'] = details
            break
        time.sleep(.5)
    else:
        raise RuntimeError('Actual WEPP hierarchy did not settle in fixture budget')
    after = artifacts(name)
    result['artifacts'] = after
    result['fresh_artifacts'] = [path for path, value in after.items() if value['mtime'] > issued_at]
    result['callback'] = inspect(store, job_id) if callback else None
    retain()
    if set(statuses.values()) != {'finished'} or not result['fresh_artifacts']:
        raise RuntimeError('Actual WEPP output acceptance failed; see job/artifact evidence')

print('Actual WEPP submissions and fresh artifacts captured.')
