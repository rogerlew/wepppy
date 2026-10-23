"""Exercise live browse-to-D-Tale loading and existing sessions across replacement."""
import json
import os
from pathlib import Path

import requests
from wepppy.nodb.mods.roads import Roads
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from wepppy.weppcloud.app import app, user_datastore
from wepppy.weppcloud.utils.auth_tokens import issue_token

runid = 'roads-lifecycle-archive-validation'
root = Path('/wc1/runs/ro') / runid
relative = 'wepp/roads/output/interchange/roads_segment_loss_summary.parquet'
with app.app_context():
    account = user_datastore.find_user(email='dev-agent@example.com')
    assert account and account.active
    roles = [role.name for role in account.roles]
    assert 'Root' in roles or 'Admin' in roles
    token = issue_token(f'admin-run-token:{account.id}', runs=[runid], audience='rq-engine', expires_in=900,
        extra_claims={'token_class':'service', 'roles':roles, 'email':account.email,
            'service_groups':['admin-run-token'],
            'feature_access_principal':{'version':1,'kind':'human','id':account.id}})['token']
headers = {'Authorization':'Bearer '+token}
base = f'http://browse:9009/weppcloud/runs/{runid}/disturbed9002-wbt-mofe'
query = f'http://query-engine:8041/runs/{runid}/query'
web = f'http://weppcloud:8000/runs/{runid}/disturbed9002-wbt-mofe'
import re
launch = base+'/dtale/'+relative
checks = {}
def open_preview():
    response = requests.get(launch,headers=headers,allow_redirects=False,timeout=90)
    assert response.status_code == 303, (response.status_code,response.text[:300])
    assert 'no-store' in response.headers.get('Cache-Control','')
    match = re.search(r'/dtale/main/([^/?]+)', response.headers['Location'])
    assert match, 'Expected public validation preview URL'
    return match.group(1)

def grid(data_id, expected):
    response = requests.get(f'http://dtale:9010/dtale/data/{data_id}',params={'ids':json.dumps(['0-1'])},timeout=90)
    assert response.status_code == expected, (response.status_code,response.text[:300])
    assert 'no-store' in response.headers.get('Cache-Control','')
    if expected == 409:
        assert response.json()['code'] == 'roads_results_unavailable'
    else:
        assert response.json().get('success') is not False, response.text[:300]
    return response.status_code

data_id = open_preview()
checks['current'] = {'launch':303,'grid':grid(data_id,200)}
for phase in ('writer_busy','reprepared'):
    from contextlib import nullcontext
    if phase == 'reprepared':
        Roads.getInstance(str(root)).prepare_segments()
    with lifecycle.operation(root) if phase == 'writer_busy' else nullcontext():
        response = requests.get(launch,headers=headers,allow_redirects=False,timeout=90)
        assert response.status_code == 409
        checks[phase] = {'launch':409,'grid':grid(data_id,409)}
    print(phase,checks[phase],flush=True)
assert Roads.getInstance(str(root)).run_roads_wepp()['status'] == 'completed'
new_id = open_preview()
checks['fresh_run'] = {'launch':303,'grid':grid(new_id,200)}
result = {'runid':runid,'uid':os.getuid(),'gid':os.getgid(),'checks':checks,
          'transport':'live browse:9009 -> dtale:9010; existing grid requests to actual D-Tale service',
          'authentication':'existing scoped dev-agent token; isolated public validation project'}
Path('/tmp/roads-lifecycle-dtale-http.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
