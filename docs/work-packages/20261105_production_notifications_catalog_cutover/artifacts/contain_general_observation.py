import json,os,time,redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
if os.environ.get('EXTERNAL_HOST')!='wepp.cloud':raise RuntimeError('Wrong environment')
r=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));key='query-catalog:batch-admission:v1:paused';owner=b'production-cutover-20261106:general-observation'
r.set(key,owner,nx=True)
print(json.dumps({'time':time.time(),'admission_paused':bool(r.exists(key)),'owned_pause':r.get(key)==owner,'ttl':r.ttl(key),'admitted_work_retained':True}))
