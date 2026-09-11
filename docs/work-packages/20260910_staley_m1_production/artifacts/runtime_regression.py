"""Run only against the dedicated disposable development project."""
from pathlib import Path
import json
import redis
from rq import Queue
from redis.exceptions import ConnectionError
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.microservices.rq_engine import postfire_debris_flow_routes as routes
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.submission_recovery import rq_submission_lock
m=json.loads(Path('/workdir/wepppy/docs/work-packages/20260910_staley_m1_production/artifacts/local_smoke_project.json').read_text())
wd=m['wd'];runid=m['runid'];assert runid.startswith('pfdf-smoke-')
controller=p.mutable(wd);before=controller.state
prep=RedisPrep.getInstance(wd);old_marker=prep.get_rq_job_id('postfire_m1_rq')
record,_=routes.new_attempt(wd,'run_attempt',{'inputs':{},'dnbr':None,'frequency':'cli'})
original=RedisPrep.set_rq_job_id
with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
 try:
  with rq_submission_lock(connection,f'{runid}:postfire-admission',lifecycle_key=runid):
   def fail(*args,**kwargs):raise ConnectionError('Injected before marker persistence')
   RedisPrep.set_rq_job_id=fail
   try:routes.enqueue(Queue(connection=connection),wd,runid,'run_attempt',record)
   except ConnectionError:pass
   else:raise AssertionError('Expected injected failure')
   pending=p.state_at(wd)['run_attempt'];assert pending['job_id'] and pending['job_id']!=old_marker
   assert pending['phase']=='enqueue_unknown'
   RedisPrep.set_rq_job_id=original
   reconciled=p.reconcile_attempts(wd,p.state_at(wd),connection,persist=True)
   assert reconciled['run_attempt']['phase']=='failed' and reconciled['run_attempt']['retryable']
   assert reconciled['run_attempt']['job_id']==pending['job_id']
 finally:
  RedisPrep.set_rq_job_id=original
  controller.change(lambda state:state.update(before))
  if old_marker:prep.set_rq_job_id('postfire_m1_rq',old_marker)
print(json.dumps({'exact_missing_receipt_recovered':True,'previous_receipt_not_reused':True,'durable_state_restored':True}))
