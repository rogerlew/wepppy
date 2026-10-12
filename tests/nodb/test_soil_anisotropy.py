"""SA-01: actual native extension, persisted inputs and consumed soil files."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import builtins
import hashlib
import importlib

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def test_inputs_persist_clear_and_reject_without_mutation(tmp_path, monkeypatch):
    from wepppy.nodb.core.wepp import Wepp
    monkeypatch.setattr(Wepp, 'clean', lambda self: None)
    wepp = Wepp(str(tmp_path), 'canada-wbt-mofe.cfg')
    with wepp.locked():
        wepp._multi_ofe = True
        wepp._run_wepp_ui = True
    assert wepp.soil_anisotropy_upper is None
    wepp.parse_inputs({'soil_anisotropy_upper': '25', 'soil_anisotropy_lower': 3})
    wepp.parse_inputs({})
    reloaded = Wepp.load_detached(str(tmp_path))
    assert (reloaded.soil_anisotropy_upper, reloaded.soil_anisotropy_lower) == (25, 3)
    baseline = (tmp_path / 'wepp.nodb').read_bytes()
    with pytest.raises(ValueError):
        wepp.parse_inputs({'soil_anisotropy_upper': 8, 'soil_anisotropy_lower': 11, 'kslast': 99})
    assert (tmp_path / 'wepp.nodb').read_bytes() == baseline
    assert wepp.soil_anisotropy_upper == 25
    wepp.parse_inputs({'soil_anisotropy_upper': '', 'soil_anisotropy_lower': None})
    reloaded = Wepp.load_detached(str(tmp_path))
    assert reloaded.soil_anisotropy_upper is reloaded.soil_anisotropy_lower is None


@pytest.mark.parametrize('value', [True, False, float('nan'), float('inf'), -1, 0, 101, 'bad', [1, 2], {}, 10**400])
def test_invalid_requested_upper(value):
    from wepppy.nodb.core.soil_anisotropy import parse_anisotropy_inputs
    with pytest.raises(ValueError):
        parse_anisotropy_inputs(SimpleNamespace(multi_ofe=True, run_wepp_ui=True), {'soil_anisotropy_upper': value})


@pytest.mark.parametrize('multi,hourly', [(False, False), (False, True), (True, False)])
def test_ineligible_request_and_saved_state(multi, hourly):
    from wepppy.nodb.core.soil_anisotropy import parse_anisotropy_inputs, effective_anisotropy
    wepp = SimpleNamespace(multi_ofe=multi, run_wepp_ui=hourly, soil_anisotropy_upper=25, soil_anisotropy_lower=3)
    with pytest.raises(ValueError, match='require MOFE'):
        parse_anisotropy_inputs(wepp, {'soil_anisotropy_upper': 25})
    assert parse_anisotropy_inputs(wepp, {'soil_anisotropy_upper': None}) == {'soil_anisotropy_upper': None}
    assert effective_anisotropy(wepp) == (None, None)
    assert wepp.soil_anisotropy_upper == 25


def test_effective_hourly_override_and_saved_validation():
    from wepppy.nodb.core.soil_anisotropy import effective_anisotropy
    wepp = SimpleNamespace(multi_ofe=True, run_wepp_ui=False, soil_anisotropy_upper=25, soil_anisotropy_lower=3)
    assert effective_anisotropy(wepp, True) == (25, 3)
    wepp.run_wepp_ui = True
    assert effective_anisotropy(wepp, False) == (None, None)
    wepp.soil_anisotropy_lower = 11
    with pytest.raises(ValueError):
        effective_anisotropy(wepp)


def _soil_source(tmp_path, version=7778, symbolic=False):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    fixture = '7777.sol' if version == 7777 else '9002.sol'
    soil = WeppSoilUtil(str(ROOT / 'tests/data/single_input_soils' / fixture), preserve_input_format=True)
    soil.obj['datver'] = version
    first = soil.obj['ofes'][0]
    first['horizons'] = [deepcopy(first['horizons'][0]) for _ in range(3)]
    first['nsl'] = 3
    for horizon, depth, ratio in zip(first['horizons'], [100, 500, 800], [0, 2, 4]):
        horizon['solthk'] = depth
        horizon['anisotropy'] = ratio
    soil.obj['ofes'] = [deepcopy(first), deepcopy(first)]
    soil.obj['ntemp'] = 2
    if symbolic:
        soil._preserve_input_format = False
        for ofe in soil.obj['ofes']:
            ofe['ki'] = 'ki'
            for horizon in ofe['horizons']:
                horizon['ksat'] = 'ksat'
    source = tmp_path / 'soils/hill_101.mofe.sol'
    source.parent.mkdir(parents=True)
    soil.write(str(source))
    return source


def _mofe_files(tmp_path):
    from wepppy.wepp.management import get_management_summary
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    slope = tmp_path / 'watershed/slope_files/hillslopes/hill_101.mofe.slp'
    slope.parent.mkdir(parents=True)
    slope.write_text('97.5\n2\n0 30\n2 30\n0,0.1 1,0.1\n2 30\n0,0.1 1,0.1\n')
    man = tmp_path / 'landuse/hill_101.mofe.man'
    man.parent.mkdir()
    management = get_management_summary('144', 'disturbed').get_management()
    ManagementMultipleOfeSynth([management, management]).write(str(man))


def _prepare(tmp_path, source, *, uploaded=False, multi=True, options=(None, None), clip=False):
    module = importlib.import_module('wepppy.nodb.core.wepp')
    runs = tmp_path / 'wepp/runs'
    runs.mkdir(parents=True, exist_ok=True)
    dst = runs / 'p1.sol'
    if multi:
        module.prep_multi_ofe_hillslope(('101', 1, str(tmp_path), str(runs), 1, .02, .4,
            False, 300, clip, 500, False, 1000, None, False, uploaded, options))
    else:
        module.prep_soil(('101', str(source), str(dst), .02, None, .4, clip, 500, False, 1000, uploaded))
    return dst


@pytest.mark.parametrize('multi', [False, True])
@pytest.mark.parametrize('uploaded,symbolic', [(False, False), (True, False), (False, True)])
def test_preparation_one_source_read_one_destination_write(tmp_path, monkeypatch, multi, uploaded, symbolic):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source = _soil_source(tmp_path, symbolic=symbolic)
    if multi:
        _mofe_files(tmp_path)
    original = source.read_bytes()
    expected = WeppSoilUtil(str(source), compute_erodibilities=symbolic,
                            compute_conductivity=symbolic, preserve_input_format=uploaded)
    if symbolic:
        expected = expected.to7778()
    expected.modify_initial_sat(.4)
    expected.modify_kslast(.02)
    counts = {'read': 0, 'write': 0}
    real_open = builtins.open
    destination = tmp_path / 'wepp/runs/p1.sol'
    def counted_open(file, mode='r', *args, **kwargs):
        if str(file) == str(source) and 'r' in mode:
            counts['read'] += 1
        if str(file) == str(destination) and 'w' in mode:
            counts['write'] += 1
        return real_open(file, mode, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', counted_open)
        dst = _prepare(tmp_path, source, uploaded=uploaded, multi=multi)
    assert counts == {'read': 1, 'write': 1}
    assert source.read_bytes() == original
    generated = WeppSoilUtil(str(dst), preserve_input_format=uploaded)
    assert generated.obj['ofes'] == expected.obj['ofes']


@pytest.mark.parametrize('version', [7778, 9001, 9002, 9003, 9005])
def test_native_values_reach_all_prepared_ofes(tmp_path, version):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source = _soil_source(tmp_path)
    # Convert using the existing owned writer for versions with extra headers.
    if version != 7778:
        soil = WeppSoilUtil(str(source)).to_over9000({}, version=version)
        soil.write(str(source))
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    _mofe_files(tmp_path)
    baseline_path = _prepare(tmp_path, source)
    baseline = deepcopy(WeppSoilUtil(str(baseline_path)).obj)
    dst = _prepare(tmp_path, source, options=(25, 3))
    actual = WeppSoilUtil(str(dst)).obj
    for ofe in baseline['ofes']:
        for horizon in ofe['horizons']:
            horizon['anisotropy'] = 25 if horizon['solthk'] <= 500 else 3
    assert actual['ofes'] == baseline['ofes']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('uploaded', [False, True])
def test_crossing_horizon_receives_lower_value_without_splitting(tmp_path, uploaded):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source = _soil_source(tmp_path)
    soil = WeppSoilUtil(str(source))
    for ofe in soil.obj['ofes']:
        ofe['horizons'][1]['solthk'] = 600
    soil.write(str(source))
    original = source.read_bytes()
    _mofe_files(tmp_path)
    dst = _prepare(tmp_path, source, options=(25, 3), uploaded=uploaded)
    for ofe in WeppSoilUtil(str(dst)).obj['ofes']:
        assert [h['solthk'] for h in ofe['horizons']] == [100, 600, 800]
        assert [h['anisotropy'] for h in ofe['horizons']] == [25, 3, 3]
    assert source.read_bytes() == original


@pytest.mark.parametrize('uploaded', [False, True])
def test_clipping_precedes_classification_and_blank_retains_zero(tmp_path, uploaded):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source = _soil_source(tmp_path)
    _mofe_files(tmp_path)
    dst = _prepare(tmp_path, source, options=(None, 3), uploaded=uploaded)
    assert [h['anisotropy'] for h in WeppSoilUtil(str(dst)).obj['ofes'][0]['horizons']] == [0, 2, 3]
    dst = _prepare(tmp_path, source, options=(25, 3), uploaded=uploaded, clip=True)
    horizons = WeppSoilUtil(str(dst)).obj['ofes'][0]['horizons']
    assert [h['solthk'] for h in horizons] == ([100, 500] if uploaded else [100, 500, 500])
    assert all(h['anisotropy'] == 25 for h in horizons)


def test_unsupported_uploaded_7777_leaves_destination_absent(tmp_path):
    source = _soil_source(tmp_path, version=7777)
    _mofe_files(tmp_path)
    original = source.read_bytes()
    with pytest.raises(ValueError, match='does not support per-horizon'):
        _prepare(tmp_path, source, options=(25, 3), uploaded=True)
    assert not (tmp_path / 'wepp/runs/p1.sol').exists()
    assert source.read_bytes() == original


def test_preserved_validation_keeps_canonical_error_and_source_read_errors(tmp_path):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.single_input import SingleInputError
    source = tmp_path / 'invalid.sol'
    source.write_text('not a soil')
    with pytest.raises(SingleInputError) as result:
        WeppSoilUtil(str(source), preserve_input_format=True)
    assert result.value.status_code == 400
    with pytest.raises(FileNotFoundError):
        WeppSoilUtil(str(tmp_path / 'missing.sol'), preserve_input_format=True)


@pytest.mark.parametrize('saved,hourly,expected', [(True, None, [25, 25, 3]), (True, False, [0, 2, 4]), (False, True, [25, 25, 3])])
def test_facade_prep_passes_effective_options_to_real_worker(tmp_path, saved, hourly, expected):
    from wepppy.nodb.core.wepp import Wepp
    from wepppy.wepp.soils.utils import WeppSoilUtil
    import logging
    _soil_source(tmp_path)
    _mofe_files(tmp_path)
    runs = tmp_path / 'wepp/runs'; runs.mkdir(parents=True)
    context = SimpleNamespace(
        multi_ofe=True, run_wepp_ui=saved, soil_anisotropy_upper=25, soil_anisotropy_lower=3,
        wd=str(tmp_path), logger=logging.getLogger(__name__), kslast=None, kslast_map=None,
        climate_instance=SimpleNamespace(input_years=1), runs_dir=str(runs),
        watershed_instance=SimpleNamespace(subs_summary={'101': {}}, clip_hillslopes_configured=False,
                                           clip_hillslope_length=300),
        soils_instance=SimpleNamespace(clip_soils=False, clip_soils_depth=1000,
            clip_soils_minimum=False, clip_soils_minimum_depth=1000, initial_sat=.4))
    Wepp._prep_multi_ofe(context, SimpleNamespace(wepp=lambda **kwargs: 1), max_workers=1, wepp_ui=hourly)
    soil = WeppSoilUtil(str(runs/'p1.sol'))
    assert all([h['anisotropy'] for h in ofe['horizons']] == expected for ofe in soil.obj['ofes'])
