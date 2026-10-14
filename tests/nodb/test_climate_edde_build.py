"""EDDE parsing and actual NoDb/native publication; remote bytes use a fixture."""
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tests.nodb.lock_contention_utils import ensure_climate_stub
from tests.climates.test_edde_cligen import source
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core.climate import Climate, ClimateMode, ClimateSpatialMode, ClimatePrecipScalingMode
from wepppy.nodb.core import climate_edde_build as service
from wepppy.nodb.core.climate_edde_inputs import validate_edde_selection

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('projection,start,end,locale,spatial,scaling', [
    ('Historical', 2060, 2060, 'us', 0, 0),
    ('WRF-MPI/SSP2-4.5', True, 2060, 'us', 0, 0),
    ('WRF-MPI/SSP2-4.5', 2060.5, 2061, 'us', 0, 0),
    ('WRF-MPI/SSP2-4.5', 2024, 2060, 'us', 0, 0),
    ('WRF-Nor/SSP2-4.5', 2060, 2080, 'us', 0, 0),
    ('WRF-MPI/SSP2-4.5', 2060, 2060, 'eu', 0, 0),
    ('WRF-MPI/SSP2-4.5', 2060, 2060, 'us', 2, 0),
    ('WRF-MPI/SSP2-4.5', 2060, 2060, 'us', 0, 3),
])
def test_reject_unsupported_inputs(projection,start,end,locale,spatial,scaling):
    with pytest.raises(ValueError):
        validate_edde_selection(projection,start,end,locales=[locale],spatial_mode=spatial,scaling_mode=scaling)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    ensure_climate_stub(str(tmp_path))
    c = Climate.getInstance(str(tmp_path))
    with c.locked():
        c._future_start_year = c._future_end_year = 2060
        c._edde_projection = 'WRF-MPI/SSP2-4.5'
        c._climatestation = 'wa458928'
        c._climate_mode = ClimateMode.EddeV2
        c._climate_spatialmode = ClimateSpatialMode.Single
        c._precip_scaling_mode = ClimatePrecipScalingMode.NoScaling
        c._cligen_seed_override = 1001
        c.cli_fn = 'old.cli'
        c.par_fn = 'old.par'
    directory = Path(c.cli_dir)
    directory.mkdir(exist_ok=True)
    (directory / 'old.cli').write_text('previous accepted climate')
    monkeypatch.setattr(Climate, 'cligen_db', property(lambda _: '2015'))
    monkeypatch.setattr(NoDbBase, 'locales', property(lambda _: ['us']))
    watershed = SimpleNamespace(require_centroid=lambda: (-118.,46.), centroid_hillslope_iter=lambda: [])
    monkeypatch.setattr(NoDbBase, 'watershed_instance', property(lambda _: watershed))
    monkeypatch.setattr(NoDbBase, 'ron_instance', property(lambda _: SimpleNamespace(map=SimpleNamespace(extent=[-119,45,-117,47],cellsize=30))))
    monkeypatch.setattr(service, 'locate', lambda path, points: [{'name':p.name,'longitude':p.longitude,'latitude':p.latitude,'row':1,'col':1} for p in points])
    class Client:
        max_download_bytes = 4_000_000_000
        def __init__(self, cache):
            self.cache = Path(cache)
            self.session = SimpleNamespace(close=lambda: None)
        def grid(self, model):
            (self.cache/'grid.attempt.json').write_text('{"status":"complete"}')
            return self.cache/'grid.nc', {'source': 'fixture', 'sha256': 'fixture'}
        def inventory(self, model, scenario, year):
            return [{'key':f'EDDE_V2/{var}.fixture.{year}-{month:02d}.raw.nc','size':1} for var in ('prday','tsmax','tsmin') for month in range(1,13)]
        def query(self, points, model, scenario, start, end, variables):
            table, metas = source()
            table['date'] = pd.date_range(start,end)
            table['point'] = 'ws'
            meta = metas[0]
            meta.update(model=model,scenario=scenario,start=start,end=end,grid={'source': 'fixture', 'sha256': 'fixture'},points=[{'name':'ws','longitude':-118.,'latitude':46.,'row':1,'col':1}])
            return table,meta
    monkeypatch.setattr(service, 'EddeClient', Client)
    yield c
    Climate._instances.pop(str(tmp_path), None)


