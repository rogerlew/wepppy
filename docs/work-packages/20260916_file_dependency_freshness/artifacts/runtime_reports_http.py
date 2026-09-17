"""Real report/download responses; preserve hashes without recording session HTML."""
import argparse
import hashlib
import json
from pathlib import Path

from runtime_http import request, session

parser = argparse.ArgumentParser()
parser.add_argument('label')
args = parser.parse_args()
runid = 'qa-freshness-runtime-7e24c8d1'
state = request(args.label+'_report_state', 'GET',
                f'/rq-engine/api/runs/{runid}/config/postfire-debris-flow/state')['result']
assert state['freshness'] == 'current', state
host, client = session()
rows = []
output = Path(__file__).with_name('runtime_reports_'+args.label+'.json')


def retain():
    output.write_text(json.dumps(rows, indent=2)+'\n')


for slug in ('avg_annual_by_landuse', 'avg_annual_watbal'):
    for suffix in ('', '?format=csv'):
        path = f'/weppcloud/runs/{runid}/config/report/wepp/{slug}/'+suffix
        response = client.get(host+path, timeout=180)
        rows.append({'path': path, 'status': response.status_code,
                     'final_path': response.url.removeprefix(host),
                     'content_type': response.headers.get('Content-Type'),
                     'bytes': len(response.content), 'sha256': hashlib.sha256(response.content).hexdigest()})
        retain()
        if response.status_code != 200:
            continue  # Preserve the failed row; assert the complete result below.
        assert '/login' not in response.url and response.content
        if suffix:
            assert 'csv' in response.headers.get('Content-Type', '')
            Path(__file__).with_name(f'runtime_{args.label}_{slug}.csv').write_bytes(response.content)
for item in state['results']['files']:
    response = client.get(host+item['url'], timeout=180)
    rows.append({'path': item['url'], 'status': response.status_code,
                 'content_type': response.headers.get('Content-Type'),
                 'bytes': len(response.content), 'sha256': hashlib.sha256(response.content).hexdigest()})
    retain()
    response.raise_for_status()
    assert response.content and '/login' not in response.url
for relative in ('wepp/reports/cache/hillslope_watbal_summary.parquet',):
    path = f'/weppcloud/runs/{runid}/config/download/'+relative
    response = client.get(host+path, timeout=180)
    source = Path('/wc1/runs/qa')/runid/relative
    rows.append({'path': path, 'status': response.status_code,
                 'sha256': hashlib.sha256(response.content).hexdigest(),
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    retain()
    assert response.status_code == 200 and rows[-1]['sha256'] == rows[-1]['source_sha256']
assert all(row['status'] == 200 for row in rows), 'One or more HTTP report rows failed; see retained complete evidence'
print('Actual reports and downloads', args.label, len(rows), 'passed')
