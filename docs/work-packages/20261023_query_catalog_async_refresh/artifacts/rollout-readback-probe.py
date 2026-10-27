import json,os,time
from pathlib import Path
import duckdb
base=Path('/wc1/query-catalog-validation/20261026/rollout-cycle-2355')
x=json.loads((base/'result.json').read_text());project=base/'runs/representative';source=Path(x['source'])
con=duckdb.connect();rows=[];start=time.monotonic()
for f in x['files']:
 p=f['path'];a=con.execute('select count(*) from read_parquet(?)',[str(source/p)]).fetchone()[0];b=con.execute('select count(*) from read_parquet(?)',[str(project/p)]).fetchone()[0]
 assert a==b
 rows.append({'path':p,'source_rows':a,'copy_rows':b})
r={'uid':os.getuid(),'gid':os.getgid(),'state':'passed','tables':rows,'elapsed_seconds':time.monotonic()-start}
(base/'readback.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
