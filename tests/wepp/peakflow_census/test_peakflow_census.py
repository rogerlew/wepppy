from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from wepppy.wepp.peakflow_census.common import atomic_write_json, content_hash, sha256_file, tree_hash
from wepppy.wepp.peakflow_census.census import (
    TERMINAL_SCHEMA_HASH,
    _atomic_parquet,
    _denominator_grains,
    _ledger_root,
    _selection_execution_lock,
    _validate_complete_terminal,
    build_execution_selection,
    execute_selection,
    load_execution_selection,
    load_input_snapshot,
    preflight_execution,
    progress_snapshot,
    stage_input_snapshot,
)
from wepppy.wepp.peakflow_census.execution import ExecutionContext, execute_trial
from wepppy.wepp.peakflow_census.manifest import load_study_manifest
from wepppy.wepp.peakflow_census.mutations import apply_mutation
from wepppy.wepp.peakflow_census.pairing import pair_events
from wepppy.wepp.peakflow_census.planning import plan_trials, trial_plan_from_dict
from wepppy.wepp.peakflow_census.validation import validate_phase2a_evidence, validate_plan

def _manifest(tmp_path: Path, scenarios: list[Path], *, selected: list[int] | None = None) -> Path:
    evidence = tmp_path / "evidence"
    evidence.mkdir(exist_ok=True)
    binary = Path("/bin/true")
    scenario_records = []
    for index, path in enumerate(scenarios):
        run_root = path / "runs"
        inputs = [candidate for candidate in run_root.iterdir() if candidate.is_file() and candidate.name.startswith("p")]
        scenario_records.append({"name": f"stratum-{index}", "authority": str(path),
                                 "input_tree_sha256": tree_hash(inputs, run_root)})
    value = {
        "schema_version": "1.0.0", "site": "synthetic-ridge", "evidence_root": str(evidence),
        "executable": {"path": str(binary), "sha256": sha256_file(binary)},
        "hillslope_discovery": {"run_dir": "runs", "file_prefix": "p", "run_suffix": ".run"},
        "scenarios": scenario_records,
        "mutation_families": [
            {"name": "ksat", "directions": ["minus", "plus"], "minus": 0.99, "plus": 1.01},
            {"name": "cover", "directions": ["minus", "plus"], "minus": -0.01, "plus": 0.01},
        ],
        "screening": {"peak_floor_m_s": 1e-7, "runoff_floor_m": 1e-5, "surplus_rate_floor_m_s": 1e-8},
    }
    if selected is not None:
        value["selected_hillslopes"] = selected
    path = tmp_path / "manifest.json"
    atomic_write_json(path, value)
    return path


def _synthetic_authorities(tmp_path: Path) -> list[Path]:
    topanga = Path("/wc1/runs/ha/hand-to-mouth-drought/wepp/runs")
    if not topanga.exists():
        pytest.skip("Topanga authority is not mounted")
    results = []
    for scenario in ("alpha", "beta"):
        authority = tmp_path / scenario
        runs = authority / "runs"
        runs.mkdir(parents=True)
        for source_id, target_id in ((8, 7), (31, 42), (106, 905)):
            for suffix in ("run", "sol", "man", "cli", "slp"):
                shutil.copy2(topanga / f"p{source_id}.{suffix}", runs / f"p{target_id}.{suffix}")
        results.append(authority)
    return results


@pytest.mark.unit
def test_synthetic_noncontiguous_site_plans_deterministically(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path)))
    first = plan_trials(study)
    second = plan_trials(study)
    assert first.as_dict() == second.as_dict()
    assert first.totals == {"requested": 24, "eligible": 24, "excluded": 0,
                            "by_scenario": {"stratum-0": {"requested": 12, "eligible": 12, "excluded": 0},
                                            "stratum-1": {"requested": 12, "eligible": 12, "excluded": 0}},
                            "by_family": {"ksat": {"requested": 12, "eligible": 12, "excluded": 0},
                                          "cover": {"requested": 12, "eligible": 12, "excluded": 0}},
                            "exclusion_reasons": {}}
    assert {trial.hillslope_id for trial in first.trials} == {7, 42, 905}
    assert validate_plan(first).valid


@pytest.mark.unit
def test_population_mismatch_requires_explicit_exception(tmp_path: Path) -> None:
    authorities = _synthetic_authorities(tmp_path)
    (authorities[1] / "runs/p905.run").unlink()
    study = load_study_manifest(_manifest(tmp_path, authorities))
    with pytest.raises(ValueError, match="populations differ"):
        plan_trials(study)


