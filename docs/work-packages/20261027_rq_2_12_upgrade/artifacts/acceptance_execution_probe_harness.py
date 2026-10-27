import json
from pathlib import Path
import redis
from rq import Queue,Worker
from rq.job import Job
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
ART=Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts')
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
q=Queue('default',connection=c)
raw=[x.decode() for x in c.zrange(q.started_job_registry.key,0,-1)]
ids=q.started_job_registry.get_job_ids(cleanup=False)
owned=[]
for i in ids:
 j=Job.fetch(i,connection=c)
 if 'rq212-20261027-upgraded' in j.args:
  owned.append({'job_id':i,'status':j.get_status().value,'raw_members':[x for x in raw if x.startswith(i+':')],
                'executions':[{'id':x.id,'job_id':x.job_id} for x in j.get_executions()],
                'webhooks':j.webhooks,
                'workers':[{'worker':w.name,'current_job':w.get_current_job_id()} for w in Worker.all(connection=c) if w.get_current_job_id()==i]})
assert owned,'No owned active job at sample'
assert all(x['raw_members'] and x['executions'] and x['workers'] and not x['webhooks'] for x in owned)
(ART/'acceptance_live_execution_tracking.json').write_text(json.dumps(owned,indent=2))
print('PASS live executions',len(owned))
