from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from wepppy.eu.soils.esdac import ESDAC, validate_disturbed_soil_artifact
from wepppy.eu.soils.esdac import esdac as esdac_module
from wepppy.eu.soils.esdac.quality import ESDACSoilBuildError, SoilQualityResult
from wepppy.eu.soils.eusoilhydrogrids import SoilHydroGrids
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture


pytestmark = pytest.mark.unit

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eu_disturbed_soil_phase1.json"
LOOKUP_PATH = (
    Path(__file__).parents[3]
    / "wepppy"
    / "nodb"
    / "mods"
    / "disturbed"
    / "data"
    / "disturbed_land_soil_lookup.csv"
)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _patch_source_provider(monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]) -> None:
    source = case["esdb"]
    esdb_keys = {"cectop": "cec_top", "cecsub": "cec_sub"}

    def query(_self: object, _lng: float, _lat: float, attrs: tuple[str, ...]) -> dict[str, tuple[Any, ...]]:
        return {
            esdac_module._attr_fmt(attr): tuple(
                source[esdb_keys.get(esdac_module._attr_fmt(attr), esdac_module._attr_fmt(attr))]
            )
            for attr in attrs
        }

    def query_derived_db(
        _self: object, _lng: float, _lat: float, attrs: tuple[str, ...]
    ) -> dict[str, Any]:
        return {attr: case["stu"][attr] for attr in attrs}

    def hydro_query(
        _self: object, _lng: float, _lat: float, _dataset: str
    ) -> dict[str, tuple[int, Any]]:
        offsets = (0, 5, 15, 30, 60, 100, 200)
        return {
            depth: (offset, case["hydrogrids"][depth])
            for depth, offset in zip(case["hydrogrids"], offsets)
        }

    monkeypatch.setattr(ESDAC, "query", query)
    monkeypatch.setattr(ESDAC, "query_derived_db", query_derived_db)
    monkeypatch.setattr(SoilHydroGrids, "__init__", lambda _self: None)
    monkeypatch.setattr(SoilHydroGrids, "query", hydro_query)


def _lookup_row(texture: str, disturbed_class: str) -> dict[str, str]:
    with LOOKUP_PATH.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["stext"] == texture and row["luse"] == disturbed_class:
                return row
    raise AssertionError(f"missing disturbed lookup row: {texture!r}, {disturbed_class!r}")


def _build_disturbed_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_index: int = 0,
) -> tuple[Path, SoilQualityResult, dict[str, str]]:
    case = _load_fixture()["cases"][case_index]
    _patch_source_provider(monkeypatch, case)
    lng = case["provenance"]["lng"]
    lat = case["provenance"]["lat"]
    key, horizon, _description = ESDAC().build_wepp_soil(lng, lat, str(tmp_path))
    base_path = tmp_path / f"{key}.sol"
    base = WeppSoilUtil(str(base_path))
    texture = simple_texture(clay=base.clay, sand=base.sand)
    assert texture is not None
    disturbed_class = "forest low sev fire"
    replacements = _lookup_row(texture, disturbed_class)
    replacements.update({"luse": disturbed_class, "stext": texture})
    disturbed = base.to_over9000(replacements, version=9002)
    disturbed_path = tmp_path / f"{key}-disturbed.sol"
    disturbed.write(str(disturbed_path))
    return disturbed_path, horizon.quality_result, replacements


def _mutate_serialized_horizon(path: Path, *, field_index: int, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) < 11:
            continue
        try:
            [float(token) for token in tokens[:11]]
        except ValueError:
            continue
        tokens[field_index] = value
        lines[index] = "\t".join(tokens)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"no serialized 9002 horizon found in {path}")


@pytest.mark.parametrize(
    ("case_index", "expected_outcome"),
    ((0, "valid"), (2, "degraded")),
    ids=("valid-base", "degraded-base"),
)
def test_fixture_base_survives_serialized_disturbed_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_index: int,
    expected_outcome: str,
) -> None:
    disturbed_path, base_quality, replacements = _build_disturbed_fixture(
        monkeypatch, tmp_path, case_index
    )

    result = validate_disturbed_soil_artifact(
        disturbed_path,
        context=base_quality.context,
        expected_datver=9002,
        expected_luse=replacements["luse"],
        expected_stext=replacements["stext"],
        base_quality=base_quality,
    )

    assert result.outcome == expected_outcome
    assert result.accepted
    if expected_outcome == "degraded":
        assert "source.usedom.no_information" in result.reason_codes

    reparsed = WeppSoilUtil(str(disturbed_path))
    assert reparsed.datver == 9002.0
    assert reparsed.obj["ofes"][0]["luse"] == replacements["luse"]
    assert reparsed.obj["ofes"][0]["stext"] == replacements["stext"]


@pytest.mark.parametrize(
    "mutation",
    ("water_content", "depth_order", "zero_ksat"),
)
def test_disturbed_artifact_validator_rejects_invalid_serialized_parameters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    disturbed_path, base_quality, replacements = _build_disturbed_fixture(
        monkeypatch, tmp_path
    )
    if mutation == "water_content":
        _mutate_serialized_horizon(disturbed_path, field_index=4, value="0.2")
        _mutate_serialized_horizon(disturbed_path, field_index=5, value="0.4")
    elif mutation == "depth_order":
        invalid = WeppSoilUtil(str(disturbed_path))
        horizon = invalid.obj["ofes"][0]["horizons"]
        horizon[-1]["solthk"] = horizon[-2]["solthk"]
        invalid.write(str(disturbed_path))
    else:
        invalid = WeppSoilUtil(str(disturbed_path))
        horizon = invalid.obj["ofes"][0]["horizons"]
        horizon[0]["ksat"] = 0.0
        invalid.write(str(disturbed_path))

    result = validate_disturbed_soil_artifact(
        disturbed_path,
        context=base_quality.context,
        expected_datver=9002,
        expected_luse=replacements["luse"],
        expected_stext=replacements["stext"],
        base_quality=base_quality,
    )

    assert result.outcome == "rejected"
    if mutation == "water_content":
        assert "disturbed.horizon.water_content_order" in result.reason_codes
    elif mutation == "depth_order":
        assert "disturbed.horizon.depth_order" in result.reason_codes
    else:
        assert "disturbed.horizon.ksat_nonpositive" in result.reason_codes


def test_rejected_base_diagnostics_are_not_replaced_by_generic_disturbed_soil(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _load_fixture()["cases"][3]
    _patch_source_provider(monkeypatch, case)

    with pytest.raises(ESDACSoilBuildError) as error:
        ESDAC().build_wepp_soil(
            case["provenance"]["lng"],
            case["provenance"]["lat"],
            str(tmp_path),
        )

    base_quality = error.value.result
    result = validate_disturbed_soil_artifact(
        tmp_path / "not-generated.sol",
        context=base_quality.context,
        expected_datver=9002,
        expected_luse="forest low sev fire",
        expected_stext="loam",
        base_quality=base_quality,
    )

    assert result.outcome == "rejected"
    assert "source.stu.mandatory_profile_empty" in result.reason_codes
    assert "disturbed.base.rejected" in result.reason_codes
    assert "disturbed.artifact.parse_error" not in result.reason_codes
    assert not (tmp_path / "not-generated.sol").exists()
