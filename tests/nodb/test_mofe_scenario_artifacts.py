"""Read back actual MOFE managements at the three incident boundaries."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import logging

import numpy as np
from osgeo import gdal, osr
import pytest

import wepppy.nodb.core.landuse as lu
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.wepp.management import Management, get_management_summary

pytestmark = pytest.mark.integration


def _raster(path, values):
    data = np.array([values], dtype=np.int32)
    ds = gdal.GetDriverByName('GTiff').Create(str(path), len(values), 1, 1, gdal.GDT_Int32)
    ds.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32610)
    ds.SetProjection(crs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(data)
    ds.GetRasterBand(1).SetNoDataValue(255)
    ds.FlushCache()
    ds = None


def _read(path):
    return Management(Key='test', ManagementFile=path.name,
                      ManagementDir=str(path.parent), Description='test', Color=(0, 0, 0, 255))


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    (tmp_path / 'landuse').mkdir()
    landuse = lu.Landuse.__new__(lu.Landuse)
    landuse.wd = str(tmp_path)
    landuse._mods = []
    landuse._mapping = 'c3s-disturbed'
    landuse.logger = logging.getLogger(__name__)
    landuse.locked = lambda: nullcontext()
    landuse.islocked = lambda: True
    landuse.managements = {key: get_management_summary(key, 'c3s-disturbed')
                           for key in ('50', '406', '418', '405', '424')}
    landuse.domlc_d = {'101': '50'}
    landuse.domlc_mofe_d = {'101': {'1': '50', '2': '50'}}
    watershed = SimpleNamespace(_subs_summary={'101': {}}, mofe_nsegments={'101': 2},
                                mofe_buffer=False, subwta=str(tmp_path / 'sub.tif'),
                                mofe_map=str(tmp_path / 'mofe.tif'))
    monkeypatch.setattr(lu.Landuse, 'watershed_instance', property(lambda self: watershed))
    monkeypatch.setattr(lu.Landuse, 'multi_ofe', property(lambda self: True))
    monkeypatch.setattr(lu.os, 'cpu_count', lambda: 1)
    monkeypatch.setattr('wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance', lambda wd: None)
    return landuse, watershed, tmp_path


@pytest.mark.parametrize('cover', [0.30, 0.50])
def test_canopy_reaches_combined_and_prepared_management(scenario, monkeypatch, cover):
    landuse, watershed, root = scenario
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '424'}})
    landuse.modify_coverage('424', 'cancov', cover)
    combined = _read(root / 'landuse/hill_101.mofe.man')
    assert [ini.data.cancov for ini in combined.inis] == pytest.approx([cover, cover])

    # Exercise the real MOFE preparation management reader/writer; unrelated
    # slope/soil preparation is isolated.
    import wepppy.nodb.core.wepp as wepp
    monkeypatch.setattr(wepp, 'copy_input_file', lambda *args: None)
    class Soil:
        obj = {'ofes': []}
        def __init__(self, path): pass
        def modify_initial_sat(self, value): pass
        def write(self, path): pass
    monkeypatch.setattr(wepp, 'WeppSoilUtil', Soil)
    (root / 'soils').mkdir()
    (root / 'soils/hill_101.mofe.sol').touch()
    runs = root / 'wepp/runs'
    runs.mkdir(parents=True)
    wepp.prep_multi_ofe_hillslope(('101', 1, str(root), str(runs), 2,
                                 None, 0.5, False, None, False, None, False, None))
    prepared = _read(runs / 'p1.man')
    assert [ini.data.cancov for ini in prepared.inis] == pytest.approx([cover, cover])


def test_real_sbs_classification_reaches_management_files(scenario, monkeypatch):
    landuse, watershed, root = scenario
    watershed.mofe_nsegments = {'101': 5}
    _raster(root / 'sub.tif', [101] * 5)
    _raster(root / 'mofe.tif', [1, 2, 3, 4, 5])
    _raster(root / 'sbs.tif', [0, 1, 2, 3, 255])
    _raster(Path(landuse.lc_fn), [50] * 5)
    sbs = SoilBurnSeverityMap(str(root / 'sbs.tif'), breaks=[0, 1, 2, 3], nodata_vals=[255], ignore_ct=True)
    assert sbs.build_lcgrid(watershed.subwta, watershed.mofe_map)['101'] == {
        '1': '130', '2': '131', '3': '132', '4': '133', '5': '130'}
    disturbed = SimpleNamespace(land_soil_replacements_d=None, burn_shrubs=False,
        burn_grass=False, disturbed_cropped=str(root / 'sbs.tif'), get_sbs=lambda: sbs,
        get_disturbed_key_lookup=lambda: {
            'forest_low_sev_fire': '406', 'forest_moderate_sev_fire': '418',
            'forest_high_sev_fire': '405'})
    monkeypatch.setattr('wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance', lambda wd: disturbed)
    landuse._build_multiple_ofe()
    expected = ['50', '406', '418', '405', '50']
    assert list(landuse.domlc_mofe_d['101'].values()) == expected
    combined = _read(root / 'landuse/hill_101.mofe.man')
    assert [ini.data.cancov for ini in combined.inis] == pytest.approx([
        landuse.managements[key].get_management().inis[0].data.cancov for key in expected])


@pytest.mark.parametrize('writer_failure', [False, True])
def test_global_mapping_writes_files_before_completion(scenario, monkeypatch, writer_failure):
    landuse, watershed, root = scenario
    import wepppy.rq.project_rq as rq
    messages = []
    monkeypatch.setattr(rq, 'get_wd', lambda runid: str(root))
    monkeypatch.setattr(rq, 'get_current_job', lambda: SimpleNamespace(id='mapping'))
    monkeypatch.setattr(rq.RedisPrep, 'getInstance', lambda wd: SimpleNamespace(get_rq_job_id=lambda key: 'mapping'))
    monkeypatch.setattr(rq, 'clear_nodb_file_cache', lambda *args, **kwargs: None)
    monkeypatch.setattr(rq.Landuse, 'getInstance', lambda *args, **kwargs: landuse)
    monkeypatch.setattr(rq, '_run_with_directory_root_lock', lambda wd, root, fn, **kwargs: fn())
    landuse.build_managements = lambda: None
    path = root / 'landuse/hill_101.mofe.man'
    def publish(channel, message):
        if 'COMPLETED' in message:
            man = _read(path)
            assert man.inis[0].data.cancov == pytest.approx(landuse.managements['405'].cancov)
        messages.append(message)
    monkeypatch.setattr(rq.StatusMessenger, 'publish', publish)
    if writer_failure:
        # A directory at the exact output path forces the real open() to fail.
        path.mkdir()
        with pytest.raises(IsADirectoryError):
            rq.modify_landuse_mapping_rq('test', '50', '405')
        assert not any('COMPLETED' in message for message in messages)
        assert landuse.domlc_mofe_d == {'101': {'1': '50', '2': '50'}}
        path.rmdir()
    rq.modify_landuse_mapping_rq('test', '50', '405')
    assert landuse.domlc_mofe_d == {'101': {'1': '405', '2': '405'}}
    assert any('LANDUSE_MODIFY_MAPPING_TASK_COMPLETED' in message for message in messages)


@pytest.mark.parametrize('assignments', [None, {}])
def test_canopy_rejects_unbuilt_assignments_before_mutation(scenario, assignments):
    landuse, _, _ = scenario
    landuse.domlc_mofe_d = assignments
    with pytest.raises(ValueError, match='build landuse before modifying'):
        landuse.modify_coverage('424', 'cancov', 0.3)
    assert landuse.managements['424'].cancov_override is None


def test_explicit_assignments_reject_nonsequential_segments(scenario):
    landuse, _, root = scenario
    with pytest.raises(ValueError, match='incomplete OFE segments'):
        landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '50', '3': '50'}})
    assert not (root / 'landuse/hill_101.mofe.man').exists()


@pytest.mark.parametrize('cover', [0.0, 0.3, 0.5])
def test_summary_rebuild_preserves_mofe_canopy_selection(scenario, monkeypatch, cover):
    landuse, watershed, root = scenario
    landuse.domlc_d = {'101': '424'}
    landuse.domlc_mofe_d = {'101': {'1': '424', '2': '424'}}
    landuse.managements['424'].cancov_override = cover
    watershed.hillslope_area = lambda topaz_id: 0.18
    _raster(root / 'sub.tif', [101, 101])
    _raster(root / 'mofe.tif', [1, 2])
    monkeypatch.setattr(lu.Landuse, 'ron_instance', property(lambda self: SimpleNamespace(cellsize=30)))
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda event: None
    landuse.build_managements()
    assert landuse.managements['424'].cancov_override == cover
    assert landuse.managements['424'].area == pytest.approx(0.18)
