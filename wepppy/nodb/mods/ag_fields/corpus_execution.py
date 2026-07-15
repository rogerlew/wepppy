"""Materialize and execute an explicit Concept 1 or hybrid parent corpus.

This diagnostic command is independent of NoDb and RQ orchestration.  It joins
an accepted OFE plan to its parent summary, writes the complete WEPP input tuple
for every represented parent, and runs a caller-supplied hillslope binary.  The
result ledger is intended for capacity and numerical-compatibility evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from .concept1_inputs import synthesize_concept1_parent_inputs


SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_parent_corpus_execution_v1"
SUCCESS_MARKER = "WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY"
REQUIRED_CONTEXT_FILES = (
    "pmetpara.txt",
    "snow.txt",
    "gwcoeff.txt",
    "chan.inp",
    "chntyp.txt",
    "wepp_ui.txt",
)
_YEAR_RE = re.compile(r"SIMULATION YEAR\s*=\s*([0-9]+)")
_NUMERICAL_RE = re.compile(
    r"SIGFPE|Floating-point exception|erroneous arithmetic operation",
    re.IGNORECASE,
)
_INVALID_INPUT_RE = re.compile(
    r"Bad (?:integer|real) for item|Bad value during floating point read|"
    r"must be between|must be greater|\*\*\*ERROR\*\*\*",
    re.IGNORECASE,
)
_INVALID_PRODUCER_RE = re.compile(
    r"invalid producer|producer[^\n]*(?:nan|inf(?:inity)?)|"
    r"(?:nan|inf(?:inity)?)[^\n]*producer",
    re.IGNORECASE,
)
_NONFINITE_TOKEN_RE = re.compile(
    rb"(?<![A-Za-z0-9_])[+-]?(?:nan|inf(?:inity)?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

__all__ = [
    "ALGORITHM",
    "SCHEMA_VERSION",
    "ParentCorpusExecutionError",
    "render_minimal_hillslope_run",
    "run_parent_corpus",
]


class ParentCorpusExecutionError(RuntimeError):
    """Raised when explicit corpus resources cannot define an execution."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _result_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("algorithm", pa.string()),
            ("parent_wepp_id", pa.int64()),
            ("planned_ofe_count", pa.int64()),
            ("target_width_m", pa.float64()),
            ("materialization_status", pa.string()),
            ("materialization_error_type", pa.string()),
            ("materialization_error", pa.string()),
            ("materialization_elapsed_seconds", pa.float64()),
            ("ofe_count", pa.int64()),
            ("referenced_yearly_scenario_count", pa.int64()),
            ("breakpoints", pa.list_(pa.float64())),
            ("target_length_m", pa.float64()),
            ("target_area_m2", pa.float64()),
            ("execution_status", pa.string()),
            ("returncode", pa.int64()),
            ("timed_out", pa.bool_()),
            ("last_simulation_year", pa.int64()),
            ("success_marker_found", pa.bool_()),
            ("pass_size_bytes", pa.int64()),
            ("pass_sha256", pa.string()),
            ("stdout_sha256", pa.string()),
            ("stderr_sha256", pa.string()),
            ("stdout_relpath", pa.string()),
            ("stderr_relpath", pa.string()),
            ("execution_elapsed_seconds", pa.float64()),
        ],
        metadata={
            b"schema_version": SCHEMA_VERSION.encode("ascii"),
            b"algorithm": ALGORITHM.encode("ascii"),
        },
    )


def _atomic_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    metadata = {
        b"schema_version": SCHEMA_VERSION.encode("ascii"),
        b"algorithm": ALGORITHM.encode("ascii"),
    }
    table = pa.Table.from_pylist(list(rows), schema=_result_schema())
    table = table.replace_schema_metadata(metadata)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        pq.write_table(table, temporary, compression="snappy")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def render_minimal_hillslope_run(parent_wepp_id: int, sim_years: int) -> str:
    """Render a PASS-focused WEPP run control for one generated parent."""
    if parent_wepp_id <= 0:
        raise ValueError("parent_wepp_id must be positive.")
    if sim_years <= 0:
        raise ValueError("sim_years must be positive.")
    stem = f"p{parent_wepp_id}"
    lines = [
        "m",
        "Yes",
        "1",
        "1",
        "Yes",
        f"../output/H{parent_wepp_id}.pass.dat",
        "1",
        "No",
        f"../output/H{parent_wepp_id}.loss.dat",
        *("No" for _ in range(10)),
        f"{stem}.man",
        f"{stem}.slp",
        f"{stem}.cli",
        f"{stem}.sol",
        "0",
        str(sim_years),
        "0",
    ]
    return "\n".join(lines) + "\n"


