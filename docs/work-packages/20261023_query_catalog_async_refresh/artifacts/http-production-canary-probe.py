"""Private interpreter overlay; no listener or live module file changes."""
import asyncio
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import threading
import time

ROOT=Path('/wc1/query-catalog-validation/20261026/async-preflight-1719')
WD=ROOT/'runs/aa/aa-preflight'
START=time.monotonic()
def emit(event, **data):
    print(json.dumps(dict(event=event, epoch=time.time(), elapsed=time.monotonic()-START, **data)),flush=True)
def timeout(signum,frame):
    raise TimeoutError('150-second isolated HTTP canary budget')
signal.signal(signal.SIGALRM,timeout);signal.alarm(150)
assert (os.getuid(),os.getgid())==(1002,130)
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps([dict(path=str(ROOT/'runs'),namespace='qcat-rollout-preflight-20261026',coordination=str(ROOT/'locks'),layout='sharded')])
os.environ['QUERY_CATALOG_REFRESH_ENABLED']='false'
# No production signing secret is read or printed. Configuration is interpreter-local.
for name in list(os.environ):
    if name.startswith('WEPP_MCP_JWT_'):os.environ.pop(name)
secret=secrets.token_hex(32)
os.environ['WEPP_MCP_JWT_SECRET']=secret
os.environ['WEPP_MCP_JWT_ALGORITHMS']='HS256'
from wepppy.query_engine.app import server
from wepppy.query_engine.app.mcp import router,auth
import wepppy.query_engine.app.mcp as package
sources={}
for module,name in [(router,'router.py'),(server,'server.py')]:
    source=(Path(__file__).parent/name).read_text()
    canonical=module.__file__
    sources[module.__name__]=dict(candidate_sha256=hashlib.sha256(source.encode()).hexdigest(),canonical_file=canonical,live_file_sha256=hashlib.sha256(Path(canonical).read_bytes()).hexdigest())
    exec(compile(source,canonical,'exec'),module.__dict__)
    assert module.__file__==canonical
package.create_mcp_app=router.create_mcp_app
auth.get_auth_config.cache_clear()
slug='qcat-isolated-http-canary'
def resolve(candidate):
    if candidate!=slug:raise FileNotFoundError(candidate)
    return WD
server.resolve_run_path=resolve
router.resolve_run_path=resolve
app=server.create_app()
assert any(getattr(route,'path',None)=='/mcp' for route in app.routes)
from wepppy.query_engine import catalog_refresh as cr
from wepppy.query_engine.activate import activate_query_engine
activate_query_engine(WD,run_interchange=False,force_refresh=True)
cr.ensure_catalog_fresh(WD,required_paths=['probe.parquet'])
asset_sha=hashlib.sha256((WD/'probe.parquet').read_bytes()).hexdigest()
receipt=cr.record_catalog_refresh(WD,'probe.parquet')
locks=list((ROOT/'locks').glob('*.lock'));assert len(locks)==1
inode=locks[0].stat().st_ino
entered=threading.Event(); original=fcntl.lockf
calls=[]
def timed(fd,operation,*args):
    start=time.monotonic()
    if operation==fcntl.LOCK_EX:entered.set();emit('guard_wait_started')
    value=original(fd,operation,*args)
    calls.append(dict(operation=operation,seconds=time.monotonic()-start))
    emit('lockf_return',operation=operation,seconds=time.monotonic()-start)
    return value
fcntl.lockf=timed
emit('ready',uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),sources=sources,guard_inode=inode,mode=sys.argv[1])
assert input()=='go'
import httpx
async def exercise():
    token=auth.encode_jwt(dict(sub='isolated-query-canary',token_class='mcp',scope='runs:read',runs=[slug],jti='qcat-canary-'+secrets.token_hex(8),exp=int(time.time())+120),secret,algorithm='HS256')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-canary') as client:
        headers={'Authorization':'Bearer '+token}
        path=f'/runs/{slug}/schema' if sys.argv[1]=='schema' else f'/mcp/runs/{slug}/catalog'
        started=time.monotonic();emit('request_start',path=path)
        task=asyncio.create_task(client.get(path,headers=headers))
        until=time.monotonic()+10
        while not entered.is_set() and time.monotonic()<until:
            if task.done():raise AssertionError((await task).text)
            await asyncio.sleep(.01)
        assert entered.is_set() and not task.done()
        for path in ['/','/health']:
            before=time.monotonic()
            response=await asyncio.wait_for(client.get(path),timeout=2)
            assert response.status_code==200
            assert not task.done()
            emit('unrelated_response',path=path,seconds=time.monotonic()-before,status=response.status_code)
        denied=await asyncio.wait_for(client.get('/mcp/runs/not-authorized/catalog',headers=headers),timeout=2)
        assert denied.status_code==404 and not task.done()
        emit('unauthorized_run_response',status=denied.status_code)
        response=await asyncio.wait_for(task,timeout=90)
        assert response.status_code==200,response.text
        assert 'probe.parquet' in response.text
        assert not cr.pending_catalog_requests(WD)
        catalog=json.loads((WD/'_query_engine/catalog.json').read_text())
        entry=next(e for e in catalog['files'] if e['path']=='probe.parquet')
        assert entry['size_bytes']==(WD/'probe.parquet').stat().st_size
        assert hashlib.sha256((WD/'probe.parquet').read_bytes()).hexdigest()==asset_sha
        assert locks[0].stat().st_ino==inode
        for source in sources.values():
            assert hashlib.sha256(Path(source['canonical_file']).read_bytes()).hexdigest()==source['live_file_sha256']
        emit('success',response_status=response.status_code,request_seconds=time.monotonic()-started,entry=entry,pending_receipts=0,source_asset_unchanged=True,live_module_files_unchanged=True,guard_inode_unchanged=True,lock_calls=calls)
asyncio.run(exercise())
signal.alarm(0)
