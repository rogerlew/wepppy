from __future__ import annotations

from pathlib import Path
import runpy

import pytest


pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    return runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_padded_shadow_evaluator.py"))


def test_direct_shallow_profile_preserves_only_valid_nonorganic_source_values() -> None:
    result = _module()["direct_shallow_profile"]([
        {"chkey": 1, "om_r": 25.0, "dbthirdbar_r": 1.1},
        {
            "chkey": 2, "hzname": "A", "om_r": 2.0, "dbthirdbar_r": 1.3,
            "ksat_r": 9.0, "cec7_r": 18.0, "hzdepb_r": 20.0,
        },
    ])

    assert result["classification"] == "profile_bearing_residual"
    assert result["source_chkey"] == 2
    assert result["direct_values"] == {
        "dbthirdbar_r": 1.3, "ksat_r": 9.0, "cec7_r": 18.0, "hzdepb_r": 20.0,
    }


def test_shadow_disposition_prefers_profile_vector_then_spatial_support() -> None:
    disposition = _module()["shadow_disposition"](
        {"direct_values": {"dbthirdbar_r": 1.2, "ksat_r": 10.0, "cec7_r": 20.0}},
        [
            {"mukey": "20", "pixel_support": 10, "direct_values": {"dbthirdbar_r": 1.8, "ksat_r": 40.0, "cec7_r": 40.0}},
            {"mukey": "30", "pixel_support": 2, "direct_values": {"dbthirdbar_r": 1.21, "ksat_r": 10.5, "cec7_r": 21.0}},
        ],
        "99",
    )
    profile_free = _module()["shadow_disposition"](
        {"direct_values": {}},
        [
            {"mukey": "20", "pixel_support": 10, "direct_values": {}},
            {"mukey": "30", "pixel_support": 2, "direct_values": {}},
        ],
        "99",
    )

    assert disposition["proposed_mukey"] == "30"
    assert disposition["reason"] == "profile_vector_shadow"
    assert profile_free["proposed_mukey"] == "20"
    assert profile_free["reason"] == "spatial_support_shadow"


def test_current_invalid_and_masked_seeds_are_current_build_and_deterministic() -> None:
    module = _module()
    raw = {"1": "10", "2": "20", "3": "30"}

    assert module["current_invalid_mukeys"](raw, {"10", "30"}) == {"20"}
    assert module["masked_valid_seeds"](raw, {"10", "30"}, count=1, seed=7) == \
        module["masked_valid_seeds"](raw, {"10", "30"}, count=1, seed=7)
