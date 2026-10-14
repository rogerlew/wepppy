"""Authenticated requests to the existing dev RQ climate endpoint; tokens never retained."""
import json
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
headers = {'Authorization': 'Bearer ' + Path('/tmp/edde-acceptance-token').read_text().strip()}
records = []
for project in json.loads((HERE/'acceptance-projects.json').read_text()):
    payload = {'climate_catalog_id':'future_edde_v2','climate_mode':17,
               'climate_spatialmode':1 if '-us-' in project['runid'] else 0,
               'edde_projection':'WRF-MPI/SSP3-7.0','future_start_year':2060,'future_end_year':2060,
               'precip_scaling_mode':0,'cligen_seed':1001}
    endpoint = f"https://wc.bearhive.duckdns.org/rq-engine/api/runs/{project['runid']}/{project['config']}/build-climate"
    response = requests.post(endpoint,headers=headers,json=payload,timeout=60)
    record = dict(project=project,payload=payload,status=response.status_code,response=response.json())
    records.append(record)
    print(project['runid'],response.status_code,response.text[:700],flush=True)
(HERE/'live-submission.json').write_text(json.dumps(records,indent=2)+'\n')
