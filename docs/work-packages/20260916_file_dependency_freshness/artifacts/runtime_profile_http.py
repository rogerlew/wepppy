"""After-restart upload/capture/promotion acceptance on a disposable run."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from runtime_http import ARTIFACTS, session

parser = argparse.ArgumentParser()
parser.add_argument('runid')
parser.add_argument('first', type=Path)
parser.add_argument('second', type=Path)
parser.add_argument('--config', default='config')
args = parser.parse_args()
if not args.runid.startswith('qa-freshness-'):
    raise ValueError('Disposable run required')
host, client = session()
profile = client.get(host + '/weppcloud/profile', timeout=30)
profile.raise_for_status()
csrf = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', profile.text, re.I).group(1)
headers = {'X-CSRFToken': csrf}
web = f'/weppcloud/runs/{args.runid}/{args.config}'
endpoint = f'/rq-engine/api/runs/{args.runid}/{args.config}/tasks/upload-sbs/'
capture = 'freshness-http'
records = []
for index, source in enumerate((args.first, args.second), 1):
    event_id = f'freshness-upload-{index}'
    request_event = {'stage': 'request', 'id': event_id, 'method': 'POST',
                     'category': 'file_upload', 'endpoint': endpoint,
                     'captureId': capture, 'requestMeta': {'bodyType': 'form-data'}}
    r = client.post(host + web + '/recorder/events', json={'events': [request_event]}, headers=headers, timeout=30)
    r.raise_for_status()
    with source.open('rb') as stream:
        response = client.post(host + endpoint, files={'input_upload_sbs': ('same-sbs.tif', stream, 'application/octet-stream')}, timeout=120)
    body = response.json()
    records.append({'event_id': event_id, 'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'status': response.status_code, 'response': body})
    (ARTIFACTS / f'runtime_profile_upload_{index}.json').write_text(json.dumps(records[-1], indent=2)+'\n')
    response.raise_for_status()
    event = dict(request_event, stage='response', ok=True, status=response.status_code)
    r = client.post(host + web + '/recorder/events', json={'events': [event]}, headers=headers, timeout=30)
    r.raise_for_status()
    print('upload and capture', index, response.status_code, flush=True)
slug = args.runid + '-sbs-profile'
r = client.post(host + web + '/recorder/promote', json={'slug': slug, 'captureId': capture}, headers=headers, timeout=180)
r.raise_for_status()
result = {'runid': args.runid, 'slug': slug, 'uploads': records, 'promotion': r.json()}
(ARTIFACTS / 'runtime_profile_capture.json').write_text(json.dumps(result, indent=2)+'\n')
print('promoted', slug, flush=True)
