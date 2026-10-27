import json,os,sys,time,types,hashlib
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
roots=[{'path':'/wc1/'+name,'namespace':'qcat-rq-inventory-20261027:'+name,'coordination':'/wc1/query-catalog-validation/20261026/inventory-rq-locks','layout':layout} for name,layout in [('runs','sharded'),('batch','batch'),('culverts','culverts')]]
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps(roots);os.environ['QUERY_CATALOG_REFRESH_ENABLED']='true'
import wepppy.rq
helper_name='wepppy.rq._query_catalog_inventory'
helper=types.ModuleType(helper_name);helper.__file__='/tmp/qcat_inventory_candidate.py';helper.__package__='wepppy.rq';sys.modules[helper_name]=helper;setattr(wepppy.rq,'_query_catalog_inventory',helper)
exec(compile(Path(helper.__file__).read_text(),helper.__file__,'exec'),helper.__dict__)
from wepppy.rq import query_catalog_rq as cq
candidate=Path('/tmp/qcat_rq_candidate.py');exec(compile(candidate.read_text(),cq.__file__,'exec'),cq.__dict__)
import redis
from rq import Queue,Worker
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.query_engine.catalog_refresh import configured_roots
conn=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue('qcat-inventory-only-20261027',connection=conn)
key='query-catalog:inventory:'+cq._configuration_id();assert not conn.exists(key+':discovery') and q.count==0
class ProbeWorker(Worker):
 def register_birth(self):
  super().register_birth();self.connection.hset(self.key,cq.WORKER_FIELD,json.dumps(cq.catalog_worker_configuration()))
w=ProbeWorker([q],connection=conn,name='qcat-inventory-only-20261027');w.register_birth()
start=time.monotonic()
try:
 lock=conn.lock(key+':lock',timeout=60,blocking_timeout=0)
 assert lock.acquire(blocking=False)
 try:state=cq._enqueue_inventory(q,key,configured_roots(),new_cycle=True,lock=lock)
 finally:lock.release()
 assert state.get('job_id') and q.count==1,state
 print(json.dumps({'started_at':time.time(),'key':key,'job_id':state['job_id'],'uid':os.getuid(),'gid':os.getgid(),'roots':roots,'helper_sha256':hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest(),'queue_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'scope':'real isolated RQ inventory only; no scheduler drain, receipts or project writes'}),flush=True)
 w.register_death();w.work(burst=True,logging_level='WARNING')
 job=q.fetch_job(state['job_id']);final=helper.state(conn,key)
 result={'status':str(job.get_status()),'elapsed_seconds':time.monotonic()-start,'discovery':final,'frontier':conn.llen(key+':frontier'),'scopes':conn.scard(key+':scopes'),'stream':conn.xlen(key+':stream')}
 print(json.dumps({'result':result}),flush=True)
 assert job.get_status()=='finished' and final.get('completed_at') and not result['frontier']
finally:
 w.register_death()
