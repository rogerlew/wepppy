import json,os,time,hashlib
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
p=Path('/geodata/weppcloud_runs/.qcat-role-20261027-0020')
anchor=(p/'probe.json').read_bytes()
assert json.loads(anchor)['probe']=='qcat-role-20261027-0020'
os.environ['QUERY_CATALOG_REFRESH_ENABLED']='false'
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps([{'path':'/geodata/weppcloud_runs','namespace':'qcat-role-legacy-20261027','coordination':'/wc1/query-catalog-validation/20261026/legacy-role-locks','layout':'flat'}])
from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard
from wepppy.nodb.project_config_update import project_config_lifecycle_guard
result={'uid':os.getuid(),'gid':os.getgid(),'anchor_sha256':hashlib.sha256(anchor).hexdigest(),'catalog_guard':None,'project_config_guard':None}
start=time.monotonic()
try:
 with catalog_lifecycle_guard(p):
  result['catalog_guard']='passed'
  try:
   with project_config_lifecycle_guard(p):result['project_config_guard']='passed'
  except OSError as e:result['project_config_guard']={'error':type(e).__name__,'errno':e.errno,'message':str(e)}
finally:
 result['elapsed_seconds']=time.monotonic()-start
 print(json.dumps(result),flush=True)
