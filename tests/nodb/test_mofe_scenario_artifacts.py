"""Read back actual MOFE managements at the three incident boundaries."""
from contextlib import contextmanager, nullcontext
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


@pytest.mark.parametrize('cover', [0.0, 0.9, 1.0])
def test_configured_defaults_reach_real_managements(scenario, cover):
    landuse, _, root = scenario
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '50'}})
    before = _read(root / 'landuse/hill_101.mofe.man')
    landuse.cover_defaults_d = {'424': dict(cancov=cover, inrcov=cover, rilcov=cover)}
    landuse.set_cover_defaults()
    after = _read(root / 'landuse/hill_101.mofe.man')
    for field in ('cancov', 'inrcov', 'rilcov'):
        assert getattr(after.inis[0].data, field) == pytest.approx(cover)
        assert getattr(after.inis[1].data, field) == getattr(before.inis[1].data, field)


@pytest.mark.parametrize('defaults', [None, {}, {'missing': dict(cancov=0, inrcov=0, rilcov=0)}])
def test_no_applicable_defaults_do_not_require_assignments(scenario, defaults):
    landuse, _, _ = scenario
    landuse.cover_defaults_d = defaults
    landuse.domlc_mofe_d = None
    landuse._build_multiple_ofe = lambda **kw: pytest.fail('unexpected regeneration')
    landuse.set_cover_defaults()


@pytest.mark.parametrize('assignments', [None, {}])
def test_applicable_defaults_reject_unbuilt_assignments_before_mutation(scenario, assignments):
    landuse, _, _ = scenario
    landuse.cover_defaults_d = {'424': dict(cancov=0, inrcov=0, rilcov=0)}
    landuse.domlc_mofe_d = assignments
    before = landuse.managements['424'].cancov_override
    with pytest.raises(ValueError, match='build landuse before modifying'):
        landuse.set_cover_defaults()
    assert landuse.managements['424'].cancov_override == before


def test_default_writer_failure_retry_regenerates_already_saved_values(scenario):
    landuse, _, root = scenario
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '424'}})
    landuse.cover_defaults_d = {'424': dict(cancov=0.3, inrcov=0.9, rilcov=0.9)}
    target = root / 'landuse/hill_101.mofe.man'
    retained = target.with_suffix('.before')
    target.rename(retained)
    target.mkdir()  # Real filesystem writer failure, with old evidence retained.
    with pytest.raises(IsADirectoryError):
        landuse.set_cover_defaults()
    assert landuse.managements['424'].inrcov_override == 0.9
    assert retained.is_file()
    target.rmdir()
    landuse.set_cover_defaults()
    after = _read(root / 'landuse/hill_101.mofe.man')
    assert [ini.data.inrcov for ini in after.inis] == pytest.approx([0.9, 0.9])


def test_single_ofe_defaults_do_not_generate_mofe(scenario, monkeypatch):
    landuse, _, _ = scenario
    monkeypatch.setattr(lu.Landuse, 'multi_ofe', property(lambda self: False))
    landuse.cover_defaults_d = {'424': dict(cancov=0.3, inrcov=0.9, rilcov=0.9)}
    landuse.domlc_mofe_d = None
    landuse._build_multiple_ofe = lambda **kw: pytest.fail('unexpected MOFE generation')
    landuse.set_cover_defaults()
    assert landuse.managements['424'].inrcov_override == 0.9


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


@pytest.mark.parametrize('field', ['cancov', 'inrcov', 'rilcov'])
@pytest.mark.parametrize('cover', [0.0, 0.30, 0.50, 0.90, 1.0])
@pytest.mark.parametrize('operation', ['coverage', 'defaults'])
def test_cover_reaches_combined_and_prepared_management(scenario, monkeypatch, field, cover, operation):
    landuse, watershed, root = scenario
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '50'}})
    before = _read(root / 'landuse/hill_101.mofe.man')
    if operation == 'coverage':
        landuse.modify_coverage('424', field, cover)
    else:
        values = {attr: getattr(before.inis[0].data, attr)
                  for attr in ('cancov', 'inrcov', 'rilcov')}
        values[field] = cover
        landuse.cover_defaults_d = {'424': values}
        landuse.set_cover_defaults()
    combined = _read(root / 'landuse/hill_101.mofe.man')
    for index in range(2):
        for attr in ('cancov', 'inrcov', 'rilcov'):
            expected = cover if index == 0 and attr == field else getattr(before.inis[index].data, attr)
            assert getattr(combined.inis[index].data, attr) == pytest.approx(expected)

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
    for attr in ('cancov', 'inrcov', 'rilcov'):
        assert [getattr(ini.data, attr) for ini in prepared.inis] == pytest.approx(
            [getattr(ini.data, attr) for ini in combined.inis])


