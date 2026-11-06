"""Local disposable-filesystem/Redis boundary checks; never connect to production."""
import copy, hashlib, importlib.util, json, os, subprocess, tempfile, time
from pathlib import Path
import redis
import pyarrow as pa
import pyarrow.parquet as pq
path=Path(__file__).with_name('read_general_catalog_evidence.py')
spec=importlib.util.spec_from_file_location('catalog_evidence_review',path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
checks=[]
def check(name,condition):
 assert condition,name
 checks.append(name)
def tree(path):return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);runs=root/'runs';runs.mkdir();scope=runs/'owned';scope.mkdir();locks=root/'locks'
 os.environ['QUERY_CATALOG_REFRESH_ENABLED']='true';os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps([{'path':str(runs),'namespace':'review:owned','coordination':str(locks),'layout':'flat'}])
 from wepppy.query_engine import catalog_refresh as cr
 (scope/'wepp.nodb').write_text('{}');pq.write_table(pa.table({'x':[1,2,3]}),scope/'data.parquet')
 started=time.time()-1;cr.record_catalog_refresh(scope);cr.refresh_catalog(scope)
 roots=cr.configured_roots();before=tree(root)
 row=helper.scope_readback(str(scope),roots,started)
 check('current raw scope',row['current'] and row['published_during_cycle'] and not row['receipts'])
 artifact=helper.artifact_readback({'path':str(scope),'datasets':['data.parquet']},roots,started)
 check('real planner executor agrees with parquet',artifact['queries'][0]['rows']==3)
 check('read-only artifact boundary',tree(root)==before)
 receipt=cr.record_catalog_refresh(scope,'data.parquet');pending_before=tree(root)
 row=helper.scope_readback(str(scope),roots,started);ages=helper.age_summary([row],time.time())
 check('pending receipt measured',not row['current'] and ages['pending_receipts_observed']==1 and ages['oldest_pending_receipt_age_seconds']>=0)
 check('published attempt preserves known prior age',row['publication_at'] is not None)
 check('pending readback does not acknowledge',tree(root)==pending_before)
 unknown=runs/'unknown';unknown.mkdir();(unknown/'wepp.nodb').write_text('{}')
 unknownrow=helper.scope_readback(str(unknown),roots,started);unknownages=helper.age_summary([unknownrow],time.time())
 check('unknown publication stays unknown',unknownrow['publication_at'] is None and unknownages['noncurrent_unknown_last_publication']==1)
 known_old={**unknownrow,'current':True,'publication_at':started-50,'published_during_cycle':False}
 oldages=helper.age_summary([known_old],time.time())
 check('old current publication not conflated with unresolved',oldages['current_publications_predating_cycle']==1 and oldages['pending_or_noncurrent_writable_scopes']==0)
 try:helper.timestamp(1)
 except ValueError:checks.append('invalid timestamp rejected')
 else:raise AssertionError('invalid timestamp accepted')
 try:helper.scope_readback(str(root/'outside'),roots,started)
 except ValueError:checks.append('out-of-root locator rejected')
 else:raise AssertionError('outside path accepted')
 sock=str(root/'redis.sock');process=subprocess.Popen(['redis-server','--port','0','--unixsocket',sock,'--save','','--appendonly','no'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  r=redis.Redis(unix_socket_path=sock)
  for _ in range(100):
   try:r.ping();break
   except redis.ConnectionError:time.sleep(.02)
  cursor={'cycle':'target','completed_at':time.time(),'cycle_started_at':started,'pending':[]}
  r.set('inventory',json.dumps(cursor));r.set('inventory:discovery',json.dumps({'cycle':'target','completed_at':time.time()}));r.set('inventory:generation','generation');r.sadd('inventory:scopes',str(scope));r.sadd('dirty',str(unknown));r.set('ledger',json.dumps({'jobs':{}}))
  before=r.dump('inventory:scopes');snap=helper.retained_snapshot(r,'inventory','dirty','ledger',10)
  check('complete retained union',snap['populations']['cycle']==[str(scope)] and snap['populations']['dirty']==[str(unknown)])
  check('snapshot does not mutate',r.dump('inventory:scopes')==before)
  check('clean cycle accepted',helper.clean_cycle(snap,'target'))
  degraded=copy.deepcopy(snap);degraded['discovery']['errors']=['new_error'];check('final same-cycle error rejected',not helper.clean_cycle(degraded,'target'))
  incomplete=copy.deepcopy(snap);incomplete['cursor'].pop('completed_at');check('lost completion rejected',not helper.clean_cycle(incomplete,'target'))
  try:helper.retained_snapshot(r,'inventory','dirty','ledger',0)
  except ValueError:checks.append('scope bound enforced')
  else:raise AssertionError('scope bound ignored')
 finally:process.terminate();process.wait(timeout=5)
print(json.dumps({'passed':len(checks),'redis_version':redis.__version__,'checks':checks},indent=2))
