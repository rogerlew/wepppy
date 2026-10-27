import ast,datetime,hashlib,json,time
from pathlib import Path
import redis
from rq import Queue,worker_registration
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue('batch',connection=c);now=time.time();rows=[]
for key in worker_registration.get_keys(queue=q):
 fields=c.hmget(key,'queues','state','death','birth','last_heartbeat','total_working_time','successful_job_count','failed_job_count')
 queues,state,death,birth,heartbeat,working,success,failed=fields
 if death is not None or c.ttl(key)<=0 or b'batch' not in (queues or b'').split(b','):continue
 parse=lambda v:v.decode() if v is not None else None
 born=datetime.datetime.fromisoformat(birth.decode().replace('Z','+00:00')).replace(tzinfo=datetime.timezone.utc).timestamp() if birth else None
 rows.append({'worker_digest':hashlib.sha256(key if isinstance(key,bytes) else key.encode()).hexdigest(),'state':parse(state),'birth':parse(birth),'age_seconds':now-born if born else None,'last_heartbeat':parse(heartbeat),'total_working_seconds':float(working or 0),'successful_job_count':int(success or 0),'failed_job_count':int(failed or 0)})
p=Path('/workdir/wepppy/wepppy/rq/rq_worker.py');tree=ast.parse(p.read_text());ttl=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULT_RESULT_TTL' for t in n.targets)]
print(json.dumps({'observed_at':now,'workers':rows,'source_default_result_ttl':ttl,'rq_worker_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'limitation':'Counters cover current worker lifetimes, not a complete24h history; previous/dead workers and earlier lost counters are not reconstructed. No registry cleanup or jobs submitted.'}))
