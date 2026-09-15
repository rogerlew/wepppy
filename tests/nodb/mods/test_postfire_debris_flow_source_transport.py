"""Real GDAL over bounded fake HTTP bodies; no external network."""
import io
import json
import time
from types import SimpleNamespace

import numpy as np
import pytest
from rasterio.io import MemoryFile, FilePath
from rasterio.transform import from_origin
from rasterio.windows import Window

from wepppy.nodb.mods.postfire_debris_flow import source_transport as t

pytestmark = pytest.mark.integration


class Response(io.BytesIO):
    def __init__(self, raw, headers, status=200, url=t.THICK_URL):
        super().__init__(raw)
        self.headers,self.status,self.url = headers,status,url
    def geturl(self): return self.url


def remote(tmp_path, raw, *, mutate=None, limit=t.MAX_BODY):
    transport = t.Transport(tmp_path,limit=limit)
    def opening(request, **kwargs):
        headers = {'Content-Length':str(len(raw)),'ETag':'"fixed"','Last-Modified':'fixed-date'}
        body,status = b'',200
        if request.method != 'HEAD':
            supplied = {k.lower():v for k,v in request.header_items()}
            assert supplied['if-match'] == '"fixed"'
            start,stop = map(int,supplied['range'].removeprefix('bytes=').split('-'))
            body,status = raw[start:stop+1],206
            headers.update({'Content-Range':f'bytes {start}-{stop}/{len(raw)}','Content-Length':str(len(body))})
        response = Response(body,headers,status)
        if mutate:
            mutate(request,response)
        return response
    transport.opener = SimpleNamespace(open=opening)
    return t.RangeFile(transport)


def test_real_gdal_reads_only_window_through_identity_ranges(tmp_path):
    values = np.arange(1024*1024,dtype='float32').reshape(1024,1024)
    with MemoryFile() as memory:
        with memory.open(driver='GTiff',count=1,height=1024,width=1024,dtype='float32',
                         crs='EPSG:32611',transform=from_origin(500000,4000000,10,10),
                         tiled=True,blockxsize=128,blockysize=128) as ds:
            ds.write(values,1)
        raw = memory.read()
    source = remote(tmp_path,raw)
    with FilePath(source) as bridge, bridge.open() as ds:
        actual = ds.read(1,window=Window(100,200,20,30))
    source.verify()
    np.testing.assert_array_equal(actual,values[200:230,100:120])
    assert 0 < source.transport.received < len(raw)//2
    assert all(json.loads(p.read_text())['status'] == 'complete' for p in tmp_path.glob('request-[0-9][0-9][0-9][0-9][0-9].json'))


@pytest.mark.parametrize('defect',['status','etag','range','length','encoding','redirect'])
def test_bad_range_is_latched_without_retry(tmp_path,defect):
    def mutate(request,response):
        if request.method == 'HEAD': return
        if defect == 'status': response.status = 200
        elif defect == 'etag': response.headers['ETag'] = '"changed"'
        elif defect == 'range': response.headers['Content-Range'] = 'bytes 1-2/3'
        elif defect == 'length': response.headers['Content-Length'] = '999999999'
        elif defect == 'encoding': response.headers['Content-Encoding'] = 'gzip'
        else: response.url = 'https://example.com/redirect'
    source = remote(tmp_path,b'x'*200000,mutate=mutate)
    with pytest.raises(ValueError): source.read(100)
    requests = source.transport.requests
    with pytest.raises(ValueError): source.read(100)
    assert source.transport.requests == requests == 2
    assert source.transport.received == 0


def test_aggregate_budget_prevents_next_body(tmp_path):
    source = remote(tmp_path,b'x'*200000,limit=65536)
    assert len(source.read(65536)) == 65536
    with pytest.raises(ValueError,match='exhausted'): source.read(1)
    assert source.transport.received == 65536


def test_whole_read_and_unapproved_endpoint_rejected(tmp_path):
    source = remote(tmp_path,b'x'*200000)
    with pytest.raises(ValueError,match='Whole'): source.read()
    with pytest.raises(ValueError,match='Whole'): source.verify()
    with pytest.raises(ValueError,match='endpoint'): source.transport.request('https://example.com')


def test_hard_deadline_interrupts_slow_body_and_restores_timer():
    before = t.signal.getsignal(t.signal.SIGALRM)
    with pytest.raises(TimeoutError):
        with t.deadline(.02): time.sleep(1)
    assert t.signal.getsignal(t.signal.SIGALRM) == before
    assert t.signal.getitimer(t.signal.ITIMER_REAL)[0] == 0


def test_thread_failure_is_latched(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    source = remote(tmp_path,b'x'*200000)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError,match='main-thread'):
            pool.submit(source.read,10).result()
    with pytest.raises(RuntimeError,match='main-thread'): source.verify()


def test_request_failure_records_start_and_reason(tmp_path):
    transport = t.Transport(tmp_path)
    def fail(*args,**kwargs): raise TimeoutError('controlled timeout')
    transport.opener = SimpleNamespace(open=fail)
    with pytest.raises(TimeoutError): transport.request(t.THICK_URL,method='HEAD')
    assert json.loads((tmp_path/'request-00001-start.json').read_text())['url'] == t.THICK_URL
    record = json.loads((tmp_path/'request-00001.json').read_text())
    assert record['status'] == 'failed' and record['error_type'] == 'TimeoutError'
