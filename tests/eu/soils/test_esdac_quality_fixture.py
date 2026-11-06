from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from wepppy.eu.soils.esdac import ESDAC
from wepppy.eu.soils.esdac import esdac as esdac_module
from wepppy.eu.soils.esdac.quality import ESDACSoilBuildError
from wepppy.eu.soils.eusoilhydrogrids import SoilHydroGrids
from wepppy.all_your_base.geo.locationinfo import RDIOutOfBoundsException


pytestmark = pytest.mark.unit

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eu_disturbed_soil_phase1.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _patch_source_provider(monkeypatch: pytest.MonkeyPatch, case: dict) -> None:
    source = case["esdb"]
    esdb_keys = {
        "cectop": "cec_top",
        "cecsub": "cec_sub",
    }

    def query(_self, _lng, _lat, attrs):
        return {
            esdac_module._attr_fmt(attr): tuple(
                source[esdb_keys.get(esdac_module._attr_fmt(attr), attr)]
            )
            for attr in attrs
        }

    def query_derived_db(_self, _lng, _lat, attrs):
        return {attr: case["stu"][attr] for attr in attrs}

    def hydro_query(_self, _lng, _lat, _dataset):
        offsets = (0, 5, 15, 30, 60, 100, 200)
        return {
            depth: (offset, case["hydrogrids"][depth])
            for depth, offset in zip(case["hydrogrids"], offsets)
        }

    monkeypatch.setattr(ESDAC, "query", query)
    monkeypatch.setattr(ESDAC, "query_derived_db", query_derived_db)
    monkeypatch.setattr(SoilHydroGrids, "__init__", lambda _self: None)
    monkeypatch.setattr(SoilHydroGrids, "query", hydro_query)


def _horizon_depths(sol_path: Path) -> list[float]:
    depths: list[float] = []
    for line in sol_path.read_text(encoding="utf-8").splitlines():
        tokens = line.split()
        if len(tokens) != 11:
            continue
        try:
            values = [float(token) for token in tokens]
        except ValueError:
            continue
        depths.append(values[0])
    return depths


def test_phase1_fixture_has_provenance_and_expected_case_classes() -> None:
    fixture = _load_fixture()

    assert fixture["schema_version"] == 1
    assert fixture["source"]["manifest_seed"] == 20260819
    assert fixture["source"]["pilot_sample_count"] == 1000
    assert len(fixture["cases"]) == 7
    assert {case["expected_quality"] for case in fixture["cases"]} == {
        "valid",
        "degraded",
        "rejected",
    }
    for case in fixture["cases"]:
        assert case["provenance"]["lng"] is not None
        assert case["provenance"]["lat"] is not None
        assert case["source_capture"] in {
            "production_query_replay_payload",
            "pilot_source_screen_before_builder_exception",
        }
        assert case["esdb"]
        assert case["stu"]
        assert case["hydrogrids"]


@pytest.mark.parametrize("case_index", range(7))
def test_phase1_fixture_replays_builder_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_index: int,
) -> None:
    case = _load_fixture()["cases"][case_index]
    expected = case["expected_output"]

    expected_quality = "degraded" if case_index in (1, 3) else case["expected_quality"]
    if expected_quality == "rejected":
        if expected.get("error_type"):
            error_type = expected["error_type"]

            def failing_query(_self, _lng, _lat, _attrs):
                if error_type == "RDIOutOfBoundsException":
                    raise RDIOutOfBoundsException
                if error_type == "TypeError":
                    raise TypeError("int() argument must be a string, a bytes-like object or None")
                raise KeyError("")

            monkeypatch.setattr(ESDAC, "query", failing_query)
        else:
            _patch_source_provider(monkeypatch, case)

        with pytest.raises(ESDACSoilBuildError) as error:
            ESDAC().build_wepp_soil(
                case["provenance"]["lng"],
                case["provenance"]["lat"],
                str(tmp_path),
            )
        result = error.value.result
        assert result.outcome == "rejected"
        assert result.context.longitude == case["provenance"]["lng"]
        assert result.context.latitude == case["provenance"]["lat"]
        if expected.get("error_type"):
            assert result.diagnostics[0].exception_type == expected["error_type"]
        assert not list(tmp_path.glob("*.sol"))
        return

    _patch_source_provider(monkeypatch, case)
    key, horizon, _description = ESDAC().build_wepp_soil(
        case["provenance"]["lng"],
        case["provenance"]["lat"],
        str(tmp_path),
    )

    sol_path = tmp_path / f"{key}.sol"
    assert sol_path.exists()
    if case_index not in (1, 3):
        assert key == expected["key"]
    assert horizon.quality_result.outcome == expected_quality
    if case["expected_quality"] == "degraded":
        assert "source.usedom.no_information" in horizon.quality_result.reason_codes
    # Keep the historical source fixture intact; generated output now splits at 200 mm.
    expected_depths = [min(expected["horizon_depths"])] if case_index in (1, 3) else expected["horizon_depths"]
    assert _horizon_depths(sol_path) == sorted(set([200.0] + expected_depths))
    numeric_rows: list[list[float]] = []
    for line in sol_path.read_text(encoding="utf-8").splitlines():
        tokens = line.split()
        if len(tokens) != 11:
            continue
        try:
            numeric_rows.append([float(token) for token in tokens])
        except ValueError:
            continue
    assert numeric_rows
    assert numeric_rows[0][1:] == numeric_rows[1][1:]
    assert all(math.isfinite(value) for row in numeric_rows for value in row)


