from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from wepppy.microservices.rq_engine import postfire_debris_flow_routes as routes
from wepppy.nodb.mods.postfire_debris_flow import production as p

pytestmark=pytest.mark.unit


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(routes,'context',lambda *a,**kw:str(tmp_path))
    monkeypatch.setattr(p,'get_state',lambda *a,**kw:{'upload_ready':True})
    app=FastAPI();app.include_router(routes.router)
    with TestClient(app) as client:yield client


def test_invalid_payloads_before_mutation(client,tmp_path):
    base='/runs/test/config/postfire-debris-flow'
    for body in ('[]','{"frequency_source":"cli","frequency_source":"noaa"}','{"frequency_source":NaN}', '"'+('a'*4096)+'"'):
        response=client.post(base+'/run-m1',content=body,headers={'Content-Type':'application/json'})
        assert response.status_code in (400,413)
        assert 'error' in response.json()
    response=client.post(base+'/upload-dnbr',files={'file':('map.shp',b'bad')})
    assert response.status_code==400
    assert not (tmp_path/'postfire_debris_flow').exists()


def test_duplicate_multipart_and_parts(client):
    base='/runs/test/config/postfire-debris-flow/upload-dnbr'
    response=client.post(base,files=[('file',('a.tif',b'a')),('file',('b.tif',b'b'))])
    assert response.status_code==400
    response=client.post(base,files=[('file',('a.tif',b'a')),('companion',('b.tif',b'b')),('extra',('c.tif',b'c'))])
    assert response.status_code==413
    assert 'error' in response.json()


def test_download_acceptance_and_changed_file(client,tmp_path,monkeypatch):
    identity='a'*32; root=p.directory(tmp_path,identity)/'results';root.mkdir(parents=True)
    path=root/'events.parquet';path.write_bytes(b'accepted bytes')
    accepted={'id':identity,'artifacts':{str(path.relative_to(tmp_path)):p.signature(tmp_path,path)}}
    monkeypatch.setattr(p,'state_at',lambda wd:{'last_successful_run':accepted})
    url=f'/runs/test/config/postfire-debris-flow/files/{identity}/events.parquet'
    response=client.get(url)
    assert response.status_code==200 and response.content==b'accepted bytes'
    assert client.get(url.replace(identity,'b'*32)).status_code==404
    assert client.get(url.replace('events.parquet','source.tif')).status_code==404
    path.write_bytes(b'changed')
    assert client.get(url).status_code==409


def test_config_readonly_and_export_scope(tmp_path,monkeypatch):
    scopes=[]
    monkeypatch.setattr(routes,'require_jwt',lambda request,required_scopes:scopes.append(required_scopes) or {})
    monkeypatch.setattr(routes,'authorize_run_access',lambda *a:None)
    monkeypatch.setattr(routes,'get_wd',lambda *a:str(tmp_path))
    monkeypatch.setattr(routes.Ron,'getInstance',lambda wd:SimpleNamespace(config_stem='config',readonly=True))
    request=Request({'type':'http','headers':[]})
    assert routes.context(request,'test','config.cfg',export=True)==str(tmp_path)
    assert scopes[-1]==['rq:export']
    with pytest.raises(p.WorkflowError,match='read-only'):routes.context(request,'test','config',True)
    with pytest.raises(p.WorkflowError,match='configuration changed'):routes.context(request,'test','old')


def test_download_deleted_file_is_conflict(client,tmp_path,monkeypatch):
    identity='a'*32; root=p.directory(tmp_path,identity)/'results';root.mkdir(parents=True)
    accepted={'id':identity,'artifacts':{}}
    monkeypatch.setattr(p,'state_at',lambda wd:{'last_successful_run':accepted})
    assert client.get(f'/runs/test/config/postfire-debris-flow/files/{identity}/events.parquet').status_code==409


@pytest.mark.parametrize('fail_at',[0,1])
def test_download_disconnect_closes_real_handle(tmp_path,fail_at):
    path=tmp_path/'result';path.write_bytes(b'x'*70000)
    handle=path.open('rb');response=routes.DownloadResponse(handle)
    count=0
    async def send(message):
        nonlocal count
        if count==fail_at:raise OSError('client disconnected')
        count+=1
    async def receive():return {'type':'http.disconnect'}
    from starlette.requests import ClientDisconnect
    with pytest.raises(ClientDisconnect):
        import asyncio
        asyncio.run(response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send))
    assert handle.closed


def test_multipart_disconnect_closes_spooled_files(monkeypatch):
    from starlette.requests import ClientDisconnect
    captured=[]
    original=routes.MultiPartParser
    class CapturingParser(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);captured.append(self)
    monkeypatch.setattr(routes,'MultiPartParser',CapturingParser)
    body=b'--bound\r\nContent-Disposition: form-data; name="file"; filename="map.tif"\r\nContent-Type: image/tiff\r\n\r\n'+b'x'*1100000
    sent=False
    async def receive():
        nonlocal sent
        if sent:return {'type':'http.disconnect'}
        sent=True;return {'type':'http.request','body':body,'more_body':True}
    request=Request({'type':'http','headers':[(b'content-type',b'multipart/form-data; boundary=bound')]},receive)
    async def consume():
        async with routes.upload_form(request):pass
    import asyncio
    with pytest.raises(ClientDisconnect):
        asyncio.run(consume())
    assert captured[0]._files_to_close_on_error
    assert all(handle.closed for handle in captured[0]._files_to_close_on_error)


