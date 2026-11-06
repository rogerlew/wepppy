import json,os,redis
from rq import Queue
from wepppy.rq import query_catalog_rq as cq,_query_catalog_admission as a
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
r=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
ledger=json.loads(r.get(a.LEDGER_KEY));rows=[]
for jid,b in ledger['jobs'].items():
 status=r.hget('rq:job:'+jid,'status');status=status.decode() if status else None
 rows.append({'id':jid,'status':status,'outstanding':a.execution_outstanding(b,status),'uncertain':a.execution_uncertain(b,status)})
print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'configuration':cq.catalog_worker_configuration(),'consumers':cq.consumer_status(Queue('default',connection=r)),'pause':(r.get(a.PAUSE_KEY) or b'').decode(),'ledger':rows,'queues':{q:{'queued':r.llen('rq:queue:'+q),'started':r.zcard('rq:wip:'+q)} for q in ('default','batch','fork-archive')}},indent=2))
