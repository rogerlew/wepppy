import os,json,time,shutil,hashlib,statistics
from pathlib import Path
base=Path('/wc1/query-catalog-validation/20261026/rollout-cycle-final-0050')
assert os.getuid()==1002 and os.getgid()==130
assert not base.exists(), 'Unique scratch already exists; inspect before retry'
base.mkdir(parents=True)
root=base/'runs';root.mkdir()
locks=base/'locks';locks.mkdir()
os.environ['QUERY_CATALOG_REFRESH_ENABLED']='true'
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps([dict(path=str(root),namespace='qcat-rollout-cycle-20261026-final-0050',coordination=str(locks),layout='flat')])
import redis
from rq import Queue,Worker
from rq.job import Job
from rq.registry import FinishedJobRegistry,StartedJobRegistry
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
import sys,types,wepppy.rq
helper_name='wepppy.rq._query_catalog_inventory'
helper=types.ModuleType(helper_name);helper.__file__='/tmp/qcat_inventory_final.py';helper.__package__='wepppy.rq';sys.modules[helper_name]=helper;setattr(wepppy.rq,'_query_catalog_inventory',helper)
exec(compile(Path(helper.__file__).read_text(),helper.__file__,'exec'),helper.__dict__)
from wepppy.rq import query_catalog_rq as cq
exec(compile(Path('/tmp/qcat_rq_final.py').read_text(),cq.__file__,'exec'),cq.__dict__)
from wepppy.query_engine import catalog_refresh as cr
conn=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
q=Queue('qcat-rollout-cycle-20261026-final-0050',connection=conn)
assert q.count==0
cq._default_queue=lambda:q
source=Path('/wc1/query-catalog-validation/20261026/rollout-cycle-2355/runs/representative')
assert source.is_dir()
# Preserve source; a catalog-only representative copy has no hydrated NoDb state.
project=root/'representative';project.mkdir();(project/'wepp.nodb').write_text('{}')
files=[];total=0
for sub in ['watershed','landuse','soils','climate','wepp/output/interchange']:
 for f in sorted((source/sub).glob('**/*.parquet')):
  assert not f.is_symlink()
  n=f.stat().st_size
  if total+n>512*1024*1024:continue
  rel=f.relative_to(source);dest=project/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
  files.append(dict(path=str(rel),bytes=n,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()));total+=n
assert files
class ProbeWorker(Worker):
 def register_birth(self):
  super().register_birth();self.connection.hset(self.key,cq.WORKER_FIELD,json.dumps(cq.catalog_worker_configuration()))
w=ProbeWorker([q],connection=conn,name='qcat-rollout-cycle-20261026-final-0050')
results={'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'source':str(source),'scratch':str(base),'files':files,'bytes':total,'ticks':[],'shared_batch':{}}
batch=Queue('batch',connection=conn)
ids=FinishedJobRegistry('batch',connection=conn).get_job_ids()[-300:]
services=[];waits=[]
for jid in ids:
 try:j=Job.fetch(jid,connection=conn)
 except Exception as e:
  results['shared_batch'].setdefault('history_errors',[]).append(type(e).__name__);continue
 if j.started_at and j.ended_at:services.append((j.ended_at-j.started_at).total_seconds())
 if j.enqueued_at and j.started_at:waits.append((j.started_at-j.enqueued_at).total_seconds())
results['shared_batch'].update(queued=batch.count,started=len(StartedJobRegistry('batch',connection=conn).get_job_ids()),retained_sample=len(ids),service_seconds=services,queue_wait_seconds=waits)
start=time.monotonic()
try:
 for i in range(6):
  w.register_birth()
  before=time.monotonic();r=cq.reconcile_query_catalogs(queue=q);r['elapsed_seconds']=time.monotonic()-before;r['queue_count']=q.count
  results['ticks'].append(r)
  w.register_death()
  w.work(burst=True,logging_level='WARNING')
  if r['state']=='completed':break
 assert results['ticks'][-1]['state']=='completed',results['ticks']
 assert not cr.pending_catalog_requests(project)
 catalog=json.loads((project/'_query_engine/catalog.json').read_text())
 indexed={f['path'] for f in catalog['files']}
 assert all(f['path'] in indexed for f in files)
 results.update(state='completed',elapsed_seconds=time.monotonic()-start,pending_receipts=0,catalog_entries=len(indexed))
finally:
 w.register_death()
 (base/'result.json').write_text(json.dumps(results,indent=2,default=str))
 print(json.dumps(results,default=str),flush=True)
