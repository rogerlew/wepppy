from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

from osgeo import gdal
import pytest

from wepppy.all_your_base.geo.webclients import wmesque as client
from wepppy.webservices.wmesque2 import _b64url

pytestmark = pytest.mark.integration


@pytest.fixture
def raster_bytes(tmp_path):
    path=tmp_path / "source.tif"
    ds=gdal.GetDriverByName("GTiff").Create(str(path), 4, 4, 1, gdal.GDT_Byte)
    ds.GetRasterBand(1).Fill(8)
    ds=None
    return path.read_bytes()


@contextmanager
def endpoint(payload=b"", status=200, revision=None, delay=0, trickle=False):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            time.sleep(delay)
            if trickle:
                try:
                    self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                    for _ in range(20):
                        self.wfile.write(b"X-Trickle: yes\r\n")
                        self.wfile.flush()
                        time.sleep(.06)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            self.send_response(status)
            self.send_header("WMesque-Meta", _b64url({"wmesque":{"revision":revision}}))
            self.send_header("Content-Length",str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Test intentionally times out the client.
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown();server.server_close();thread.join()


def test_defaults_overrides_and_bad_configuration(monkeypatch):
    monkeypatch.delenv("WMESQUE_ENDPOINTS",raising=False)
    assert client.resolve_endpoints()==[client.WMESQUE2_ENDPOINT.rstrip("/")]
    monkeypatch.setenv("WMESQUE_ENDPOINTS"," ")
    assert client.resolve_endpoints()==[client.WMESQUE2_ENDPOINT.rstrip("/")]
    for raw in ('[]','{}','nope','["file:///tmp/x"]','["https://user:secret@host"]','["https://host/?a=b"]'):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",raw)
        with pytest.raises(ValueError):client.resolve_endpoints()
        assert client.resolve_endpoints("http://explicit/")==["http://explicit"]


@pytest.mark.parametrize("status", [404,409,429,500,502,503,504])
def test_ordered_failover(status, raster_bytes, tmp_path, monkeypatch):
    with endpoint(status=status) as (first, first_calls), endpoint(raster_bytes) as (second, second_calls):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",json.dumps([first,second]))
        out=tmp_path/"result.tif"
        assert client.wmesque_retrieve("test/map", [0,0,1,1],str(out),30)==1
        assert len(first_calls)==len(second_calls)==1
        meta=json.loads((tmp_path/"result.tif.meta").read_text())
        assert meta["wmesque_retrieve"]["wmesque_endpoint"]==second
        assert len(meta["wmesque_retrieve"]["attempts"])==2
        assert gdal.Open(str(out)).ReadAsArray()[0,0]==8


@pytest.mark.parametrize("status", [400,401,403,422])
def test_nonretryable_status(status,raster_bytes,tmp_path,monkeypatch):
    with endpoint(status=status) as (first,_),endpoint(raster_bytes) as (second,calls):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",json.dumps([first,second]))
        out=tmp_path/"result.tif";out.write_bytes(b"old")
        with pytest.raises(RuntimeError,match="HTTPError"):
            client.wmesque_retrieve("test/map",[0,0,1,1],str(out),30)
        assert calls==[] and out.read_bytes()==b"old"


def test_revision_mismatch_and_invalid_raster(raster_bytes,tmp_path,monkeypatch):
    revision="a"*64
    with endpoint(b"not a raster", revision=revision) as (bad,_),endpoint(raster_bytes,revision=revision) as (good,_):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",json.dumps([bad,good]))
        out=tmp_path/"result.tif"
        client.wmesque_retrieve("test/map",[0,0,1,1],str(out),30,expected_revision=revision)
        assert json.loads((tmp_path/"result.tif.meta").read_text())["wmesque"]["revision"]==revision
        before=out.read_bytes()
        with pytest.raises(RuntimeError):
            client.wmesque_retrieve("test/map",[0,0,1,1],str(out),30,expected_revision="b"*64)
        assert out.read_bytes()==before


def test_attempt_timeout_reserves_fallback_time(raster_bytes,tmp_path,monkeypatch):
    with endpoint(raster_bytes,delay=1) as (slow,_),endpoint(raster_bytes) as (fast,_):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",json.dumps([slow,fast]))
        monkeypatch.setattr(client,"TIMEOUT",0.6)
        start=time.monotonic()
        client.wmesque_retrieve("test/map",[0,0,1,1],str(tmp_path/"result.tif"),30)
        assert time.monotonic()-start<0.9


def test_local_publish_failure_rolls_back(raster_bytes,tmp_path,monkeypatch):
    out=tmp_path/"result.tif";out.write_bytes(b"old raster")
    meta=tmp_path/"result.tif.meta";meta.write_text("old metadata")
    replace=client.os.replace
    def fail(source,target):
        if str(target)==str(out):raise PermissionError("injected")
        return replace(source,target)
    with endpoint(raster_bytes) as (url,calls):
        monkeypatch.setattr(client.os,"replace",fail)
        with pytest.raises(PermissionError):
            client.wmesque_retrieve("test/map",[0,0,1,1],str(out),30,wmesque_endpoint=url)
        assert len(calls)==1
    assert out.read_bytes()==b"old raster" and meta.read_text()=="old metadata"


def test_vrt_payload_is_not_accepted_as_tiff(tmp_path):
    path=tmp_path/"external.tif"
    ds=gdal.GetDriverByName("GTiff").Create(str(path),1,1,1,gdal.GDT_Byte)
    ds.SetGeoTransform((500000,30,0,5100000,0,-30))
    ds.GetRasterBand(1).Fill(73);ds=None
    vrt=tmp_path/"response.vrt"
    gdal.BuildVRT(str(vrt),[str(path)])
    payload=vrt.read_bytes()
    with endpoint(payload) as (url,_):
        out=tmp_path/"result.tif"
        with pytest.raises(RuntimeError):
            client.wmesque_retrieve("test/map",[0,0,1,1],str(out),30,wmesque_endpoint=url)
        assert not out.exists()


def test_trickling_headers_leave_time_for_fallback(raster_bytes,tmp_path,monkeypatch):
    with endpoint(trickle=True) as (slow,_), endpoint(raster_bytes) as (fast,calls):
        monkeypatch.setenv("WMESQUE_ENDPOINTS",json.dumps([slow,fast]))
        monkeypatch.setattr(client,"TIMEOUT",.6)
        start=time.monotonic()
        client.wmesque_retrieve("test/map",[0,0,1,1],str(tmp_path/"result.tif"),30)
        assert calls and time.monotonic()-start<.9


@pytest.mark.parametrize('extension,driver', [('.asc','AAIGrid'),('.png','PNG')])
def test_supported_formats_use_the_requested_driver(extension,driver,raster_bytes,tmp_path):
    source=tmp_path/'source.tif';source.write_bytes(raster_bytes)
    fixture=tmp_path/('fixture'+extension)
    gdal.Translate(str(fixture),str(source),format=driver)
    with endpoint(fixture.read_bytes()) as (url,_):
        output=tmp_path/('result'+extension)
        client.wmesque_retrieve('test/map',[0,0,1,1],str(output),30,wmesque_endpoint=url)
        ds=gdal.Open(str(output))
        assert ds.GetDriver().ShortName==driver
        assert ds.ReadAsArray()[0,0]==8
