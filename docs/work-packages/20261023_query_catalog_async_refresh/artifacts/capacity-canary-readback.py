"""Read-only sample consumer proof and owned queue cleanup observation."""
import json,os,sys,time
from pathlib import Path
import duckdb,redis
from rq import Queue
from rq.registry import StartedJobRegistry
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
assert (os.getuid(),os.getgid())==(1002,130)
base=Path(sys.argv[1]);setup=json.loads((base/'setup.json').read_text())
source=Path('/wc1/query-catalog-validation/20261026/rollout-cycle-2355/runs/representative')
con=duckdb.connect();samples=[]
for relative in ['watershed/channels.parquet','wepp/output/interchange/H.pass.parquet']:
 expected=con.execute('select count(*) from read_parquet(?)',[str(source/relative)]).fetchone()[0]
 for scope in setup['scopes']:
  observed=con.execute('select count(*) from read_parquet(?)',[str(Path(scope)/relative)]).fetchone()[0]
  assert observed==expected
  samples.append(dict(scope=scope,path=relative,source_rows=expected,scope_rows=observed))
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue(base.name,connection=c)
assert q.count==0 and StartedJobRegistry(queue=q,connection=c).count==0
print(json.dumps(dict(uid=os.getuid(),gid=os.getgid(),status='passed',samples=samples,queue_count=q.count,started_count=StartedJobRegistry(queue=q,connection=c).count,epoch=time.time(),setup=setup,result=json.loads((base/'result.json').read_text())),default=str))
