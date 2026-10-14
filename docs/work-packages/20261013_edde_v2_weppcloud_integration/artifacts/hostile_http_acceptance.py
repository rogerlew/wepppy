import requests,json,hashlib
from pathlib import Path
p=Path('docs/work-packages/20261013_edde_v2_weppcloud_integration/artifacts'); root=Path('/wc1/runs/ed/edde-ca-20261014')
h={'Authorization':'Bearer '+Path('/tmp/edde-acceptance-token').read_text().strip()};base='https://wc.bearhive.duckdns.org/rq-engine/api'
def snapshot():
 return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [root/'climate.nodb',*sorted((root/'climate').glob('*.cli'))]}
payload={'climate_catalog_id':'future_edde_v2','climate_mode':17,'climate_spatialmode':0,'edde_projection':'WRF-MPI/SSP3-7.0','future_start_year':2060,'future_end_year':2060,'precip_scaling_mode':0,'cligen_seed':1001}
records=[]
for change in [{'edde_projection':'../../etc/passwd'},{'future_start_year':2024},{'future_end_year':2100},{'climate_spatialmode':2},{'precip_scaling_mode':3}]:
 before=snapshot(); r=requests.post(base+'/runs/edde-ca-20261014/config/build-climate',headers=h,json=payload|change,timeout=60); after=snapshot();record={'change':change,'status':r.status_code,'response':r.json(),'unchanged':before==after}; print(record);records.append(record)
 assert r.status_code==400 and before==after
r=requests.post(base+'/runs/edde-ca-20261014/config/build-climate',json=payload,timeout=30);records.append({'case':'unauthenticated','status':r.status_code}); assert r.status_code in (401,403)
(p/'hostile-http-no-mutation.json').write_text(json.dumps(records,indent=2)+'\n')
