"""Bounded operator observation; never clears another owner's pause or deletes work."""
import json,os,signal,sys,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
import redis
from rq import Queue
from rq.registry import StartedJobRegistry
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.rq import query_catalog_rq as cq, _query_catalog_admission as admission
from wepppy.query_engine import catalog_refresh as cr
from tools.query_catalog_pilot import ordinary_waits

if not __debug__:raise RuntimeError('Optimized Python forbidden')
assert (os.getuid(),os.getgid())==(1002,130)
root=Path(sys.argv[1]);manifest=json.loads((root/'manifest.json').read_text())
assert root.is_absolute() and root.resolve()==root and root.stat().st_mode&0o077==0
assert manifest['environment']=='https://wepp.cloud' and os.getenv('EXTERNAL_HOST')=='wepp.cloud'
assert manifest['state']=='authorized_observation' and manifest['expected_configuration']==cq.catalog_worker_configuration()
assert cr.catalog_refresh_enabled()
r=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));q=Queue('default',connection=r)
owner=manifest['pause_owner'].encode();key='query-catalog:inventory:'+cq._configuration_id()
start=time.time();deadline=min(start+manifest['maximum_observation_seconds'],manifest['absolute_deadline']);ordinary={};maintenance_seen=set();samples=0;passed=False
assert deadline>start
marker=os.open(root/'observer-start.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(marker,'w') as f:json.dump({'started_at':start,'deadline':deadline,'pid':os.getpid()},f);f.flush();os.fsync(f.fileno())
activation=None;target_cycle=None;baseline_cycle=json.loads(r.get(key) or '{}').get('cycle')

def save(name,data):
 p=root/name;tmp=p.with_suffix('.tmp');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as f:json.dump(data,f,default=str);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)

def pause(reason):
 r.set(admission.PAUSE_KEY,owner,nx=True)
 save('stop.json',{'time':time.time(),'reason':reason,'pause_owned':r.get(admission.PAUSE_KEY)==owner})

def interrupted(signum,frame):raise RuntimeError('Observer interrupted or sample deadline exceeded')
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,interrupted)

