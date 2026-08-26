"""Plan, terminal, and immutable Phase 2A evidence validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .common import content_hash, sha256_file
from .planning import TrialPlan


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    checks: dict[str, Any]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0.0", "valid": self.valid,
                "checks": self.checks, "errors": list(self.errors)}


def validate_plan(plan: TrialPlan) -> ValidationReport:
    errors: list[str] = []
    eligible = sum(item.eligibility == "eligible" for item in plan.trials)
    excluded = sum(item.eligibility == "excluded" for item in plan.trials)
    if plan.totals.get("requested") != len(plan.trials) or plan.totals.get("eligible") != eligible or plan.totals.get("excluded") != excluded:
        errors.append("plan totals do not recompute from trial records")
    if len({trial.trial_id for trial in plan.trials}) != len(plan.trials):
        errors.append("trial IDs are not unique")
    identity_records = [{key: value for key, value in trial.as_dict().items()
                         if key not in {"trial_id", "evidence_locator"}} for trial in plan.trials]
    expected_plan_id = content_hash({"study_id": plan.study_id,
                                     "input_authorities": plan.input_authorities,
                                     "trials": identity_records})
    if plan.plan_id != expected_plan_id:
        errors.append("plan ID does not bind the ordered trial records and authorities")
    forbidden = ("route", "watershed", "channel", "chan.out", "closure")
    for trial in plan.trials:
        expected_trial_id = f"{trial.site}-{trial.scenario}-h{trial.hillslope_id}-{trial.family}-{trial.direction}-{plan.plan_id[:12]}"
        if trial.trial_id != expected_trial_id:
            errors.append(f"trial ID binding mismatch: {trial.trial_id}")
        expected_locator = f"{plan.plan_id}/{trial.scenario}/h{trial.hillslope_id}/{trial.family}-{trial.direction}"
        if trial.evidence_locator != expected_locator:
            errors.append(f"evidence locator binding mismatch: {trial.trial_id}")
        serialized = str(trial.as_dict()).lower()
        if any(word in serialized for word in forbidden):
            errors.append(f"routing concept found in {trial.trial_id}")
            break
        target = Path(plan.evidence_root) / trial.evidence_locator
        try:
            target.resolve().relative_to(Path(plan.evidence_root).resolve())
        except ValueError:
            errors.append(f"evidence locator escapes root: {trial.trial_id}")
    return ValidationReport(not errors, {"requested": len(plan.trials), "eligible": eligible,
                                         "excluded": excluded, "plan_id": plan.plan_id}, tuple(errors))


def validate_artifacts(plan: TrialPlan, terminals: Iterable[dict[str, Any]]) -> ValidationReport:
    errors = list(validate_plan(plan).errors)
    terminal_list = list(terminals)
    planned = {trial.trial_id: trial for trial in plan.trials if trial.eligibility == "eligible"}
    for terminal in terminal_list:
        trial = planned.get(terminal.get("trial_id"))
        if trial is None:
            errors.append(f"unknown or excluded terminal: {terminal.get('trial_id')}")
            continue
        for key, expected in (("plan_id", plan.plan_id), ("input_sha256", trial.input_sha256),
                              ("executable_sha256", plan.executable["sha256"])):
            if terminal.get(key) != expected:
                errors.append(f"terminal {trial.trial_id} has mismatched {key}")
        if terminal.get("status") not in {"complete", "failed", "stopped"}:
            errors.append(f"terminal {trial.trial_id} has invalid status")
    checks = {"planned_eligible": len(planned), "terminals": len(terminal_list),
              "complete": sum(item.get("status") == "complete" for item in terminal_list)}
    return ValidationReport(not errors, checks, tuple(errors))


def validate_phase2a_evidence(root: Path) -> ValidationReport:
    terminals = pd.read_parquet(root / "terminal-ledger.parquet")
    pairs = pd.read_parquet(root / "event-pairs.parquet")
    checks = {"terminal_trials": len(terminals),
              "complete_trials": int((terminals.status == "complete").sum()),
              "exact_one_input_diff_trials": int((terminals.changed_inputs.map(len) == 1).sum()),
              "outer_join_rows": len(pairs),
              "baseline_only_rows": int((pairs.baseline_event_present & ~pairs.mutant_event_present).sum()),
              "mutant_only_rows": int((~pairs.baseline_event_present & pairs.mutant_event_present).sum()),
              "candidate_rows": int(pairs.candidate.sum()),
              "candidate_trials": int(pairs.loc[pairs.candidate, "trial_id"].nunique()),
              "terminal_ledger_sha256": sha256_file(root / "terminal-ledger.parquet"),
              "event_pairs_sha256": sha256_file(root / "event-pairs.parquet")}
    expected = {"terminal_trials": 64, "complete_trials": 64, "exact_one_input_diff_trials": 64,
                "outer_join_rows": 14157, "baseline_only_rows": 30, "mutant_only_rows": 25,
                "candidate_rows": 697, "candidate_trials": 61}
    errors = tuple(f"{key}: expected {value}, found {checks[key]}" for key, value in expected.items() if checks[key] != value)
    checks["report_id"] = content_hash(checks)
    return ValidationReport(not errors, checks, errors)
