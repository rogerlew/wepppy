"""Local-only native discovery authority characterization, no external target."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from osgeo import gdal
import pytest

pytestmark = pytest.mark.integration


def test_local_vrt_discovery_remote_child_boundary(tmp_path):
    source = tmp_path / 'source.tif'
    dataset = gdal.GetDriverByName('GTiff').Create(str(source), 4, 4, 1, gdal.GDT_Byte)
    dataset.GetRasterBand(1).Fill(25)
    dataset = None
    requests = []
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp_path), **kwargs)
        def log_message(self, format, *args):
            pass
        def do_HEAD(self):
            requests.append({'method': 'HEAD', 'path': self.path})
            return super().do_HEAD()
        def do_GET(self):
            requests.append({'method': 'GET', 'path': self.path})
            return super().do_GET()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        port = server.server_address[1]
        vrt = tmp_path / 'selected.vrt'
        vrt.write_text(f'''<VRTDataset rasterXSize="4" rasterYSize="4">
<VRTRasterBand dataType="Byte" band="1"><SimpleSource>
<SourceFilename relativeToVRT="0">/vsicurl/http://127.0.0.1:{port}/source.tif</SourceFilename>
<SourceBand>1</SourceBand><SrcRect xOff="0" yOff="0" xSize="4" ySize="4"/>
<DstRect xOff="0" yOff="0" xSize="4" ySize="4"/>
</SimpleSource></VRTRasterBand></VRTDataset>''')
        observations = []
        driver = gdal.IdentifyDriver(str(vrt))
        observations.append({'stage': 'IdentifyDriver', 'driver': driver.ShortName,
                             'requests': list(requests)})
        dataset = gdal.OpenEx(str(vrt), gdal.OF_RASTER | gdal.OF_READONLY)
        observations.append({'stage': 'OpenEx', 'requests': list(requests)})
        members = dataset.GetFileList()
        observations.append({'stage': 'GetFileList', 'members': members,
                             'requests': list(requests)})
        dataset = None
        output = {'gdal': gdal.VersionInfo(), 'scope': 'loopback disposable HTTP fixture only',
                  'observations': observations, 'discovery_network_requests': len(requests)}
        Path(__file__).with_suffix('.json').write_text(json.dumps(output, indent=2) + '\n')
        print('RASTER_DISCOVERY_NETWORK ' + json.dumps(output))
        assert driver.ShortName == 'VRT'
        assert members
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
