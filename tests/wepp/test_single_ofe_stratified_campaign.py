from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

import pytest

from wepppy.wepp.fuzzing.single_ofe_stratified_campaign import (
    EligibleRecord,
    OversamplingWeights,
    POSITIVE_CONTROL_CASE_PREFIX,
    SeedSignal,
    _ensure_rosetta3_available,
    _evaluate_secondary_oracle,
    _load_positive_controls,
    _upper_bound,
    build_adaptive_selection_plan,
    build_targeted_slice_selection_plan,
    summarize_classifier_outputs,
    preflight_single_ofe_seeds,
    select_stratified_seeds,
    shard_selected_seeds,
    stratify_eligible_seeds,
)
from wepppy.wepp.fuzzing.seeded_soil_landuse_generators import SeedTuple

pytestmark = pytest.mark.integration

FIXTURE_RUNS_DIR = (
    Path(__file__).resolve().parents[1]
    / "wepp"
    / "interchange"
    / "fixtures"
    / "deductive-futurist"
    / "wepp"
    / "runs"
)


def _seed(stem: str, seed_id: str) -> SeedTuple:
    return SeedTuple(
        seed_id=seed_id,
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem=stem,
        sol_path=str(FIXTURE_RUNS_DIR / f"{stem}.sol"),
        man_path=str(FIXTURE_RUNS_DIR / f"{stem}.man"),
        slp_path=str(FIXTURE_RUNS_DIR / f"{stem}.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / f"{stem}.cli"),
        run_path=str(FIXTURE_RUNS_DIR / f"{stem}.run"),
    )


def test_preflight_quarantines_multi_ofe_and_keeps_single_ofe() -> None:
    single = _seed("p1", "seed-single")
    multi = _seed("pw0", "seed-multi")

    eligible, quarantined = preflight_single_ofe_seeds([single, multi])

    assert [row.seed.seed_id for row in eligible] == ["seed-single"]
    assert len(quarantined) == 1
    assert quarantined[0].seed_id == "seed-multi"
    assert "SOIL_MULTI_OFE" in quarantined[0].reason_codes
    assert quarantined[0].soil_ofe_count is not None
    assert quarantined[0].soil_ofe_count > 1


def test_stratify_assigns_expected_three_bins() -> None:
    records = [
        EligibleRecord(
            seed=_seed("p1", "seed-a"),
            soil_ofe_count=1,
            climate_annual_precip_mm=100.0,
            slope_scalar=0.01,
            climate_bin="",
            slope_bin="",
        ),
        EligibleRecord(
            seed=_seed("p2", "seed-b"),
            soil_ofe_count=1,
            climate_annual_precip_mm=200.0,
            slope_scalar=0.02,
            climate_bin="",
            slope_bin="",
        ),
        EligibleRecord(
            seed=_seed("p3", "seed-c"),
            soil_ofe_count=1,
            climate_annual_precip_mm=300.0,
            slope_scalar=0.03,
            climate_bin="",
            slope_bin="",
        ),
    ]

    stratified, thresholds = stratify_eligible_seeds(records)

    assert thresholds.climate_dry_upper < thresholds.climate_mesic_upper
    assert thresholds.slope_gradual_upper < thresholds.slope_moderate_upper
    assert {row.climate_bin for row in stratified} == {"dry", "mesic", "wet"}
    assert {row.slope_bin for row in stratified} == {"gradual", "moderate", "steep"}


def test_select_and_shard_cover_all_bins_deterministically() -> None:
    prepared: list[EligibleRecord] = []
    climate_bins = ("dry", "mesic", "wet")
    slope_bins = ("gradual", "moderate", "steep")
    idx = 0
    for climate_bin in climate_bins:
        for slope_bin in slope_bins:
            idx += 1
            prepared.append(
                EligibleRecord(
                    seed=_seed("p1", f"seed-{idx:02d}"),
                    soil_ofe_count=1,
                    climate_annual_precip_mm=100.0 + idx,
                    slope_scalar=0.01 + idx * 0.001,
                    climate_bin=climate_bin,
                    slope_bin=slope_bin,
                )
            )

    selected, availability = select_stratified_seeds(
        prepared, per_bin_quota=1, random_seed=20260422
    )
    assert len(selected) == 9
    assert all(value == 1 for value in availability.values())

    shard_a = shard_selected_seeds(selected, shard_count=3, random_seed=20260423)
    shard_b = shard_selected_seeds(selected, shard_count=3, random_seed=20260423)

    assert sum(len(part) for part in shard_a) == 9
    assert [len(part) for part in shard_a] == [3, 3, 3]
    assert [[row.seed.seed_id for row in part] for part in shard_a] == [
        [row.seed.seed_id for row in part] for part in shard_b
    ]


def test_adaptive_selection_retains_bins_and_assigns_profiles() -> None:
    prepared: list[EligibleRecord] = []
    climate_bins = ("dry", "mesic", "wet")
    slope_bins = ("gradual", "moderate", "steep")
    idx = 0
    for climate_bin in climate_bins:
        for slope_bin in slope_bins:
            for _ in range(3):
                idx += 1
                prepared.append(
                    EligibleRecord(
                        seed=_seed("p1", f"seed-{idx:03d}"),
                        soil_ofe_count=1,
                        climate_annual_precip_mm=100.0 + idx,
                        slope_scalar=0.01 + idx * 0.001,
                        climate_bin=climate_bin,
                        slope_bin=slope_bin,
                    )
                )

    prior_signals = {
        "seed-001": SeedSignal(soft_warning_density=5.0, non_pass_hits=1, novel_non_pass_hits=1),
        "seed-002": SeedSignal(soft_warning_density=4.0, non_pass_hits=0, novel_non_pass_hits=1),
    }
    selected, _, selection_meta = build_adaptive_selection_plan(
        prepared,
        per_bin_quota=1,
        target_case_count=18,
        base_seed=20260422,
        oversampling_weights=OversamplingWeights(
            warning_density=0.55,
            non_pass_signature=1.5,
            novel_signature=1.75,
            dry_wet_corner=0.6,
            gradual_steep_corner=0.6,
        ),
        prior_signals=prior_signals,
        profile_weights={
            "P1_DENOMINATOR_EDGE": 1.0,
            "P2_EVENT_EDGE": 1.0,
            "P3_CONDUCTIVITY_SATURATION_CONTRAST": 1.2,
            "P4_TEXTURE_DENSITY_DISCONTINUITY": 1.0,
            "P5_SLOPE_RESPONSE_AMPLIFICATION": 1.15,
        },
        profile_floor=1,
    )

    assert len(selected) == 18
    assert set(selection_meta[row.seed.seed_id]["mutation_profile_id"] for row in selected).issubset(
        {
            "P1_DENOMINATOR_EDGE",
            "P2_EVENT_EDGE",
            "P3_CONDUCTIVITY_SATURATION_CONTRAST",
            "P4_TEXTURE_DENSITY_DISCONTINUITY",
            "P5_SLOPE_RESPONSE_AMPLIFICATION",
        }
    )
    selected_bins = {(row.climate_bin, row.slope_bin) for row in selected}
    assert len(selected_bins) == 9


def test_targeted_slice_selection_is_deterministic_and_single_slice() -> None:
    prepared: list[EligibleRecord] = []
    climate_bins = ("dry", "mesic", "wet")
    slope_bins = ("gradual", "moderate", "steep")
    idx = 0
    for climate_bin in climate_bins:
        for slope_bin in slope_bins:
            repeat = 220 if (climate_bin, slope_bin) == ("wet", "moderate") else 3
            for _ in range(repeat):
                idx += 1
                prepared.append(
                    EligibleRecord(
                        seed=_seed("p1", f"seed-{idx:04d}"),
                        soil_ofe_count=1,
                        climate_annual_precip_mm=100.0 + idx,
                        slope_scalar=0.01 + idx * 0.001,
                        climate_bin=climate_bin,
                        slope_bin=slope_bin,
                    )
                )

    target = "wet:moderate:P5_SLOPE_RESPONSE_AMPLIFICATION"
    selected_a, availability_a, meta_a = build_targeted_slice_selection_plan(
        prepared,
        target_slice=target,
        target_case_count=200,
        random_seed=20260422,
    )
    selected_b, availability_b, meta_b = build_targeted_slice_selection_plan(
        prepared,
        target_slice=target,
        target_case_count=200,
        random_seed=20260422,
    )

    assert len(selected_a) == 200
    assert len(selected_b) == 200
    assert [row.seed.seed_id for row in selected_a] == [row.seed.seed_id for row in selected_b]
    assert availability_a == availability_b
    assert all(row.climate_bin == "wet" and row.slope_bin == "moderate" for row in selected_a)
    assert all(
        meta_a[row.seed.seed_id]["mutation_profile_id"] == "P5_SLOPE_RESPONSE_AMPLIFICATION"
        for row in selected_a
    )
    assert meta_a == meta_b


def test_targeted_slice_selection_rejects_baseline_profile() -> None:
    prepared = [
        EligibleRecord(
            seed=_seed("p1", "seed-a"),
            soil_ofe_count=1,
            climate_annual_precip_mm=100.0,
            slope_scalar=0.01,
            climate_bin="wet",
            slope_bin="moderate",
        )
    ]
    with pytest.raises(ValueError, match="non-baseline profile"):
        build_targeted_slice_selection_plan(
            prepared,
            target_slice="wet:moderate:P0_BASELINE",
            target_case_count=1,
            random_seed=20260422,
        )


def test_load_positive_controls_prefixes_case_id(tmp_path: Path) -> None:
    seed_dir = tmp_path / "generative-inputs-fuzzing" / "seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    manifest = seed_dir / "known.csv"
    stderr_path = tmp_path / "artifact.stderr.txt"
    stderr_path.write_text("Program received signal SIGFPE\n", encoding="utf-8")
    manifest.write_text(
        (
            "case_id,stderr_path,observe_path,expected_signal_class,expected_top_frame,"
            "expected_last_marker_tag,expected_classification,expected_routine_chain_hash,"
            "expected_signature_key,expected_last_simulation_year,notes\n"
            "control-a,artifact.stderr.txt,,SIGFPE,wshpas_,NONE,TRAP_SIGFPE,abc123,"
            "SIGFPE|wshpas_|abc123|NONE,1,test-control\n"
        ),
        encoding="utf-8",
    )

    controls = _load_positive_controls(str(manifest))
    assert len(controls) == 1
    assert controls[0].case_id == f"{POSITIVE_CONTROL_CASE_PREFIX}control-a"
    assert controls[0].expected_classification == "TRAP_SIGFPE"
    assert controls[0].expected_signature_key == "SIGFPE|wshpas_|abc123|NONE"


def test_secondary_oracle_flags_token_anomaly(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-a"
    output_dir = case_dir / "execution" / "workspace" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "execution" / "combined.log").write_text(
        "Fortran runtime output includes NaN token\n",
        encoding="utf-8",
    )
    (output_dir / "H1.loss.dat").write_text("soil loss summary 0.0\n", encoding="utf-8")
    (output_dir / "H1.wat.dat").write_text("runoff summary 0.0\n", encoding="utf-8")

    status, flags, _ = _evaluate_secondary_oracle(case_dir=case_dir, execution_status="executed")
    assert status == "flag"
    assert "ORACLE_TOKEN_ANOMALY" in flags


def test_upper_bound_matches_formula() -> None:
    bound = _upper_bound(0.05, 1000)
    assert bound is not None
    assert bound == pytest.approx(0.0029912495, rel=1e-6)


def test_rosetta3_preflight_guard_fails_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "rosetta", raising=False)
    rosetta_stub = types.ModuleType("rosetta")
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    with pytest.raises(RuntimeError, match="Rosetta3 dependency unavailable"):
        _ensure_rosetta3_available()


