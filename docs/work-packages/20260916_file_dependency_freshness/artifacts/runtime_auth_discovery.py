"""Bootstrap dev-agent without logging secrets; retain public discovery only."""
import json
import os
from pathlib import Path
import re
import requests

HOST = 'https://wc.bearhive.duckdns.org'
ARTIFACTS = Path(__file__).parent
SECRET = Path('/tmp/wepppy-freshness-runtime-auth.json')
values = {}
for line in Path('docker/secrets/dev-agent.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('\"\'')
session = requests.Session()
login = session.get(HOST + '/weppcloud/login', timeout=30)
login.raise_for_status()
if 'name="cap_token"' in login.text:
    raise SystemExit('Login requires Cap.js; browser bootstrap required.')
def csrf(page):
    return re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', page.text, re.I).group(1)
response = session.post(HOST + '/weppcloud/login', data={
    'email': values['DEV_AGENT_EMAIL'], 'password': values['DEV_AGENT_PASSWORD'],
    'remember': 'y', 'csrf_token': csrf(login)}, timeout=30)
response.raise_for_status()
profile = session.get(HOST + '/weppcloud/profile', timeout=30)
profile.raise_for_status()
response = session.post(HOST + '/weppcloud/profile/mint-token',
                        headers={'X-CSRFToken': csrf(profile)}, timeout=30)
response.raise_for_status()
payload = response.json()
token = (payload.get('Content') or payload.get('content') or payload.get('success') or {}).get('token')
if not token:
    raise SystemExit('Token absent; response body intentionally omitted.')
with os.fdopen(os.open(SECRET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
    json.dump({'host': HOST, 'token': token, 'cookies': session.cookies.get_dict()}, stream)
os.chmod(SECRET, 0o600)
for name in ('configs', 'endpoints'):
    response = session.get(HOST + '/rq-engine/api/' + name,
                           headers={'Authorization': 'Bearer ' + token}, timeout=30)
    response.raise_for_status()
    (ARTIFACTS / ('runtime_discovery_' + name + '.json')).write_text(json.dumps(response.json(), indent=2)+'\n')
    print(name, response.status_code)
print('Authenticated discovery retained; token/cookies held in private temporary file.')