@pytest.mark.parametrize('operation', ['initial_build', 'selected_modify'])
def test_defaults_at_normal_build_and_modify_boundaries(scenario, monkeypatch, operation):
    landuse, watershed, root = scenario
    landuse.cover_defaults_d = {'424': dict(cancov=0.3, inrcov=0.9, rilcov=1.0)}
    watershed.hillslope_area = lambda topaz_id: 0.18
    watershed.is_abstracted = True
    _raster(root / 'sub.tif', [101, 101])
    _raster(root / 'mofe.tif', [1, 2])
    monkeypatch.setattr(lu.Landuse, 'ron_instance', property(lambda self: SimpleNamespace(cellsize=30)))
    monkeypatch.setattr(lu.Landuse, 'getInstance', lambda wd: landuse)
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda event: None
    if operation == 'selected_modify':
        landuse.modify(['101'], '424')
    else:
        locked = False
        @contextmanager
        def lock():
            nonlocal locked
            locked = True
            try:
                yield
            finally:
                locked = False
        landuse.locked = lock
        landuse.islocked = lambda: locked
        landuse._mode = lu.LanduseMode.Gridded
        landuse._locales = ['canada']
        monkeypatch.setattr('wepppy.nodb.project_config_capabilities.resolve_run_capability_authority',
                            lambda obj: SimpleNamespace(runtime_tokens=('canada',)))
        landuse._build_NLCD = lambda **kw: None  # Isolate acquisition, not synthesis/default ordering.
        landuse._build_fractionals = lambda: None
        monkeypatch.setattr(lu, 'identify_mode_intersecting_raster_keys',
                            lambda **kw: {'101': {'1': '424', '2': '424'}})
        monkeypatch.setattr(lu, '_wait_for_gdal_openable_raster', lambda *a, **kw: None)
        monkeypatch.setattr(lu.RedisPrep, 'getInstance', lambda wd: SimpleNamespace(timestamp=lambda task: None))
        landuse.build(retrieve_nlcd=False)
    man = _read(root / 'landuse/hill_101.mofe.man')
    assert [(ini.data.cancov, ini.data.inrcov, ini.data.rilcov) for ini in man.inis] == [(0.3, 0.9, 1.0)] * 2


@pytest.mark.parametrize('kind,source,target,canopy,ground', [
    ('thinning', '90', '424', 40, 75), ('prescribed_fire', '90', '410', 40, 75),
    ('mulch', '418', '418030', 40, 75),
] + [('thinning', '90', str(443 + ci * 4 + gi), canopy, ground)
     for ci, canopy in enumerate((30, 50, 60, 70))
     for gi, ground in enumerate((93, 90, 85, 75))])