def test_real_replay_publication_and_reload(prepared):
    c = prepared
    service.run_edde_build(c)
    current = Climate.getInstance(c.wd)
    assert current.cli_fn == 'wepp.cli'
    assert current.edde_provenance['projection'] == 'WRF-MPI/SSP2-4.5'
    frame = service.read_cli(Path(c.cli_dir)/current.cli_fn)
    assert frame.index.equals(pd.date_range('2060-01-01','2060-12-31'))
    assert current.edde_provenance['files']['wepp.cli'] == service.sha256(Path(c.cli_dir)/'wepp.cli')
    assert not (Path(c.cli_dir)/'old.cli').exists()
    assert next(Path(c.cli_dir).glob('edde-build-*/grid-source/grid.attempt.json')).is_file()


@pytest.mark.parametrize('failure',['scaling','superseded','replace'])
def test_failed_build_preserves_previous_publication(prepared, monkeypatch, failure):
    c = prepared
    original = service._scale
    def scale(*args):
        if failure == 'scaling':
            raise ValueError('injected scaling failure')
        if failure == 'superseded':
            with c.locked():
                c._future_end_year = 2061
        return original(*args)
    monkeypatch.setattr(service, '_scale', scale)
    if failure == 'replace':
        import os
        replace = os.replace
        def denied(src, dst):
            if Path(dst) == Path(c.cli_dir)/'wepp.cli':
                raise PermissionError('injected publication failure')
            return replace(src,dst)
        monkeypatch.setattr(os,'replace',denied)
    with pytest.raises((ValueError,RuntimeError,PermissionError)):
        service.run_edde_build(c)
    restored = Climate.getInstance(c.wd)
    assert restored.cli_fn == 'old.cli'
    assert (Path(c.cli_dir)/'old.cli').read_text() == 'previous accepted climate'
    assert restored.edde_provenance is None
    status = json.loads(next(Path(c.cli_dir).glob('edde-build-*/build-status.json')).read_text())
    assert status['state'] == ('superseded' if failure == 'superseded' else 'failed')


def test_parser_failure_rolls_back_selection(prepared):
    c = prepared
    with pytest.raises(ValueError,match='AnnualMonthlies'):
        c.parse_inputs({'climate_mode':17,'climate_spatialmode':0,'edde_projection':'WRF-Nor/SSP2-4.5',
                        'future_start_year':2061,'future_end_year':2070,'precip_scaling_mode':3})
    assert c.edde_projection == 'WRF-MPI/SSP2-4.5'
    assert c.future_start_year == 2060
    assert c.precip_scaling_mode == ClimatePrecipScalingMode.NoScaling


def test_switch_away_clears_published_attribution_and_retains_attempt(prepared):
    c = prepared
    service.run_edde_build(c)
    attempt = c.edde_provenance['attempt']
    c.climate_mode = ClimateMode.Vanilla
    assert Climate.getInstance(c.wd).edde_provenance is None
    c.climate_mode = ClimateMode.EddeV2
    assert c.edde_provenance is None
    assert (Path(c.cli_dir)/attempt/'build-status.json').is_file()


def test_failed_grid_preflight_retains_request_and_reason(prepared, monkeypatch):
    def rejected(*args):
        raise service.DataQualityError('fixture landmask failure')
    monkeypatch.setattr(service, 'locate', rejected)
    with pytest.raises(service.DataQualityError):
        service.run_edde_build(prepared)
    status = json.loads(next(Path(prepared.cli_dir).glob('edde-build-*/build-status.json')).read_text())
    assert status['locations']['ws'] == [-118.,46.]
    assert status['error']['message'] == 'fixture landmask failure'


