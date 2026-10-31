"""Treatments' real raster validation and promotion at the HTTP boundary."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import uuid

import numpy as np
import pytest
from osgeo import gdal, osr
from fastapi import FastAPI
from fastapi.testclient import TestClient
from wepppy.nodb.core import Ron, Landuse, Watershed
from wepppy.nodb.mods.treatments import Treatments
from wepppy.microservices.rq_engine import treatments_routes as routes

pytestmark = pytest.mark.integration


def test_invalid_raster_preserves_state_then_valid_upload_builds(tmp_path, monkeypatch):
    wd = tmp_path / ('mrs-' + uuid.uuid4().hex); wd.mkdir()
    cfg = 'canada-wbt-mofe.cfg'
    Ron(str(wd), cfg, initialize_components=False)
    Landuse(str(wd), cfg)
    watershed = Watershed(str(wd), cfg)
    Treatments(str(wd), cfg)
    landuse = Landuse.getInstance(str(wd))
    landuse.mapping = 'disturbed'
    treatments = Treatments.getInstance(str(wd))
    key = int(treatments.get_valid_treatment_keys()[0])
    def raster(path, value):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        ds = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Int32)
        sr = osr.SpatialReference(); sr.ImportFromEPSG(32611)
        ds.SetProjection(sr.ExportToWkt()); ds.SetGeoTransform((500000, 30, 0, 4500000, 0, -30))
        ds.GetRasterBand(1).WriteArray(np.full((2, 2), value, dtype=np.int32))
        ds = None
    raster(watershed.subwta, 11)
    upload_path = tmp_path / 'valid.tif'; raster(upload_path, key)
    destination = Path(treatments.treatments_dir) / 'source.tif'
    destination.write_bytes(b'prior accepted source')
    before = {p.name: p.read_bytes() for p in wd.glob('*.nodb')}
    calls = []
    prep = SimpleNamespace(remove_timestamp=lambda task: calls.append(task), timestamp=lambda task: None)
    monkeypatch.setattr(routes, 'get_wd', lambda *a: str(wd))
    monkeypatch.setattr(routes, 'require_jwt', lambda *a, **k: {})
    monkeypatch.setattr(routes, 'authorize_run_access', lambda *a: None)
    monkeypatch.setattr(routes.RedisPrep, 'getInstance', lambda *a: prep)
    monkeypatch.setattr(routes, 'redis', SimpleNamespace(Redis=lambda **k: nullcontext(None)))
    monkeypatch.setattr(routes, 'Queue', lambda **k: None)
    monkeypatch.setattr(routes, 'enqueue_tracked_rq_job', lambda *a, **k: SimpleNamespace(id='controlled-job'))
    app = FastAPI(); app.include_router(routes.router)
    with TestClient(app) as client:
        url = '/runs/test/cfg/build-treatments'
        data = {'mode':'4', 'landuse_management_mapping_selection':'disturbed'}
        response = client.post(url, data=data, files={'input_upload_landuse':('source.tif', b'not a raster')})
        assert response.status_code == 400, response.text
        assert {p.name:p.read_bytes() for p in wd.glob('*.nodb')} == before
        assert destination.read_bytes() == b'prior accepted source'
        assert calls == []
        response = client.post(url, data=data, files={'input_upload_landuse':('source.tif', upload_path.read_bytes())})
        assert response.status_code == 200, response.text
        assert destination.read_bytes() == upload_path.read_bytes()
        reloaded = Treatments.load_detached(str(wd))
        assert int(reloaded.mode) == 4
        ds = gdal.Open(reloaded.treatments_map)
        assert ds is not None and ds.RasterXSize == 2
        assert np.all(ds.ReadAsArray() == key)
        assert reloaded.treatments_domlc_d