@pytest.mark.parametrize('cap',['request','file'])
def test_streamed_caps_without_content_length(tmp_path,monkeypatch,cap):
    import asyncio
    monkeypatch.setattr(routes,'context',lambda *a,**kw:str(tmp_path))
    monkeypatch.setattr(p,'get_state',lambda *a,**kw:{'upload_ready':True})
    monkeypatch.setattr(routes,'REQUEST_LIMIT',2048 if cap=='request' else 8192)
    monkeypatch.setattr(routes,'LIMIT',2048)
    monkeypatch.setattr(routes.redis,'Redis',lambda **kw:nullcontext(None))
    monkeypatch.setattr(routes,'rq_submission_lock',lambda *a,**kw:nullcontext())
    monkeypatch.setattr(p,'reconcile_attempts',lambda wd,state,*a,**kw:state)
    monkeypatch.setattr(p,'sources',lambda *a,**kw:(True,False,{}, {},{}))
    body=b'--bound\r\nContent-Disposition: form-data; name="file"; filename="map.tif"\r\n\r\n'+b'x'*4096+b'\r\n--bound--\r\n'
    chunks=iter(body[i:i+512] for i in range(0,len(body),512))
    async def receive():
        chunk=next(chunks,b'')
        return {'type':'http.request','body':chunk,'more_body':bool(chunk)}
    request=Request({'type':'http','headers':[(b'content-type',b'multipart/form-data; boundary=bound')]},receive)
    response=asyncio.run(routes.upload('run','config',request))
    assert response.status_code==413
    assert not (tmp_path/'postfire_debris_flow.nodb').exists()


def test_cross_project_retry_candidate_is_not_read(tmp_path,monkeypatch):
    import asyncio
    monkeypatch.setattr(routes,'context',lambda *a,**kw:str(tmp_path))
    monkeypatch.setattr(routes.redis,'Redis',lambda **kw:nullcontext(None))
    monkeypatch.setattr(routes,'rq_submission_lock',lambda *a,**kw:nullcontext())
    monkeypatch.setattr(p,'reconcile_attempts',lambda wd,state,*a,**kw:state)
    identity='b'*32
    foreign=tmp_path.parent/'foreign-project'/'postfire_debris_flow'/'.staging'/identity
    foreign.mkdir(parents=True);(foreign/'private').write_text('foreign bytes')
    body=json.dumps({'candidate_id':identity,'scale_mode':'auto'}).encode()
    async def receive():return {'type':'http.request','body':body,'more_body':False}
    request=Request({'type':'http','headers':[(b'content-type',b'application/json')]},receive)
    response=asyncio.run(routes.retry('run','config',request))
    assert response.status_code==404
    assert not (tmp_path/'postfire_debris_flow').exists()


@pytest.mark.parametrize('reason,status',[('readonly',403),('config_mismatch',409)])
def test_admission_rechecks_context_before_staging(client,tmp_path,monkeypatch,reason,status):
    calls=0
    def changed(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls>1:raise p.WorkflowError(reason,'Project changed.',status)
        return str(tmp_path)
    monkeypatch.setattr(routes,'context',changed)
    monkeypatch.setattr(routes.redis,'Redis',lambda **kw:nullcontext(None))
    monkeypatch.setattr(routes,'rq_submission_lock',lambda *a,**kw:nullcontext())
    response=client.post('/runs/test/config/postfire-debris-flow/upload-dnbr',files={'file':('map.tif',b'bytes')})
    assert response.status_code==status
    assert not (tmp_path/'postfire_debris_flow').exists()


def test_ineligible_run_does_not_create_or_change_nodb(client,tmp_path,monkeypatch):
    monkeypatch.setattr(routes.redis,'Redis',lambda **kw:nullcontext(None))
    monkeypatch.setattr(routes,'rq_submission_lock',lambda *a,**kw:nullcontext())
    monkeypatch.setattr(p,'reconcile_attempts',lambda wd,state,*a,**kw:state)
    monkeypatch.setattr(p,'sources',lambda *a,**kw:(False,False,{}, {},{}))
    monkeypatch.setattr(p,'get_state',lambda *a,**kw:{'run_ready':False})
    response=client.post('/runs/test/config/postfire-debris-flow/run-m1',json={'frequency_source':'noaa'})
    assert response.status_code==422
    assert not (tmp_path/'postfire_debris_flow.nodb').exists()


@pytest.mark.parametrize('value',['1e309','true','-1e309'])
def test_nonfinite_and_boolean_custom_scale_rejected(client,tmp_path,value):
    response=client.post('/runs/test/config/postfire-debris-flow/retry-dnbr',content='{"candidate_id":"'+('a'*32)+'","scale_mode":"custom","scale_factor":'+value+',"add_offset":0}',headers={'Content-Type':'application/json'})
    assert response.status_code==400
    assert not (tmp_path/'postfire_debris_flow.nodb').exists()
