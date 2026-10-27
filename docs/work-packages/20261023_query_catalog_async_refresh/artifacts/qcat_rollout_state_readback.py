import hashlib,json,os,socket,time
from pathlib import Path
base=Path('/workdir/wepppy')
files=['wepppy/rq/query_catalog_rq.py','wepppy/rq/_query_catalog_inventory.py','wepppy/query_engine/app/server.py','wepppy/query_engine/app/mcp/router.py']
print(json.dumps({'observed_at':time.time(),'hostname':socket.gethostname(),'uid':os.getuid(),'gid':os.getgid(),'refresh_enabled_environment':os.environ.get('QUERY_CATALOG_REFRESH_ENABLED'),'explicit_roots_set':bool(os.environ.get('QUERY_CATALOG_ROOTS_JSON')),'on_disk_sources':{p:hashlib.sha256((base/p).read_bytes()).hexdigest() if (base/p).is_file() else None for p in files},'limitation':'Environment and on-disk source readback; does not inspect function objects already loaded by long-lived processes.'}))
