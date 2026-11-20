import threading
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest
from osgeo import gdal, osr
from scipy.interpolate import RectBivariateSpline
from werkzeug.serving import make_server

from wepppy.climates import metquery_client
from wepppy.climates.cligen.cligen import CligenStationsManager
from wepppy.eu.climates.eobs.scripts.process import _monthly_statistics, dump_tif
from wepppy.nodb.core.climate_station_catalog_service import ClimateStationCatalogService
from wepppy.webservices import metquery


RAIN = 'eu/e-obs/rr/mean'
TMIN = 'eu/e-obs/tn/mean'
TMAX = 'eu/e-obs/tx/mean'
TRANSFORM = (0, 1, 0, 10, 0, -1)


def _wgs84():
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(4326)
    return crs.ExportToWkt()


def _write_monthly(root, field, bands, nodata=-9999):
    directory = root / field
    directory.mkdir(parents=True)
    height, width = bands[0].shape
    tif = gdal.GetDriverByName('GTiff').Create(
        str(directory / 'monthly.tif'), width, height, len(bands), gdal.GDT_Float32,
    )
    tif.SetGeoTransform(TRANSFORM)
    tif.SetProjection(_wgs84())
    for index, values in enumerate(bands, 1):
        band = tif.GetRasterBand(index)
        band.SetNoDataValue(nodata)
        band.WriteArray(values)
    tif.FlushCache()
    gdal.Translate(str(directory / '.vrt'), tif, format='VRT')


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(metquery, 'geodata_dir', str(tmp_path))
    return metquery.app.test_client()


@pytest.mark.parametrize(('field', 'missing'), [
    (RAIN, -999.9), (RAIN, -460), (RAIN, -9999), (TMIN, -99.99), (TMAX, 9999),
])
def test_coastal_bilinear_renormalizes_only_immediate_valid_cells(client, tmp_path, field, missing):
    values = np.full((8, 8), 50, dtype=np.float32)
    values[3:5, 3:5] = [[4, missing], [8, 12]]
    _write_monthly(tmp_path, field, [values] * 12, nodata=9999 if field == TMAX else -9999)

    response = client.get('/monthly', query_string=dict(dataset=field, lng=3.75, lat=6.25))

    assert response.status_code == 200
    assert response.json['Method'] == 'cubic'
    assert response.json['MonthlyValues'] == pytest.approx([4.5 / 0.8125] * 12)


def test_complete_stencils_keep_legacy_cubic_and_finite_rainfall_undershoot(client, tmp_path):
    # Positive source cells can have a negative cubic estimate near a dry pixel.
    values = np.tile(np.array([1, 1, 0, 0, 1, 1, 1, 1]), (8, 1))
    _write_monthly(tmp_path, RAIN, [values] * 12)
    lng, lat = 2.5, 6.25
    expected = RectBivariateSpline(range(5), range(1, 6), values[1:6, :5].T)(lng, 10 - lat)[0, 0]
    assert expected < 0

    response = client.get('/monthly', query_string=dict(dataset=RAIN, lng=lng, lat=lat))

    assert response.status_code == 200
    assert response.json['MonthlyValues'] == pytest.approx([expected] * 12)
    linear = client.get('/monthly', query_string=dict(dataset=RAIN, lng=lng, lat=lat, method='bilinear'))
    assert linear.status_code == 200
    assert linear.json['MonthlyValues'] == [0.0] * 12


def test_complete_inland_stencil_matches_original_interpolator(client, tmp_path):
    rows, columns = np.mgrid[:8, :8]
    values = columns**2 + 0.6 * columns * rows + 4 * rows
    _write_monthly(tmp_path, RAIN, [values + month for month in range(12)])
    lng, lat = 4.3, 6.2
    original = metquery.RasterDatasetInterpolator(str(tmp_path / RAIN / '.vrt'))

    response = client.get('/monthly', query_string=dict(dataset=RAIN, lng=lng, lat=lat))

    assert response.status_code == 200
    assert response.json['MonthlyValues'] == pytest.approx(original.get_location_info(lng, lat))


def test_month_specific_coverage_error_and_outside_extent(client, tmp_path):
    valid = np.full((8, 8), 5, dtype=np.float32)
    missing = valid.copy()
    missing[3, 3] = -99.99
    _write_monthly(tmp_path, TMIN, [valid] * 6 + [missing] + [valid] * 5)

    response = client.post('/monthly', json=dict(dataset=TMIN, lng=3.75, lat=6.25))
    assert response.status_code == 422
    assert response.json['Code'] == 'eobs_coverage_unavailable'
    assert response.json['Month'] == 7
    assert response.json['Dataset'] == TMIN
    assert (response.json['Longitude'], response.json['Latitude']) == (3.75, 6.25)

    outside = client.get('/monthly', query_string=dict(dataset=TMIN, lng=-0.1, lat=6.25))
    assert outside.status_code == 422
    assert 'Month' not in outside.json


@pytest.mark.parametrize('args', [dict(lat=6), dict(lng='nan', lat=6), dict(lng=0, lat=91)])
def test_malformed_location_is_distinguished_from_a_missing_dataset(client, args):
    data = dict(dataset=RAIN, **args)
    assert client.get('/monthly', query_string=data).status_code == 400
    assert client.post('/monthly', json=data).status_code == 400


def test_boolean_coordinate_is_invalid(client):
    response = client.post('/monthly', json=dict(dataset=RAIN, lng=True, lat=6))
    assert response.status_code == 400