@pytest.mark.unit
def test_mutation_realization_and_cover_boundary_exclusion(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[905]))
    plan = plan_trials(study)
    trial = next(item for item in plan.trials if item.scenario == "stratum-0" and item.family == "ksat" and item.direction == "plus")
    run_dir = tmp_path / "mutation"
    run_dir.mkdir()
    source = study.scenarios[0].authority / study.run_dir / trial.relative_input
    shutil.copy2(source, run_dir / trial.relative_input)
    realization = apply_mutation(trial, run_dir)
    assert realization.requested_change == 1.01
    assert realization.realized_value == pytest.approx(realization.source_value * 1.01)
    assert realization.before_sha256 != realization.after_sha256


@pytest.mark.unit
def test_cover_that_cannot_realize_both_directions_is_excluded(tmp_path: Path) -> None:
    authorities = _synthetic_authorities(tmp_path)
    for authority in authorities:
        path = authority / "runs/p905.man"
        lines = path.read_text().splitlines()
        marker = next(index for index, line in enumerate(lines) if "Initial Condition Section" in line)
        line_index = next(index for index in range(marker + 1, len(lines)) if len(lines[index].split()) == 6)
        tokens = lines[line_index].split()
        tokens[5] = "0"
        lines[line_index] = " ".join(tokens)
        path.write_text("\n".join(lines) + "\n")
    plan = plan_trials(load_study_manifest(_manifest(tmp_path, authorities, selected=[905])))
    cover = [trial for trial in plan.trials if trial.family == "cover"]
    assert len(cover) == 4
    assert all(trial.eligibility == "excluded" for trial in cover)
    assert {trial.exclusion_reason for trial in cover} == {"paired_cover_direction_would_clip"}


@pytest.mark.integration
def test_topanga_pilot_selection_plans_same_64_trials(tmp_path: Path) -> None:
    manifest_path = Path("docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-study-manifest.json")
    if not Path("/wc1/runs/ha/hand-to-mouth-drought/wepp/runs").exists():
        pytest.skip("Topanga authority is not mounted")
    raw = json.loads(manifest_path.read_text())
    raw["selected_hillslopes"] = [106, 84, 8, 35, 31, 91, 85, 62]
    path = tmp_path / "pilot-manifest.json"
    atomic_write_json(path, raw)
    plan = plan_trials(load_study_manifest(path))
    assert plan.totals["requested"] == 64
    assert plan.totals["eligible"] == 64
    assert {(trial.scenario, trial.hillslope_id, trial.family, trial.direction) for trial in plan.trials} == {
        (scenario, hillslope, family, direction)
        for scenario in ("burned", "undisturbed")
        for hillslope in (106, 84, 8, 35, 31, 91, 85, 62)
        for family in ("ksat", "cover") for direction in ("minus", "plus")
    }


@pytest.mark.unit
def test_manifest_rejects_symlinked_authority_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    authority = tmp_path / "authority"
    authority.mkdir()
    (authority / "runs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink path component|escapes declared root"):
        load_study_manifest(_manifest(tmp_path, [authority]))


