import json,time
import redis
from rq import Queue,worker_registration
from rq.registry import StartedJobRegistry
from rq.suspension import WORKERS_SUSPENDED
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue('batch',connection=c);registry=StartedJobRegistry('batch',connection=c)
for n in range(20):
 states={}
 for key in worker_registration.get_keys(queue=q):
  queues,state,death=c.hmget(key,'queues','state','death')
  if death is not None or c.ttl(key)<=0 or b'batch' not in (queues or b'').split(b','):continue
  name=(state or b'unknown').decode();states[name]=states.get(name,0)+1
 now=time.time()
 print(json.dumps({'epoch':now,'queued':q.count,'started_registry_total':c.zcard(registry.key),'unexpired_executions':c.zcount(registry.key,now,'+inf'),'live_consumer_states':states,'suspended':bool(c.exists(WORKERS_SUSPENDED)),'method':'read-only raw registry/worker fields; no cleanup; no jobs submitted'}),flush=True)
 if n<19:time.sleep(30)
