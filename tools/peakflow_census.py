#!/usr/bin/env python3
"""Operator CLI for manifest-driven local WEPP peak-flow censuses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from wepppy.wepp.peakflow_census.common import atomic_write_json, content_hash
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
    if not args.trial_id:
        raise ValueError("execute requires at least one explicit --trial-id; implicit all is prohibited")
    plan = _load_plan(args.plan)
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
    execute.add_argument("--trial-id", action="append", required=True)
    execute.add_argument("--run-dir", default="runs")
    execute.add_argument("--file-prefix", default="p")
    execute.set_defaults(function=execute_command)
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