def test_omni_mixed_segments_reach_combined_and_prepared_inputs(
    scenario, monkeypatch, kind, source, target, canopy, ground,
):
    from wepppy.nodb.mods.omni.omni_mode_build_services import OmniModeBuildServices
    from wepppy.nodb.mods.omni.omni import OmniScenario
    from wepppy.nodb.mods.treatments import Treatments
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.core import Soils, Watershed
    import wepppy.nodb.core.wepp as wepp

    landuse, watershed, root = scenario
    # Both segments are real managements; scalar bare class must not hide forest.
    for key in ('90', '200', '410'):
        landuse.managements[key] = get_management_summary(key, 'c3s-disturbed')
    landuse.domlc_d = {'101': '200'}
    landuse.domlc_mofe_d = {'101': {'1': '200', '2': source}}
    landuse._build_multiple_ofe(domlc_mofe_override=landuse.domlc_mofe_d)
    before = _read(root / 'landuse/hill_101.mofe.man')
    unchanged_cover = before.inis[0].data.inrcov
    source_cover = before.inis[1].data.inrcov
    landuse.build = lambda: None  # Existing burned-base build is independently tested.
    landuse.build_managements = lambda: None
    landuse.dump_landuse_parquet = lambda: None
    watershed.translator_factory = lambda: object()
    monkeypatch.setattr(Watershed, 'getInstance', lambda wd: watershed)
    monkeypatch.setattr(lu.Landuse, 'getInstance', lambda wd: landuse)
    soils = SimpleNamespace(build=lambda **kwargs: None)
    monkeypatch.setattr(Soils, 'getInstance', lambda wd: soils)
    soil_calls = []
    disturbed = SimpleNamespace(has_sbs=False, land_soil_replacements_d={},
        get_disturbed_key_lookup=lambda: {f'thinning_{canopy}_{ground}': target,
            'forest_prescribed_fire': '410'},
        modify_mofe_soils=lambda: soil_calls.append('rebuilt'))
    monkeypatch.setattr(Disturbed, 'getInstance', lambda wd: disturbed)
    treatments = Treatments.__new__(Treatments)
    treatments.wd = str(root)
    treatments.logger = logging.getLogger(__name__)
    treatments.locked = lambda: nullcontext()
    monkeypatch.setattr(Treatments, 'getInstance', lambda wd: treatments)
    omni = SimpleNamespace(wd=str(root), has_sbs=False, logger=logging.getLogger(__name__),
        timed=lambda label: nullcontext(), rq_job_pool_max_worker_per_scenario_task=1)
    definition = {'type': kind, 'canopy_cover': f'{canopy}%', 'ground_cover': f'{ground}%',
                  'ground_cover_increase': '30%'}
    OmniModeBuildServices().apply_scenario_mode(omni, scenario_name=kind,
        scenario={'thinning': OmniScenario.Thinning, 'prescribed_fire': OmniScenario.PrescribedFire,
                  'mulch': OmniScenario.Mulch}[kind], scenario_def=definition,
        new_wd=str(root), disturbed=disturbed, landuse=landuse, soils=soils,
        omni_base_scenario_name='uniform_moderate' if kind == 'mulch' else None)
    assert landuse.domlc_mofe_d['101'] == {'1': '200', '2': target}
    assert soil_calls == ['rebuilt']
    combined = _read(root / 'landuse/hill_101.mofe.man')
    assert combined.inis[0].data.inrcov == pytest.approx(unchanged_cover)
    if kind == 'mulch':
        assert combined.inis[1].data.inrcov > source_cover
    else:
        expected = get_management_summary(target, 'c3s-disturbed').get_management()
        assert combined.inis[1].data.inrcov == pytest.approx(expected.inis[0].data.inrcov)

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
    assert [ini.data.inrcov for ini in prepared.inis] == pytest.approx(
        [ini.data.inrcov for ini in combined.inis])
    if kind == 'thinning':
        for management in (combined, prepared):
            assert (management.inis[1].data.cancov, management.inis[1].data.inrcov,
                    management.inis[1].data.rilcov) == pytest.approx(
                        (canopy / 100, ground / 100, ground / 100))


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
@pytest.mark.parametrize('field', ['cancov', 'inrcov', 'rilcov'])
def test_cover_rejects_unbuilt_assignments_before_mutation(scenario, assignments, field):
    landuse, _, _ = scenario
    landuse.domlc_mofe_d = assignments
    with pytest.raises(ValueError, match='build landuse before modifying'):
        landuse.modify_coverage('424', field, 0.3)
    assert getattr(landuse.managements['424'], field + '_override') is None


def test_explicit_assignments_reject_nonsequential_segments(scenario):
    landuse, _, root = scenario
    with pytest.raises(ValueError, match='incomplete OFE segments'):
        landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '50', '3': '50'}})
    assert not (root / 'landuse/hill_101.mofe.man').exists()


@pytest.mark.parametrize('cover', [0.0, 0.3, 0.5])
@pytest.mark.parametrize('field', ['cancov', 'inrcov', 'rilcov'])
def test_summary_rebuild_preserves_mofe_cover_selection(scenario, monkeypatch, cover, field):
    landuse, watershed, root = scenario
    landuse.domlc_d = {'101': '424'}
    landuse.domlc_mofe_d = {'101': {'1': '424', '2': '424'}}
    setattr(landuse.managements['424'], field + '_override', cover)
    watershed.hillslope_area = lambda topaz_id: 0.18
    _raster(root / 'sub.tif', [101, 101])
    _raster(root / 'mofe.tif', [1, 2])
    monkeypatch.setattr(lu.Landuse, 'ron_instance', property(lambda self: SimpleNamespace(cellsize=30)))
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda event: None
    landuse.build_managements()
    assert getattr(landuse.managements['424'], field + '_override') == cover
    assert landuse.managements['424'].area == pytest.approx(0.18)


