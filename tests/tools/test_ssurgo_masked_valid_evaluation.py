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


def test_global_baseline_masks_withheld_mukey_before_selecting_mode() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    baseline = module["_global_baseline"](
        {"1": "10", "2": "10", "3": "20", "4": "30"},
        {"10", "20", "30"},
        ["10", "20", "30"],
        "10",
    )
    assert baseline == "20"


def test_cohort_summary_counts_paired_feature_and_elevation_outcomes() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    summary = module["summarize_evaluations"](
        [
            {"run_path": "run-a", "local_majority_mukey": "20", "global_mukey": "30", "local_feature_distance": 1.0, "global_feature_distance": 2.0, "local_elevation_delta_m": 2.0, "global_elevation_delta_m": 1.0},
            {"run_path": "run-a", "local_majority_mukey": "20", "global_mukey": "20", "local_feature_distance": 2.0, "global_feature_distance": 2.0, "local_elevation_delta_m": 1.0, "global_elevation_delta_m": 1.0},
        ]
    )
    assert summary["all_runs"]["feature_local_better"] == 1
    assert summary["all_runs"]["feature_tied"] == 1
    assert summary["all_runs"]["elevation_global_better"] == 1
    assert summary["by_run"]["run-a"]["proposal_disagreements"] == 1


def test_scoring_summary_compares_each_variant_with_global() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    summary = module["summarize_score_variants"](
        [
            {"global_feature_distance": 2.0, "score_variants": {"terrain_00pct": {"selected_feature_distance": 1.0}}},
            {"global_feature_distance": 1.0, "score_variants": {"terrain_00pct": {"selected_feature_distance": 3.0}}},
        ]
    )
    assert summary["terrain_00pct"] == {
        "comparable": 2,
        "local_better": 1,
        "global_better": 1,
        "tied": 0,
    }
