from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.eu.soils.esdac.quality import (
    SoilQualityContext,
    merge_quality_results,
    rejected_quality_result,
    validate_esdac_source_profile,
    validate_horizon_depths,
    validate_horizon_profile,
    validate_ksat_profile,
)


pytestmark = pytest.mark.unit

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eu_disturbed_soil_phase1.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _context(case: dict) -> SoilQualityContext:
    provenance = case["provenance"]
    return SoilQualityContext(
        longitude=provenance["lng"],
        latitude=provenance["lat"],
        topaz_id=f"fixture-{provenance['sample_id']}",
    )


def _horizon(depth: float) -> dict[str, float]:
    return {
        "depth": depth,
        "bd": 1.2,
        "ks": 10.0,
        "anisotropy": 1.0,
        "field_cap": 0.25,
        "wilt_pt": 0.1,
        "sand": 40.0,
        "clay": 20.0,
        "silt": 40.0,
        "om": 2.0,
        "cec": 27.5,
        "smr": 0.0,
        "interrill": 100.0,
        "rill": 0.01,
        "shear": 3.5,
    }


def _fixture_result(case: dict):
    context = _context(case)
    expected_output = case["expected_output"]
    depths = expected_output.get("horizon_depths", [1200.0, 1500.0])
    horizons = [_horizon(depth) for depth in depths]

    return merge_quality_results(
        validate_esdac_source_profile(
            context,
            esdb=case["esdb"],
            stu=case["stu"],
        ),
        validate_horizon_profile(context, horizons),
        validate_ksat_profile(context, case["hydrogrids"]),
    )


def test_phase3_contract_classifies_all_captured_cases() -> None:
    for case in _load_fixture()["cases"]:
        result = _fixture_result(case)

        assert result.outcome == case["expected_quality"], case["case_id"]
        assert result.context.longitude == case["provenance"]["lng"]
        assert result.context.latitude == case["provenance"]["lat"]
        if result.outcome == "rejected":
            assert result.diagnostics, case["case_id"]


def test_individual_zero_texture_component_and_zero_gravel_are_valid() -> None:
    case = _load_fixture()["cases"][0]
    stu = dict(case["stu"])
    stu.update(
        {
            "STU_EU_T_CLAY": 0.0,
            "STU_EU_T_SAND": 60.0,
            "STU_EU_T_SILT": 40.0,
            "STU_EU_T_GRAVEL": 0.0,
        }
    )

    result = validate_esdac_source_profile(
        _context(case),
        esdb=case["esdb"],
        stu=stu,
    )

    assert result.outcome == "valid"
    assert result.reason_codes == ()


def test_horizon_contract_rejects_order_and_water_content_violations() -> None:
    context = SoilQualityContext(23.5, 69.9, "topaz-1")
    result = validate_horizon_profile(
        context,
        [
            _horizon(1200.0),
            {
                **_horizon(600.0),
                "field_cap": 0.2,
                "wilt_pt": 0.3,
            },
        ],
    )

    assert result.outcome == "rejected"
    assert {
        "horizon.depth_order",
        "output.water_content_order",
    } <= set(result.reason_codes)


def test_source_contract_rejects_nonfinite_and_unbalanced_texture() -> None:
    case = _load_fixture()["cases"][0]

    nonfinite_stu = dict(case["stu"])
    nonfinite_stu["STU_EU_T_CLAY"] = float("nan")
    nonfinite = validate_esdac_source_profile(
        _context(case),
        esdb=case["esdb"],
        stu=nonfinite_stu,
    )

    unbalanced_stu = dict(case["stu"])
    unbalanced_stu.update(
        {
            "STU_EU_T_CLAY": 20.0,
            "STU_EU_T_SAND": 20.0,
            "STU_EU_T_SILT": 20.0,
        }
    )
    unbalanced = validate_esdac_source_profile(
        _context(case),
        esdb=case["esdb"],
        stu=unbalanced_stu,
    )

    assert "source.stu.nonfinite_value" in nonfinite.reason_codes
    assert "source.stu.texture_balance" in unbalanced.reason_codes


def test_horizon_contract_rejects_nonfinite_output() -> None:
    context = SoilQualityContext(23.5, 69.9, "topaz-1")
    result = validate_horizon_profile(
        context,
        [{**_horizon(1200.0), "ks": float("nan")}],
    )

    assert result.outcome == "rejected"
    assert result.reason_codes == ("output.nonfinite_value",)


def test_ksat_contract_distinguishes_partial_and_all_missing_profiles() -> None:
    context = SoilQualityContext(13.1, 68.0)

    partial = validate_ksat_profile(context, {"sl1": 10.0, "sl2": None})
    missing = validate_ksat_profile(context, {"sl1": None, "sl2": None})

    assert partial.outcome == "degraded"
    assert partial.reason_codes == ("source.hydrogrids.partial_missing",)
    assert missing.outcome == "rejected"
    assert missing.reason_codes == ("source.hydrogrids.all_missing",)


def test_rejected_provider_result_preserves_exception_context() -> None:
    context = SoilQualityContext(71.3, 58.8, "topaz-50")
    result = rejected_quality_result(
        context,
        code="source.hydrogrids.provider_unavailable",
        field="hydrogrids",
        exception=KeyError("KS"),
    )

    assert result.outcome == "rejected"
    assert result.diagnostics[0].exception_type == "KeyError"
    assert result.context.topaz_id == "topaz-50"


def test_missing_depth_source_is_rejected_without_a_fallback() -> None:
    result = validate_horizon_depths(
        SoilQualityContext(13.1, 68.0),
        None,
    )

    assert result.outcome == "rejected"
    assert result.reason_codes == ("horizon.depth_missing",)
