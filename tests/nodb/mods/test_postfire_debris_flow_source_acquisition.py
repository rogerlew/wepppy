"""Two project-derived acquisitions with real TIFFs and controlled HTTP."""
import json
from types import SimpleNamespace

import pytest
import rasterio

from tests.nodb.mods.test_postfire_debris_flow_source_preparation import basin
from tests.nodb.mods.test_postfire_debris_flow_source_transport import Response
from wepppy.nodb.mods.postfire_debris_flow import source_acquisition as a, source_transport as t
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import META

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('offset,key,primary',[(0,'7',True),(40,'11',True),(20,'7',False)])
def test_generic_acquisition_derives_keys_window_and_does_not_activate(tmp_path,monkeypatch,offset,key,primary):
    root = tmp_path/'project'
    grid,domain,args = basin(root,offset,key,primary)
    with rasterio.open(args['thick'],'r+') as ds:
        ds.nodata = float('nan')
    raw = args['thick'].read_bytes()
    calls = []
    def opening(request,**kwargs):
        calls.append(request)
        if request.full_url == t.SDA_URL:
            query = json.loads(request.data)['query']
            assert "'"+key+"'" in query and "'8'" in query
            payload = {'Table':[a.FIELDS,[key,'Non-MLRA Soil Survey Area','AZ001','1','2026-01-01'],
                              ['8','Country','US','1','2026-01-01']]}
            body = json.dumps(payload).encode()
            return Response(body,{'Content-Length':str(len(body))},url=t.SDA_URL)
        assert request.full_url == t.THICK_URL
        headers = {'Content-Length':str(len(raw)),'ETag':'"original"','Last-Modified':'date'}
        body,status = b'',200
        if request.method == 'GET':
            incoming = {k.lower():v for k,v in request.header_items()}
            assert incoming['if-match'] == '"original"'
            start,stop = map(int,incoming['range'].removeprefix('bytes=').split('-'))
            body,status = raw[start:stop+1],206
            headers.update({'Content-Length':str(len(body)),'Content-Range':f'bytes {start}-{stop}/{len(raw)}'})
        return Response(body,headers,status)
    monkeypatch.setattr(t,'build_opener',lambda *args:SimpleNamespace(open=opening))
    cache = root/'soils/ssurgo_tabular_cache.sqlite'
    before = cache.read_bytes() if cache.exists() else None
    receipt = a.acquire_sources(root,args['dem'],args['mask'])
    assert io.read_json(receipt)['status'] == 'complete'
    assert not (root/META).exists()
    assert (cache.read_bytes() if cache.exists() else None) == before
    candidate = io.read_json(receipt.parent/'soil_sources.json')
    assert candidate.get('primary',{}).get('mukeys') == ([key] if primary else None)
    with rasterio.open(root/candidate['fallback']['path']) as ds:
        assert list(ds.shape) == grid['shape']
        assert list(ds.transform)[:6] == grid['transform']
    assert len(list((root/'postfire_debris_flow/source_preparation').glob('*/acquisition/sda_requests/request-*-start.json'))) == int(primary)
    from wepppy.nodb.mods.postfire_debris_flow.source_replay import recover_sources
    acquisition = next((root/'postfire_debris_flow/source_preparation').glob('*/acquisition'))
    original = acquisition.parent/'receipt.json'
    assert io.read_json(acquisition/'native_evidence.json')['source_metadata']['nodata'] == 'NaN'
    def no_network(*args,**kwargs):
        raise AssertionError('Recovery must not connect to a service')
    monkeypatch.setattr(t,'build_opener',no_network)
    recovered = recover_sources(root,args['dem'],args['mask'],original,
                                expected_sha256=io.digest(original,io.MAX_TEXT))
    assert io.read_json(recovered)['status'] == 'complete'
    assert not (root/META).exists()
    if primary:
        catalog = acquisition/'collection_catalog.json'
        changed = io.read_json(catalog)
        changed['collection_by_mukey']['8'] = 'SSURGO'
        catalog.write_text(json.dumps(changed))
        with pytest.raises(ValueError,match='catalog differs'):
            recover_sources(root,args['dem'],args['mask'],original,
                            expected_sha256=io.digest(original,io.MAX_TEXT))


@pytest.mark.parametrize('payload',[{'Table':[['unexpected']]},{'Table':''},{},
    {'Table':[a.FIELDS,['7','Non-MLRA Soil Survey Area','','1','date']]}])