def test_multiple_prism_native_outputs_and_normals_provenance(prepared, monkeypatch):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from wepppy.nodb.core import climate_build_helpers
    c = prepared
    with c.locked():
        c._climate_spatialmode = ClimateSpatialMode.Multiple
    watershed = SimpleNamespace(require_centroid=lambda: (-118.,46.),
        centroid_hillslope_iter=lambda: [('1',(-117.9,46.))],
        hillslope_centroid_lnglat=lambda top: (-117.9,46.))
    monkeypatch.setattr(NoDbBase,'watershed_instance',property(lambda _:watershed))
    def retrieve(owner, map_obj, ppt, tmin, tmax):
        for variable, path, values in [('ppt',ppt,[100.,150.]),('tmin',tmin,[10.,11.]),('tmax',tmax,[20.,22.])]:
            with rasterio.open(path,'w',driver='GTiff',height=1,width=2,count=12,dtype='float32',
                               crs='EPSG:4326',transform=from_origin(-118.05,46.05,.1,.1),nodata=-9999) as dst:
                dst.write(np.tile(np.array(values,dtype='float32'),(12,1,1)))
            Path(path+'.meta').write_text(json.dumps({'wmesque':{'dataset':f'prism/{variable}/', 'revision':'a'*64},
                'wmesque_retrieve':{'wmesque_endpoint':f'http://{variable}.fixture'}}))
    monkeypatch.setattr(climate_build_helpers,'_retrieve_prism_revision_tiles',retrieve)
    service.run_edde_build(c)
    current = Climate.getInstance(c.wd)
    base = service.read_cli(Path(c.cli_dir)/current.cli_fn)
    hill = service.read_cli(Path(c.cli_dir)/current.sub_cli_fns['1'])
    np.testing.assert_allclose(hill.prcp,base.prcp*1.5,atol=.051)
    np.testing.assert_allclose(hill.tmax,base.tmax+2,atol=.051)
    record = json.loads((Path(c.cli_dir)/current.edde_provenance['attempt']/'prism-normals.json').read_text())
    assert record['period'] == '1991-2020'
    assert set(record['sha256']) == {'ppt','tmin','tmax'}
    assert record['serving_endpoints'] == {key:f'http://{key}.fixture' for key in ('ppt','tmin','tmax')}
    assert record['dataset_revisions'] == {key:'a'*64 for key in ('ppt','tmin','tmax')}
    assert Path(c.cli_dir,current.sub_cli_fns['1']+'.temperature-ordering.log').is_file()


def test_query_grid_change_rejects_before_replay_and_preserves_publication(prepared, monkeypatch):
    query = service.EddeClient.query
    def changed(self, *args, **kwargs):
        frame, manifest = query(self, *args, **kwargs)
        manifest['grid']['sha256'] = 'changed-source-grid'
        return frame, manifest
    monkeypatch.setattr(service.EddeClient, 'query', changed)
    with pytest.raises(service.DataQualityError, match='grid identity changed'):
        service.run_edde_build(prepared)
    current = Climate.getInstance(prepared.wd)
    assert current.cli_fn == 'old.cli'
    assert (Path(current.cli_dir)/'old.cli').read_text() == 'previous accepted climate'
    attempt = next(Path(current.cli_dir).glob('edde-build-*'))
    assert not (attempt/'generated').exists()
    assert json.loads((attempt/'source-2060.json').read_text())['grid']['sha256'] == 'changed-source-grid'


def test_report_uses_published_station_not_pending_selection():
    from jinja2 import Environment, FileSystemLoader
    templates = Path(__file__).resolve().parents[2]/'wepppy/weppcloud/templates'
    env = Environment(loader=FileSystemLoader(templates), autoescape=True)
    station = dict(desc='Published auxiliary station', id='published-id', longitude=-118., latitude=46., elevation=1000.)
    climate = SimpleNamespace(edde_provenance=dict(station=station, projection='WRF-MPI/SSP3-7.0',
        start_year=2060, end_year=2060, seed=1001, points=[], attempt='edde-build-example'),
        climate_mode=ClimateMode.EddeV2, is_single_storm=False, ss_batch_storms=None,
        par_fn='published.par', cli_fn='wepp.cli', monthlies=None)
    html = env.get_template('reports/climate.htm').render(climate=climate,
        station_meta=dict(station, desc='Pending station', id='pending-id'), runid='example', config='config',
        url_for_run=lambda *args, **kwargs: '/browse/'+kwargs.get('subpath',''))
    assert 'published-id' in html
    assert 'pending-id' not in html


def test_failed_new_period_preserves_published_simulation_length(prepared, monkeypatch):
    c = prepared
    service.run_edde_build(c)
    previous = c.edde_provenance
    assert c.input_years == 1
    c.parse_inputs({'climate_mode':17, 'climate_spatialmode':0, 'input_years':99,
        'edde_projection':'WRF-MPI/SSP2-4.5', 'future_start_year':2061, 'future_end_year':2062})
    assert (c.future_start_year, c.future_end_year) == (2061, 2062)
    assert c.input_years == 1
    assert c.calendar_start_year == 2060
    def rejected(*args):
        raise service.DataQualityError('new period acquisition failed')
    monkeypatch.setattr(service, 'locate', rejected)
    with pytest.raises(service.DataQualityError):
        service.run_edde_build(c)
    current = Climate.getInstance(c.wd)
    assert current.input_years == 1
    assert current.calendar_start_year == 2060
    assert current.edde_provenance == previous
    assert service.sha256(Path(c.cli_dir)/current.cli_fn) == previous['files'][current.cli_fn]
