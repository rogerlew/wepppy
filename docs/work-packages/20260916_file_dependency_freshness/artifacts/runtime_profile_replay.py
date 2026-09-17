"""Real authenticated PlaybackSession HTTP, distinct from canonical CLI status."""
import argparse
from email.parser import BytesParser
from email.policy import default
import hashlib
import json
from pathlib import Path

import requests
from services.profile_playback.app import PROFILE_ROOT, _prepare_sandbox_run
from wepppy.profile_recorder.playback import PlaybackSession
from wepppy.profile_recorder.sbs_seed import read_event_seed

parser = argparse.ArgumentParser()
parser.add_argument('slug')
args = parser.parse_args()
if not args.slug.startswith('qa-freshness-'):
    raise ValueError('Disposable profile required')
profile_root = PROFILE_ROOT / args.slug
capture = profile_root / 'capture'
events = [json.loads(line) for line in (capture / 'events.jsonl').read_text().splitlines()]
original = PlaybackSession._detect_run_id(events)
if not original.startswith('qa-freshness-'):
    raise ValueError('Original lock scope must also be disposable')
sandbox_id, run_dir = _prepare_sandbox_run(profile_root, original)
auth = json.loads(Path('/workdir/wepppy/docker/secrets/freshness-runtime-auth.json').read_text())
expected = [read_event_seed(capture / 'seed/uploads', str(event['id']), required=True)
            for event in events if event.get('stage') == 'response']
observations = []


class ObservedSession(requests.Session):
    def request(self, method, url, **kwargs):
        response = super().request(method, url, **kwargs)
        if method == 'POST' and '/tasks/upload-sbs' in url:
            header = response.request.headers['Content-Type']
            message = BytesParser(policy=default).parsebytes(
                ('Content-Type: ' + header + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + response.request.body)
            parts = [part for part in message.iter_parts()
                     if part.get_param('name', header='Content-Disposition') == 'input_upload_sbs']
            assert len(parts) == 1
            payload = parts[0].get_payload(decode=True)
            stored = run_dir / 'disturbed' / parts[0].get_filename()
            record = {'url': url, 'status': response.status_code, 'bytes': len(payload),
                      'wire_sha256': hashlib.sha256(payload).hexdigest(),
                      'server_sha256': hashlib.sha256(stored.read_bytes()).hexdigest() if stored.exists() else None}
            observations.append(record)
            Path(__file__).with_name('runtime_profile_http_wire.json').write_text(json.dumps(observations, indent=2)+'\n')
        return response


client = ObservedSession()
client.headers['Authorization'] = 'Bearer ' + auth['token']
client.cookies.update(auth['cookies'])
playback = PlaybackSession(profile_root, base_url=auth['host']+'/weppcloud', execute=True,
                           run_dir=run_dir, session=client, verbose=True,
                           playback_run_id='profile;;tmp;;'+sandbox_id)
playback.run()
assert len(observations) == len(expected) == 2
for record, seed in zip(observations, expected):
    checksum = hashlib.sha256(seed.payload).hexdigest()
    assert record['status'] == 200, record
    assert record['wire_sha256'] == record['server_sha256'] == checksum
assert observations[0]['wire_sha256'] != observations[1]['wire_sha256']
result = {'status': 'passed', 'profile': str(profile_root), 'original_disposable': original,
          'sandbox_runid': playback.playback_run_id, 'sandbox': str(run_dir),
          'requests': playback.results, 'observations': observations,
          'canonical_cli': 'separate evidence; this uses supported preauthenticated Session injection'}
Path(__file__).with_name('runtime_profile_http_acceptance.json').write_text(json.dumps(result, indent=2)+'\n')
print('Actual HTTP seed/wire/server parity passed for both distinct uploads.')
