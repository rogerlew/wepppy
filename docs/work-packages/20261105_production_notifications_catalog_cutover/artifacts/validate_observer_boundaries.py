import ast, copy, json, os, subprocess, tempfile, time, types, typing
from datetime import datetime, timezone
from pathlib import Path
import redis
collector=Path('/home/workdir/wepppy/docs/work-packages/20261105_production_notifications_catalog_cutover/artifacts/observe_general_catalog.py')
def funcs(path,names):return [n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names]
functions=funcs(collector,{'sample','save'})+funcs('/home/workdir/wepppy/tools/query_catalog_pilot.py',{'ordinary_waits'})+funcs('/home/workdir/wepppy/wepppy/rq/_query_catalog_admission.py',{'execution_uncertain','execution_outstanding'})
code=compile(ast.Module(body=functions,type_ignores=[]),str(collector),'exec')
now=1800000000.0;activated=now-100
iso=lambda x:datetime.fromtimestamp(x,timezone.utc).isoformat().encode()
base={'cursor':{'cycle':'fresh','cycle_started_at':activated+1,'completed_at':now-1,'pending':[]},'discovery':{'cycle':'fresh','completed_at':now-2},'bindings':{},'statuses':{},'waiting':[],'started':['ordinary'],'ordinary':{'ordinary':{'description':b'ordinary.work()','enqueued_at':iso(activated+2),'started_at':iso(activated+3)}},'proof':{'cycle':'fresh','artifacts_verified':True,'pending_age_coverage_accepted':True},'activation':activated}
results=[]
with tempfile.TemporaryDirectory() as temp:
 socket=str(Path(temp)/'redis.sock')
 process=subprocess.Popen(['redis-server','--port','0','--unixsocket',socket,'--unixsocketperm','700','--save','','--appendonly','no'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  r=redis.Redis(unix_socket_path=socket)
  for attempt in range(100):
   try:r.ping();break
   except redis.ConnectionError:time.sleep(.02)
  else:raise RuntimeError('Disposable Redis failed to start')
  def run(name,mutate,expected,race=None):
   r.flushdb();d=copy.deepcopy(base);mutate(d)
   r.set('ledger',json.dumps({'jobs':d['bindings']}));r.set('inventory',json.dumps(d['cursor']));r.set('inventory:discovery',json.dumps(d['discovery']))
   for jid,data in d['ordinary'].items():r.hset('rq:job:'+jid,mapping={k:v for k,v in data.items() if v is not None})
   for jid,status in d['statuses'].items():
    if status is not None:r.hset('rq:job:'+jid,'status',status)
   if d['waiting']:r.rpush('rq:queue:default',*d['waiting'])
   if d.get('paused'):r.set('pause',b'another-owner')
   class Registry:
    def __init__(self,*a,**k):pass
    def get_job_ids(self,**k):return d['started']
   class Proxy:
    def __init__(self,p):self.p=p;self.changed=False
    def __enter__(self):self.p.__enter__();return self
    def __exit__(self,*args):return self.p.__exit__(*args)
    def __getattr__(self,name):return getattr(self.p,name)
    def get(self,key):
     if race=='before_read' and key=='ledger' and not self.changed:
      r.set('ledger',json.dumps({'jobs':{'new':{'claimed':False}}}));self.changed=True
     return self.p.get(key)
    def execute(self):
     if race=='during_watch':r.set('inventory',json.dumps({**d['cursor'],'last_tick_at':now}))
     return self.p.execute()
   class Client:
    ledger_reads=0
    def get(self,key):
     if key=='ledger':
      self.ledger_reads+=1
      if race=='maintenance_admission' and self.ledger_reads==2:
       r.set('ledger',json.dumps({'jobs':{'ordinary':{'claimed':True}}}));r.hset('rq:job:ordinary','status','started')
     return r.get(key)
    def __getattr__(self,name):return getattr(r,name)
    def pipeline(self):return Proxy(r.pipeline())
   with tempfile.TemporaryDirectory(dir=temp) as tmp:
    root=Path(tmp);(root/'artifact-acceptance.json').write_text(json.dumps(d['proof']))
    env={'Any':typing.Any,'json':json,'os':os,'time':types.SimpleNamespace(time=lambda:now),'datetime':datetime,'timezone':timezone,'root':root,'samples':0,'target_cycle':None,'baseline_cycle':'old','activation':d['activation'],'deadline':now+100,'ordinary':d.get('initial_ordinary',{}),'maintenance_seen':set(),'r':Client(),'q':types.SimpleNamespace(key='rq:queue:default'),'key':'inventory','StartedJobRegistry':Registry,'cq':types.SimpleNamespace(PREFIX='query_catalog_refresh_',DESCRIPTION='Query catalog maintenance',consumer_status=lambda q:{'compatible':12,'incompatible':[],'suspended':False}),'TERMINAL':frozenset({'finished','failed','stopped','canceled'}),'redis':redis}
    exec(code,env);env['admission']=types.SimpleNamespace(LEDGER_KEY='ledger',PAUSE_KEY='pause',execution_uncertain=env['execution_uncertain'],execution_outstanding=env['execution_outstanding'])
    try:outcome=env['sample']()
    except (AssertionError,RuntimeError) as exc:outcome=str(exc)
    assert outcome==expected,(name,outcome,expected)
    results.append({'case':name,'result':outcome,'completed_file':(root/'completed.json').exists()})
  run('fresh_cycle_and_new_started_arrival',lambda d:None,True)
  run('paused_preflight_cannot_complete',lambda d:d.update(activation=None),False)
  run('old_completed_cycle_cannot_complete',lambda d:(d['cursor'].update(cycle='old',cycle_started_at=activated-100),d['discovery'].update(cycle='old'),d['proof'].update(cycle='old')),False)
  run('old_arrival_cannot_satisfy_acceptance',lambda d:d['ordinary']['ordinary'].update(enqueued_at=iso(activated-50),started_at=iso(activated-49)),False)
  run('preexisting_300s_backlog_stops',lambda d:(d.update(waiting=['ordinary'],started=[]),d['ordinary']['ordinary'].update(enqueued_at=iso(now-301),started_at=None)),'Ordinary wait stop threshold')
  run('missing_timestamp_stops',lambda d:d['ordinary']['ordinary'].update(enqueued_at=None),'Ordinary arrival timestamps unavailable')
  run('failed_maintenance_stops',lambda d:(d['bindings'].update(maintenance={'claimed':True}),d['statuses'].update(maintenance=b'failed')),'Maintenance terminal failure: maintenance')
  run('discovery_errors_stop',lambda d:d['discovery'].update(errors=['StorageUnavailable']),'Discovery failure')
  run('wrong_cycle_proof_stops',lambda d:d['proof'].update(cycle='wrong'),'Artifact/age acceptance missing')
  run('new_pause_stops',lambda d:d.update(paused=True),'Observation interrupted by admission pause')
  run('scheduler_tick_not_ordinary_acceptance',lambda d:d['ordinary']['ordinary'].update(description=b'wepppy.rq.query_catalog_rq.reconcile_query_catalogs()'),False)
  run('scheduler_tick_old_backlog_stops',lambda d:(d.update(waiting=['ordinary'],started=[]),d['ordinary']['ordinary'].update(description=b'wepppy.rq.query_catalog_rq.reconcile_query_catalogs()',enqueued_at=iso(now-301),started_at=None)),'Ordinary wait stop threshold')
  run('unaccounted_maintenance_stops',lambda d:d['ordinary']['ordinary'].update(description=b'wepppy.rq.query_catalog_rq.refresh_query_catalog_rq()'),'Unaccounted maintenance-looking job: ordinary')
  run('ledger_changed_before_checkpoint_defers',lambda d:None,False,race='before_read')
  run('actual_watch_error_defers',lambda d:None,False,race='during_watch')
  run('canonical_description_unaccounted_maintenance_stops',lambda d:d['ordinary']['ordinary'].update(description=b'Query catalog maintenance'),'Unaccounted maintenance-looking job: ordinary')
  run('canonical_maintenance_admitted_mid_sample_excluded',lambda d:d['ordinary']['ordinary'].update(description=b'Query catalog maintenance'),False,race='maintenance_admission')
  run('previously_misclassified_ordinary_purged',lambda d:(d['bindings'].update(ordinary={'claimed':True}),d['statuses'].update(ordinary=b'finished'),d.update(initial_ordinary={'ordinary':{'enqueued_at':iso(activated+2).decode(),'started_at':iso(activated+3).decode()}})),False)
 finally:
  process.terminate();process.wait(timeout=5)
print(json.dumps({'checks_passed':len(results),'redis':redis.__version__,'results':results},indent=2))