def test_rosetta3_preflight_guard_passes_when_available() -> None:
    _ensure_rosetta3_available()


def test_summarize_builds_sensitivity_and_confidence(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    campaign_root.mkdir(parents=True, exist_ok=True)

    execution_rows = [
        {
            "case_id": f"case-generated-{idx:02d}",
            "seed_id": f"seed-{idx:02d}",
            "run_id": "aa/bb",
            "stem": "p1",
            "shard_id": "shard-001",
            "climate_bin": climate_bin,
            "slope_bin": slope_bin,
            "generation_status": "ok",
            "mutation_seed": "1",
            "mutation_profile_id": "P1_DENOMINATOR_EDGE",
            "adaptive_score": "1.0",
            "case_dir": str(campaign_root / "case-generated-1"),
            "execution_status": "executed",
            "execution_exit_code": "0",
            "execution_duration_seconds": "0.1",
            "stderr_path": "shards/shard-001/generated/case-generated-1/execution/combined.log",
            "execution_error": "",
            "oracle_status": "pass",
            "oracle_flags": "",
            "oracle_evidence": "",
        }
        for idx, (climate_bin, slope_bin) in enumerate(
            (
                (climate_bin, slope_bin)
                for climate_bin in ("dry", "mesic", "wet")
                for slope_bin in ("gradual", "moderate", "steep")
            ),
            start=1,
        )
    ]
    with (campaign_root / "execution_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(execution_rows[0].keys()))
        writer.writeheader()
        writer.writerows(execution_rows)

    classifier_rows = [
        {
            "case_id": row["case_id"],
            "stderr_path": row["stderr_path"],
            "observe_path": "",
            "signal_class": "NONE",
            "top_frame": "UNKNOWN",
            "routine_chain": "",
            "routine_chain_hash": "none",
            "last_marker_tag": "NONE",
            "last_simulation_year": "1",
            "success_marker_present": "True",
            "classification": "PASS",
            "signature_key": "NONE|UNKNOWN|none|NONE",
        }
        for row in execution_rows
    ]
    classifier_rows.append(
        {
            "case_id": f"{POSITIVE_CONTROL_CASE_PREFIX}control-1",
            "stderr_path": "control.stderr",
            "observe_path": "",
            "signal_class": "SIGFPE",
            "top_frame": "wshpas_",
            "routine_chain": "wshpas_",
            "routine_chain_hash": "abc",
            "last_marker_tag": "NONE",
            "last_simulation_year": "",
            "success_marker_present": "False",
            "classification": "TRAP_SIGFPE",
            "signature_key": "SIGFPE|wshpas_|abc|NONE",
        }
    )
    classifier_csv = campaign_root / "classifier_results.csv"
    with classifier_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(classifier_rows[0].keys()))
        writer.writeheader()
        writer.writerows(classifier_rows)

    (campaign_root / "positive_control_manifest.json").write_text(
        json.dumps(
            {
                "controls": [
                    {
                        "case_id": f"{POSITIVE_CONTROL_CASE_PREFIX}control-1",
                        "expected_classification": "TRAP_SIGFPE",
                        "expected_signature_key": "SIGFPE|wshpas_|abc|NONE",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (campaign_root / "campaign_manifest.json").write_text(
        json.dumps(
            {
                "execution_manifest_csv": str(campaign_root / "execution_manifest.csv"),
                "wepp_binary": "/workdir/wepppy/wepp_runner/bin/latest",
                "per_bin_quota": 1,
                "stratification": {
                    "seed_count_by_bin": {
                        f"{climate}:{slope}": 1
                        for climate in ("dry", "mesic", "wet")
                        for slope in ("gradual", "moderate", "steep")
                    },
                    "selected_count_by_bin": {
                        f"{climate}:{slope}": 1
                        for climate in ("dry", "mesic", "wet")
                        for slope in ("gradual", "moderate", "steep")
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    args = type(
        "Args",
        (),
        {
            "campaign_root": str(campaign_root),
            "classifier_csv": str(classifier_csv),
            "known_failures_manifest": None,
            "minimum_case_count": 9,
            "oracle_indeterminate_rate_limit": 0.05,
        },
    )()
    summary = summarize_classifier_outputs(args)
    assert summary["sensitivity_gate_pass"] is True
    assert summary["composite_non_pass_count"] == 0
    confidence = json.loads((campaign_root / "confidence_summary.json").read_text(encoding="utf-8"))
    assert confidence["disposition"] == "Inconclusive"
