import requests,re,json,hashlib,csv,io,math,os
from pathlib import Path
from datetime import datetime,timezone
import pyarrow.parquet as pq
import pyarrow as pa
from wepppy.nodb.core import Ron,Wepp,Climate
from wepppy.weppcloud.app import app,user_datastore
BASE='https://wc.bearhive.duckdns.org';TARGET=os.environ.get('RQ212_TARGET','rq212-20261027-baseline');CONFIG='disturbed-wbt-profile'
PHASE=os.environ.get('RQ212_PHASE','baseline')
OUT=Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts')
WD=Path('/wc1/runs/rq')/TARGET
record={'target':TARGET,'phase':PHASE,'time':datetime.now(timezone.utc).isoformat(),'identity':{'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()},'inputs':{},'outputs':{},'reports':{}}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
w=Wepp.getInstance(str(WD));cl=Climate.getInstance(str(WD));ron=Ron.getInstance(str(WD))
record['persisted']={'wepp_bin':w.wepp_bin,'pass_family':w.pass_family,'config':ron.config_stem,'climate_mode':str(cl.climate_mode)}
for p in sorted((WD/'wepp/runs').iterdir()):
 if p.is_file():
  suffix=p.suffix
  d={'sha256':digest(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
  if suffix in ('.run','.slp','.sol','.man','.cli'):
   lines=p.read_text(errors='strict').splitlines();d['lines']=len(lines)
   if suffix=='.run': d['deck']=lines
   if suffix=='.cli':d['header']=lines[:16];d['last_record']=lines[-1]
   if suffix in ('.sol','.slp'):d['header']=lines[:12]
  record['inputs'][p.name]=d
assert len([n for n in record['inputs'] if re.match(r'p\d+\.run$',n)])==28
for p in sorted((WD/'wepp/output/interchange').glob('*.parquet')):
 table=pq.read_table(p);df=table.to_pandas();numeric={}
 for name in df.select_dtypes(include='number').columns:
  col=df[name];vals=col.dropna()
  numeric[name]={'count':len(vals),'min':float(vals.min()) if len(vals) else None,'max':float(vals.max()) if len(vals) else None,'sum':float(vals.sum())}
 record['outputs'][p.name]={'sha256':digest(p),'rows':table.num_rows,'schema':str(table.schema),'numeric':numeric,'mtime_ns':p.stat().st_mtime_ns}
assert record['outputs']
with app.app_context():
 u=user_datastore.find_user(email='dev-agent@example.com');assert u and u.active
 c=app.test_client()
 with c.session_transaction() as x:x['_user_id']=u.fs_uniquifier;x['_fresh']=True
 assert c.get('/profile').status_code==200
 cookie=c.get_cookie(app.config.get('SESSION_COOKIE_NAME','session'));assert cookie
 s=requests.Session();s.cookies.set(cookie.key,cookie.value)
 for table in ['outlet','hillslopes','channels']:
  path=f'/weppcloud/runs/{TARGET}/{CONFIG}/report/wepp/summary/?format=csv&table={table}'
  r=s.get(BASE+path,timeout=90);r.raise_for_status()
  assert 'text/csv' in r.headers.get('Content-Type',''),r.headers.get('Content-Type')
  rows=list(csv.reader(io.StringIO(r.text)));assert len(rows)>1
  record['reports'][table]={'path':path,'status':r.status_code,'sha256':hashlib.sha256(r.content).hexdigest(),'rows':rows}
  (OUT/f'acceptance_{PHASE}_{table}.csv').write_bytes(r.content)
(OUT/f'acceptance_{PHASE}_readback.json').write_text(json.dumps(record,indent=2,allow_nan=False))
print(json.dumps({'phase':PHASE,'inputs':len(record['inputs']),'parquets':len(record['outputs']),'reports':{k:len(v['rows']) for k,v in record['reports'].items()}}))