def _read_rows(path: Path, required: set[str], label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ParentCorpusExecutionError(f"{label} does not exist: {path}")
    table = pq.read_table(path)
    missing = sorted(required - set(table.column_names))
    if missing:
        raise ParentCorpusExecutionError(f"{label} is missing columns: {missing}")
    rows = table.to_pylist()
    if not rows:
        raise ParentCorpusExecutionError(f"{label} contains no rows.")
    return rows


def _prepare_requests(
    plan_path: Path,
    parent_summary_path: Path,
    sim_years: int,
) -> list[dict[str, Any]]:
    plan_rows = _read_rows(
        plan_path,
        {
            "parent_wepp_id",
            "ofe_id",
            "normalized_start",
            "normalized_end",
            "source_kind",
            "sub_field_id",
        },
        "OFE plan",
    )
    summary_rows = _read_rows(
        parent_summary_path,
        {"parent_wepp_id", "residual_width_m", "fit_status"},
        "parent summary",
    )
    summaries: dict[int, Mapping[str, Any]] = {}
    for row in summary_rows:
        parent_wepp_id = int(row["parent_wepp_id"])
        if parent_wepp_id in summaries:
            raise ParentCorpusExecutionError(
                f"Parent summary repeats parent {parent_wepp_id}."
            )
        summaries[parent_wepp_id] = row

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        grouped[int(row["parent_wepp_id"])].append(row)

    requests: list[dict[str, Any]] = []
    for parent_wepp_id in sorted(grouped):
        summary = summaries.get(parent_wepp_id)
        if summary is None:
            raise ParentCorpusExecutionError(
                f"OFE plan parent {parent_wepp_id} is absent from parent summary."
            )
        target_width_m = float(summary["residual_width_m"])
        if target_width_m <= 0.0:
            raise ParentCorpusExecutionError(
                f"Parent {parent_wepp_id} has non-positive residual_width_m."
            )
        requests.append(
            {
                "parent_wepp_id": parent_wepp_id,
                "ofe_rows": sorted(
                    grouped[parent_wepp_id],
                    key=lambda item: int(item["ofe_id"]),
                ),
                "target_width_m": target_width_m,
                "sim_years": sim_years,
            }
        )
    return requests


def _materialize_parent(
    request: Mapping[str, Any],
    parent_runs_dir: Path,
    subfield_runs_dir: Path,
    target_runs_dir: Path,
) -> dict[str, Any]:
    parent_wepp_id = int(request["parent_wepp_id"])
    started = time.monotonic()
    try:
        result = synthesize_concept1_parent_inputs(
            parent_wepp_id=parent_wepp_id,
            ofe_rows=request["ofe_rows"],
            parent_runs_dir=parent_runs_dir,
            subfield_runs_dir=subfield_runs_dir,
            target_runs_dir=target_runs_dir,
            target_width_m=float(request["target_width_m"]),
        )
        run_path = target_runs_dir / f"p{parent_wepp_id}.run"
        run_path.write_text(
            render_minimal_hillslope_run(parent_wepp_id, int(request["sim_years"])),
            encoding="utf-8",
        )
    except (OSError, ValueError, AssertionError, IndexError, KeyError) as exc:
        return {
            "parent_wepp_id": parent_wepp_id,
            "materialization_status": "failed",
            "materialization_error_type": type(exc).__name__,
            "materialization_error": str(exc),
            "materialization_elapsed_seconds": time.monotonic() - started,
        }
    return {
        "parent_wepp_id": parent_wepp_id,
        "materialization_status": "passed",
        "materialization_error_type": "",
        "materialization_error": "",
        "materialization_elapsed_seconds": time.monotonic() - started,
        **result,
    }


def _materialize_worker(payload: tuple[dict[str, Any], str, str, str]) -> dict[str, Any]:
    request, parent_runs, subfield_runs, target_runs = payload
    return _materialize_parent(
        request,
        Path(parent_runs),
        Path(subfield_runs),
        Path(target_runs),
    )


def _classify_execution(
    *,
    returncode: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
    pass_path: Path,
) -> str:
    if timed_out:
        return "timeout"
    if _NUMERICAL_RE.search(stderr):
        return "numerical_fault"
    diagnostic_tail = stderr + "\n" + "\n".join(stdout.splitlines()[-120:])
    if _INVALID_PRODUCER_RE.search(diagnostic_tail):
        return "invalid_producer"
    if _INVALID_INPUT_RE.search(diagnostic_tail):
        return "invalid_input"
    if pass_path.is_file() and pass_path.stat().st_size > 0:
        with pass_path.open("rb") as stream:
            if any(_NONFINITE_TOKEN_RE.search(line) for line in stream):
                return "non_finite_pass"
    if (
        returncode == 0
        and SUCCESS_MARKER in stdout
        and pass_path.is_file()
        and pass_path.stat().st_size > 0
    ):
        return "passed"
    if returncode == 0 and SUCCESS_MARKER not in stdout:
        return "missing_success_marker"
    if returncode == 0:
        return "missing_pass_output"
    if returncode < 0 or returncode >= 128:
        return "process_signal"
    return "process_failure"


def _execute_parent(
    parent_wepp_id: int,
    binary: Path,
    runs_dir: Path,
    output_dir: Path,
    failure_logs_dir: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    run_path = runs_dir / f"p{parent_wepp_id}.run"
    pass_path = output_dir / f"H{parent_wepp_id}.pass.dat"
    loss_path = output_dir / f"H{parent_wepp_id}.loss.dat"
    pass_path.unlink(missing_ok=True)
    loss_path.unlink(missing_ok=True)
    timed_out = False
    stdout = ""
    stderr = ""
    returncode = 0
    with run_path.open("r", encoding="utf-8") as stdin_stream:
        try:
            completed = subprocess.run(
                [str(binary)],
                cwd=runs_dir,
                stdin=stdin_stream,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            returncode = int(completed.returncode)
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = (
                exc.stdout
                if isinstance(exc.stdout, str)
                else (exc.stdout or b"").decode(errors="replace")
            )
            stderr = (
                exc.stderr
                if isinstance(exc.stderr, str)
                else (exc.stderr or b"").decode(errors="replace")
            )

    classification = _classify_execution(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        pass_path=pass_path,
    )
    stdout_sha256 = hashlib.sha256(stdout.encode("utf-8")).hexdigest()
    stderr_sha256 = hashlib.sha256(stderr.encode("utf-8")).hexdigest()
    stdout_relpath = ""
    stderr_relpath = ""
    if classification != "passed":
        failure_logs_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = failure_logs_dir / f"p{parent_wepp_id}.stdout.log"
        stderr_path = failure_logs_dir / f"p{parent_wepp_id}.stderr.log"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        stdout_relpath = str(stdout_path.relative_to(failure_logs_dir.parent))
        stderr_relpath = str(stderr_path.relative_to(failure_logs_dir.parent))
    years = [int(match.group(1)) for match in _YEAR_RE.finditer(stdout)]
    return {
        "parent_wepp_id": parent_wepp_id,
        "execution_status": classification,
        "returncode": returncode,
        "timed_out": timed_out,
        "last_simulation_year": max(years, default=0),
        "success_marker_found": SUCCESS_MARKER in stdout,
        "pass_size_bytes": pass_path.stat().st_size if pass_path.is_file() else 0,
        "pass_sha256": (
            _sha256(pass_path)
            if pass_path.is_file() and pass_path.stat().st_size > 0
            else ""
        ),
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "stdout_relpath": stdout_relpath,
        "stderr_relpath": stderr_relpath,
        "execution_elapsed_seconds": time.monotonic() - started,
    }


def _execute_worker(payload: tuple[int, str, str, str, str, int]) -> dict[str, Any]:
    (
        parent_wepp_id,
        binary,
        runs_dir,
        output_dir,
        failure_logs_dir,
        timeout_seconds,
    ) = payload
    return _execute_parent(
        parent_wepp_id,
        Path(binary),
        Path(runs_dir),
        Path(output_dir),
        Path(failure_logs_dir),
        timeout_seconds,
    )


def _ordered_map(function: Any, payloads: Sequence[Any], workers: int) -> list[Any]:
    if workers == 1:
        return [function(payload) for payload in payloads]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(function, payloads))


def run_parent_corpus(
    *,
    ofe_plan: Path,
    parent_summary: Path,
    parent_runs: Path,
    subfield_runs: Path,
    output_dir: Path,
    wepp_bin: Path,
    sim_years: int,
    workers: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Materialize, execute, and inventory every parent represented in a plan."""
    if workers <= 0:
        raise ParentCorpusExecutionError("workers must be positive.")
    if timeout_seconds <= 0:
        raise ParentCorpusExecutionError("timeout_seconds must be positive.")
    if sim_years <= 0:
        raise ParentCorpusExecutionError("sim_years must be positive.")
    if not wepp_bin.is_file() or not os.access(wepp_bin, os.X_OK):
        raise ParentCorpusExecutionError(f"WEPP binary is not executable: {wepp_bin}")
    for label, directory in (
        ("parent runs", parent_runs),
        ("subfield runs", subfield_runs),
    ):
        if not directory.is_dir():
            raise ParentCorpusExecutionError(
                f"{label} directory does not exist: {directory}"
            )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ParentCorpusExecutionError(f"Output directory is not empty: {output_dir}")

    started = time.monotonic()
    requests = _prepare_requests(ofe_plan, parent_summary, sim_years)
    runs_dir = output_dir / "runs"
    model_output_dir = output_dir / "output"
    failure_logs_dir = output_dir / "failure_logs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    model_output_dir.mkdir(parents=True, exist_ok=True)
    context_hashes: dict[str, str] = {}
    for name in REQUIRED_CONTEXT_FILES:
        source = parent_runs / name
        if not source.is_file():
            raise ParentCorpusExecutionError(
                f"Required runtime context is missing: {source}"
            )
        destination = runs_dir / name
        shutil.copy2(source, destination)
        context_hashes[name] = _sha256(destination)

    materialization_payloads = [
        (request, str(parent_runs), str(subfield_runs), str(runs_dir))
        for request in requests
    ]
    materialized = _ordered_map(_materialize_worker, materialization_payloads, workers)
    materialized_by_parent = {int(row["parent_wepp_id"]): row for row in materialized}
    executable_ids = [
        int(row["parent_wepp_id"])
        for row in materialized
        if row["materialization_status"] == "passed"
    ]
    execution_payloads = [
        (
            parent_wepp_id,
            str(wepp_bin),
            str(runs_dir),
            str(model_output_dir),
            str(failure_logs_dir),
            timeout_seconds,
        )
        for parent_wepp_id in executable_ids
    ]
    executed = _ordered_map(_execute_worker, execution_payloads, workers)
    executed_by_parent = {int(row["parent_wepp_id"]): row for row in executed}

    result_rows: list[dict[str, Any]] = []
    for request in requests:
        parent_wepp_id = int(request["parent_wepp_id"])
        row = {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "parent_wepp_id": parent_wepp_id,
            "planned_ofe_count": len(request["ofe_rows"]),
            "target_width_m": float(request["target_width_m"]),
            **materialized_by_parent[parent_wepp_id],
        }
        execution = executed_by_parent.get(parent_wepp_id)
        if execution is None:
            row.update(
                {
                    "execution_status": "not_run_materialization_failed",
                    "returncode": 0,
                    "timed_out": False,
                    "last_simulation_year": 0,
                    "success_marker_found": False,
                    "pass_size_bytes": 0,
                    "pass_sha256": "",
                    "stdout_sha256": "",
                    "stderr_sha256": "",
                    "stdout_relpath": "",
                    "stderr_relpath": "",
                    "execution_elapsed_seconds": 0.0,
                }
            )
        else:
            row.update(execution)
        result_rows.append(row)

    _atomic_parquet(output_dir / "execution_results.parquet", result_rows)
    classifications = Counter(str(row["execution_status"]) for row in result_rows)
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "parent_count": len(result_rows),
        "materialized_count": len(executable_ids),
        "passed_count": classifications.get("passed", 0),
        "failure_count": len(result_rows) - classifications.get("passed", 0),
        "execution_status_counts": dict(sorted(classifications.items())),
        "workers": workers,
        "timeout_seconds": timeout_seconds,
        "sim_years": sim_years,
        "elapsed_seconds": time.monotonic() - started,
        "ofe_plan": str(ofe_plan),
        "ofe_plan_sha256": _sha256(ofe_plan),
        "parent_summary": str(parent_summary),
        "parent_summary_sha256": _sha256(parent_summary),
        "parent_runs": str(parent_runs),
        "subfield_runs": str(subfield_runs),
        "wepp_bin": str(wepp_bin),
        "wepp_bin_sha256": _sha256(wepp_bin),
        "runtime_context_sha256": context_hashes,
    }
    _atomic_json(output_dir / "execution_summary.json", summary)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ofe-plan", required=True, type=Path)
    parser.add_argument("--parent-summary", required=True, type=Path)
    parser.add_argument("--parent-runs", required=True, type=Path)
    parser.add_argument("--subfield-runs", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--wepp-bin", required=True, type=Path)
    parser.add_argument("--sim-years", required=True, type=int)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_parent_corpus(
        ofe_plan=args.ofe_plan,
        parent_summary=args.parent_summary,
        parent_runs=args.parent_runs,
        subfield_runs=args.subfield_runs,
        output_dir=args.output_dir,
        wepp_bin=args.wepp_bin,
        sim_years=args.sim_years,
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
