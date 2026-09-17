"""Bounded GTiff/AAIGrid authority controls; loopback only."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from osgeo import gdal, osr
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('kind', ['gtiff_plain', 'gtiff_internal_overview', 'aaigrid_plain', 'aaigrid_mask'])
def test_local_driver_authority_controls(tmp_path, kind):
    memory = gdal.GetDriverByName('MEM').Create('', 4, 4, 1, gdal.GDT_Byte)
    memory.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    memory.SetProjection(spatial.ExportToWkt())
    memory.GetRasterBand(1).Fill(25)
    child = tmp_path / 'child.tif'
    dataset = gdal.GetDriverByName('GTiff').CreateCopy(str(child), memory)
    dataset = None
    driver_name = 'AAIGrid' if kind.startswith('aaigrid') else 'GTiff'
    source = tmp_path / ('source.asc' if driver_name == 'AAIGrid' else 'source.tif')
    dataset = gdal.GetDriverByName(driver_name).CreateCopy(str(source), memory)
    dataset = None
    memory = None
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
        remote = f'/vsicurl/http://127.0.0.1:{server.server_address[1]}/child.tif'
        if kind == 'gtiff_internal_overview':
            dataset = gdal.Open(str(source), gdal.GA_Update)
            dataset.SetMetadataItem('OVERVIEW_FILE', remote, 'OVERVIEWS')
            dataset = None
        if kind == 'aaigrid_mask':
            mask = Path(str(source) + '.msk')
            dataset = gdal.Warp(str(mask), str(child), format='VRT', dstSRS='EPSG:4326')
            dataset = None
            xml = mask.read_text().replace('<SourceDataset relativeToVRT="1">child.tif</SourceDataset>',
                f'<SourceDataset relativeToVRT="0">{remote}</SourceDataset>')
            assert remote in xml
            mask.write_text(xml)
        stages = []
        driver = gdal.IdentifyDriver(str(source))
        stages.append({'stage': 'IdentifyDriver', 'driver': driver.ShortName, 'requests': list(requests)})
        dataset = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY,
                             allowed_drivers=['GTiff', 'AAIGrid'])
        stages.append({'stage': 'OpenEx', 'requests': list(requests)})
        metadata = dataset.GetMetadata('OVERVIEWS')
        stages.append({'stage': 'GetMetadata_OVERVIEWS', 'metadata': metadata, 'requests': list(requests)})
        members = dataset.GetFileList()
        stages.append({'stage': 'GetFileList', 'members': members, 'requests': list(requests)})
        dataset = None
        output = {'gdal': gdal.VersionInfo(), 'kind': kind, 'stages': stages,
                  'local_members': sorted(p.name for p in tmp_path.iterdir()),
                  'discovery_network_requests': len(requests)}
        Path(__file__).with_name(f'raster_discovery_security_{kind}_revision4.json').write_text(json.dumps(output, indent=2)+'\n')
        print('LOCAL_DRIVER_AUTHORITY ' + json.dumps(output))
        assert driver.ShortName == driver_name
        assert members
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
