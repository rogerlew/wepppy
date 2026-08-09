"""Frozen-selection preflight, bounded execution, and census aggregation."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import fcntl
import hashlib
import math
import subprocess
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .common import atomic_write_json, content_hash, resolve_within, sha256_file, tree_hash
from .execution import ExecutionContext, execute_trial
from .observer import parse_trace
from .pairing import pair_events
from .planning import PlannedTrial, TrialPlan
from .validation import validate_plan

SELECTION_SCHEMA_VERSION = "1.0.0"
PREFLIGHT_SCHEMA_VERSION = "1.0.0"
PROGRESS_SCHEMA_VERSION = "1.0.0"
SUMMARY_SCHEMA_VERSION = "1.0.0"
TERMINAL_SCHEMA_HASH = content_hash({"terminal_schema_version": "1.1.0",
                                    "required_binding": "input_snapshot_id"})
MAX_WORKERS = 32


@contextmanager
def _selection_execution_lock(plan: TrialPlan):
    evidence_root = Path(plan.evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(evidence_root)
    plan_root = evidence_root / plan.plan_id
    _reject_symlink_components(plan_root, stop=evidence_root)
    plan_root.mkdir(parents=True, exist_ok=True)
    plan_root = resolve_within(evidence_root, plan_root)
    lock_path = plan_root / ".selection-execution.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("selection is already executing in another process") from error
        yield
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class ExecutionSelection:
    schema_version: str
    selection_id: str
    plan_id: str
    plan_file_sha256: str
    trial_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "trial_ids": list(self.trial_ids)}


@dataclass(frozen=True)
class PreflightReport:
    valid: bool
    checks: dict[str, Any]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = {"schema_version": PREFLIGHT_SCHEMA_VERSION, "valid": self.valid,
                 "checks": self.checks, "errors": list(self.errors)}
        return {**value, "report_id": content_hash(value)}


@dataclass(frozen=True)
class ProgressSnapshot:
    plan_id: str
    plan_file_sha256: str
    selection_id: str
    terminal_schema_hash: str
    executable_sha256: str
    input_snapshot_id: str | None
    selected: int
    complete: int
    failed: int
    stopped: int
    pending: int
    active: int

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": PROGRESS_SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ExecutionSummary:
    plan_id: str
    selection_id: str
    terminal_trials: int
    event_pairs: int
    candidate_events: int
    candidate_trials: int
    artifacts: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        value = {"schema_version": SUMMARY_SCHEMA_VERSION, **asdict(self)}
        return {**value, "summary_id": content_hash(value)}


def stage_input_snapshot(plan: TrialPlan, selection: ExecutionSelection,
                         plan_file_sha256: str, output: Path) -> dict[str, Any]:
    """Copy and freeze every selected trial input plus shared WEPP inputs."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite frozen input snapshot manifest: {output}")
    source_by_scenario = {item["scenario"]: Path(item["authority"]) / "runs"
                          for item in plan.input_authorities}
    evidence_root = Path(plan.evidence_root)
    _reject_symlink_components(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(evidence_root)
    plan_root = evidence_root / plan.plan_id
    _reject_symlink_components(plan_root, stop=evidence_root)
    plan_root.mkdir(parents=True, exist_ok=True)
    plan_root = resolve_within(evidence_root, plan_root)
    stage_root = plan_root / "input-snapshot"
    if stage_root.exists():
        raise FileExistsError(f"refusing to overwrite input snapshot: {stage_root}")
    selected = {trial.trial_id: trial for trial in plan.trials
                if trial.trial_id in set(selection.trial_ids)}
    scenario_hillslopes: dict[str, set[int]] = {}
    for trial in selected.values():
        scenario_hillslopes.setdefault(trial.scenario, set()).add(trial.hillslope_id)
    scenario_records: dict[str, Any] = {}
    try:
        for scenario, hillslopes in sorted(scenario_hillslopes.items()):
            source_root = source_by_scenario[scenario]
            destination = stage_root / scenario / "runs"
            destination.mkdir(parents=True)
            names = [f"p{hillslope}.{suffix}" for hillslope in sorted(hillslopes)
                     for suffix in ("cli", "man", "slp", "sol", "run")]
            names.extend(name for name in ("gwcoeff.txt", "pmetpara.txt", "snow.txt", "wepp_ui.txt")
                         if (source_root / name).exists())
            hashes: dict[str, str] = {}
            for name in names:
                source = resolve_within(source_root, source_root / name)
                before = sha256_file(source)
                shutil.copy2(source, destination / name)
                after = sha256_file(destination / name)
                if before != after:
                    raise ValueError(f"input changed while staging {scenario}/{name}")
                hashes[name] = after
                (destination / name).chmod(0o444)
            destination.chmod(0o555)
            scenario_records[scenario] = {"run_root": str(destination), "files": hashes,
                                           "bundle_id": content_hash(hashes)}
        identity = {"schema_version": "1.0.0", "plan_id": plan.plan_id,
                    "plan_file_sha256": plan_file_sha256,
                    "selection_id": selection.selection_id, "scenarios": scenario_records}
        manifest = {**identity, "input_snapshot_id": content_hash(identity)}
        atomic_write_json(output, manifest, overwrite=False)
        return manifest
    except (OSError, ValueError):
        # Deliberate staging boundary: leave partial files for diagnosis and refuse reuse.
        raise


def load_input_snapshot(path: Path, plan: TrialPlan,
                        selection: ExecutionSelection) -> dict[str, Any]:
    _reject_symlink_components(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    identity = {key: raw[key] for key in ("schema_version", "plan_id", "plan_file_sha256",
                                          "selection_id", "scenarios")}
    if raw.get("schema_version") != "1.0.0" or raw.get("input_snapshot_id") != content_hash(identity):
        raise ValueError("input snapshot identity mismatch")
    if raw.get("plan_id") != plan.plan_id or raw.get("selection_id") != selection.selection_id:
        raise ValueError("input snapshot plan or selection binding mismatch")
    if raw.get("plan_file_sha256") != selection.plan_file_sha256:
        raise ValueError("input snapshot plan-file hash mismatch")
    for scenario, record in raw["scenarios"].items():
        run_root = Path(record["run_root"])
        _reject_symlink_components(run_root)
        for name, expected in record["files"].items():
            candidate = resolve_within(run_root, run_root / name)
            if sha256_file(candidate) != expected:
                raise ValueError(f"staged input hash mismatch for {scenario}/{name}")
        if record.get("bundle_id") != content_hash(record["files"]):
            raise ValueError(f"staged input bundle ID mismatch for {scenario}")
    return raw


def build_execution_selection(plan: TrialPlan, plan_file_sha256: str) -> ExecutionSelection:
    trial_ids = tuple(trial.trial_id for trial in plan.trials if trial.eligibility == "eligible")
    identity = {"schema_version": SELECTION_SCHEMA_VERSION, "plan_id": plan.plan_id,
                "plan_file_sha256": plan_file_sha256, "trial_ids": list(trial_ids)}
    return ExecutionSelection(selection_id=content_hash(identity), trial_ids=trial_ids,
                              **{key: identity[key] for key in identity if key != "trial_ids"})


def load_execution_selection(path: Path, plan: TrialPlan) -> ExecutionSelection:
    _reject_symlink_components(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SELECTION_SCHEMA_VERSION:
        raise ValueError(f"unsupported execution selection schema: {raw.get('schema_version')}")
    trial_ids = raw.get("trial_ids")
    if not isinstance(trial_ids, list) or not trial_ids or not all(isinstance(item, str) for item in trial_ids):
        raise ValueError("execution selection trial_ids must be a nonempty string list")
    selection = ExecutionSelection(raw["schema_version"], raw.get("selection_id", ""),
                                   raw.get("plan_id", ""), raw.get("plan_file_sha256", ""),
                                   tuple(trial_ids))
    expected = build_execution_selection(plan, selection.plan_file_sha256)
    if selection.plan_id != plan.plan_id:
        raise ValueError("execution selection plan ID mismatch")
    if selection.selection_id != expected.selection_id:
        raise ValueError("execution selection ID or ordered eligible trials mismatch")
    if selection.trial_ids != expected.trial_ids:
        raise ValueError("execution selection must contain every eligible trial in plan order")
    return selection


def _reject_symlink_components(path: Path, *, stop: Path | None = None) -> None:
    current = path.absolute()
    boundary = stop.absolute() if stop else Path(current.anchor)
    if stop is not None:
        try:
            current.relative_to(boundary)
        except ValueError as error:
            raise ValueError(f"path escapes declared root {boundary}: {path}") from error
    while current != boundary:
        if current.exists() and current.is_symlink():
            raise ValueError(f"symlink path component is prohibited: {current}")
        current = current.parent
    if boundary.exists() and boundary.is_symlink():
        raise ValueError(f"symlink path component is prohibited: {boundary}")


def _terminal_path(plan: TrialPlan, trial: PlannedTrial) -> Path:
    return Path(plan.evidence_root) / trial.evidence_locator / "terminal.json"


def _load_terminal(plan: TrialPlan, trial: PlannedTrial) -> dict[str, Any] | None:
    path = _terminal_path(plan, trial)
    if not path.exists():
        return None
    _reject_symlink_components(path, stop=Path(plan.evidence_root))
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_complete_terminal(plan: TrialPlan, trial: PlannedTrial, terminal: dict[str, Any],
                                *, input_snapshot_id: str) -> None:
    expected = {"schema_hash": TERMINAL_SCHEMA_HASH, "plan_id": plan.plan_id,
                "trial_id": trial.trial_id, "input_sha256": trial.input_sha256,
                "executable_sha256": plan.executable["sha256"], "status": "complete",
                "input_snapshot_id": input_snapshot_id}
    mismatches = [key for key, value in expected.items() if terminal.get(key) != value]
    if mismatches:
        raise ValueError(f"terminal binding mismatch for {trial.trial_id}: {', '.join(mismatches)}")
    if terminal.get("changed_inputs") != [trial.relative_input]:
        raise ValueError(f"terminal changed-input mismatch for {trial.trial_id}")
    if terminal.get("schema_version") != "1.1.0" or terminal.get("returncode") != 0:
        raise ValueError(f"terminal schema or return code mismatch for {trial.trial_id}")
    mutation = terminal.get("mutation")
    if not isinstance(mutation, dict):
        raise ValueError(f"terminal mutation record missing for {trial.trial_id}")
    exact_fields = {"file": trial.relative_input, "parameter": trial.parameter,
                    "requested_change": trial.requested_change, "source_value": trial.source_value,
                    "expected_value": trial.expected_value, "lines": list(trial.lines),
                    "tokens": list(trial.tokens), "before_sha256": trial.input_sha256}
    for key, expected_value in exact_fields.items():
        actual_value = mutation.get(key)
        if isinstance(expected_value, float):
            if not isinstance(actual_value, (int, float)) or not math.isclose(
                float(actual_value), expected_value, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError(f"terminal mutation {key} mismatch for {trial.trial_id}")
        elif actual_value != expected_value:
            raise ValueError(f"terminal mutation {key} mismatch for {trial.trial_id}")
    realized = mutation.get("realized_value")
    expected = trial.expected_value
    if isinstance(expected, dict):
        if set(realized or {}) != set(expected) or any(
            not math.isclose(float(realized[key]), float(value), rel_tol=1e-12, abs_tol=1e-12)
            for key, value in expected.items()
        ):
            raise ValueError(f"terminal realized mutation mismatch for {trial.trial_id}")
    elif not isinstance(realized, (int, float)) or not math.isclose(
        float(realized), float(expected), rel_tol=1e-12, abs_tol=1e-12
    ):
        raise ValueError(f"terminal realized mutation mismatch for {trial.trial_id}")
    before = terminal.get("input_hashes_before")
    after = terminal.get("input_hashes_after")
    if not isinstance(before, dict) or not isinstance(after, dict) or set(before) != set(after):
        raise ValueError(f"terminal input hash inventory mismatch for {trial.trial_id}")
    if before.get(trial.relative_input) != trial.input_sha256 or after.get(trial.relative_input) != mutation.get("after_sha256"):
        raise ValueError(f"terminal mutated input hash mismatch for {trial.trial_id}")
    if any(before[name] != after[name] for name in before if name != trial.relative_input):
        raise ValueError(f"terminal non-target input drift for {trial.trial_id}")
    expected_terminal_id = content_hash({key: terminal[key] for key in (
        "schema_hash", "plan_id", "trial_id", "input_sha256", "executable_sha256",
        "input_snapshot_id", "attempt_id") } | {"status": "complete"})
    if terminal.get("terminal_id") != expected_terminal_id:
        raise ValueError(f"terminal identity mismatch for {trial.trial_id}")
    trial_root = Path(plan.evidence_root) / trial.evidence_locator
    for path_key, hash_key in (("trace", "trace_sha256"), ("hbp", "hbp_sha256")):
        declared = Path(terminal[path_key])
        _reject_symlink_components(declared, stop=trial_root)
        artifact = resolve_within(trial_root, declared)
        if sha256_file(artifact) != terminal.get(hash_key):
            raise ValueError(f"terminal {path_key} hash mismatch for {trial.trial_id}")


def preflight_execution(plan_path: Path, selection: ExecutionSelection, *, require_empty: bool = False) -> PreflightReport:
    errors = list(validate_plan(plan := _load_plan_path(plan_path)).errors)
    checks: dict[str, Any] = {"plan_id": plan.plan_id, "plan_file_sha256": sha256_file(plan_path),
                              "selection_id": selection.selection_id,
                              "requested": len(plan.trials),
                              "eligible": sum(t.eligibility == "eligible" for t in plan.trials),
                              "excluded": sum(t.eligibility == "excluded" for t in plan.trials),
                              "selected": len(selection.trial_ids)}
    if selection.plan_id != plan.plan_id or selection.plan_file_sha256 != checks["plan_file_sha256"]:
        errors.append("selection does not bind the supplied plan bytes")
    try:
        expected = build_execution_selection(plan, checks["plan_file_sha256"])
        if selection != expected:
            errors.append("selection differs from the ordered eligible plan records")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))
    authorities: dict[str, str] = {}
    for item in plan.input_authorities:
        try:
            authority = Path(item["authority"])
            _reject_symlink_components(authority)
            run_root = resolve_within(authority, authority / "runs")
            inputs = [candidate for candidate in run_root.iterdir()
                      if candidate.is_file() and candidate.name.startswith("p")]
            actual = tree_hash(inputs, run_root)
            authorities[item["scenario"]] = actual
            if actual != item["input_tree_sha256"]:
                errors.append(f"input tree SHA-256 mismatch for {item['scenario']}")
        except (OSError, KeyError, ValueError) as error:
            errors.append(f"authority {item.get('scenario', '<unknown>')}: {error}")
    checks["input_tree_sha256"] = authorities
    authority_by_scenario = {item["scenario"]: Path(item["authority"]) / "runs"
                             for item in plan.input_authorities}
    for trial in plan.trials:
        if trial.eligibility != "eligible":
            continue
        try:
            source = resolve_within(authority_by_scenario[trial.scenario],
                                    authority_by_scenario[trial.scenario] / trial.relative_input)
            if source.is_symlink() or sha256_file(source) != trial.input_sha256:
                errors.append(f"planned input SHA-256 mismatch for {trial.trial_id}")
        except (OSError, KeyError, ValueError) as error:
            errors.append(f"planned input {trial.trial_id}: {error}")
    try:
        executable = Path(plan.executable["path"])
        _reject_symlink_components(executable)
        if not executable.is_file() or sha256_file(executable) != plan.executable["sha256"]:
            errors.append("executable SHA-256 mismatch")
    except (OSError, KeyError, ValueError) as error:
        errors.append(f"executable: {error}")
    evidence_root = Path(plan.evidence_root)
    try:
        _reject_symlink_components(evidence_root)
        storage_probe = evidence_root
        while not storage_probe.exists():
            storage_probe = storage_probe.parent
        resolved_evidence_root = evidence_root.resolve(strict=False)
        plan_root = (evidence_root / plan.plan_id).resolve(strict=False)
        if not plan_root.is_relative_to(resolved_evidence_root):
            raise ValueError("plan evidence root escapes declared evidence root")
        if plan_root.exists():
            symlinks = [path for path in plan_root.rglob("*") if path.is_symlink()]
            if symlinks:
                errors.append(f"evidence tree contains prohibited symlink: {symlinks[0]}")
        terminals = list(plan_root.rglob("terminal.json")) if plan_root.exists() else []
        if require_empty and terminals:
            errors.append(f"first-authorization preflight found {len(terminals)} terminals")
        usage = shutil.disk_usage(storage_probe)
        projected = int(plan.totals.get("projections", {}).get("expected_retained_bytes", 0))
        checks.update({"evidence_root": str(evidence_root.resolve()), "existing_terminals": len(terminals),
                       "available_bytes": usage.free, "projected_retained_bytes": projected})
        if usage.free < projected:
            errors.append("insufficient available storage for projected retained evidence")
    except (OSError, ValueError) as error:
        errors.append(f"evidence root: {error}")
    checks["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    return PreflightReport(not errors, checks, tuple(errors))


def _load_plan_path(path: Path) -> TrialPlan:
    from .planning import trial_plan_from_dict
    if path.is_symlink():
        raise ValueError("trial plan must not be a symlink")
    return trial_plan_from_dict(json.loads(path.read_text(encoding="utf-8")))


def progress_snapshot(plan: TrialPlan, selection: ExecutionSelection,
                      *, active_trial_ids: set[str] | None = None,
                      input_snapshot_id: str | None = None,
                      active: int = 0) -> ProgressSnapshot:
    counts = {"complete": 0, "failed": 0, "stopped": 0}
    ignored = active_trial_ids or set()
    trials = {trial.trial_id: trial for trial in plan.trials}
    for trial_id in selection.trial_ids:
        if trial_id in ignored:
            continue
        terminal = _load_terminal(plan, trials[trial_id])
        if terminal is not None:
            status = terminal.get("status")
            if status not in counts:
                raise ValueError(f"invalid terminal status for {trial_id}: {status}")
            trial = trials[trial_id]
            expected_bindings = {"plan_id": plan.plan_id, "trial_id": trial_id,
                                 "input_sha256": trial.input_sha256,
                                 "executable_sha256": plan.executable["sha256"]}
            if input_snapshot_id is not None:
                expected_bindings.update({"schema_hash": TERMINAL_SCHEMA_HASH,
                                          "input_snapshot_id": input_snapshot_id})
            mismatches = [key for key, value in expected_bindings.items()
                          if terminal.get(key) != value]
            if mismatches:
                raise ValueError(f"terminal binding mismatch in progress for {trial_id}: "
                                 f"{', '.join(mismatches)}")
            counts[status] += 1
    pending = len(selection.trial_ids) - sum(counts.values()) - active
    if pending < 0:
        raise ValueError("progress counts do not reconcile")
    return ProgressSnapshot(plan.plan_id, selection.plan_file_sha256, selection.selection_id,
                            TERMINAL_SCHEMA_HASH, plan.executable["sha256"], input_snapshot_id,
                            len(selection.trial_ids),
                            counts["complete"], counts["failed"], counts["stopped"], pending, active)


def execute_selection(plan: TrialPlan, selection: ExecutionSelection, workers: int,
                      dry_run: bool, *, input_snapshot: dict[str, Any] | None = None,
                      progress_path: Path | None = None) -> ProgressSnapshot:
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
    trials_by_id = {trial.trial_id: trial for trial in plan.trials}
    trials = [trials_by_id[trial_id] for trial_id in selection.trial_ids]
    if dry_run:
        for trial in trials:
            source_root = next(Path(item["authority"]) / "runs" for item in plan.input_authorities
                               if item["scenario"] == trial.scenario)
            source = resolve_within(source_root, source_root / trial.relative_input)
            if source.is_symlink() or sha256_file(source) != trial.input_sha256:
                raise ValueError(f"planned input mismatch for {trial.trial_id}")
        return progress_snapshot(plan, selection,
                                 input_snapshot_id=(input_snapshot or {}).get("input_snapshot_id"))

    if input_snapshot is None:
        raise ValueError("full execution requires a validated input snapshot")

    authorities = {scenario: Path(record["run_root"])
                   for scenario, record in input_snapshot["scenarios"].items()}
    def context_for(trial: PlannedTrial) -> ExecutionContext:
        all_hashes = input_snapshot["scenarios"][trial.scenario]["files"]
        names = {f"p{trial.hillslope_id}.{suffix}" for suffix in ("cli", "man", "slp", "sol", "run")}
        names.update({"gwcoeff.txt", "pmetpara.txt", "snow.txt", "wepp_ui.txt"} & set(all_hashes))
        expected_hashes = {name: all_hashes[name] for name in names}
        run_name = f"p{trial.hillslope_id}.run"
        run_text = (authorities[trial.scenario] / run_name).read_text()
        if run_text.count(".pass.dat") != 1:
            raise ValueError(f"staged run deck must contain one legacy pass suffix: {run_name}")
        expected_hashes[run_name] = hashlib.sha256(
            run_text.replace(".pass.dat", ".hbp").encode()
        ).hexdigest()
        return ExecutionContext(plan.plan_id, TERMINAL_SCHEMA_HASH, authorities[trial.scenario],
                                Path(plan.evidence_root), Path(plan.executable["path"]),
                                plan.executable["sha256"],
                                input_snapshot_id=input_snapshot["input_snapshot_id"],
                                source_hashes=expected_hashes)
    with _selection_execution_lock(plan):
        runnable: list[PlannedTrial] = []
        for trial in trials:
            terminal = _load_terminal(plan, trial)
            if terminal is not None and terminal.get("status") == "complete":
                _validate_complete_terminal(plan, trial, terminal,
                                            input_snapshot_id=input_snapshot["input_snapshot_id"])
            else:
                runnable.append(trial)
        if progress_path:
            active = min(workers, len(runnable))
            atomic_write_json(progress_path, progress_snapshot(
            plan, selection, active_trial_ids={trial.trial_id for trial in runnable},
            input_snapshot_id=input_snapshot["input_snapshot_id"], active=active,
            ).as_dict())
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="peakflow-census") as executor:
            futures = {executor.submit(execute_trial, trial, context_for(trial)): trial
                       for trial in runnable}
            remaining = {trial.trial_id for trial in runnable}
            for future in as_completed(futures):
                try:
                    future.result()
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    errors.append(f"{futures[future].trial_id}: {error}")
                remaining.remove(futures[future].trial_id)
                if progress_path:
                    atomic_write_json(progress_path, progress_snapshot(
                        plan, selection, active_trial_ids=remaining,
                        input_snapshot_id=input_snapshot["input_snapshot_id"],
                        active=min(workers, len(remaining)),
                    ).as_dict())
    snapshot = progress_snapshot(plan, selection,
                                 input_snapshot_id=input_snapshot["input_snapshot_id"])
    if errors:
        raise RuntimeError(f"{len(errors)} trials stopped; first error: {errors[0]}")
    return snapshot


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        frame.to_parquet(temporary_path, index=False, compression="zstd")
        if path.exists():
            if sha256_file(temporary_path) != sha256_file(path):
                raise FileExistsError(f"refusing to replace immutable ledger: {path}")
            return
        try:
            os.link(temporary_path, path)
        except FileExistsError as error:
            if sha256_file(temporary_path) != sha256_file(path):
                raise FileExistsError(f"refusing to replace immutable ledger: {path}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_frozen_json(path: Path, value: Any) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise FileExistsError(f"refusing to replace immutable summary: {path}")
        return
    atomic_write_json(path, value, overwrite=False)


def _ledger_root(plan: TrialPlan) -> Path:
    evidence_root = Path(plan.evidence_root)
    _reject_symlink_components(evidence_root)
    plan_root = resolve_within(evidence_root, evidence_root / plan.plan_id)
    root = plan_root / "ledgers"
    _reject_symlink_components(root, stop=plan_root)
    root.mkdir(parents=False, exist_ok=True)
    return resolve_within(plan_root, root)


def _denominator_grains(plan: TrialPlan, selection: ExecutionSelection,
                        pairs: pd.DataFrame, candidates: pd.DataFrame) -> list[dict[str, Any]]:
    selected_set = set(selection.trial_ids)
    trial_frame = pd.DataFrame([{"trial_id": trial.trial_id, "scenario": trial.scenario,
                                "family": trial.family, "direction": trial.direction}
                               for trial in plan.trials if trial.trial_id in selected_set])
    candidate_trial_ids = set(candidates.trial_id.unique())
    grains: list[dict[str, Any]] = []
    for grain, columns in (("overall", []), ("scenario", ["scenario"]),
                           ("family", ["family"]), ("direction", ["direction"])):
        groups = [((), trial_frame)] if not columns else trial_frame.groupby(columns, sort=True)
        for key, group in groups:
            keys = key if isinstance(key, tuple) else (key,)
            labels = dict(zip(columns, keys, strict=True))
            selected_ids = set(group.trial_id)
            requested_group = [trial for trial in plan.trials
                               if all(getattr(trial, column) == value
                                      for column, value in labels.items())]
            paired_group = pairs[pairs.trial_id.isin(selected_ids)]
            candidate_group = candidates[candidates.trial_id.isin(selected_ids)]
            record = {"grain": grain, **labels,
                      "requested_trials": len(requested_group),
                      "excluded_trials": sum(trial.eligibility == "excluded" for trial in requested_group),
                      "selected_trials": len(selected_ids), "terminal_trials": len(selected_ids),
                      "complete_trials": len(selected_ids), "failed_trials": 0, "stopped_trials": 0,
                      "paired_events": len(paired_group), "candidate_events": len(candidate_group),
                      "candidate_trials": len(selected_ids & candidate_trial_ids)}
            record["candidate_trial_prevalence"] = record["candidate_trials"] / record["complete_trials"]
            record["candidate_event_prevalence"] = (record["candidate_events"] / record["paired_events"]
                                                       if record["paired_events"] else None)
            grains.append(record)
    return grains


def aggregate_execution(plan: TrialPlan, selection: ExecutionSelection,
                        baseline_events: Path, baseline_events_sha256: str,
                        input_snapshot_id: str) -> ExecutionSummary:
    with _selection_execution_lock(plan):
        return _aggregate_execution_locked(plan, selection, baseline_events,
                                           baseline_events_sha256, input_snapshot_id)


def _aggregate_execution_locked(plan: TrialPlan, selection: ExecutionSelection,
                                baseline_events: Path, baseline_events_sha256: str,
                                input_snapshot_id: str) -> ExecutionSummary:
    trials = {trial.trial_id: trial for trial in plan.trials}
    terminals: list[dict[str, Any]] = []
    paired_frames: list[pd.DataFrame] = []
    _reject_symlink_components(baseline_events)
    if sha256_file(baseline_events) != baseline_events_sha256:
        raise ValueError("baseline events SHA-256 mismatch")
    baseline = pd.read_parquet(baseline_events)
    for trial_id in selection.trial_ids:
        trial = trials[trial_id]
        terminal = _load_terminal(plan, trial)
        if terminal is None:
            raise ValueError(f"missing terminal for {trial_id}")
        _validate_complete_terminal(plan, trial, terminal, input_snapshot_id=input_snapshot_id)
        terminals.append(terminal)
        scenario_baseline = baseline[(baseline.scenario == trial.scenario) &
                                     (baseline.hillslope_id == trial.hillslope_id)]
        if scenario_baseline.empty:
            raise ValueError(f"missing baseline events for {trial_id}")
        mutant = parse_trace(Path(terminal["trace"]), trial.scenario, trial.hillslope_id)
        paired_frames.append(pair_events(scenario_baseline, mutant, trial))
    root = _ledger_root(plan)
    terminal_records = []
    for terminal in terminals:
        terminal_records.append({
            key: value for key, value in terminal.items()
            if key not in {"changed_inputs", "mutation", "input_hashes_before", "input_hashes_after"}
        } | {
            "changed_inputs_json": json.dumps(terminal["changed_inputs"], sort_keys=True),
            "mutation_json": json.dumps(terminal["mutation"], sort_keys=True),
            "input_hashes_before_json": json.dumps(terminal["input_hashes_before"], sort_keys=True),
            "input_hashes_after_json": json.dumps(terminal["input_hashes_after"], sort_keys=True),
        })
    terminal_frame = pd.DataFrame(terminal_records)
    pairs = pd.concat(paired_frames, ignore_index=True)
    candidates = pairs.loc[pairs.candidate].copy()
    terminal_path, pairs_path, candidate_path = (root / "terminal-ledger.parquet",
                                                  root / "event-pairs.parquet",
                                                  root / "candidate-events.parquet")
    _atomic_parquet(terminal_frame, terminal_path)
    _atomic_parquet(pairs, pairs_path)
    _atomic_parquet(candidates, candidate_path)
    artifacts = {path.name: {"path": str(path), "bytes": path.stat().st_size,
                             "sha256": sha256_file(path), "format": "parquet",
                             "retention": "immutable study evidence"}
                 for path in (terminal_path, pairs_path, candidate_path)}
    artifacts[baseline_events.name] = {"path": str(baseline_events.resolve()),
                                       "bytes": baseline_events.stat().st_size,
                                       "sha256": baseline_events_sha256,
                                       "format": "parquet", "retention": "read-only input authority"}
    grains = _denominator_grains(plan, selection, pairs, candidates)
    denominator_value = {"schema_version": SUMMARY_SCHEMA_VERSION, "plan_id": plan.plan_id,
                         "selection_id": selection.selection_id, "grains": grains}
    denominator_path = root / "denominator-ledger.json"
    _write_frozen_json(denominator_path, denominator_value)
    prevalence_path = root / "prevalence-summary-v2.json"
    _write_frozen_json(prevalence_path, denominator_value)
    for path in (denominator_path, prevalence_path):
        artifacts[path.name] = {"path": str(path), "bytes": path.stat().st_size,
                                "sha256": sha256_file(path), "format": "json",
                                "retention": "immutable study evidence"}
    summary = ExecutionSummary(plan.plan_id, selection.selection_id, len(terminals), len(pairs),
                               len(candidates), candidates.trial_id.nunique(), artifacts)
    _write_frozen_json(root / "execution-summary-v2.json", summary.as_dict())
    plan_root = root.parent
    inventory = []
    for path in sorted(plan_root.rglob("*")):
        if (not path.is_file() or path.name.startswith(".") or
                path.name in {"storage-manifest.json", "storage-manifest-v2.json"}):
            continue
        inventory.append({"locator": str(path), "relative_locator": path.relative_to(plan_root).as_posix(),
                          "bytes": path.stat().st_size, "sha256": sha256_file(path),
                          "format": path.suffix.lstrip(".") or "binary",
                          "retention": "immutable study evidence"})
    storage = {"schema_version": "2.0.0", "plan_id": plan.plan_id,
               "selection_id": selection.selection_id, "artifact_count": len(inventory),
               "artifacts": inventory}
    _write_frozen_json(root / "storage-manifest-v2.json", storage)
    return summary
