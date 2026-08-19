from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.eu.soils.esdac import ESDAC
from wepppy.eu.soils.esdac import esdac as esdac_module
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

    if expected["status"] == "exception":
        error_type = expected["error_type"]

        def failing_query(_self, _lng, _lat, _attrs):
            if error_type == "RDIOutOfBoundsException":
                raise RDIOutOfBoundsException
            if error_type == "TypeError":
                raise TypeError("int() argument must be a string, a bytes-like object or None")
            raise KeyError("")

        monkeypatch.setattr(ESDAC, "query", failing_query)
        with pytest.raises(
            {"RDIOutOfBoundsException": RDIOutOfBoundsException,
             "TypeError": TypeError,
             "KeyError": KeyError}[error_type]
        ):
            ESDAC().build_wepp_soil(
                case["provenance"]["lng"],
                case["provenance"]["lat"],
                str(tmp_path),
            )
        return

    _patch_source_provider(monkeypatch, case)
    key, _horizon, _description = ESDAC().build_wepp_soil(
        case["provenance"]["lng"],
        case["provenance"]["lat"],
        str(tmp_path),
    )

    sol_path = tmp_path / f"{key}.sol"
    assert sol_path.exists()
    assert key == expected["key"]
    assert _horizon_depths(sol_path) == expected["horizon_depths"]
    if "output.horizon_depth_order" in case["expected_issues"]:
        depths = expected["horizon_depths"]
        assert depths[1] <= depths[0]
    else:
        depths = expected["horizon_depths"]
        assert depths[1] > depths[0]
