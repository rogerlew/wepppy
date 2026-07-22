from pathlib import Path
import runpy

import pytest


pytestmark = pytest.mark.unit


def test_masked_valid_evaluation_reports_both_recovery_and_distance() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    result = module["evaluate_masked_case"](
        {
            "case_id": "local-wins",
            "withheld_mukey": "10",
            "global_mukey": "30",
            "candidate_support": [[20, 8], [30, 3]],
            "soil_summaries": {
                "10": {"sand": 50, "clay": 20},
                "20": {"sand": 51, "clay": 20},
                "30": {"sand": 80, "clay": 5},
            },
        }
    )
    assert result["local_majority_mukey"] == "20"
    assert result["exact_local_recovery"] is False
    assert result["local_feature_distance"] < result["global_feature_distance"]
    assert result["distance_fields"] == ["clay", "sand"]