@pytest.mark.unit
def test_terminal_retry_requires_matching_bindings_and_preserves_attempt(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    trial = next(item for item in plan.trials if item.scenario == "stratum-0" and item.family == "ksat")
    context = ExecutionContext(plan.plan_id, "schema-a", study.scenarios[0].authority / "runs",
                               study.evidence_root, Path("/bin/true"), sha256_file(Path("/bin/true")))
    first = execute_trial(trial, context)
    assert first["status"] == "failed"
    with pytest.raises(ValueError, match="binding mismatch"):
        execute_trial(trial, ExecutionContext(plan.plan_id, "schema-b", context.source_root,
                                              context.evidence_root, context.executable,
                                              context.executable_sha256))
    second = execute_trial(trial, context)
    assert second["status"] == "failed"
    trial_root = study.evidence_root / trial.evidence_locator
    assert list(trial_root.glob("terminal.attempt-*.json"))
    assert list(trial_root.glob("runs.attempt-*"))


@pytest.mark.unit
def test_outer_join_preserves_absence_and_zero() -> None:
    shared = {"ofe": 1, "ordinal": 1, "runoff_post_m": 0.0, "surdra_raw_m": 0.0,
              "surdra_realized_m": 0.0, "added_rate_m_s": 0.0, "forcing_mode": 0,
              "solver": "APPMTH", "peak_m_s": 0.0}
    baseline = pd.DataFrame([{**shared, "year": 1980, "day": 1}, {**shared, "year": 1980, "day": 2}])
    mutant = pd.DataFrame([{**shared, "year": 1980, "day": 2}, {**shared, "year": 1980, "day": 3}])
    trial = type("Trial", (), {"trial_id": "t", "scenario": "s", "hillslope_id": 7,
                                "family": "ksat", "direction": "plus"})()
    paired = pair_events(baseline, mutant, trial)
    assert pd.isna(paired.loc[paired.day == 1, "peak_m_s_mutant"].iloc[0])
    assert paired.loc[paired.day == 2, "peak_m_s_mutant"].iloc[0] == 0.0
    assert paired.loc[paired.day == 3, "mutant_event_present"].iloc[0]


@pytest.mark.integration
def test_phase2a_immutable_evidence_parity_and_precision() -> None:
    root = Path("/home/workdir/peakflow-phase2a-evidence/8162d509d69cb4da")
    if not root.exists():
        pytest.skip("Phase 2A evidence is unavailable")
    report = validate_phase2a_evidence(root)
    assert report.valid, report.errors
    pairs = pd.read_parquet(root / "event-pairs.parquet")
    row = pairs.iloc[0]
    assert row.trial_id == "burned-h106-ksat-minus"
    assert row.runoff_post_m_baseline == 0.030281635001301765
    assert row.runoff_post_m_mutant == 0.030291365459561348
    assert row.peak_m_s_baseline == 1.1847274663523422e-06
    assert row.peak_m_s_mutant == 1.1851082035718719e-06
    assert not bool(row.candidate)


@pytest.mark.unit
def test_execution_selection_is_exact_ordered_eligible_set(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    plan_path = tmp_path / "plan.json"
    atomic_write_json(plan_path, plan.as_dict())
    selection = build_execution_selection(plan, sha256_file(plan_path))
    selection_path = tmp_path / "selection.json"
    atomic_write_json(selection_path, selection.as_dict())
    assert load_execution_selection(selection_path, plan) == selection
    assert selection.trial_ids == tuple(
        trial.trial_id for trial in plan.trials if trial.eligibility == "eligible"
    )
    tampered = selection.as_dict()
    tampered["trial_ids"] = list(reversed(tampered["trial_ids"]))
    atomic_write_json(selection_path, tampered)
    with pytest.raises(ValueError, match="eligible trial"):
        load_execution_selection(selection_path, plan)


@pytest.mark.unit
def test_preflight_and_dry_run_create_no_trial_evidence(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    plan_path = tmp_path / "plan.json"
    atomic_write_json(plan_path, plan.as_dict())
    selection = build_execution_selection(plan, sha256_file(plan_path))
    report = preflight_execution(plan_path, selection, require_empty=True)
    assert report.valid, report.errors
    snapshot = execute_selection(plan, selection, workers=2, dry_run=True)
    assert snapshot.selected == len(selection.trial_ids)
    assert snapshot.pending == len(selection.trial_ids)
    assert snapshot.active == snapshot.complete == snapshot.failed == snapshot.stopped == 0
    assert not (study.evidence_root / plan.plan_id).exists()


@pytest.mark.unit
def test_execute_selection_rejects_unbounded_worker_count(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    plan_path = tmp_path / "plan.json"
    atomic_write_json(plan_path, plan.as_dict())
    selection = build_execution_selection(plan, sha256_file(plan_path))
    with pytest.raises(ValueError, match="workers must be between"):
        execute_selection(plan, selection, workers=0, dry_run=True)
    with pytest.raises(ValueError, match="workers must be between"):
        execute_selection(plan, selection, workers=33, dry_run=True)


@pytest.mark.unit
def test_execute_selection_rejects_concurrent_process_owner(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    plan_path = tmp_path / "plan.json"
    atomic_write_json(plan_path, plan.as_dict())
    selection = build_execution_selection(plan, sha256_file(plan_path))
    with _selection_execution_lock(plan):
        with pytest.raises(ValueError, match="already executing"):
            with _selection_execution_lock(plan):
                pass


@pytest.mark.unit
def test_resolve_within_rejects_in_root_symlink_redirect(tmp_path: Path) -> None:
    from wepppy.wepp.peakflow_census.common import resolve_within

    root = tmp_path / "root"
    target = root / "target"
    target.mkdir(parents=True)
    (root / "redirect").symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink path component"):
        resolve_within(root, root / "redirect" / "artifact", must_exist=False)


@pytest.mark.unit
def test_staged_bundle_is_hash_bound_and_required_for_execution(tmp_path: Path) -> None:
    study = load_study_manifest(_manifest(tmp_path, _synthetic_authorities(tmp_path), selected=[7]))
    plan = plan_trials(study)
    plan_path = tmp_path / "plan.json"
    atomic_write_json(plan_path, plan.as_dict())
    selection = build_execution_selection(plan, sha256_file(plan_path))
    snapshot_path = tmp_path / "input-snapshot.json"
    staged = stage_input_snapshot(plan, selection, sha256_file(plan_path), snapshot_path)
    loaded = load_input_snapshot(snapshot_path, plan, selection)
    assert loaded["input_snapshot_id"] == staged["input_snapshot_id"]
    with pytest.raises(ValueError, match="requires a validated input snapshot"):
        execute_selection(plan, selection, workers=1, dry_run=False)
    result = execute_selection(plan, selection, workers=2, dry_run=False,
                               input_snapshot=loaded)
    assert result.failed == len(selection.trial_ids)
    assert result.stopped == 0
    snapshot_file = Path(loaded["scenarios"]["stratum-0"]["run_root"]) / "p7.cli"
    snapshot_file.chmod(0o644)
    snapshot_file.write_text("drift")
    with pytest.raises(ValueError, match="staged input hash mismatch"):
        load_input_snapshot(snapshot_path, plan, selection)


@pytest.mark.unit
def test_complete_terminal_rejects_mutation_tampering(tmp_path: Path) -> None:
    frozen = trial_plan_from_dict(json.loads(Path(
        "docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json"
    ).read_text()))
    plan = replace(frozen, evidence_root=str(tmp_path / "evidence"))
    trial = next(item for item in plan.trials if item.eligibility == "eligible")
    trial_root = Path(plan.evidence_root) / trial.evidence_locator
    trace = trial_root / "runs/peak_diag.csv"
    hbp = trial_root / f"output/H{trial.hillslope_id}.hbp"
    trace.parent.mkdir(parents=True)
    hbp.parent.mkdir(parents=True)
    trace.write_text("trace")
    hbp.write_text("pass")
    after_hash = "a" * 64
    bindings = {"schema_hash": TERMINAL_SCHEMA_HASH, "plan_id": plan.plan_id,
                "trial_id": trial.trial_id, "input_sha256": trial.input_sha256,
                "executable_sha256": plan.executable["sha256"],
                "input_snapshot_id": "snapshot", "attempt_id": "attempt"}
    terminal = {"schema_version": "1.1.0", **bindings, "status": "complete",
                "terminal_id": content_hash({**bindings, "status": "complete"}),
                "returncode": 0, "changed_inputs": [trial.relative_input],
                "mutation": {"file": trial.relative_input, "parameter": trial.parameter,
                             "requested_change": trial.requested_change,
                             "source_value": trial.source_value,
                             "expected_value": trial.expected_value,
                             "realized_value": trial.expected_value,
                             "lines": list(trial.lines), "tokens": list(trial.tokens),
                             "before_sha256": trial.input_sha256, "after_sha256": after_hash},
                "input_hashes_before": {trial.relative_input: trial.input_sha256, "shared": "b" * 64},
                "input_hashes_after": {trial.relative_input: after_hash, "shared": "b" * 64},
                "trace": str(trace), "trace_sha256": sha256_file(trace),
                "hbp": str(hbp), "hbp_sha256": sha256_file(hbp)}
    _validate_complete_terminal(plan, trial, terminal, input_snapshot_id="snapshot")
    terminal["mutation"]["realized_value"] = -1
    with pytest.raises(ValueError, match="realized mutation mismatch"):
        _validate_complete_terminal(plan, trial, terminal, input_snapshot_id="snapshot")
    terminal["plan_id"] = "0" * 64
    atomic_write_json(trial_root / "terminal.json", terminal)
    selection = build_execution_selection(plan, "f" * 64)
    with pytest.raises(ValueError, match="binding mismatch in progress"):
        progress_snapshot(plan, selection, input_snapshot_id="snapshot")


@pytest.mark.unit
def test_denominator_grains_include_exclusions_and_immutable_parquet(tmp_path: Path) -> None:
    plan = trial_plan_from_dict(json.loads(Path(
        "docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json"
    ).read_text()))
    selection = build_execution_selection(plan, "f" * 64)
    pairs = pd.DataFrame([{"trial_id": selection.trial_ids[0], "candidate": True}])
    grains = _denominator_grains(plan, selection, pairs, pairs)
    overall = next(item for item in grains if item["grain"] == "overall")
    assert (overall["requested_trials"], overall["excluded_trials"],
            overall["selected_trials"]) == (1120, 32, 1088)
    path = tmp_path / "ledger.parquet"
    _atomic_parquet(pd.DataFrame({"value": [1]}), path)
    first_hash = sha256_file(path)
    _atomic_parquet(pd.DataFrame({"value": [1]}), path)
    assert sha256_file(path) == first_hash
    with pytest.raises(FileExistsError, match="immutable ledger"):
        _atomic_parquet(pd.DataFrame({"value": [2]}), path)


@pytest.mark.unit
def test_ledger_root_rejects_symlinked_parent(tmp_path: Path) -> None:
    frozen = trial_plan_from_dict(json.loads(Path(
        "docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json"
    ).read_text()))
    evidence = tmp_path / "evidence"
    plan = replace(frozen, evidence_root=str(evidence))
    plan_root = evidence / plan.plan_id
    outside = tmp_path / "outside"
    plan_root.mkdir(parents=True)
    outside.mkdir()
    (plan_root / "ledgers").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink path component"):
        _ledger_root(plan)
