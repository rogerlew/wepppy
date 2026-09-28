"""Read real combined and consumed files for independent single-input choices."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import logging
import shutil

import pytest

from wepppy.nodb.core.landuse import Landuse, LanduseMode
from wepppy.nodb.core.soils import Soils, SoilsMode
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepppy.wepp.management import Management, get_management_summary
from wepppy.wepp.management.managements import ManagementSummary
from wepppy.wepp.single_input import canonical_management, read_uploaded_management, decode_source
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
MAN = ROOT / 'wepppy/wepp/management/data/GeoWEPP/grass.man'
SOIL_DB = ROOT / 'wepppy/wepp/soils/soilsdb/data'


def _management(path):
    return Management(Key='test', ManagementFile=path.name, ManagementDir=str(path.parent),
                      Description='test', Color=(0, 0, 0, 255))


def _prepare_independent_sources(tmp_path, monkeypatch, uploaded_landuse, soil_source, uploaded_soil, ofe_counts=(2, 12)):
    for directory in ('landuse', 'soils', 'watershed/slope_files/hillslopes', 'wepp/runs'):
        (tmp_path / directory).mkdir(parents=True)
    segments = {str(101 + index): count for index, count in enumerate(ofe_counts)}
    watershed = SimpleNamespace(_subs_summary={hill: {} for hill in segments},
                                mofe_nsegments=segments, mofe_buffer=False)
    getter = lambda section, key, default=None: 'True' if key == 'single_user_defined_uploads' else ('wepp_260803' if key == 'bin' else default)
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path); landuse._mods = []; landuse._mapping = 'c3s-disturbed'
    landuse.config_get_str = getter; landuse.logger = logging.getLogger(__name__)
    landuse.locked = lambda: nullcontext()
    landuse.managements = {key: get_management_summary(key, 'c3s-disturbed') for key in ('50', '424')}
    landuse.domlc_d = {hill: '50' for hill in segments}
    monkeypatch.setattr(Landuse, 'watershed_instance', property(lambda _: watershed))
    monkeypatch.setattr('wepppy.nodb.core.landuse.os.cpu_count', lambda: 1)
    if uploaded_landuse:
        source = tmp_path / 'landuse/single-user-defined.man'
        source.write_text(decode_source(MAN.read_bytes()))
        source.write_text(canonical_management(read_uploaded_management(source)))
        landuse.managements = {'single-user-defined': ManagementSummary(
            Key='single-user-defined', ManagementFile=source.name, ManagementDir=str(source.parent),
            Description='source', Color=(0, 0, 0, 255))}
    assignments = {hill: {str(i): ('single-user-defined' if uploaded_landuse else ('424' if i == 10 else '50'))
                          for i in range(1, count + 1)} for hill, count in watershed.mofe_nsegments.items()}
    landuse._build_multiple_ofe(domlc_mofe_override=assignments)
    soils = Soils.__new__(Soils); soils.wd = str(tmp_path); soils._mods = []
    soils.config_get_str = getter
    soils._mode = SoilsMode.SingleUserDefined if uploaded_soil else SoilsMode.SingleDb
    soils.domsoil_d = {hill: 'source' for hill in segments}
    soils.soils = {'source': SimpleNamespace(fname='source.sol')}
    monkeypatch.setattr(Soils, 'watershed_instance', property(lambda _: watershed))
    source_text = (SOIL_DB / soil_source).read_text()
    if uploaded_soil:
        from wepppy.nodb.single_input_sources import _canonical_text
        source_text = _canonical_text(None, source_text.encode(), 'soils')
    (tmp_path / 'soils/source.sol').write_text(source_text)
    soils._build_undisturbed_multiple_ofe()
    for wepp_id, (hill, count) in enumerate(watershed.mofe_nsegments.items(), 1):
        slope = tmp_path / f'watershed/slope_files/hillslopes/hill_{hill}.mofe.slp'
        slope.write_text(f'97.5\n{count}\n180 20\n' + '2 10\n0, 0.1 1, 0.1\n' * count)
        combined = _management(tmp_path / f'landuse/hill_{hill}.mofe.man')
        assert combined.nofe == count
        active_covers = [combined.inis[int(str(ref))-1].data.cancov for ref in combined.man.ofeindx]
        if uploaded_landuse:
            assert len(set(active_covers)) == 1
        elif count == 12:
            expected = [landuse.managements[assignments[hill][str(i)]].cancov for i in range(1, count + 1)]
            assert active_covers == pytest.approx(expected)
        prep_multi_ofe_hillslope((hill, wepp_id, str(tmp_path), str(tmp_path / 'wepp/runs'), 2,
                                 None, 0.42, False, None, False, None, False, None, None, True, uploaded_soil))
        prepared = _management(tmp_path / f'wepp/runs/p{wepp_id}.man')
        prepared_soil = WeppSoilUtil(str(tmp_path / f'wepp/runs/p{wepp_id}.sol'), preserve_input_format=uploaded_soil)
        if uploaded_soil:
            original = WeppSoilUtil(str(tmp_path / 'soils/source.sol'), preserve_input_format=True)
            expected_ofe = original.obj['ofes'][0]
            expected_ofe['sat'] = 0.42
            assert prepared_soil.obj['datver'] == original.obj['datver']
            assert prepared_soil.obj['ksflag'] == original.obj['ksflag']
            assert all(ofe == expected_ofe for ofe in prepared_soil.obj['ofes'])
        assert prepared.nofe == count
        assert prepared.sim_years == 2
        assert len(prepared_soil.obj['ofes']) == count
        assert all(ofe['sat'] == pytest.approx(0.42) for ofe in prepared_soil.obj['ofes'])
        assert [prepared.inis[int(str(ref))-1].data.cancov for ref in prepared.man.ofeindx] == pytest.approx(active_covers)
        assert len({str(ofe) for ofe in prepared_soil.obj['ofes']}) == 1


@pytest.mark.parametrize('uploaded_landuse', [False, True])
@pytest.mark.parametrize(('soil_source', 'uploaded_soil'), [
    ('Forest/Forest loam.sol', True), ('Forest2006/Forest loam.sol', False),
    (str(ROOT / 'wepppy/locales/tenerife/soils/db/12.sol'), False),
])
def test_independent_sources_reach_all_hillslope_ofes(tmp_path, monkeypatch, uploaded_landuse, soil_source, uploaded_soil):
    _prepare_independent_sources(tmp_path, monkeypatch, uploaded_landuse, soil_source, uploaded_soil)


@pytest.mark.parametrize('ofe_counts', [(1,), (2, 12), (32,)])
@pytest.mark.parametrize('soil_source', ['Forest/Forest loam.sol'] + [str(ROOT / f'tests/data/single_input_soils/{version}.sol') for version in ('2006', '2006.2', '7777', '9002', 'boulderck_mica_1_7777')])
def test_uploaded_management_and_soil_execute_with_certified_binary(tmp_path, monkeypatch, ofe_counts, soil_source):
    from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope
    _prepare_independent_sources(tmp_path, monkeypatch, True, soil_source, True, ofe_counts)
    runs = tmp_path / 'wepp/runs'
    (tmp_path / 'wepp/output').mkdir()
    for wepp_id in range(1, len(ofe_counts) + 1):
        shutil.copyfile(ROOT / 'tests/disturbed/data/test_climate.cli', runs / f'p{wepp_id}.cli')
        make_hillslope_run(wepp_id, 2, str(runs), reveg=False, wepp_bin='wepp_260803')
        success, returned_id, _elapsed = run_hillslope(wepp_id, str(runs), wepp_bin='wepp_260803')
        assert success and returned_id == wepp_id
        output = (tmp_path / f'wepp/output/H{wepp_id}.loss.dat').read_text()
        import re
        assert output and not re.search(r'\b(?:nan|inf(?:inity)?)\b', output, re.IGNORECASE)


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
@pytest.mark.parametrize('count', [1, 3])
def test_native_preparation_modifiers_preserve_uploaded_formats(tmp_path, monkeypatch, version, count):
    from wepppy.nodb.core.wepp import prep_soil
    from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope
    source = ROOT / f'tests/data/single_input_soils/{version}.sol'
    _prepare_independent_sources(tmp_path, monkeypatch, False, str(source), True, (count,))
    raw = source.read_bytes()
    runs = tmp_path / 'wepp/runs'
    # Exercise flag zero as well as the flag-one baseline native matrix.
    if version == '9002':
        for path in [tmp_path / 'soils/source.sol', tmp_path / 'soils/hill_101.mofe.sol']:
            path.write_text(path.read_text().replace("1 'developed'", "0 'developed'"))
    if count == 1:
        prep_soil(('101', str(tmp_path / 'soils/source.sol'), str(runs / 'p1.sol'),
                   0.012345, None, 0.42, True, 400, True, 1000, True))
    else:
        prep_multi_ofe_hillslope(('101', 1, str(tmp_path), str(runs), 2, 0.012345, 0.42,
                                 False, None, True, 400, True, 1000, None, True, True))
    prepared = WeppSoilUtil(str(runs / 'p1.sol'), preserve_input_format=True)
    assert prepared.obj['datver'] == float(version)
    for ofe in prepared.obj['ofes']:
        assert ofe['res_lyr']['kslast'] == 0.012345
        assert ofe['sat'] == 0.42
        assert ofe['nsl'] == 1 and ofe['horizons'][0]['solthk'] == 400
        if version == '9002':
            assert ofe['horizons'][0]['native_hydraulics']['ks'] == 12.345
            assert ofe['horizons'][0]['native_hydraulics']['fc'] == 0.2876
            assert ofe['ksatadj'] == '0'
        elif version == '7777':
            assert ofe['res_lyr']['anisrt'] == 23.75
            assert ofe['horizons'][0]['ksat'] == 2.345
            assert ofe['horizons'][0]['anisotropy'] is None
        else:
            assert ofe['avke'] == 37.25
    (tmp_path / 'wepp/output').mkdir()
    shutil.copyfile(ROOT / 'tests/disturbed/data/test_climate.cli', runs / 'p1.cli')
    make_hillslope_run(1, 2, str(runs), reveg=False, wepp_bin='wepp_260803')
    assert run_hillslope(1, str(runs), wepp_bin='wepp_260803')[0]
    output = (tmp_path / 'wepp/output/H1.loss.dat').read_text()
    import re
    assert output and not re.search(r'\b(?:nan|inf(?:inity)?)\b', output, re.IGNORECASE)
    assert source.read_bytes() == raw
