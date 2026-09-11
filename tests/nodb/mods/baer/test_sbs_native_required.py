from types import SimpleNamespace

import numpy as np
import pytest
from osgeo import gdal, osr

import wepppy.nodb.mods.baer.sbs_map as module

pytestmark = pytest.mark.unit

OPERATIONS = (
    ('summarize_sbs_raster', lambda: module._summarize_sbs_raster_rust('unused')),
    ('read_color_table', lambda: module._read_color_table_rust('unused')),
    ('summarize_color_table', lambda: module._summarize_color_table_rust('unused')),
    ('reclassify_sbs_raster', lambda: module._reclassify_sbs_raster_rust('unused', breaks=[0, 1, 2, 3], ct=None, nodata_vals=[], offset=130)),
    ('export_sbs_4class', lambda: module._export_sbs_4class_rust('unused', 'unused-out', breaks=[0, 1, 2, 3], ct=None, nodata_vals=[])),
)


@pytest.mark.parametrize('name,invoke', OPERATIONS)
@pytest.mark.parametrize('missing', [None, SimpleNamespace()])
def test_missing_native_operation_fails_explicitly(monkeypatch, name, invoke, missing):
    monkeypatch.setattr(module, '_rust_sbs_map', missing)
    with pytest.raises(RuntimeError, match=name):
        invoke()


@pytest.mark.parametrize('name,invoke', OPERATIONS)
def test_native_execution_failure_is_not_hidden(monkeypatch, name, invoke):
    def fail(*args, **kwargs):
        raise RuntimeError('native failure sentinel')
    monkeypatch.setattr(module, '_rust_sbs_map', SimpleNamespace(**{name: fail}))
    with pytest.raises(RuntimeError, match='native failure sentinel'):
        invoke()


def test_failed_summary_is_not_cached(monkeypatch):
    module._summarize_sbs_raster_cached.cache_clear()
    calls = []
    def summarize(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('native failure')
        return {'class_count': 1}
    monkeypatch.setattr(module, '_rust_sbs_map', SimpleNamespace(summarize_sbs_raster=summarize))
    with pytest.raises(RuntimeError):
        module._summarize_sbs_raster_cached('unused', 0, 0)
    assert module._summarize_sbs_raster_cached('unused', 0, 0) == {'class_count': 1}
    assert len(calls) == 2
    module._summarize_sbs_raster_cached.cache_clear()


@pytest.mark.parametrize('palette', [False, True])
def test_native_export_preserves_source_mask_after_display_export(tmp_path, palette):
    source = tmp_path / 'source.tif'
    values = np.array([[0, 1, 2, 3, 7], [3, 2, 1, 0, 7]], dtype=np.uint8)
    ds = gdal.GetDriverByName('GTiff').Create(str(source), 5, 2, 1, gdal.GDT_Byte)
    transform = (500000.0, 30.0, 0.0, 4500000.0, 0.0, -30.0)
    ds.SetGeoTransform(transform)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(32612); ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1); band.SetNoDataValue(7)
    if palette:
        ct = gdal.ColorTable()
        for code, rgba in {0: (0,100,0,255), 1: (127,255,212,255), 2: (255,255,0,255), 3: (255,0,0,255), 7: (255,255,255,255)}.items():
            ct.SetColorEntry(code, rgba)
        band.SetColorTable(ct)
    band.WriteArray(values)
    band = None
    ds = None
    sbs = module.SoilBurnSeverityMap(str(source), breaks=None if palette else [0,1,2,3])
    sbs.export_wgs_map(str(tmp_path / 'display.tif'))
    output = tmp_path / 'four.tif'; sbs.export_4class_map(str(output))
    ds = gdal.Open(str(output))
    expected = np.where(values == 7, 255, values).astype(np.uint8)
    np.testing.assert_array_equal(ds.ReadAsArray(), expected)
    assert ds.GetGeoTransform() == transform
    assert ds.GetRasterBand(1).GetNoDataValue() == 255


@pytest.mark.parametrize('nodata', [float('nan'), 0.5])
def test_noninteger_nodata_metadata_does_not_mask_valid_zero(tmp_path, nodata):
    source = tmp_path / 'metadata.tif'
    ds = gdal.GetDriverByName('GTiff').Create(str(source), 5, 1, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((500000, 30, 0, 4500000, 0, -30))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32612)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).SetNoDataValue(nodata)
    ds.GetRasterBand(1).WriteArray(np.array([[0, 1, 2, 3, 255]], dtype=np.float32))
    ds = None
    sbs = module.SoilBurnSeverityMap(str(source), breaks=[0, 1, 2, 255])
    sbs.export_wgs_map(str(tmp_path / 'display.tif'))
    output = tmp_path / 'four.tif'
    sbs.export_4class_map(str(output))
    ds = gdal.Open(str(output))
    np.testing.assert_array_equal(ds.ReadAsArray(), [[0, 1, 2, 3, 3]])
