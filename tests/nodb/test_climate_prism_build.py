"""Real NoDb publication and native model files; only remote acquisition is replaced."""
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tests.nodb.lock_contention_utils import ensure_climate_stub
from tests.climates.prism.test_wepp_adapter import source
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core.climate import Climate, ClimateMode
from wepppy.nodb.core import climate_prism_build as service
from wepppy.climates.prism.bulk_client import PrismBulkResult, snap

pytestmark = pytest.mark.integration


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    ensure_climate_stub(str(tmp_path))
    c=Climate.getInstance(str(tmp_path))
    with c.locked():
        c._observed_start_year=c._observed_end_year=2020
        c._climatestation='or354811'
        c._climate_mode=ClimateMode.Prism800m
        c._climate_spatialmode=2
        c._cligen_seed_override=84568
        c._adjust_mx_pt5=False
        c._silent_pass_observed_quality_guard=True
        c.cli_fn='old.cli';c.par_fn='old.par'
        c.sub_cli_fns={'1':'old.cli'};c.sub_par_fns={'1':'old.par'}
    directory=Path(c.cli_dir);directory.mkdir(exist_ok=True)
    (directory/'old.cli').write_text('previous accepted climate')
    monkeypatch.setattr(Climate,'cligen_db',property(lambda _: '2015'))
    monkeypatch.setattr(NoDbBase,'locales',property(lambda _: ['us']))
    monkeypatch.setattr(service,'_locations',lambda _: {'ws':(-116.5,46.5),'1':(-116.5,46.5),'2':(-116.5,46.5)})
    frame=source()
    cell=snap(-116.5,46.5).id
    class Client:
        def __init__(self): self.attempt_directories=[]
        def retrieve(self, locations, start, end):
            own=tmp_path/'cache-attempt';own.mkdir(exist_ok=True)
            (own/'status.json').write_text('{"state":"complete"}')
            self.attempt_directories.append(own)
            return PrismBulkResult({cell:frame}, {name:{'cell':cell} for name in locations},
                [{'source_directory':str(own),'cache_root':str(tmp_path),
                  'freshness_check_attempt':own.name}])
    monkeypatch.setattr(service,'PrismBulkClient',Client)
    wind=pd.DataFrame({'vs(m/s)':2.,'th(DegreesClockwisefromnorth)':180.},index=frame.index)
    monkeypatch.setattr(service,'retrieve_historical_wind',lambda *args,**kw: wind)
    yield c,frame,wind
    Climate._instances.pop(str(tmp_path),None)


def test_publication_maps_aliases_and_retains_portable_sources(prepared):
    c,frame,_=prepared
    service.run_prism800m_build(c)
    current=Climate.getInstance(c.wd)
    assert current.has_climate
    assert current.sub_cli_fns['1'] != current.sub_cli_fns['2']
    assert (Path(c.cli_dir)/current.sub_cli_fns['1']).read_bytes() == (Path(c.cli_dir)/current.sub_cli_fns['2']).read_bytes()
    attempt=next(Path(c.cli_dir).glob('prism800m-build-*'))
    assert json.loads((attempt/'build-status.json').read_text())['state']=='complete'
    pd.testing.assert_frame_equal(pd.read_parquet(attempt/'prism800m-source-ws.parquet'),frame)
    provenance=json.loads((attempt/'provenance.json').read_text())
    assert (Path(c.wd)/provenance['sources'][0]['source_directory']/'status.json').is_file()
    assert not (Path(c.cli_dir)/'old.cli').exists()


@pytest.mark.parametrize('failure',['superseded','replace'])
def test_failed_publication_preserves_previous_and_retains_evidence(prepared,monkeypatch,failure):
    c,_,wind=prepared
    if failure=='superseded':
        def changed(*args,**kw):
            with c.locked(): c._observed_end_year=2021
            return wind
        monkeypatch.setattr(service,'retrieve_historical_wind',changed)
    else:
        import os
        real=os.replace
        def denied(src,dst):
            if Path(dst)==Path(c.cli_dir)/'wepp.cli': raise PermissionError('injected publication denial')
            return real(src,dst)
        monkeypatch.setattr(os,'replace',denied)
    with pytest.raises((RuntimeError,PermissionError)):
        service.run_prism800m_build(c)
    assert (Path(c.cli_dir)/'old.cli').read_text()=='previous accepted climate'
    restored=Climate.getInstance(c.wd)
    assert restored.cli_fn=='old.cli'
    status=next(Path(c.cli_dir).glob('prism800m-build-*/build-status.json'))
    assert json.loads(status.read_text())['state']=='failed'


def test_acquisition_failure_copies_only_own_attempt(prepared,monkeypatch):
    c,_,_=prepared
    class Failed:
        def __init__(self): self.attempt_directories=[]
        def retrieve(self,*args):
            p=Path(c.wd)/'failed-cache-attempt';p.mkdir();(p/'raw.csv').write_text('invalid payload')
            self.attempt_directories.append(p)
            raise ValueError('provider omitted cell')
    monkeypatch.setattr(service,'PrismBulkClient',Failed)
    with pytest.raises(ValueError,match='omitted'):service.run_prism800m_build(c)
    attempt=next(Path(c.cli_dir).glob('prism800m-build-*'))
    assert (attempt/'source/failed-cache-attempt/raw.csv').read_text()=='invalid payload'
    assert (Path(c.cli_dir)/'old.cli').exists()


def test_other_dataset_cleanup_keeps_prism_attempt(prepared):
    from wepppy.nodb.core.climate_build_router import _clear_directory_preserving_symlink_mount
    c,_,_=prepared
    stage=Path(c.cli_dir)/'prism800m-build-example';stage.mkdir();(stage/'status.json').write_text('working')
    _clear_directory_preserving_symlink_mount(c.cli_dir)
    assert (stage/'status.json').read_text()=='working'
    assert not (Path(c.cli_dir)/'old.cli').exists()


def test_same_cell_hills_can_receive_distinct_spatial_scaling(prepared,monkeypatch):
    import numpy as np
    from wepppy.nodb.core import climate_scaling_service as scaling
    from wepppy.climates.prism.wepp_adapter import read_cli
    c,_,_=prepared
    service.run_prism800m_build(c)
    originals={top:read_cli(Path(c.cli_dir)/name).prcp.copy() for top,name in c.sub_cli_fns.items()}
    watershed=SimpleNamespace(centroid=(0,0),hillslope_centroid_lnglat=lambda top: (int(top),0))
    monkeypatch.setattr(NoDbBase,'watershed_instance',property(lambda _: watershed))
    # Sampling is the controlled input; exercise native Rust scaling and persisted per-hill files.
    monkeypatch.setattr(scaling,'RasterDatasetInterpolator',lambda _: SimpleNamespace(get_location_info=lambda lon,lat: {0:1.,1:2.,2:3.}[lon]))
    raster=Path(c.wd)/'scale.tif';raster.write_bytes(b'sampling supplied by fixture')
    scaling.ClimateScalingService().spatial_scale_precip(c,str(raster))
    for top,factor in [('1',2),('2',3)]:
        actual=read_cli(Path(c.cli_dir)/c.sub_cli_fns[top]).prcp
        assert np.allclose(actual,originals[top]*factor,atol=.051)