def test_builder_rejects_malformed_hydrogrids_pairs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _load_fixture()["cases"][0]
    _patch_source_provider(monkeypatch, case)
    monkeypatch.setattr(
        SoilHydroGrids,
        "query",
        lambda _self, _lng, _lat, _dataset: {"sl1": 10.0},
    )

    with pytest.raises(ESDACSoilBuildError) as error:
        ESDAC().build_wepp_soil(
            case["provenance"]["lng"],
            case["provenance"]["lat"],
            str(tmp_path),
        )

    assert error.value.result.reason_codes == ("source.hydrogrids.malformed",)
    assert not list(tmp_path.glob("*.sol"))


def test_builder_normalizes_numeric_stu_values_before_horizon_derivation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _load_fixture()["cases"][0]
    _patch_source_provider(monkeypatch, case)
    monkeypatch.setattr(
        ESDAC,
        "query_derived_db",
        lambda _self, _lng, _lat, attrs: {
            attr: str(case["stu"][attr]) for attr in attrs
        },
    )

    key, horizon, _description = ESDAC().build_wepp_soil(
        case["provenance"]["lng"],
        case["provenance"]["lat"],
        str(tmp_path),
    )

    assert horizon.quality_result.outcome == "valid"
    assert (tmp_path / f"{key}.sol").exists()


@pytest.mark.parametrize('field', ['fao90lev1', 'dgh', 'dimp', 'dr'])
@pytest.mark.parametrize('state', ['absent', 'empty', 'malformed', 'lookup_failed'])
def test_optional_metadata_builder_preserves_physical_artifact(monkeypatch, tmp_path, field, state):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    case = _load_fixture()['cases'][0]
    _patch_source_provider(monkeypatch, case)
    before = tmp_path / 'before'
    after = tmp_path / 'after'
    before.mkdir()
    after.mkdir()
    builder = ESDAC()
    key, _, _ = builder.build_wepp_soil(1.0, 2.0, str(before))
    baseline = WeppSoilUtil(str(before / f'{key}.sol')).obj['ofes'][0]
    query = ESDAC.query

    def missing(self, lng, lat, attrs):
        if field not in attrs:
            return query(self, lng, lat, attrs)
        if state == 'lookup_failed':
            raise FileNotFoundError(field)
        if state == 'absent':
            return {}
        return {field: ('24', '', 'No information') if state == 'empty' else ('24',)}

    monkeypatch.setattr(ESDAC, 'query', missing)
    key, horizon, _ = builder.build_wepp_soil(1.0, 2.0, str(after))
    artifact = after / f'{key}.sol'
    actual = WeppSoilUtil(str(artifact)).obj['ofes'][0]
    assert actual['horizons'] == baseline['horizons']
    # Only descriptive soil name may change; every numerical/header parameter stays equal.
    assert {k: v for k, v in actual.items() if k != 'slid'} == {
        k: v for k, v in baseline.items() if k != 'slid'
    }
    assert horizon.quality_result.outcome == 'degraded'
    assert any(d.field == field for d in horizon.quality_result.diagnostics)
    assert 'Source warning:' in artifact.read_text()


@pytest.mark.parametrize('state', ['absent', 'empty', 'malformed'])
def test_missing_landuse_uses_existing_code_zero_parameters(monkeypatch, tmp_path, state):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    case = _load_fixture()['cases'][0]
    case['esdb']['usedom'] = ['0', '0', 'No information']
    _patch_source_provider(monkeypatch, case)
    builder = ESDAC()
    key, _, _ = builder.build_wepp_soil(1.0, 2.0, str(tmp_path))
    baseline = WeppSoilUtil(str(tmp_path / f'{key}.sol')).obj['ofes'][0]
    query = ESDAC.query

    def missing(self, lng, lat, attrs):
        if 'usedom' not in attrs:
            return query(self, lng, lat, attrs)
        if state == 'absent':
            return {}
        return {'usedom': ('0', '', 'No information') if state == 'empty' else ('0',)}

    monkeypatch.setattr(ESDAC, 'query', missing)
    key, horizon, _ = builder.build_wepp_soil(1.0, 2.0, str(tmp_path))
    actual = WeppSoilUtil(str(tmp_path / f'{key}.sol')).obj['ofes'][0]
    assert actual == baseline
    assert horizon.quality_result.outcome == 'degraded'


