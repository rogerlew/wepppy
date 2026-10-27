"""Read-only HTTP acceptance against the installed forest dashboard service."""
import hashlib
import json
import os
import platform
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import rq

expected_edges = {
    '2b203a33-aedc-4a0e-bdc6-13feb27b07fa': ['17a57a30-c4a5-45a0-b7ab-430f1853e6ad'],
    '1f6b862e-9769-474a-b269-f6a1ae4c1236': ['eb1db899-c57b-4a2b-abdc-127f224552f2'],
}
results = []
for job_id, dependencies in expected_edges.items():
    route = '/rq-dashboard/0/data/job/' + job_id + '.json'
    with urllib.request.urlopen('http://127.0.0.1:9181' + route, timeout=10) as response:
        payload = json.load(response)
        assert response.status == 200
        assert payload['id'] == job_id
        assert payload['status'] == 'finished'
        assert payload['depends_on'] == dependencies
        assert payload['depends_on_status'] == ['active']
        assert datetime.fromisoformat(payload['ended_at']).tzinfo is not None
        results.append({key:payload[key] for key in (
            'id','status','depends_on','depends_on_status','created_at','enqueued_at','ended_at'
        )} | {'route':route, 'http_status':response.status})
    with urllib.request.urlopen('http://127.0.0.1:9181/rq-dashboard/0/view/job/' + job_id, timeout=10) as response:
        page = response.read().decode()
        assert response.status == 200
        assert job_id in page
        results[-1]['detail_page_http_status'] = response.status

print(json.dumps({
    'captured_at':datetime.now(timezone.utc).isoformat(),
    'rq':rq.__version__, 'python':platform.python_version(),
    'uid':os.getuid(), 'gid':os.getgid(), 'groups':os.getgroups(),
    'web_py_sha256':hashlib.sha256(Path('/rq-dashboard/rq_dashboard/web.py').read_bytes()).hexdigest(),
    'boundary':'installed Gunicorn HTTP on dashboard loopback, read-only real model jobs',
    'acceptance_run':'rq212-20261027-upgraded', 'jobs':results,
},indent=2,sort_keys=True))
