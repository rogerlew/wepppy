"""Two-host, same-owner service canary. All mutations confined to owned scope/queue."""
import errno
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import time
import types

START=time.monotonic()
def emit(event,**data):
 print(json.dumps(dict(event=event,epoch=time.time(),elapsed=time.monotonic()-START,**data),default=str),flush=True)
def deadline(signum,frame):raise TimeoutError('bounded owned canary process deadline')
signal.signal(signal.SIGALRM,deadline);signal.alarm(720)
assert (os.getuid(),os.getgid())==(1002,130)
config=json.loads((Path(__file__).parent/'config.json').read_text())
base=Path(config['base']);root=base/'batches';source=Path(config['source'])
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps([dict(path=str(root),namespace=config['name'],coordination=str(base/'locks'),layout='batch')])
os.environ['QUERY_CATALOG_REFRESH_ENABLED']='true'
hashes={}
for name in ['_query_catalog_inventory','query_catalog_rq']:
 full='wepppy.rq.'+name
 try:module=importlib.import_module(full)
 except ModuleNotFoundError as exc:
  if exc.name!=full:raise
  module=types.ModuleType(full);module.__file__='/workdir/wepppy/wepppy/rq/'+name+'.py';module.__package__='wepppy.rq';sys.modules[full]=module
 code=(Path(__file__).parent/(name+'.py')).read_text();hashes[name]=hashlib.sha256(code.encode()).hexdigest()
 exec(compile(code,module.__file__,'exec'),module.__dict__)
 from wepppy import rq
 setattr(rq,name,module)
import redis
from rq import Queue,Worker
from rq.job import Job
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.rq import query_catalog_rq as cq
from wepppy.query_engine import catalog_refresh as cr
conn=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue(config['name'],connection=conn)
cq._default_queue=lambda:q
emit('identity',role=sys.argv[1],host=socket.gethostname(),uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),candidate_sha256=hashes,configuration=cq.catalog_worker_configuration())

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
role=sys.argv[1]
if role=='setup':
 assert not base.exists();base.mkdir(parents=True);root.mkdir();(base/'locks').mkdir()
 files=sorted(source.rglob('*.parquet'));assert len(files)==79
 manifest=[dict(path=f.relative_to(source).as_posix(),bytes=f.stat().st_size,sha256=digest(f)) for f in files]
 assert sum(f['bytes'] for f in manifest)==73328103
 assert all(not f.is_symlink() for f in files)
 method='hardlink';count=8
 try:os.link(files[0],base/'immutable-link-probe.parquet')
 except OSError as exc:
  if exc.errno not in {errno.EXDEV,errno.EPERM,errno.EOPNOTSUPP}:raise
  method='copy';count=4;emit('hardlink_unavailable',errno=exc.errno)
 scopes=[]
 for i in range(count):
  scope=root/'owner'/'scopes'/f'scope-{i:02d}';scope.mkdir(parents=True);(scope/'wepp.nodb').write_text('{}')
  for f in files:
   dest=scope/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
   if method=='hardlink':os.link(f,dest)
   else:shutil.copyfile(f,dest)
  scopes.append(str(scope))
 assert not (root/'owner'/'wepp.nodb').exists()
 data=dict(method=method,scopes=scopes,files=manifest,bytes_per_scope=sum(f['bytes'] for f in manifest))
 (base/'setup.json').write_text(json.dumps(data,indent=2));emit('setup_complete',**{k:v for k,v in data.items() if k!='files'})
elif role=='worker':
 class ProbeWorker(Worker):
  def register_birth(self):
   super().register_birth();self.connection.hset(self.key,cq.WORKER_FIELD,json.dumps(cq.catalog_worker_configuration()))
 worker=ProbeWorker([q],connection=conn,name=config['name']+'-'+sys.argv[2])
 try:
  worker.register_birth();emit('worker_ready',name=worker.name)
  assert input()=='go'
  worker.register_death()
  started=time.time();worker.work(burst=True,logging_level='WARNING')
  emit('worker_complete',name=worker.name,started=started,ended=time.time())
 finally:worker.register_death()
elif role=='enqueue':
 setup=json.loads((base/'setup.json').read_text());assert q.count==0
 status=cq.consumer_status(q);assert status['compatible']==2 and not status['incompatible'] and not status['suspended'],status
 jobs=[];owners=[]
 for path in setup['scopes']:
  receipt=cr.record_catalog_refresh(path)
  result=cq.enqueue_catalog_refresh(path,queue=q,timeout=240)
  assert result['state']=='queued',result
  jobs.append(dict(path=path,receipt=receipt,job_id=result['job_id']));owners.append(cr.catalog_guard_identity(path))
 assert len(set(owners))==1
 assert len({j['receipt']['scope_id'] for j in jobs})==len(jobs)
 data=dict(jobs=jobs,owner=owners[0],queued=q.count,consumer_status=status,enqueued_at=time.time())
 (base/'admitted.json').write_text(json.dumps(data,indent=2));emit('admitted',**data)
elif role=='verify':
 setup=json.loads((base/'setup.json').read_text());admitted=json.loads((base/'admitted.json').read_text());rows=[]
 for record in admitted['jobs']:
  job=Job.fetch(record['job_id'],connection=conn)
  row=dict(job_id=job.id,path=record['path'],status=str(job.get_status(refresh=True)),worker=job.worker_name,enqueued_at=job.enqueued_at,started_at=job.started_at,ended_at=job.ended_at,exception=job.exc_info)
  if job.started_at and job.enqueued_at:row['wait_seconds']=(job.started_at-job.enqueued_at).total_seconds()
  if job.ended_at and job.started_at:row['service_seconds']=(job.ended_at-job.started_at).total_seconds()
  rows.append(row)
 (base/'job-observations.json').write_text(json.dumps(rows,indent=2,default=str))
 assert all(row['status'] in {'finished','JobStatus.FINISHED'} for row in rows),rows
 for row in rows:
  scope=Path(row['path']);assert not cr.pending_catalog_requests(scope)
  catalog=json.loads((scope/'_query_engine/catalog.json').read_text());indexed={f['path']:f for f in catalog['files']}
  assert all(f['path'] in indexed and indexed[f['path']]['size_bytes']==f['bytes'] for f in setup['files'])
  # Only after raw current/pending checks, run the actual consumer freshness barrier.
  cr.ensure_catalog_fresh(scope,required_paths=[f['path'] for f in setup['files']])
  assert not cr.pending_catalog_requests(scope)
  row.update(catalog_entries=len(indexed),pending_receipts=0,catalog_sha256=digest(scope/'_query_engine/catalog.json'))
  first=setup['files'][0]['path'];row['sample']=dict(path=first,sha256=digest(scope/first),source_sha256=digest(source/first),shared_inode=(scope/first).stat().st_ino==(source/first).stat().st_ino)
  assert row['sample']['sha256']==row['sample']['source_sha256']
 assert all(digest(source/f['path'])==f['sha256'] for f in setup['files'])
 assert len(list((base/'locks').glob('*.lock')))==1
 result=dict(status='passed',source_contents_unchanged=True,method=setup['method'],jobs=rows,unique_guard_files=1,queue_count=q.count,consumer_status=cq.consumer_status(q),candidate_sha256=hashes,verified_at=time.time())
 (base/'result.json').write_text(json.dumps(result,indent=2,default=str));emit('result',**result)
else:raise ValueError(role)
