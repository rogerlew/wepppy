import json
import redis
from rq.job import Job
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.rq.job_info import get_wepppy_rq_job_info
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));key='query-catalog:inventory:9d4205ed0955b7518cd3b2a8556a00c6e83cf29b7a8ca97b2a32a165d341a6d4'
s=json.loads(c.get(key+':discovery'));j=Job.fetch(s['job_id'],connection=c)
assert j.get_status()=='finished' and s.get('completed_at') and not s.get('errors') and c.llen(key+':frontier')==0
assert c.scard(key+':scopes')==c.xlen(key+':stream')>0
print(json.dumps({'state':'passed','job_status':j.get_status(),'discovery':s,'frontier':0,'scopes':c.scard(key+':scopes'),'stream':c.xlen(key+':stream'),'job_tree':get_wepppy_rq_job_info(j.id),'scope':'post-driver API assertion correction; no rerun or production project writes'},default=str))
for suffix in ('',':discovery',':frontier',':seen',':scopes',':stream',':generation'):c.expire(key+suffix,7*86400)
