import json,time
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));key='query-catalog:validation:20261027:legacy-stream-0035'
with c.pipeline() as p:
 p.watch(key+':discovery');s=json.loads(p.get(key+':discovery'))
 assert s['job_id']=='owned-readonly-probe-0035' and not s.get('completed_at')
 evidence={'time':time.time(),'before':s,'frontier':p.llen(key+':frontier'),'scopes':p.scard(key+':scopes'),'seen':p.scard(key+':seen'),'reason':'owned read-only candidate deliberately superseded; successor must replay current directory without losing emitted children'}
 s['job_id']='owned-readonly-resume-0055';p.multi();p.set(key+':discovery',json.dumps(s));p.set(key+':restart-evidence',json.dumps(evidence));p.execute()
 print(json.dumps(evidence))