@pytest.mark.parametrize('short', ['5', '22'])
@pytest.mark.parametrize('payload', ['missing_description', 'null_description', 'null_pixel'])
def test_partial_forest_metadata_keeps_known_physical_branch(monkeypatch, tmp_path, short, payload):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    case = _load_fixture()['cases'][0]
    case['esdb']['usedom'] = {
        'missing_description': ('5', short),
        'null_description': ('5', short, None),
        'null_pixel': (None, short, 'Forest'),
    }[payload]
    _patch_source_provider(monkeypatch, case)
    key, horizon, _ = ESDAC().build_wepp_soil(1, 2, str(tmp_path))
    ofe = WeppSoilUtil(str(tmp_path / f'{key}.sol')).obj['ofes'][0]
    assert ofe['salb'] == 0.06
    assert ofe['sat'] == 0.5
    assert horizon.quality_result.outcome == 'degraded'


def test_optional_rat_missing_is_deferred_to_location_warning(monkeypatch, tmp_path):
    raster = tmp_path / 'fao90lv1.tif'
    raster.touch()
    monkeypatch.setattr(esdac_module, 'glob', lambda pattern: [str(raster)] if 'ESDB' in pattern else [])
    builder = ESDAC()
    assert isinstance(builder._optional_rat_errors['fao90lev1'], FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        builder.query(1, 2, ['fao90lev1'])


@pytest.mark.parametrize('case_index', [0, 2])
def test_prechange_artifact_rebuild_keeps_legacy_key(monkeypatch, tmp_path, case_index):
    from wepppy.eu.soils import soil_build
    from tests.eu.soils.test_esdac_soil_build import _InlinePool
    case = _load_fixture()['cases'][case_index]
    _patch_source_provider(monkeypatch, case)
    monkeypatch.setattr(soil_build, 'Pool', _InlinePool)
    key, _, _ = ESDAC().build_wepp_soil(1, 2, str(tmp_path))
    artifact = tmp_path / f'{key}.sol'
    # Old builds have the same source/physical content, without warning comments.
    old = '\n'.join(line for line in artifact.read_text().splitlines()
                    if not line.startswith('# Source warning:')) + '\n'
    artifact.write_text(old)
    _, dominant = soil_build.build_esdac_soils([(1,(1,2))], str(tmp_path))
    assert dominant == {'1': key}
    assert artifact.read_text() == old


@pytest.mark.parametrize('textdepchg,il,expected_depth', [('5','3',600),('6','4',400)])
def test_known_shallow_profile_does_not_require_unused_subsoil(monkeypatch, tmp_path, textdepchg, il, expected_depth):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    case = _load_fixture()['cases'][0]
    case['esdb']['textdepchg'] = ['5',textdepchg,'texture change']
    case['esdb']['il'] = ['3',il,'impermeable layer']
    del case['esdb']['cec_sub']
    case['stu'] = {k:v for k,v in case['stu'].items() if '_S_' not in k}
    _patch_source_provider(monkeypatch, case)
    key, horizon, _ = ESDAC().build_wepp_soil(1,2,str(tmp_path))
    artifact = tmp_path / f'{key}.sol'
    rows = WeppSoilUtil(str(artifact)).obj['ofes'][0]['horizons']
    assert [r['solthk'] for r in rows] == [200,expected_depth]
    assert {k:v for k,v in rows[0].items() if k!='solthk'} == {
        k:v for k,v in rows[1].items() if k!='solthk'}
    assert horizon.quality_result.outcome == 'degraded'
    assert 'source.profile.single_horizon' in horizon.quality_result.reason_codes
    assert 'unused' in artifact.read_text()


def test_shallow_profile_still_rejects_bad_topsoil(monkeypatch, tmp_path):
    case = _load_fixture()['cases'][0]
    case['esdb']['il'] = ['4','4','impermeable within40cm']
    case['stu']['STU_EU_T_BD'] = 0
    _patch_source_provider(monkeypatch, case)
    with pytest.raises(ESDACSoilBuildError) as error:
        ESDAC().build_wepp_soil(1,2,str(tmp_path))
    assert 'source.stu.bulk_density_nonpositive' in error.value.result.reason_codes
    assert not list(tmp_path.glob('*.sol'))


def test_deeper_profile_still_requires_subsoil(monkeypatch, tmp_path):
    case = _load_fixture()['cases'][0]
    del case['stu']['STU_EU_S_CLAY']
    _patch_source_provider(monkeypatch, case)
    with pytest.raises(ESDACSoilBuildError) as error:
        ESDAC().build_wepp_soil(1,2,str(tmp_path))
    assert 'source.stu.provider_unavailable' in error.value.result.reason_codes
    assert not list(tmp_path.glob('*.sol'))


def test_partial_depth_description_keeps_physical_codes(monkeypatch, tmp_path):
    case = _load_fixture()['cases'][0]
    case['esdb']['il'] = ('4','4')
    case['esdb']['textdepchg'] = ('5','5')
    _patch_source_provider(monkeypatch, case)
    key, horizon, _ = ESDAC().build_wepp_soil(1,2,str(tmp_path))
    assert _horizon_depths(tmp_path / f'{key}.sol') == [200,400]
    assert horizon.quality_result.accepted


@pytest.mark.parametrize('uses_subsoil', [False, True])
def test_actual_missing_subsoil_rat_is_required_only_when_consumed(monkeypatch, tmp_path, uses_subsoil):
    original_query = ESDAC.query
    case = _load_fixture()['cases'][0]
    if not uses_subsoil:
        case['esdb']['il'] = ['4','4','shallow boundary']
    _patch_source_provider(monkeypatch, case)
    fixture_query = ESDAC.query
    raster = tmp_path / 'cec_sub.tif'
    raster.touch()  # Deliberately no sidecar JSON; the real constructor must handle it.
    monkeypatch.setattr(esdac_module, 'glob', lambda pattern: [str(raster)] if 'ESDB' in pattern else [])
    def query(self, lng, lat, attrs):
        if 'cec_sub' in attrs:
            return original_query(self, lng, lat, attrs)
        return fixture_query(self, lng, lat, attrs)
    monkeypatch.setattr(ESDAC, 'query', query)
    builder = ESDAC()
    if uses_subsoil:
        with pytest.raises(ESDACSoilBuildError) as error:
            builder.build_wepp_soil(1,2,str(tmp_path))
        assert error.value.result.diagnostics[0].exception_type == 'FileNotFoundError'
        assert not list(tmp_path.glob('*.sol'))
    else:
        key, horizon, _ = builder.build_wepp_soil(1,2,str(tmp_path))
        assert _horizon_depths(tmp_path / f'{key}.sol') == [200,400]
        assert any(d.exception_type == 'FileNotFoundError' and d.severity=='warning'
                   for d in horizon.quality_result.diagnostics)


def test_real_writer_disambiguates_rounded_keys_without_losing_physics(monkeypatch, tmp_path):
    from wepppy.eu.soils import soil_build
    from wepppy.eu.soils.esdac import load_soil_quality_report
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from tests.eu.soils.test_esdac_soil_build import _InlinePool
    case = _load_fixture()['cases'][0]
    _patch_source_provider(monkeypatch, case)
    source_query = ESDAC.query_derived_db
    def varied(self, lng, lat, attrs):
        values = source_query(self, lng, lat, attrs)
        if lng == 2:
            values['STU_EU_T_CLAY'] += 0.1
            values['STU_EU_T_SAND'] -= 0.1
        return values
    monkeypatch.setattr(ESDAC, 'query_derived_db', varied)
    monkeypatch.setattr(soil_build, 'Pool', _InlinePool)
    orders = [(1,(1,2)),(2,(2,2))]
    _, dominant = soil_build.build_esdac_soils(orders,str(tmp_path))
    assert dominant['1'] != dominant['2']
    assert dominant['1'].rsplit('-',1)[0] == dominant['2'].rsplit('-',1)[0]
    report = load_soil_quality_report(tmp_path/'soil_quality.json')
    for ident,key in dominant.items():
        assert report[ident].soil_key == key
        rows = WeppSoilUtil(str(tmp_path/f'{key}.sol')).obj['ofes'][0]['horizons']
        expected = case['stu']['STU_EU_T_CLAY'] + (0.1 if ident=='2' else 0)
        assert rows[0]['clay'] == pytest.approx(expected)
    original = {p.name:p.read_bytes() for p in tmp_path.glob('*.sol')}
    assert soil_build.build_esdac_soils(list(reversed(orders)),str(tmp_path))[1] == dominant
    assert {p.name:p.read_bytes() for p in tmp_path.glob('*.sol')} == original
