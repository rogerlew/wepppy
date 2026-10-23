"""Exercise live consumer admission across replacement and a fresh Roads run."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess

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
urls = {
    'download': base+'/download/'+relative,
    'csv': base+'/download/'+relative+'?as_csv=1',
    'schema': base+'/schema/'+relative,
    'files_meta': base+'/files/'+relative+'?meta=true',
    'browse': base+'/browse/wepp/roads/output/interchange/',
    'dashboard': web+'/gl-dashboard?output_scope=roads',
}
checks = {}
def check(phase, expected):
    statuses = {}
    for name, url in urls.items():
        response = requests.get(url, headers=headers, timeout=90)
        assert response.status_code == expected, (phase,name,response.status_code,response.text[:200])
        assert 'no-store' in response.headers.get('Cache-Control',''), (name,response.headers)
        if expected == 409:
            payload = response.json()
            error = payload.get('error')
            code = error.get('code') if isinstance(error, dict) else payload.get('code')
            assert code == 'roads_results_unavailable', (name,response.text)
        if name == 'csv' and expected == 200:
            assert len(list(csv.DictReader(io.StringIO(response.text)))) == 34
        statuses[name] = response.status_code
    response = requests.post(query, headers=headers, json={'datasets':[relative], 'columns':['segment_run_id','soil_loss_kg'], 'limit':100}, timeout=90)
    assert response.status_code == expected, (phase,'query',response.status_code,response.text[:500])
    assert 'no-store' in response.headers.get('Cache-Control','')
    if expected == 200:
        assert response.json()['row_count'] == 34
    else:
        assert response.json()['code'] == 'roads_results_unavailable'
    statuses['query'] = response.status_code
    checks[phase] = statuses
    print(phase, statuses, flush=True)

check('current',200)
with lifecycle.operation(root):
    check('writer_busy',409)
controller = Roads.getInstance(str(root))
controller.prepare_segments()
check('reprepared',409)
historical = sorted((root/lifecycle.HISTORY).glob('*/'+relative))[-1]
response = requests.get(base+'/download/'+str(historical.relative_to(root)),headers=headers,timeout=90)
assert response.status_code == 200 and response.content == historical.read_bytes()
assert controller.query_map_segments_geojson()['features']
print('Running Roads again',flush=True)
assert controller.run_roads_wepp()['status'] == 'completed'
check('fresh_run',200)
javascript = """const { chromium } = require('playwright');
(async () => {
 const input = JSON.parse(require('fs').readFileSync(0,'utf8'));
 const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
 const page = await browser.newPage({extraHTTPHeaders:input.headers});
 const response = await page.goto(input.url, {waitUntil:'domcontentloaded'});
 if (response.status() !== 200) throw new Error('Browse HTTP '+response.status());
 if (!(await page.locator('body').innerText()).includes('roads_segment_loss_summary.parquet'))
   throw new Error('Summary missing in browse listing');
 await browser.close();
 console.log(JSON.stringify({browse_status:response.status()}));
})().catch(error => {console.error(error.message);process.exit(1)});"""
probe = subprocess.run(['node','-e',javascript],input=json.dumps({'headers':headers,'url':urls['browse']}),
    text=True,capture_output=True,check=True,cwd='/workdir/wepppy/wepppy/weppcloud/static-src',timeout=90)
result = {'runid':runid,'uid':os.getuid(),'gid':os.getgid(),'checks':checks,
          'historical_download':200,'prepared_geometry_available':True,
          'browser':json.loads(probe.stdout),'authentication':'existing scoped dev-agent token; live access checks'}
Path('/tmp/roads-lifecycle-http.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