def test_malformed_sda_response_is_not_fallback_success(tmp_path,monkeypatch,payload):
    def opening(request,**kwargs):
        raw = json.dumps(payload).encode()
        return Response(raw,{'Content-Length':str(len(raw))},url=t.SDA_URL)
    monkeypatch.setattr(t,'build_opener',lambda *args:SimpleNamespace(open=opening))
    with pytest.raises(ValueError):
        a._lineage(['7'],tmp_path)
    assert (tmp_path/'sda_response.json').exists()
    assert not (tmp_path/'collection_catalog.json').exists()


@pytest.mark.parametrize('defect',['scale','offset','point'])
def test_native_encoding_is_not_erased_before_admission(tmp_path,monkeypatch,defect):
    from tests.nodb.mods.test_postfire_debris_flow_source_transport import remote
    root = tmp_path/'project'; grid,_,args = basin(root)
    with rasterio.open(args['thick'],'r+') as ds:
        if defect == 'scale': ds.scales = (2,)
        elif defect == 'offset': ds.offsets = (5,)
        else: ds.update_tags(AREA_OR_POINT='Point')
    raw = args['thick'].read_bytes()
    # Real FilePath and GDAL, only HTTP service is replaced.
    monkeypatch.setattr(a,'RangeFile',lambda transport:remote(transport.output,raw))
    with pytest.raises(ValueError,match='metadata'):
        a._native_window(grid,root)
    assert not (root/'native_evidence.json').exists()


def test_parent_watchdog_stops_noninterruptible_native_worker(tmp_path,monkeypatch):
    import hashlib
    import time
    def native_cpu(*args):
        hashlib.pbkdf2_hmac('sha256',b'fixture',b'fixture',10_000_000)
    monkeypatch.setattr(a,'_native_window',native_cpu)
    started = time.monotonic()
    with pytest.raises(TimeoutError,match='wall deadline'):
        a._supervised_native({},tmp_path,timeout=.05)
    assert time.monotonic()-started < 2
    assert io.read_json(tmp_path/'native_timeout.json')['worker_stopped'] is True
    assert (tmp_path/'native_started.json').exists()


def test_parent_enforces_active_request_deadline_inside_native_opener(tmp_path):
    import hashlib
    import time
    def blocked_request(output):
        transport = t.Transport(output,seconds=.05)
        def blocked(*args,**kwargs):
            hashlib.pbkdf2_hmac('sha256',b'fixture',b'fixture',10_000_000)
        transport.opener = SimpleNamespace(open=blocked)
        transport.request(t.SDA_URL,method='POST',data=b'{}')
    started = time.monotonic()
    with pytest.raises(TimeoutError,match='wall deadline'):
        a._supervise('sda',blocked_request,(),tmp_path,2)
    assert time.monotonic()-started < 1.5
    assert io.read_json(tmp_path/'sda_timeout.json')['worker_stopped'] is True
    assert (tmp_path/'request-00001-start.json').exists()


@pytest.mark.parametrize('phase',['lineage','final_preparation'])
def test_wal_only_drift_cannot_complete_acquisition(tmp_path,monkeypatch,phase):
    import sqlite3
    root = tmp_path/'project'; _,_,args = basin(root)
    cache = root/'soils/ssurgo_tabular_cache.sqlite'
    connection = sqlite3.connect(cache)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA wal_autocheckpoint=0')
    connection.commit()
    def change():
        connection.execute('UPDATE chorizon SET hzdepb_r=125'); connection.commit()
    def lineage(*args_):
        if phase == 'lineage': change()
        (args_[-1]/'collection_catalog.json').write_bytes(args['collection_catalog'].read_bytes())
        return args['collection_catalog']
    original = a.prepare_local_sources
    calls = 0
    def prepare(*args_,**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2 and phase == 'final_preparation': change()
        return original(*args_,**kwargs)
    monkeypatch.setattr(a,'_lineage',lineage)
    monkeypatch.setattr(a,'_supervise',lambda operation,target,arguments,output,timeout:target(*arguments,output))
    monkeypatch.setattr(a,'_supervised_native',lambda *args_:(args['thick'],args['thick_evidence']))
    monkeypatch.setattr(a,'prepare_local_sources',prepare)
    try:
        with pytest.raises(ValueError,match='cache changed'):
            a.acquire_sources(root,args['dem'],args['mask'])
        assert not list((root/'postfire_debris_flow/source_preparation').glob('*/acquisition/complete.json'))
    finally:
        connection.close()