@pytest.mark.parametrize('preloaded', [False, True])
def test_ground_overrides_win_after_disturbed_replacements(scenario, monkeypatch, preloaded):
    landuse, _, root = scenario
    summary = landuse.managements['424']
    summary.inrcov_override, summary.rilcov_override = 0.0, 1.0
    if preloaded:
        landuse.managements['424'] = SimpleNamespace(
            disturbed_class=summary.disturbed_class, get_management=summary.get_management,
            inrcov_override=0.0, rilcov_override=1.0)
    disturbed = SimpleNamespace(land_soil_replacements_d={
        ('sand loam', summary.disturbed_class): {
            'ini.data.inrcov': '0.2', 'ini.data.rilcov': '0.4'}})
    monkeypatch.setattr('wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance', lambda wd: disturbed)
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '424'}})
    actual = _read(root / 'landuse/hill_101.mofe.man')
    assert [ini.data.inrcov for ini in actual.inis] == [0.0, 0.0]
    assert [ini.data.rilcov for ini in actual.inis] == [1.0, 1.0]


@pytest.mark.parametrize('missing', [False, True])
def test_legacy_ground_override_absence_keeps_source(scenario, missing):
    landuse, _, root = scenario
    if missing:
        del landuse.managements['424'].inrcov_override
        del landuse.managements['424'].rilcov_override
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '424'}})
    actual = _read(root / 'landuse/hill_101.mofe.man')
    assert [ini.data.inrcov for ini in actual.inis] == [0.75, 0.75]
    assert [ini.data.rilcov for ini in actual.inis] == [0.75, 0.75]


def test_ground_overrides_cross_real_process_pool(scenario, monkeypatch):
    landuse, watershed, root = scenario
    watershed._subs_summary['102'] = {}
    watershed.mofe_nsegments['102'] = 2
    monkeypatch.setattr(lu.os, 'cpu_count', lambda: 2)
    monkeypatch.setenv('WEPPPY_NCPU', '2')
    landuse.managements['424'].inrcov_override = 0.9
    landuse.managements['424'].rilcov_override = 0.6
    landuse._build_multiple_ofe(domlc_mofe_override={
        topaz: {'1': '424', '2': '424'} for topaz in ('101', '102')})
    for topaz in ('101', '102'):
        actual = _read(root / f'landuse/hill_{topaz}.mofe.man')
        assert [ini.data.inrcov for ini in actual.inis] == [0.9, 0.9]
        assert [ini.data.rilcov for ini in actual.inis] == [0.6, 0.6]


@pytest.mark.parametrize('field', ['inrcov', 'rilcov'])
def test_ground_writer_error_is_visible_and_operation_can_retry(scenario, monkeypatch, field):
    landuse, _, root = scenario
    landuse._build_multiple_ofe(domlc_mofe_override={'101': {'1': '424', '2': '424'}})
    original = lu._write_mofe_management_file_task
    def fail(task):
        raise OSError('injected management writer failure')
    monkeypatch.setattr(lu, '_write_mofe_management_file_task', fail)
    with pytest.raises(OSError, match='injected management writer failure'):
        landuse.modify_coverage('424', field, 0.9)
    monkeypatch.setattr(lu, '_write_mofe_management_file_task', original)
    landuse.modify_coverage('424', field, 0.9)
    actual = _read(root / 'landuse/hill_101.mofe.man')
    assert [getattr(ini.data, field) for ini in actual.inis] == [0.9, 0.9]


@pytest.mark.parametrize('field', ['cancov', 'inrcov', 'rilcov'])
def test_single_ofe_coverage_does_not_require_mofe_assignments(scenario, monkeypatch, field):
    landuse, _, _ = scenario
    monkeypatch.setattr(lu.Landuse, 'multi_ofe', property(lambda self: False))
    landuse.domlc_mofe_d = None
    def unexpected_builder(**kwargs):
        pytest.fail('Single-OFE coverage must not invoke MOFE synthesis')
    landuse._build_multiple_ofe = unexpected_builder
    landuse.modify_coverage('424', field, 0.9)
    assert getattr(landuse.managements['424'], field + '_override') == 0.9
