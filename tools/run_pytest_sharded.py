#!/usr/bin/env python3
"""Run pytest in module-level shards without xdist."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
TIMING_CACHE_FILE = REPO_ROOT / ".pytest_cache" / "wctl" / "run_pytest_sharded_module_timings.json"
TIMING_CACHE_VERSION = 1
TIMING_CACHE_ALPHA = 0.6
DEFAULT_TARGETS: tuple[str, ...] = ("tests",)
XDIST_OPTIONS = {
    "-n",
    "--numprocesses",
    "--dist",
    "--tx",
}
OPTIONS_REQUIRING_VALUE = {
    "-k",
    "-m",
    "-c",
    "-o",
    "-p",
    "-r",
    "--basetemp",
    "--capture",
    "--confcutdir",
    "--durations",
    "--durations-min",
    "--ignore",
    "--ignore-glob",
    "--deselect",
    "--import-mode",
    "--junitxml",
    "--log-cli-level",
    "--log-level",
    "--log-file",
    "--maxfail",
    "--override-ini",
    "--rootdir",
    "--tb",
}


@dataclass
class WorkerSummary:
    exit_code: int
    collected: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    warnings: int = 0
    module_durations: dict[str, float] = field(default_factory=dict)
    failed_nodeids: list[str] = field(default_factory=list)
    error_nodeids: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "exit_code": self.exit_code,
            "collected": self.collected,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "module_durations": dict(self.module_durations),
            "failed_nodeids": list(self.failed_nodeids),
            "error_nodeids": list(self.error_nodeids),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "WorkerSummary":
        raw_module_durations = payload.get("module_durations", {})
        if not isinstance(raw_module_durations, dict):
            raw_module_durations = {}
        return cls(
            exit_code=int(payload.get("exit_code", 2)),
            collected=int(payload.get("collected", 0)),
            passed=int(payload.get("passed", 0)),
            failed=int(payload.get("failed", 0)),
            errors=int(payload.get("errors", 0)),
            skipped=int(payload.get("skipped", 0)),
            warnings=int(payload.get("warnings", 0)),
            module_durations={
                _normalize_path(str(path)): float(duration)
                for path, duration in raw_module_durations.items()
                if float(duration) >= 0.0
            },
            failed_nodeids=[str(item) for item in payload.get("failed_nodeids", [])],  # type: ignore[arg-type]
            error_nodeids=[str(item) for item in payload.get("error_nodeids", [])],  # type: ignore[arg-type]
        )


@dataclass
class AggregateSummary:
    shards: int
    total_tests: int
    passed: int
    skipped: int
    warnings: int
    failures: int
    failed_nodeids: list[str]


@dataclass
class WorkerProcess:
    shard_index: int
    shard_total: int
    shard_files: list[str]
    process: subprocess.Popen[str]
    result_json: str
    basetemp_dir: str
    stdout_thread: threading.Thread
    stderr_thread: threading.Thread


def _strip_remainder_separator(args: Sequence[str]) -> list[str]:
    values = list(args)
    if values and values[0] == "--":
        return values[1:]
    return values


def _normalize_path(path: str | Path) -> str:
    raw = Path(path)
    if raw.is_absolute():
        return str(raw.resolve())
    return str((Path.cwd() / raw).resolve())


def _relative_display(path: str) -> str:
    resolved = Path(path)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _item_path(item: object) -> str:
    path = getattr(item, "path", None)
    if path is not None:
        return _normalize_path(path)
    fspath = getattr(item, "fspath", None)
    return _normalize_path(str(fspath))


class _CollectFilesPlugin:
    def __init__(self) -> None:
        self.files: set[str] = set()

    def pytest_collection_modifyitems(self, session: object, config: object, items: list[object]) -> None:
        for item in items:
            self.files.add(_item_path(item))


def _option_requires_value(option: str) -> bool:
    if option in OPTIONS_REQUIRING_VALUE:
        return True
    if option.startswith("--") and "=" in option:
        return False
    if option.startswith("-k") and option != "-k":
        return False
    if option.startswith("-m") and option != "-m":
        return False
    if option.startswith("-c") and option != "-c":
        return False
    if option.startswith("-o") and option != "-o":
        return False
    if option.startswith("-p") and option != "-p":
        return False
    if option.startswith("-r") and option != "-r":
        return False
    return option in OPTIONS_REQUIRING_VALUE


def split_pytest_options_and_targets(pytest_args: Sequence[str]) -> tuple[list[str], list[str]]:
    options: list[str] = []
    targets: list[str] = []
    index = 0
    args = list(pytest_args)
    while index < len(args):
        token = args[index]
        if token == "--":
            targets.extend(args[index + 1 :])
            break
        if token.startswith("-"):
            options.append(token)
            if _option_requires_value(token) and "=" not in token and (index + 1) < len(args):
                options.append(args[index + 1])
                index += 1
            index += 1
            continue
        targets.append(token)
        index += 1
    return options, targets


def _normalized_file_target(target: str) -> str | None:
    module_token = target.split("::", 1)[0]
    candidate = Path(module_token)
    if candidate.suffix == ".py":
        return _normalize_path(candidate)
    if candidate.is_absolute() and candidate.is_file():
        return _normalize_path(candidate)
    resolved = (Path.cwd() / candidate).resolve()
    if resolved.is_file():
        return str(resolved)
    return None


def _has_basetemp_option(pytest_options: Sequence[str]) -> bool:
    for token in pytest_options:
        if token == "--basetemp" or token.startswith("--basetemp="):
            return True
    return False


def build_worker_pytest_args(
    pytest_options: Sequence[str],
    original_targets: Sequence[str],
    shard_files: Sequence[str],
    *,
    basetemp_dir: str,
) -> list[str]:
    shard_set = {_normalize_path(path) for path in shard_files}
    selected_targets: list[str] = []
    for target in original_targets:
        normalized = _normalized_file_target(target)
        if normalized is None:
            continue
        if normalized in shard_set:
            selected_targets.append(target)

    if not selected_targets:
        selected_targets = list(shard_files)

    worker_args: list[str] = list(pytest_options)
    if not _has_basetemp_option(pytest_options):
        worker_args.append(f"--basetemp={basetemp_dir}")
    worker_args.extend(selected_targets)
    return worker_args


class _WorkerRecorderPlugin:
    def __init__(self) -> None:
        self.collected = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.warnings = 0
        self.module_durations: dict[str, float] = {}
        self.passed_nodeids: set[str] = set()
        self.failed_nodeids: set[str] = set()
        self.error_nodeids: set[str] = set()
        self.skipped_nodeids: set[str] = set()

    def pytest_runtest_logreport(self, report: object) -> None:
        when = str(getattr(report, "when", ""))
        failed = bool(getattr(report, "failed", False))
        passed = bool(getattr(report, "passed", False))
        skipped = bool(getattr(report, "skipped", False))
        nodeid = str(getattr(report, "nodeid", "<unknown>"))
        duration = float(getattr(report, "duration", 0.0) or 0.0)
        module_nodeid = nodeid.split("::", 1)[0]
        module_path = _normalize_path(module_nodeid)
        self.module_durations[module_path] = self.module_durations.get(module_path, 0.0) + max(0.0, duration)

        if when == "call":
            if passed:
                self.passed_nodeids.add(nodeid)
            elif failed:
                self.failed_nodeids.add(nodeid)
            elif skipped:
                self.skipped_nodeids.add(nodeid)
            return

        if failed:
            self.error_nodeids.add(nodeid)
            return
        if skipped:
            self.skipped_nodeids.add(nodeid)

    def pytest_warning_recorded(
        self,
        warning_message: object,
        when: str,
        nodeid: str,
        location: object,
    ) -> None:
        self.warnings += 1

    def pytest_sessionfinish(self, session: object, exitstatus: int) -> None:
        self.collected = int(getattr(session, "testscollected", 0))
        self.passed = len(self.passed_nodeids)
        self.failed = len(self.failed_nodeids)
        # Treat non-call failures that do not already have a call failure as setup/teardown errors.
        self.errors = len(self.error_nodeids - self.failed_nodeids)
        self.skipped = len(self.skipped_nodeids)


def _contains_xdist_options(pytest_args: Sequence[str]) -> bool:
    for arg in pytest_args:
        if arg in XDIST_OPTIONS:
            return True
        if arg.startswith("-n") and arg != "-n":
            return True
        if arg.startswith("--numprocesses="):
            return True
        if arg.startswith("--dist="):
            return True
        if arg.startswith("--tx="):
            return True
    return False


def _default_workers() -> int:
    cpu_count = os.cpu_count() or 2
    return max(1, min(cpu_count, 4))


def _run_pytest_subprocess(pytest_args: Sequence[str]) -> int:
    command = [sys.executable, "-m", "pytest", *pytest_args]
    completed = subprocess.run(command)
    return int(completed.returncode)


def _collect_selected_files(pytest_args: Sequence[str]) -> tuple[list[str], int, str]:
    import pytest

    plugin = _CollectFilesPlugin()
    collect_args = [*pytest_args, "--collect-only", "-q"]
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
        exit_code = int(pytest.main(collect_args, plugins=[plugin]))
    files = sorted(plugin.files)
    return files, exit_code, output_buffer.getvalue()


def _file_weight(path: str) -> int:
    try:
        size = Path(path).stat().st_size
    except OSError:
        return 1
    return max(1, int(size))


def _cache_key_from_path(path: str) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _path_from_cache_key(key: str) -> str:
    candidate = Path(key)
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((REPO_ROOT / candidate).resolve())


def load_module_timing_cache() -> dict[str, float]:
    if not TIMING_CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(TIMING_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}

    raw_timings = payload.get("module_timings", {})
    if not isinstance(raw_timings, dict):
        return {}

    timings: dict[str, float] = {}
    for cache_key, duration in raw_timings.items():
        try:
            normalized_duration = float(duration)
        except (TypeError, ValueError):
            continue
        if normalized_duration <= 0.0:
            continue
        timings[_path_from_cache_key(str(cache_key))] = normalized_duration
    return timings


def merge_module_timings(
    existing: dict[str, float],
    observed: dict[str, float],
    *,
    alpha: float = TIMING_CACHE_ALPHA,
) -> dict[str, float]:
    merged = dict(existing)
    clamped_alpha = min(max(alpha, 0.0), 1.0)
    for path, observed_duration in observed.items():
        if observed_duration <= 0.0:
            continue
        previous = merged.get(path)
        if previous is None:
            merged[path] = float(observed_duration)
            continue
        merged[path] = (clamped_alpha * float(observed_duration)) + (
            (1.0 - clamped_alpha) * float(previous)
        )
    return merged


def save_module_timing_cache(module_timings: dict[str, float]) -> None:
    TIMING_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    serialized = {
        _cache_key_from_path(path): round(float(duration), 6)
        for path, duration in sorted(module_timings.items(), key=lambda item: item[0])
        if float(duration) > 0.0
    }
    payload = {
        "version": TIMING_CACHE_VERSION,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "module_timings": serialized,
    }
    TIMING_CACHE_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _shard_weight(path: str, module_timings: dict[str, float] | None) -> float:
    if module_timings:
        observed = module_timings.get(_normalize_path(path))
        if observed is not None and observed > 0.0:
            return float(observed)
    return float(_file_weight(path))


def plan_shards(
    files: Sequence[str],
    workers: int,
    *,
    module_timings: dict[str, float] | None = None,
) -> list[list[str]]:
    if not files:
        return []
    shard_count = min(max(1, workers), len(files))
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    shard_weights = [0.0 for _ in range(shard_count)]

    weighted_files = sorted(
        files,
        key=lambda path: (-_shard_weight(path, module_timings), path),
    )

    for file_path in weighted_files:
        idx = min(range(shard_count), key=lambda shard_index: (shard_weights[shard_index], shard_index))
        shards[idx].append(file_path)
        shard_weights[idx] += _shard_weight(file_path, module_timings)

    for shard in shards:
        shard.sort()
    return [shard for shard in shards if shard]


def _stream_pipe(
    stream: io.TextIOBase | None,
    *,
    shard_index: int,
    stream_name: str,
    print_lock: threading.Lock,
) -> None:
    if stream is None:
        return
    try:
        for raw_line in iter(stream.readline, ""):
            line = raw_line.rstrip("\n")
            output_stream = sys.stderr if stream_name == "stderr" else sys.stdout
            with print_lock:
                print(f"[pytest-shard {shard_index}][{stream_name}] {line}", file=output_stream, flush=True)
    finally:
        stream.close()


def _start_worker(
    *,
    shard_index: int,
    shard_total: int,
    shard_files: Sequence[str],
    pytest_options: Sequence[str],
    original_targets: Sequence[str],
    print_lock: threading.Lock,
) -> WorkerProcess:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f"pytest-shard-{shard_index:02d}-",
        suffix=".result.json",
        delete=False,
    ) as result_handle:
        result_json = result_handle.name

    basetemp_dir = tempfile.mkdtemp(prefix=f"pytest-shard-{shard_index:02d}-basetemp-")
    worker_pytest_args = build_worker_pytest_args(
        pytest_options,
        original_targets,
        shard_files,
        basetemp_dir=basetemp_dir,
    )

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        f"--result-json={result_json}",
        "--",
        *worker_pytest_args,
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_thread = threading.Thread(
        target=_stream_pipe,
        kwargs={
            "stream": process.stdout,
            "shard_index": shard_index,
            "stream_name": "stdout",
            "print_lock": print_lock,
        },
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_pipe,
        kwargs={
            "stream": process.stderr,
            "shard_index": shard_index,
            "stream_name": "stderr",
            "print_lock": print_lock,
        },
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    return WorkerProcess(
        shard_index=shard_index,
        shard_total=shard_total,
        shard_files=list(shard_files),
        process=process,
        result_json=result_json,
        basetemp_dir=basetemp_dir,
        stdout_thread=stdout_thread,
        stderr_thread=stderr_thread,
    )


def _cleanup_worker_artifacts(worker: WorkerProcess) -> None:
    Path(worker.result_json).unlink(missing_ok=True)
    shutil.rmtree(worker.basetemp_dir, ignore_errors=True)


def _load_worker_summary(worker: WorkerProcess) -> WorkerSummary:
    payload_path = Path(worker.result_json)
    if not payload_path.exists():
        return WorkerSummary(
            exit_code=2,
            errors=1,
            failed_nodeids=["<missing-worker-summary>"],
            error_nodeids=["<missing-worker-summary>"],
        )
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception:
        return WorkerSummary(
            exit_code=2,
            errors=1,
            failed_nodeids=["<invalid-worker-summary>"],
            error_nodeids=["<invalid-worker-summary>"],
        )
    if not isinstance(payload, dict):
        return WorkerSummary(
            exit_code=2,
            errors=1,
            failed_nodeids=["<invalid-worker-summary>"],
            error_nodeids=["<invalid-worker-summary>"],
        )
    return WorkerSummary.from_payload(payload)


def aggregate_worker_summaries(summaries: Sequence[WorkerSummary]) -> AggregateSummary:
    passed = sum(summary.passed for summary in summaries)
    skipped = sum(summary.skipped for summary in summaries)
    warnings = sum(summary.warnings for summary in summaries)
    failed_nodeids = sorted(
        {
            *[nodeid for summary in summaries for nodeid in summary.failed_nodeids],
            *[nodeid for summary in summaries for nodeid in summary.error_nodeids],
        }
    )
    failures = len(failed_nodeids)
    total_tests = sum(summary.collected for summary in summaries)
    minimum_total = passed + skipped + failures
    if total_tests < minimum_total:
        total_tests = minimum_total
    return AggregateSummary(
        shards=len(summaries),
        total_tests=total_tests,
        passed=passed,
        skipped=skipped,
        warnings=warnings,
        failures=failures,
        failed_nodeids=failed_nodeids,
    )


def _print_summary(summary: AggregateSummary) -> None:
    print()
    print("=== Pytest Sharded Summary ===")
    print(f"Shards: {summary.shards}")
    print(f"Total tests: {summary.total_tests}")
    print(f"Skipped: {summary.skipped}")
    print(f"Warnings: {summary.warnings}")
    print(f"Failures: {summary.failures}")
    if summary.failed_nodeids:
        print("Failed tests:")
        for nodeid in summary.failed_nodeids:
            print(f"- {nodeid}")


def should_update_timing_cache(first_failure: int, aggregate: AggregateSummary) -> bool:
    return first_failure == 0 and aggregate.failures == 0


def normalize_worker_exit_code(return_code: int, summary: WorkerSummary) -> int:
    # pytest uses 5 for "no tests collected". Treat empty shards as neutral
    # so broad filters like `-k` don't fail healthy multi-shard runs.
    if return_code == 5 and summary.collected == 0:
        return 0
    return return_code


def _orchestrate(pytest_args: Sequence[str], workers: int) -> int:
    if _contains_xdist_options(pytest_args):
        print(
            "run_pytest_sharded does not support xdist options. "
            "Remove -n/--numprocesses/--dist/--tx.",
            file=sys.stderr,
        )
        return 2

    files, collect_exit_code, collect_output = _collect_selected_files(pytest_args)
    if collect_exit_code not in (0, 5):
        print(
            f"Pytest collection failed (exit={collect_exit_code}); "
            "running serial pytest to preserve default error output.",
            file=sys.stderr,
        )
        if collect_output.strip():
            print(collect_output.rstrip(), file=sys.stderr)
        return _run_pytest_subprocess(pytest_args)

    if not files:
        print("No test files collected; running serial pytest.")
        return _run_pytest_subprocess(pytest_args)

    if workers <= 1 or len(files) <= 1:
        print(f"Collected {len(files)} file(s); running serial pytest.")
        return _run_pytest_subprocess(pytest_args)

    pytest_options, original_targets = split_pytest_options_and_targets(pytest_args)
    timing_cache = load_module_timing_cache()
    cached_modules = sum(1 for file_path in files if _normalize_path(file_path) in timing_cache)
    if cached_modules > 0:
        print(
            f"Using module timing cache for {cached_modules}/{len(files)} file(s) "
            f"from {TIMING_CACHE_FILE}."
        )
    else:
        print("No module timing cache for selected files; using file-size weighting.")

    shards = plan_shards(files=files, workers=workers, module_timings=timing_cache)
    if len(shards) <= 1:
        print(f"Collected {len(files)} file(s); running serial pytest.")
        return _run_pytest_subprocess(pytest_args)

    print(
        f"Collected {len(files)} file(s); running {len(shards)} shard(s) "
        f"with workers={min(workers, len(shards))}."
    )

    print_lock = threading.Lock()
    worker_processes = [
        _start_worker(
            shard_index=index,
            shard_total=len(shards),
            shard_files=shard_files,
            pytest_options=pytest_options,
            original_targets=original_targets,
            print_lock=print_lock,
        )
        for index, shard_files in enumerate(shards, start=1)
    ]

    summaries: list[WorkerSummary] = []
    first_failure = 0
    for worker in worker_processes:
        return_code = int(worker.process.wait())
        worker.stdout_thread.join()
        worker.stderr_thread.join()
        worker_summary = _load_worker_summary(worker)
        summaries.append(worker_summary)
        _cleanup_worker_artifacts(worker)

        effective_code = normalize_worker_exit_code(return_code, worker_summary)
        if effective_code != 0 and first_failure == 0:
            first_failure = effective_code

    aggregate = aggregate_worker_summaries(summaries)
    observed_module_timings = {
        path: duration
        for summary in summaries
        for path, duration in summary.module_durations.items()
        if duration > 0.0
    }
    if observed_module_timings and should_update_timing_cache(first_failure, aggregate):
        merged_timings = merge_module_timings(timing_cache, observed_module_timings)
        save_module_timing_cache(merged_timings)
        print(
            f"Updated module timing cache with {len(observed_module_timings)} file(s): "
            f"{TIMING_CACHE_FILE}"
        )
    elif observed_module_timings:
        print("Skipped timing cache update because the sharded run was not clean.")
    _print_summary(aggregate)
    if first_failure == 0 and all(summary.collected == 0 for summary in summaries):
        return 5
    if first_failure == 0 and aggregate.failures > 0:
        return 1
    return first_failure


def _run_worker(result_json: str, pytest_args: Sequence[str]) -> int:
    import pytest

    recorder = _WorkerRecorderPlugin()

    exit_code = int(pytest.main(list(pytest_args), plugins=[recorder]))
    summary = WorkerSummary(
        exit_code=exit_code,
        collected=recorder.collected,
        passed=recorder.passed,
        failed=recorder.failed,
        errors=recorder.errors,
        skipped=recorder.skipped,
        warnings=recorder.warnings,
        module_durations=dict(recorder.module_durations),
        failed_nodeids=sorted(recorder.failed_nodeids),
        error_nodeids=sorted(recorder.error_nodeids),
    )
    Path(result_json).write_text(json.dumps(summary.to_payload()), encoding="utf-8")
    return exit_code


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run module-level concurrent pytest shards.")
    parser.add_argument("--workers", type=int, default=_default_workers(), help="Maximum concurrent shard workers.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--result-json", type=str, help=argparse.SUPPRESS)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    pytest_args = _strip_remainder_separator(args.pytest_args)
    if not pytest_args:
        pytest_args = list(DEFAULT_TARGETS)

    if args.worker:
        if not args.result_json:
            print("--worker requires --result-json", file=sys.stderr)
            return 2
        try:
            return _run_worker(
                result_json=args.result_json,
                pytest_args=pytest_args,
            )
        except Exception:
            failure_summary = WorkerSummary(
                exit_code=2,
                errors=1,
                failed_nodeids=["<worker-exception>"],
                error_nodeids=["<worker-exception>"],
            )
            Path(args.result_json).write_text(json.dumps(failure_summary.to_payload()), encoding="utf-8")
            traceback.print_exc(file=sys.stderr)
            return 2

    return _orchestrate(pytest_args=pytest_args, workers=max(1, int(args.workers)))


if __name__ == "__main__":
    raise SystemExit(main())
