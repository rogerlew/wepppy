import hashlib,importlib.util,json,os,sys,threading,time,traceback
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.query_engine.catalog_refresh import RootConfig
source=Path('/tmp/qcat_inventory_final.py')
spec=importlib.util.spec_from_file_location('qcat_inventory_candidate',source);inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
key='query-catalog:validation:20261027:legacy-stream-0035'
conn=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
assert conn.exists(key+':discovery')
roots=[RootConfig(Path('/geodata/weppcloud_runs'),'legacy:runs',Path('/wc1/query-engine-coordination/locks'),'flat')]
s=inv.state(conn,key)
assert s['job_id']=='owned-readonly-resume-0055' and s['entries']>=62200
start=time.monotonic();done=threading.Event()
def report():
 s=inv.state(conn,key)
 return {'elapsed_seconds':time.monotonic()-start,'entries':s.get('entries'),'visited':s.get('visited'),'errors':s.get('errors'),'completed_at':s.get('completed_at'),'updated_at':s.get('updated_at'),'frontier_remaining':conn.llen(key+':frontier'),'scope_count':conn.scard(key+':scopes'),'discovery_stream_count':conn.xlen(key+':stream')}
def monitor():
 while not done.wait(15):print(json.dumps({'progress':report()}),flush=True)
t=threading.Thread(target=monitor,daemon=True);t.start()
print(json.dumps({'started_at':time.time(),'uid':os.getuid(),'gid':os.getgid(),'helper_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'key':key,'roots':[str(r.path) for r in roots],'scope':'resumed read-only helper after deliberate generation fencing; prefix replay expected; no project writes/admissions; not RQ execution'}),flush=True)
try:
 inv.run(conn,key,s['job_id'],s['cycle'],roots,100)
 print(json.dumps({'result':'completed','summary':report()}),flush=True)
except (OSError,ValueError,RuntimeError) as exc:
 print(json.dumps({'result':'failed','exception_type':type(exc).__name__,'summary':report()}),flush=True)
 raise
finally:
 done.set()
 for suffix in (':discovery',':frontier',':seen',':scopes',':stream',':generation'):conn.expire(key+suffix,7*86400)
