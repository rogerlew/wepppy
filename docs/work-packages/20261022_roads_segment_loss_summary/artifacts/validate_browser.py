"""Read corrected summary through live browse/download and an actual Chromium page."""
import csv
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path

import pyarrow.parquet as pq
import requests
from wepppy.weppcloud.app import app, user_datastore
from wepppy.weppcloud.utils.auth_tokens import issue_token

runid = 'roads-segment-summary-validation'
root = Path('/wc1/runs/ro')/runid
relative = 'wepp/roads/output/interchange/roads_segment_loss_summary.parquet'
path = root/relative
with app.app_context():
    account = user_datastore.find_user(email='dev-agent@example.com')
    assert account and account.active
    roles = [role.name for role in account.roles]
    assert 'Root' in roles or 'Admin' in roles
    token = issue_token(f'admin-run-token:{account.id}', runs=[runid], audience='rq-engine', expires_in=300,
        extra_claims={'token_class':'service', 'roles':roles, 'email':account.email,
            'service_groups':['admin-run-token'],
            'feature_access_principal':{'version':1,'kind':'human','id':account.id}})['token']
headers = {'Authorization':'Bearer '+token}
base = f'http://browse:9009/weppcloud/runs/{runid}/disturbed9002-wbt-mofe'
response = requests.get(base+'/download/'+relative,headers=headers,timeout=90)
assert response.status_code == 200, (response.status_code,response.text[:300])
assert response.content == path.read_bytes()
response_csv = requests.get(base+'/download/'+relative+'?as_csv=1',headers=headers,timeout=90)
assert response_csv.status_code == 200, (response_csv.status_code,response_csv.text[:300])
rows = list(csv.DictReader(io.StringIO(response_csv.text)))
table = pq.read_table(path)
assert list(rows[0]) == table.column_names
assert len(rows) == table.num_rows == 34
for actual, expected in zip(rows, table.to_pylist()):
    assert int(actual['segment_run_id']) == expected['segment_run_id']
    assert abs(float(actual['sediment_yield_kg'])-expected['sediment_yield_kg']) < 1e-9
    assert actual['sediment_leaving_buffer_kg'] == ''
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
probe = subprocess.run(['node','-e',javascript], input=json.dumps({'headers':headers,
    'url':base+'/browse/wepp/roads/output/interchange/'}), text=True,capture_output=True,check=True,
    cwd='/workdir/wepppy/wepppy/weppcloud/static-src',timeout=90)
browse_status = json.loads(probe.stdout)['browse_status']
result = {'runid':runid, 'browser':'Chromium via Playwright, live browse service',
    'authorization':'existing active dev-agent account; 300-second scoped admin-run-token; live auth/feature DB checks',
    'uid':os.getuid(),'gid':os.getgid(),'rows':len(rows), 'browse_status':browse_status,
    'parquet_status':response.status_code,'csv_status':response_csv.status_code,
    'csv_headers_unchanged':True,'csv_all_row_sediment_verified':True,
    'summary_sha256':hashlib.sha256(response.content).hexdigest(),
    'csv_sha256':hashlib.sha256(response_csv.content).hexdigest()}
Path('/tmp/roads-segment-browser-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
