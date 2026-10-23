"""Verify live Roads catalog cache policy and report admission after service reload."""
import json
import os
from pathlib import Path
import subprocess

import requests
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
urls = {
    'catalog': f'http://query-engine:8041/runs/{runid}/schema',
    'query_console': query,
    'query_info': f'http://query-engine:8041/runs/{runid}',
    'report': f'https://{os.environ["EXTERNAL_HOST"]}/weppcloud/runs/{runid}/disturbed9002-wbt-mofe/report/wepp/summary?output_scope=roads',
}
# Reuse the canonical smoke login, including the site's normal CAP challenge.
smoke = Path('/workdir/wepppy/wepppy/weppcloud/static-src/tests/smoke/wepp-executable-capabilities.spec.js').read_text()
helpers = smoke[smoke.index('function fnv32aHash'):smoke.index("test('Builder executable")]
javascript = """const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { createHash } = require('crypto');
const repo = '/workdir/wepppy';
const base = JSON.parse(fs.readFileSync(0,'utf8')).base;
""" + helpers + """
(async () => {
 const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
 const context = await browser.newContext();
 const page = await context.newPage();
 await login(page);
 process.stdout.write(JSON.stringify(await context.cookies()));
 await browser.close();
})().catch(error => {console.error(error.message);process.exit(1)});
"""
probe = subprocess.run(['node','-e',javascript],
    input=json.dumps({'base':f'https://{os.environ["EXTERNAL_HOST"]}'}),
    text=True,capture_output=True,check=True,
    cwd='/workdir/wepppy/wepppy/weppcloud/static-src',timeout=120)
session = requests.Session()
for cookie in json.loads(probe.stdout):
    session.cookies.set(cookie['name'],cookie['value'],domain=cookie['domain'],
                        path=cookie['path'],secure=cookie['secure'])
checks = {}
for phase in ('current', 'writer_busy'):
    from contextlib import nullcontext
    with lifecycle.operation(root) if phase == 'writer_busy' else nullcontext():
        statuses = {}
        for name, url in urls.items():
            response = (session if name == 'report' else requests).get(url,headers=headers,timeout=90)
            expected = 409 if name == 'report' and phase == 'writer_busy' else 200
            assert response.status_code == expected, (name,phase,response.status_code,response.text[:300])
            assert 'no-store' in response.headers.get('Cache-Control',''), (name,response.headers)
            if name == 'report' and phase == 'current':
                assert response.url == url
                assert 'Loss summary' in response.text and 'Reports not available:' not in response.text
            if name == 'catalog':
                entries = [entry['path'] for entry in response.json()['entries']]
                assert (relative in entries) is (phase == 'current')
            statuses[name] = response.status_code
        checks[phase] = statuses
        print(phase,statuses,flush=True)
result = {'runid':runid,'uid':os.getuid(),'gid':os.getgid(),'checks':checks,
          'discovery_no_store':True,'busy_catalog_omits_current_roads':True}
Path('/tmp/roads-lifecycle-discovery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
