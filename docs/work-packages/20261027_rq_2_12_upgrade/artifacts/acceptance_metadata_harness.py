import json
from pathlib import Path
import redis
from rq.job import Job
from rq import Worker
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
ART=Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts')
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
d=json.loads((ART/'acceptance_upgraded.json').read_text());ids={}
def walk(x):
 if isinstance(x,dict):
  if 'job_id' in x:ids[x['job_id']]=None
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(d)
ids[d['blocker_job_id']] = None
ids['019bd6c0-81e8-4fef-a01c-22495fc2d809'] = None
for name in ('acceptance_archive_restore.json','acceptance_restore_repair_initial_failure.json','acceptance_restore_repair.json'):
 walk(json.loads((ART/name).read_text()))
r=[]
for i in ids:
 j=Job.fetch(i,connection=c)
 assert not j.webhooks
 r.append({'job_id':i,'status':j.get_status().value,'function':j.func_name,
 'auth_actor':j.meta.get('auth_actor'),'correlation_id':j.meta.get('correlation_id'),
 'profile_keys':[k for k in j.meta if 'profile' in k], 'webhook_count':len(j.webhooks),
 'started_at':j.started_at,'ended_at':j.ended_at})
workers=[{'name':w.name,'current_job_id':w.get_current_job_id(),'state':w.get_state()} for w in Worker.all(connection=c)]
assert not any(w['current_job_id'] in ids for w in workers)
(ART/'acceptance_metadata_final.json').write_text(json.dumps({'jobs':r,'workers':workers},indent=2,default=str))
print('PASS',len(r),'owned jobs (44 API plus one blocker) with no configured webhooks; no owned active jobs')