def test_missing_and_wrong_band_count_are_provider_errors(client, tmp_path):
    query = dict(dataset=RAIN, lng=0.1, lat=9.8)
    missing = client.get('/monthly', query_string=query)
    assert missing.status_code == 503
    values = np.full((2, 2), 7, dtype=np.float32)
    _write_monthly(tmp_path, RAIN, [values])
    malformed = client.post('/monthly', json=query)
    assert malformed.status_code == 503
    assert missing.json == malformed.json == {'Error': 'The E-OBS dataset is temporarily unavailable.'}


def test_bilinear_clips_window_at_outer_edge(client, tmp_path):
    values = np.array([[7, -999.9], [-999.9, -999.9]], dtype=np.float32)
    _write_monthly(tmp_path, RAIN, [values] * 12)
    response = client.post('/monthly', json=dict(dataset=RAIN, lng=0.1, lat=9.8))
    assert response.status_code == 200
    assert response.json['MonthlyValues'] == pytest.approx([7] * 12)


def test_preprocessing_uses_valid_days_and_round_trips_unscaled_nodata(tmp_path):
    raw = [np.array([[-9999, -9999], [20, 30]]), np.array([[40, -9999], [40, 30]])]
    daily = [np.ma.masked_equal(day, -9999) for day in raw]
    statistics = _monthly_statistics(daily, 0.1)

    for stat, grid in statistics.items():
        filename = tmp_path / f'{stat}.tif'
        dump_tif(grid.T, str(filename), _wgs84(), TRANSFORM, nodata=-9999)
        dataset = gdal.Open(str(filename))
        assert dataset.GetRasterBand(1).GetNoDataValue() == -9999
        expected = [[4, -9999], [3, 3]] if stat == 'mean' else [[0, -9999], [1, 0]]
        np.testing.assert_allclose(dataset.ReadAsArray(), expected)


def test_configured_http_provider_surfaces_coverage_without_retry(client, tmp_path, monkeypatch):
    values = np.full((8, 8), 5, dtype=np.float32)
    values[2, 2] = -500
    _write_monthly(tmp_path, RAIN, [values] * 12)
    with make_server('127.0.0.1', 0, metquery.app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setenv('EOBS_METQUERY_URL', f'http://127.0.0.1:{server.server_port}/')
            monkeypatch.setattr(metquery_client, '_metquery_url', 'http://127.0.0.1:1/')

            valid = metquery_client.get_eobs_monthly_ppt(4.75, 5.25)
            assert valid == pytest.approx([5] * 12)
            with pytest.raises(ValueError, match=r'E-OBS has no coverage for rainfall.*month 1'):
                metquery_client.get_eobs_monthly_ppt(2.25, 7.75)
            with pytest.raises(RuntimeError, match='E-OBS provider is temporarily unavailable'):
                metquery_client.get_eobs_monthly_tmin(4.75, 5.25)
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_eobs_heuristic_keeps_saved_station_when_provider_lacks_coverage(client, tmp_path, monkeypatch):
    point = (2.25, 7.75)
    rain = np.full((8, 8), 5, dtype=np.float32)
    rain[2, 2] = -999.9
    _write_monthly(tmp_path, RAIN, [rain] * 12)
    model = str(tmp_path / RAIN / 'monthly.tif')
    dem = tmp_path / 'dem.tif'
    gdal.Translate(str(dem), model, bandList=[1])

    saved_ranking = ['SPE00119882']
    climate = SimpleNamespace(
        cligen_db='ghcn_stations.db', locked=nullcontext, _heuristic_stations=saved_ranking,
        _climatestation='SPE00119882', ron_instance=SimpleNamespace(dem_fn=str(dem)),
        watershed_instance=SimpleNamespace(require_centroid=lambda: point),
    )
    station = CligenStationsManager(version=climate.cligen_db).get_station_fromid(climate._climatestation)
    assert station is not None
    monkeypatch.setattr(CligenStationsManager, 'get_closest_stations_by_lat', lambda *_: [station])
    with make_server('127.0.0.1', 0, metquery.app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setenv('EOBS_METQUERY_URL', f'http://127.0.0.1:{server.server_port}/')
            with pytest.raises(ValueError, match='E-OBS has no coverage for rainfall'):
                ClimateStationCatalogService().find_eu_heuristic_stations(climate, num_stations=1)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    assert climate._heuristic_stations is saved_ranking
    assert climate._climatestation == 'SPE00119882'


@pytest.mark.parametrize('override', [None, '', 'http://metquery:8004/'])
def test_provider_override_is_scoped_to_eobs_cubic(monkeypatch, override):
    if override is None:
        monkeypatch.delenv('EOBS_METQUERY_URL', raising=False)
    else:
        monkeypatch.setenv('EOBS_METQUERY_URL', override)
    default = 'https://example.invalid/metquery/'
    monkeypatch.setattr(metquery_client, '_metquery_url', default)
    destinations = []

    def record(url):
        destinations.append(url.split('?')[0])
        return SimpleNamespace(status_code=200, json=lambda: {'MonthlyValues': [5] * 12})

    monkeypatch.setattr(metquery_client.requests, 'get', record)
    metquery_client.get_eobs_monthly_ppt(3, 40)
    metquery_client.get_eobs_monthly_ppt(3, 40, method='bilinear')
    metquery_client.get_prism_monthly_ppt(-116, 47)
    assert destinations == [(override or default) + 'monthly', default + 'monthly', default + 'monthly']
