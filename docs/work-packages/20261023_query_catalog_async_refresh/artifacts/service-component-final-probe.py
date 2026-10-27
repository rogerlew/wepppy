"""Read-only catalog collection/validation; no lifecycle or publication APIs."""
import hashlib,json,logging,os,sys,time
from pathlib import Path
logging.disable(logging.CRITICAL)
process_started=time.monotonic()
item=json.load(sys.stdin)
assert (os.getuid(),os.getgid())==(1002,130)
from wepppy.query_engine import catalog_refresh as cr
from wepppy.query_engine import activate as activation_export
import importlib
act=importlib.import_module('wepppy.query_engine.activate')
from wepppy.wepp.interchange import _rust_interchange
import pyarrow.parquet
native=_rust_interchange.require_wepppyo3_interchange('readonly service profile','catalog_scan')
source_hashes={name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in [('catalog_refresh',cr),('activate',act),('rust_boundary',_rust_interchange)]}
source_hashes['native']={name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in list(sys.modules.items()) if name.startswith('wepppyo3.wepp_interchange') and str(getattr(module,'__file__','')).endswith('.so')}
# Defense-in-depth for Python mutations. Rust scanner source was separately inspected.
blocked=[]
def audit(event,args):
 mutation=event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','os.chmod','os.chown'}
 if event=='open':
  mode=args[1] or '';flags=args[2]
  mutation=any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
 if mutation:
  blocked.append(event);raise PermissionError('read-only profiling forbids filesystem mutation')
sys.addaudithook(audit)
base=Path(item['path']);results=[];phase='preflight'
def emit(event,**fields):print(json.dumps(dict(marker='component-profile',event=event,digest=item['digest'],namespace=item['namespace'],process_elapsed_seconds=time.monotonic()-process_started,**fields)),flush=True)
emit('start',uid=os.getuid(),gid=os.getgid(),source_sha256=source_hashes)
try:
 for attempt in [1,2]:
  phase='collect';emit('phase',attempt=attempt,phase=phase);started=time.monotonic()
  catalog=cr._updated_catalog(base,None,[None],prefer_canonical=True)
  collect=time.monotonic()-started
  phase='verify';emit('phase',attempt=attempt,phase=phase,collect_seconds=collect,entry_count=len(catalog['files']));started=time.monotonic()
  cr._verify_required(base,catalog,[None])
  verify=time.monotonic()-started
  result=dict(attempt=attempt,collect_seconds=collect,verify_seconds=verify,component_seconds=collect+verify,entry_count=len(catalog['files']),entries_sha256=hashlib.sha256(json.dumps(catalog['files'],sort_keys=True).encode()).hexdigest())
  results.append(result);emit('pass',**result)
 emit('result',status='passed',passes=results,blocked_mutations=blocked)
except Exception as exc:
 # Diagnostic process boundary: never copy exception messages containing project paths.
 emit('result',status='error',phase=phase,error_type=type(exc).__name__,errno=getattr(exc,'errno',None),passes=results,blocked_mutations=blocked)
 sys.exit(1)
