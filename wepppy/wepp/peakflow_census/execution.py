"""Bounded local hillslope trial execution and terminal persistence."""

from __future__ import annotations

import shutil
import subprocess
import time
import fcntl
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import atomic_write_json, content_hash, resolve_within, sha256_file
from .mutations import apply_mutation


@dataclass(frozen=True)
class ExecutionContext:
    plan_id: str
    schema_hash: str
    source_root: Path
    evidence_root: Path
    executable: Path
    executable_sha256: str
    file_prefix: str = "p"
    input_snapshot_id: str | None = None
    source_hashes: dict[str, str] | None = None
    timeout_s: float = 300.0


def _copy_inputs(source: Path, destination: Path, hillslope_id: int, prefix: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for suffix in ("cli", "man", "slp", "sol"):
        copied = destination / f"{prefix}{hillslope_id}.{suffix}"
        shutil.copy2(source / copied.name, copied)
        copied.chmod(0o644)
    run_source = source / f"{prefix}{hillslope_id}.run"
    run_text = run_source.read_text()
    if run_text.count(".pass.dat") != 1:
        raise ValueError("run deck must contain exactly one legacy pass suffix")
    (destination / run_source.name).write_text(run_text.replace(".pass.dat", ".hbp"))
    for name in ("gwcoeff.txt", "pmetpara.txt", "snow.txt", "wepp_ui.txt"):
        candidate = source / name
        if candidate.exists():
            shutil.copy2(candidate, destination / name)


@contextmanager
def _trial_lock(run_parent: Path):
    run_parent.mkdir(parents=True, exist_ok=True)
    lock_path = run_parent / ".trial.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"trial is already owned by another process: {run_parent}") from error
        yield
    finally:
        os.close(descriptor)


def execute_trial(trial: Any, context: ExecutionContext) -> dict[str, Any]:
    if trial.eligibility != "eligible":
        raise ValueError(f"cannot execute excluded trial {trial.trial_id}")
    source = resolve_within(context.source_root, context.source_root)
    executable = context.executable.resolve(strict=True)
    if sha256_file(executable) != context.executable_sha256:
        raise ValueError("executable SHA-256 mismatch")
    run_parent = resolve_within(context.evidence_root, context.evidence_root / trial.evidence_locator,
                                must_exist=False)
    with _trial_lock(run_parent):
        return _execute_trial_locked(trial, context, source, executable, run_parent)


def _execute_trial_locked(trial: Any, context: ExecutionContext, source: Path,
                          executable: Path, run_parent: Path) -> dict[str, Any]:
    run_dir = run_parent / "runs"
    output_dir = run_parent / "output"
    terminal_path = run_parent / "terminal.json"
    bindings = {"schema_hash": context.schema_hash, "plan_id": context.plan_id,
                "trial_id": trial.trial_id, "input_sha256": trial.input_sha256,
                "executable_sha256": context.executable_sha256}
    if context.input_snapshot_id is not None:
        bindings["input_snapshot_id"] = context.input_snapshot_id
    if terminal_path.exists():
        import json
        prior = json.loads(terminal_path.read_text())
        if not all(prior.get(key) == value for key, value in bindings.items()):
            raise ValueError(f"terminal binding mismatch for {trial.trial_id}")
        if prior.get("status") == "complete":
            if prior.get("changed_inputs") != [trial.relative_input]:
                raise ValueError(f"complete terminal changed-input mismatch for {trial.trial_id}")
            for path_key, hash_key in (("trace", "trace_sha256"), ("hbp", "hbp_sha256")):
                artifact = resolve_within(run_parent, Path(prior[path_key]))
                if sha256_file(artifact) != prior.get(hash_key):
                    raise ValueError(f"complete terminal {path_key} mismatch for {trial.trial_id}")
            return prior
        if prior.get("status") not in {"failed", "stopped"}:
            raise ValueError(f"terminal has unsupported retry status for {trial.trial_id}")
        archive = terminal_path.with_name(f"terminal.attempt-{prior['terminal_id'][:12]}.json")
        if not archive.exists():
            shutil.copy2(terminal_path, archive)
        for partial in (run_dir, output_dir):
            if partial.exists():
                partial_archive = partial.with_name(f"{partial.name}.attempt-{prior['terminal_id'][:12]}")
                if partial_archive.exists():
                    raise ValueError(f"retry archive already exists: {partial_archive}")
                partial.rename(partial_archive)
    started = time.perf_counter()
    attempt_id = content_hash({**bindings, "started_ns": time.time_ns()})
    try:
        if run_dir.exists() or output_dir.exists():
            raise ValueError(f"unbound partial trial directory exists for {trial.trial_id}")
        _copy_inputs(source, run_dir, trial.hillslope_id, context.file_prefix)
        output_dir.mkdir(parents=True, exist_ok=True)
        before = {path.name: sha256_file(path) for path in run_dir.iterdir() if path.is_file()}
        if context.source_hashes is not None:
            mismatched = sorted(name for name, digest in before.items()
                                if context.source_hashes.get(name) != digest)
            unexpected = sorted(set(context.source_hashes) - set(before))
            if mismatched or unexpected:
                raise ValueError(f"staged input bundle mismatch for {trial.trial_id}: "
                                 f"mismatched={mismatched}, missing={unexpected}")
        if before.get(trial.relative_input) != trial.input_sha256:
            raise ValueError(f"planned input hash mismatch for {trial.trial_id}")
        realization = apply_mutation(trial, run_dir)
        after = {path.name: sha256_file(path) for path in run_dir.iterdir() if path.is_file()}
        changed = sorted(name for name in before if before[name] != after[name])
        if changed != [trial.relative_input]:
            raise ValueError(f"mutation isolation failure for {trial.trial_id}: {changed}")
        (run_dir / "peak_diag.on").touch()
        with (run_dir / f"{context.file_prefix}{trial.hillslope_id}.run").open("rb") as stdin:
            completed = subprocess.run([str(executable)], cwd=run_dir, stdin=stdin,
                                       capture_output=True, check=False, shell=False,
                                       timeout=context.timeout_s)
        (run_dir / "stdout.log").write_bytes(completed.stdout)
        (run_dir / "stderr.log").write_bytes(completed.stderr)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        stopped = {"schema_version": "1.1.0" if context.input_snapshot_id else "1.0.0",
                   **bindings, "attempt_id": attempt_id,
                   "terminal_id": content_hash({**bindings, "attempt_id": attempt_id,
                                                "status": "stopped", "error": str(error)}),
                   "status": "stopped", "runtime_s": time.perf_counter() - started,
                   "error_type": type(error).__name__, "error": str(error)}
        atomic_write_json(terminal_path, stopped, overwrite=terminal_path.exists())
        raise
    runtime = time.perf_counter() - started
    trace = run_dir / "peak_diag.csv"
    hbp = output_dir / f"H{trial.hillslope_id}.hbp"
    success = completed.returncode == 0 and b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" in completed.stdout and trace.exists() and hbp.exists()
    terminal = {"schema_version": "1.1.0" if context.input_snapshot_id else "1.0.0",
                **bindings, "attempt_id": attempt_id,
                "terminal_id": content_hash({**bindings, "attempt_id": attempt_id,
                                             "status": "complete" if success else "failed"}),
                "status": "complete" if success else "failed", "returncode": completed.returncode,
                "runtime_s": runtime, "changed_inputs": changed, "mutation": realization.as_dict(),
                "input_hashes_before": before, "input_hashes_after": after,
                "trace": str(trace), "trace_sha256": sha256_file(trace) if trace.exists() else None,
                "hbp": str(hbp), "hbp_sha256": sha256_file(hbp) if hbp.exists() else None}
    atomic_write_json(terminal_path, terminal, overwrite=terminal_path.exists())
    return terminal
