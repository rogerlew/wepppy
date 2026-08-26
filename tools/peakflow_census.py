#!/usr/bin/env python3
"""Operator CLI for manifest-driven local WEPP peak-flow censuses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from wepppy.wepp.peakflow_census.common import atomic_write_json, content_hash, sha256_file
from wepppy.wepp.peakflow_census.census import (
    aggregate_execution,
    build_execution_selection,
    execute_selection,
    load_input_snapshot,
    load_execution_selection,
    preflight_execution,
    stage_input_snapshot,
)
from wepppy.wepp.peakflow_census.execution import ExecutionContext, execute_trial
from wepppy.wepp.peakflow_census.manifest import load_study_manifest
from wepppy.wepp.peakflow_census.observer import parse_trace
from wepppy.wepp.peakflow_census.pairing import pair_events
from wepppy.wepp.peakflow_census.planning import plan_trials, trial_plan_from_dict
from wepppy.wepp.peakflow_census.validation import validate_artifacts, validate_phase2a_evidence, validate_plan


def _load_plan(path: Path):
    return trial_plan_from_dict(json.loads(path.read_text()))


def plan_command(args: argparse.Namespace) -> None:
    plan = plan_trials(load_study_manifest(args.study_manifest))
    atomic_write_json(args.output, plan.as_dict(), overwrite=args.allow_overwrite)
    print(json.dumps({"plan_id": plan.plan_id, **plan.totals}, indent=2, sort_keys=True))


def validate_plan_command(args: argparse.Namespace) -> None:
    report = validate_plan(_load_plan(args.plan))
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if not report.valid:
        raise SystemExit(1)


def execute_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    if args.selection:
        if args.trial_id:
            raise ValueError("use either --selection or --trial-id, not both")
        selection = load_execution_selection(args.selection, plan)
        report = preflight_execution(args.plan, selection)
        if not report.valid:
            raise ValueError(f"execution preflight failed: {report.errors[0]}")
        input_snapshot = (load_input_snapshot(args.input_snapshot, plan, selection)
                          if args.input_snapshot else None)
        snapshot = execute_selection(plan, selection, args.workers, args.dry_run,
                                     input_snapshot=input_snapshot,
                                     progress_path=args.progress)
        print(json.dumps(snapshot.as_dict(), indent=2, sort_keys=True))
        return
    if not args.trial_id:
        raise ValueError("execute requires --selection or at least one explicit --trial-id")
    selected = set(args.trial_id)
    trials = [trial for trial in plan.trials if trial.trial_id in selected]
    if {trial.trial_id for trial in trials} != selected:
        raise ValueError("selection contains trial IDs absent from the explicit plan")
    authorities = {item["scenario"]: Path(item["authority"]) for item in plan.input_authorities}
    terminals = []
    for trial in trials:
        context = ExecutionContext(plan.plan_id, content_hash({"terminal_schema_version": "1.0.0"}),
                                   authorities[trial.scenario] / args.run_dir, Path(plan.evidence_root),
                                   Path(plan.executable["path"]), plan.executable["sha256"], args.file_prefix)
        terminals.append(execute_trial(trial, context))
    print(json.dumps({"selected": len(trials), "statuses": [item["status"] for item in terminals]}, indent=2))


def freeze_selection_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    selection = build_execution_selection(plan, sha256_file(args.plan))
    atomic_write_json(args.output, selection.as_dict(), overwrite=False)
    print(json.dumps({"selection_id": selection.selection_id,
                      "selected": len(selection.trial_ids)}, indent=2, sort_keys=True))


def preflight_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    selection = load_execution_selection(args.selection, plan)
    report = preflight_execution(args.plan, selection, require_empty=args.require_empty)
    if args.output:
        atomic_write_json(args.output, report.as_dict())
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if not report.valid:
        raise SystemExit(1)


def stage_inputs_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    selection = load_execution_selection(args.selection, plan)
    report = preflight_execution(args.plan, selection)
    if not report.valid:
        raise ValueError(f"input staging preflight failed: {report.errors[0]}")
    manifest = stage_input_snapshot(plan, selection, sha256_file(args.plan), args.output)
    print(json.dumps({"input_snapshot_id": manifest["input_snapshot_id"],
                      "scenarios": sorted(manifest["scenarios"])}, indent=2, sort_keys=True))


def aggregate_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    selection = load_execution_selection(args.selection, plan)
    snapshot = load_input_snapshot(args.input_snapshot, plan, selection)
    authority = json.loads(args.baseline_authority.read_text(encoding="utf-8"))
    identity = {key: authority[key] for key in ("schema_version", "plan_id", "selection_id",
                                                "path", "sha256")}
    if authority.get("authority_id") != content_hash(identity):
        raise ValueError("baseline authority identity mismatch")
    if authority["plan_id"] != plan.plan_id or authority["selection_id"] != selection.selection_id:
        raise ValueError("baseline authority plan or selection mismatch")
    summary = aggregate_execution(plan, selection, Path(authority["path"]), authority["sha256"],
                                  snapshot["input_snapshot_id"])
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))


def pair_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    trials = {trial.trial_id: trial for trial in plan.trials}
    trial = trials[args.trial_id]
    baseline = pd.read_parquet(args.baseline)
    mutant = parse_trace(args.mutant_trace, trial.scenario, trial.hillslope_id)
    pair_events(baseline, mutant, trial).to_parquet(args.output, index=False, compression="zstd")


def validate_artifacts_command(args: argparse.Namespace) -> None:
    plan = _load_plan(args.plan)
    terminals = [json.loads(path.read_text()) for path in args.terminal]
    report = validate_artifacts(plan, terminals)
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if not report.valid:
        raise SystemExit(1)


def validate_phase2a_command(args: argparse.Namespace) -> None:
    report = validate_phase2a_evidence(args.evidence_root)
    if args.output:
        atomic_write_json(args.output, report.as_dict())
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if not report.valid:
        raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--study-manifest", type=Path, required=True)
    plan_parser.add_argument("--output", type=Path, required=True)
    plan_parser.add_argument("--allow-overwrite", action="store_true")
    plan_parser.set_defaults(function=plan_command)
    validate = commands.add_parser("validate-plan")
    validate.add_argument("--plan", type=Path, required=True)
    validate.set_defaults(function=validate_plan_command)
    execute = commands.add_parser("execute")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--selection", type=Path)
    execute.add_argument("--input-snapshot", type=Path)
    execute.add_argument("--trial-id", action="append")
    execute.add_argument("--workers", type=int, default=1)
    execute.add_argument("--dry-run", action="store_true")
    execute.add_argument("--progress", type=Path)
    execute.add_argument("--run-dir", default="runs")
    execute.add_argument("--file-prefix", default="p")
    execute.set_defaults(function=execute_command)
    selection = commands.add_parser("freeze-selection")
    selection.add_argument("--plan", type=Path, required=True)
    selection.add_argument("--output", type=Path, required=True)
    selection.set_defaults(function=freeze_selection_command)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--plan", type=Path, required=True)
    preflight.add_argument("--selection", type=Path, required=True)
    preflight.add_argument("--output", type=Path)
    preflight.add_argument("--require-empty", action="store_true")
    preflight.set_defaults(function=preflight_command)
    stage = commands.add_parser("stage-inputs")
    stage.add_argument("--plan", type=Path, required=True)
    stage.add_argument("--selection", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    stage.set_defaults(function=stage_inputs_command)
    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--plan", type=Path, required=True)
    aggregate.add_argument("--selection", type=Path, required=True)
    aggregate.add_argument("--input-snapshot", type=Path, required=True)
    aggregate.add_argument("--baseline-authority", type=Path, required=True)
    aggregate.set_defaults(function=aggregate_command)
    pair = commands.add_parser("pair-events")
    pair.add_argument("--plan", type=Path, required=True)
    pair.add_argument("--trial-id", required=True)
    pair.add_argument("--baseline", type=Path, required=True)
    pair.add_argument("--mutant-trace", type=Path, required=True)
    pair.add_argument("--output", type=Path, required=True)
    pair.set_defaults(function=pair_command)
    artifacts = commands.add_parser("validate-artifacts")
    artifacts.add_argument("--plan", type=Path, required=True)
    artifacts.add_argument("--terminal", type=Path, action="append", default=[])
    artifacts.set_defaults(function=validate_artifacts_command)
    phase2a = commands.add_parser("validate-phase2a")
    phase2a.add_argument("--evidence-root", type=Path, required=True)
    phase2a.add_argument("--output", type=Path)
    phase2a.set_defaults(function=validate_phase2a_command)
    return result


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