def sample():
 global samples,target_cycle
 now=time.time();consumers=cq.consumer_status(q)
 if activation is not None:assert not r.exists(admission.PAUSE_KEY),'Observation interrupted by admission pause'
 assert consumers=={'compatible':12,'incompatible':[],'suspended':False},'Consumer configuration/suspension changed'
 ledger=json.loads(r.get(admission.LEDGER_KEY));bindings=ledger['jobs'];assert len(bindings)<=7,'Cap exceeded'
 maintenance_seen.update(bindings)
 for jid in maintenance_seen:ordinary.pop(jid,None)
 uncertain=[];outstanding=[];statuses={}
 for jid,binding in bindings.items():
  status=r.hget('rq:job:'+jid,'status');status=status.decode() if status else None;statuses[jid]=status
  assert status not in {'failed','stopped','canceled'},'Maintenance terminal failure: '+jid
  if admission.execution_uncertain(binding,status):uncertain.append(jid)
  if admission.execution_outstanding(binding,status):outstanding.append(jid)
 assert not uncertain,'Uncertain maintenance execution'
 cursor=json.loads(r.get(key) or '{}');discovery=json.loads(r.get(key+':discovery') or '{}')
 assert not discovery.get('errors') and discovery.get('state') not in {'failed','unavailable'},'Discovery failure'
 assert not cursor.get('failures') and not cursor.get('cycle_errors') and not cursor.get('unavailable_namespaces'),'Catalog cycle degraded'
 waiting=[x.decode() for x in r.lrange(q.key,0,-1)]
 started=StartedJobRegistry('default',connection=r).get_job_ids(cleanup=False)
 for jid in waiting+started:
  if jid in maintenance_seen:continue
  fields=r.hmget('rq:job:'+jid,'description','enqueued_at','started_at')
  description=(fields[0] or b'').decode()
  if jid.startswith(cq.PREFIX) or description == cq.DESCRIPTION or description.startswith(('wepppy.rq.query_catalog_rq.refresh_query_catalog_rq','wepppy.rq.query_catalog_rq.inventory_query_catalog_rq')):
   refreshed=json.loads(r.get(admission.LEDGER_KEY))
   if jid in refreshed['jobs']:
    maintenance_seen.add(jid);ordinary.pop(jid,None);continue
   raise RuntimeError('Unaccounted maintenance-looking job: '+jid)
  scheduler_tick=description.startswith('wepppy.rq.query_catalog_rq.reconcile_query_catalogs')
  ordinary[jid]={k:v.decode() if v else None for k,v in zip(['enqueued_at','started_at'],fields[1:])};ordinary[jid]['scheduler_tick']=scheduler_tick
 for jid in ordinary:
  fields=r.hmget('rq:job:'+jid,'enqueued_at','started_at')
  if fields[0]:ordinary[jid].update({k:v.decode() if v else None for k,v in zip(['enqueued_at','started_at'],fields)})
 eligible={}
 for jid,fields in ordinary.items():
  raw=fields.get('enqueued_at')
  if activation is not None and raw and not fields.get('scheduler_tick'):
   stamp=datetime.fromisoformat(raw.replace('Z','+00:00'))
   stamp=stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
   if stamp.timestamp()>=activation:eligible[jid]=fields
 waits=ordinary_waits(ordinary,waiting,now)
 arrival_waits=ordinary_waits(eligible,waiting,now)
 assert not waits['unavailable_timestamps'],'Ordinary arrival timestamps unavailable'
 assert waits['max_observed_wait_seconds']<300,'Ordinary wait stop threshold'
 paths={x['path'] for x in cursor.get('pending',[]) if x.get('path')}
 paths.update(b['scope']['wd'] for b in bindings.values() if b.get('scope'))
 ages=[]
 for path in sorted(paths):
  state=cr.catalog_refresh_status(path)
  if state.get('oldest_pending_at'):ages.append({'path':path,'oldest_pending_at':state['oldest_pending_at']})
 row={'time':now,'consumers':consumers,'ledger_jobs':len(bindings),'outstanding':outstanding,'uncertain':uncertain,'cursor':cursor,'discovery':discovery,'ordinary':waits,'post_activation_arrival_waits':arrival_waits,'ordinary_seen':eligible,'activation':activation,'target_cycle':target_cycle,'tracked_pending_ages':ages,'age_coverage':'cursor-pending and currently admitted scopes only; not an assertion of global oldest receipt','cycle_elapsed_seconds':now-cursor['cycle_started_at'] if cursor.get('cycle_started_at') else None}
 with (root/'samples.jsonl').open('a') as f:f.write(json.dumps(row,default=str)+'\n');f.flush()
 samples+=1;save('heartbeat.json',{'time':time.time(),'sample_started_at':now,'samples':samples,'deadline':deadline,'pid':os.getpid()})
 acceptance=root/'artifact-acceptance.json'
 if activation is not None and target_cycle is None and cursor.get('cycle') != baseline_cycle and cursor.get('cycle_started_at',0)>=activation:
  target_cycle=cursor['cycle'];save('target-cycle.json',{'cycle':target_cycle,'started_at':cursor['cycle_started_at'],'activation':activation,'baseline_cycle':baseline_cycle})
 if activation is not None and target_cycle is not None and cursor.get('cycle')==target_cycle and cursor.get('completed_at') and discovery.get('completed_at') and cursor.get('cycle')==discovery.get('cycle') and not any(p.get('cycle') for p in cursor.get('pending',[])) and not outstanding and any(v.get('started_at') for v in eligible.values()) and acceptance.exists():
  proof=json.loads(acceptance.read_text())
  assert proof['cycle']==cursor['cycle'] and proof['artifacts_verified'] and proof['pending_age_coverage_accepted'],'Artifact/age acceptance missing'
  try:
   with r.pipeline() as checkpoint:
    checkpoint.watch(admission.LEDGER_KEY,admission.PAUSE_KEY,key,key+':discovery',*['rq:job:'+jid for jid in bindings])
    if checkpoint.exists(admission.PAUSE_KEY):raise RuntimeError('Admission paused at completion')
    if json.loads(checkpoint.get(admission.LEDGER_KEY))!=ledger or json.loads(checkpoint.get(key) or '{}')!=cursor or json.loads(checkpoint.get(key+':discovery') or '{}')!=discovery:return False
    for jid,status in statuses.items():
     current=checkpoint.hget('rq:job:'+jid,'status');current=current.decode() if current else None
     if current!=status:return False
    checkpoint.multi();checkpoint.get(admission.PAUSE_KEY);checkpoint.execute()
  except redis.WatchError:return False
  save('completed.json',{'time':now,'cycle':cursor['cycle'],'samples':samples,'ordinary_arrivals':eligible,'activation':activation,'baseline_cycle':baseline_cycle,'artifact_proof':proof});return True
 return False

reason='observer_stopped'
try:
 assert r.get(admission.PAUSE_KEY)==owner,'Expected owned pause required at launch'
 signal.alarm(45);sample();signal.alarm(0)
 activation=time.time();ordinary.clear()
 assert r.eval("if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",1,admission.PAUSE_KEY,owner)==1
 save('activation.json',{'started_at':activation,'deadline':deadline,'baseline_cycle':baseline_cycle,'configuration':cq.catalog_worker_configuration(),'inventory_key':key})
 while time.time()<deadline:
  signal.alarm(45);passed=sample();signal.alarm(0)
  if passed:break
  time.sleep(10)
 if not passed:reason='deadline_without_complete_evidence'
finally:
 signal.alarm(0)
 if not passed:pause(reason)
