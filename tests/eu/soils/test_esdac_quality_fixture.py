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

    if case["expected_quality"] == "rejected":
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
    assert key == expected["key"]
    assert horizon.quality_result.outcome == case["expected_quality"]
    if case["expected_quality"] == "degraded":
        assert "source.usedom.no_information" in horizon.quality_result.reason_codes
    assert _horizon_depths(sol_path) == expected["horizon_depths"]
    assert expected["horizon_depths"][1] > expected["horizon_depths"][0]
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
