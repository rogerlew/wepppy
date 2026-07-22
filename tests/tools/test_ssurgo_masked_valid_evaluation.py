import json
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


def test_failure_aware_scoring_fixture_corpus_gates_evidence_by_failure_class() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    cases = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "ssurgo_masked_valid" / "scoring_cases.json")
        .read_text(encoding="utf-8")
    )

    for case in cases:
        geometry = [
            (int(candidate["mukey"]), candidate["support_pixels"], candidate["shared_edges"])
            for candidate in case["geometry_candidates"]
        ]
        result = module["score_failure_aware_candidates"](
            geometry,
            case["candidate_elevation_deltas"],
            failure_class=case["failure_class"],
            source_profile=case.get("source_profile"),
            candidate_profiles=case.get("candidate_profiles"),
        )

        assert result["selected_mukey"] == case["expected_mukey"], case["id"]
        assert result["profile_fields"] == case["expected_profile_fields"], case["id"]
        if "expected_reason" in case:
            assert result["reason"] == case["expected_reason"]


def test_evaluation_persists_failure_aware_component_evidence() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    result = module["evaluate_masked_case"](
        {
            "case_id": "partial-profile",
            "withheld_mukey": "10",
            "global_mukey": "20",
            "candidate_support": [[20, 8], [30, 2]],
            "soil_summaries": {
                "10": {"sand_pct": 50.0, "clay_pct": 20.0},
                "20": {"sand_pct": 80.0, "clay_pct": 5.0},
                "30": {"sand_pct": 51.0, "clay_pct": 20.0},
            },
            "failure_class": "partial_profile",
            "geometry_candidates": [
                {"mukey": "20", "support_pixels": 8, "shared_edges": 8},
                {"mukey": "30", "support_pixels": 2, "shared_edges": 2},
            ],
            "candidate_elevation_deltas": {"20": 5.0, "30": 5.0},
            "source_profile": {"sand_pct": 50.0, "clay_pct": 20.0},
            "candidate_profiles": {
                "20": {"sand_pct": 80.0, "clay_pct": 5.0},
                "30": {"sand_pct": 51.0, "clay_pct": 20.0},
            },
        }
    )

    assert result["failure_aware_score"]["selected_mukey"] == "30"
    assert result["failure_aware_score"]["profile_fields"] == ["clay_pct", "sand_pct"]
    assert result["failure_aware_score"]["selected_feature_distance"] < result["global_feature_distance"]
    assert result["geometry_candidates"][0]["shared_edges"] == 8


def test_candidate_study_separates_candidate_coverage_from_top_rank() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    result = module["evaluate_masked_case"](
        {
            "case_id": "rank-misses-local-oracle",
            "run_path": "heldout-run",
            "withheld_mukey": "10",
            "global_mukey": "99",
            "candidate_support": [[20, 8], [30, 2]],
            "soil_summaries": {
                "10": {"sand": 50.0},
                "20": {"sand": 80.0},
                "30": {"sand": 51.0},
                "99": {"sand": 60.0},
            },
            "geometry_candidates": [
                {"mukey": "20", "support_pixels": 8, "shared_edges": 8},
                {"mukey": "30", "support_pixels": 2, "shared_edges": 2},
            ],
            "score_variants": {
                "geometry": {
                    "selected_mukey": "20",
                    "candidates": [{"mukey": "20", "score": 0.8}, {"mukey": "30", "score": 0.2}],
                }
            },
        }
    )
    study = module["summarize_candidate_study"]([result])
    summary = study["all_runs"]["geometry"]

    assert result["candidate_feature_distances"] == {"20": 30.0, "30": 1.0}
    assert summary["top_1_global_better"] == 1
    assert summary["top_2_local_better"] == 1
    assert summary["top_3_local_better"] == 1
    assert summary["oracle_local_better"] == 1
    assert summary["global_in_local_candidate_set"] == 0
    assert study["by_candidate_count"]["2-3"]["geometry"]["comparable"] == 1


def test_case_id_restriction_keeps_only_requested_run_topaz_pairs() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/ssurgo_masked_valid_evaluation.py"))
    eligible = [("1", "10"), ("2", "20"), ("3", "30")]

    assert module["_restrict_eligible_case_ids"](eligible, "fixture-run", {"fixture-run:2"}) == [("2", "20")]
    assert module["_restrict_eligible_case_ids"](eligible, "fixture-run", None) == eligible
