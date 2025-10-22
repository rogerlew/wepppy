#!/usr/bin/env python3
"""Test isolation checker tooling.

This script implements the ``wctl check-test-isolation`` workflow specified in
``docs/dev-notes/test-tooling-spec.md``. It orchestrates three phases:

1. Random-order fuzzing of the requested pytest targets
2. Per-file isolation runs to surface files that only fail when run in suite
3. Optional global state diffing (sys.modules, environment variables,
   singleton caches, filesystem)

Usage examples:

    python tools/check_test_isolation.py --quick
    python tools/check_test_isolation.py tests/weppcloud/routes/

Exit codes:
    0 - No issues detected
    1 - Isolation issues detected (order dependence, pollution, etc.)
    2 - Tool execution error
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    tomllib = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS: Sequence[int] = (42, 123, 999, 1337, 8675309)
WATCHED_SINGLETON_ATTRS: Sequence[str] = (
    "_instances",
    "_instance",
    "_cache",
    "_caches",
    "_singleton",
    "_registry",
    "_registries",
)
DEFAULT_FS_IGNORE: Sequence[str] = (
    ".git/*",
    ".eggs/*",
    ".mypy_cache/*",
    ".pytest_cache/*",
    "build/*",
    "dist/*",
    "node_modules/*",
    "venv/*",
    ".tox/*",
    "__pycache__/*",
    "htmlcov/*",
    ".docker-data/*",
)


class ExitCode(Enum):
    """Process exit codes."""

    CLEAN = 0
    ISSUES_FOUND = 1
    TOOL_ERROR = 2


@dataclass
class ModuleRecord:
    """Capture metadata about a module difference."""

    name: str
    file: Optional[str]
    has_file: bool
    is_package: bool
    is_stub: bool
    loader: Optional[str]
    reason: str


@dataclass
class ModuleDiff:
    """Summarize module pollution findings."""

    added: List[ModuleRecord] = field(default_factory=list)
    replaced: List[ModuleRecord] = field(default_factory=list)
    suspicious: List[ModuleRecord] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.added or self.replaced or self.suspicious)


@dataclass
class SingletonDiffEntry:
    module: str
    attribute: str
    before: int
    after: int


@dataclass
class SingletonDiff:
    entries: List[SingletonDiffEntry] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.entries


@dataclass
class EnvDiff:
    added: Dict[str, str] = field(default_factory=dict)
    removed: Dict[str, str] = field(default_factory=dict)
    changed: Dict[str, Tuple[str, str]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


@dataclass
class FileSystemDiff:
    created_files: List[str] = field(default_factory=list)
    created_dirs: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.created_files or self.created_dirs)


@dataclass
class StateDiff:
    modules: Optional[ModuleDiff] = None
    env: Optional[EnvDiff] = None
    singletons: Optional[SingletonDiff] = None
    filesystem: Optional[FileSystemDiff] = None

    def is_empty(self) -> bool:
        return all(
            diff is None or diff.is_empty()
            for diff in (self.modules, self.env, self.singletons, self.filesystem)
        )


@dataclass
class FailureEntry:
    nodeid: str
    when: str
    longrepr: Optional[str] = None


@dataclass
class PytestOutcome:
    exit_code: int
    failures: List[FailureEntry] = field(default_factory=list)
    errors: List[FailureEntry] = field(default_factory=list)
    skips: List[str] = field(default_factory=list)
    xfails: List[str] = field(default_factory=list)
    collected: int = 0
    duration_s: float = 0.0
    files: List[str] = field(default_factory=list)
    json_report: Optional[Dict[str, Any]] = None
    state_diff: Optional[StateDiff] = None
    stdout: str = ""
    stderr: str = ""

    def failed_nodeids(self) -> Set[str]:
        return {entry.nodeid for entry in self.failures + self.errors}


@dataclass
class RandomRunResult:
    seed: Optional[int]
    shuffle_scope: Optional[str]
    outcome: PytestOutcome


@dataclass
class FileIsolationResult:
    file_path: str
    outcome: PytestOutcome


@dataclass
class IssueRecord:
    key: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)


class Baseline:
    """Baseline suppression helper."""

    def __init__(self, suppressions: Optional[Set[str]] = None) -> None:
        self._suppressions = suppressions or set()

    @classmethod
    def from_path(cls, path: Optional[Path]) -> "Baseline":
        if path is None:
            return cls()
        if not path.exists():
            raise FileNotFoundError(f"Baseline file not found: {path}")
        data = json.loads(path.read_text())
        suppressions: Set[str] = set()
        if isinstance(data, dict):
            raw = data.get("suppressions")
            if isinstance(raw, list):
                suppressions = {str(entry) for entry in raw}
        elif isinstance(data, list):
            suppressions = {str(entry) for entry in data}
        else:
            raise ValueError(f"Unsupported baseline structure in {path}")
        return cls(suppressions=suppressions)

    def allows(self, key: str) -> bool:
        return key not in self._suppressions


def debug(msg: str, *, verbose: bool) -> None:
    if verbose:
        print(f"[debug] {msg}")


def discover_random_plugin(preferred: Optional[str], verbose: bool) -> Optional[str]:
    options = [preferred] if preferred else []
    options.extend(["pytest-randomly", "pytest-random-order"])
    for candidate in options:
        if not candidate:
            continue
        if importlib.util.find_spec(candidate.replace("-", "_")):
            debug(f"Detected randomization plugin: {candidate}", verbose=verbose)
            return candidate
    debug("No randomization plugin detected; proceeding without randomization.", verbose=verbose)
    return None


def discover_json_report_plugin(verbose: bool) -> bool:
    available = importlib.util.find_spec("pytest_jsonreport") is not None
    if available:
        debug("pytest-json-report plugin is available.", verbose=verbose)
    else:
        debug("pytest-json-report plugin not found; falling back to recorder output.", verbose=verbose)
    return available


def load_config_toml(repo_root: Path, verbose: bool) -> Dict[str, Any]:
    config_path = repo_root / "tools" / "check_test_isolation.toml"
    if not config_path.exists():
        debug("No tools/check_test_isolation.toml found; using defaults.", verbose=verbose)
        return {}
    if tomllib is None:
        raise RuntimeError("tomllib is required to parse tools/check_test_isolation.toml")
    debug(f"Loading configuration from {config_path}", verbose=verbose)
    return tomllib.loads(config_path.read_text())


def shlex_split_optional(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return shlex.split(value)


def should_ignore_path(relative: str, is_dir: bool, ignore_patterns: Sequence[str]) -> bool:
    rel = relative.rstrip("/") + ("/" if is_dir else "")
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def scan_filesystem(repo_root: Path, ignore_patterns: Sequence[str]) -> Tuple[Set[str], Set[str]]:
    files: Set[str] = set()
    dirs: Set[str] = set()
    for root, dirnames, filenames in os.walk(repo_root):
        rel_root = Path(root).relative_to(repo_root)
        rel_root_str = "" if str(rel_root) == "." else str(rel_root)

        # Filter directories in-place to avoid walking ignored paths.
        keep_dirs = []
        for dirname in dirnames:
            rel_path = str(Path(rel_root_str, dirname)) if rel_root_str else dirname
            if should_ignore_path(rel_path, True, ignore_patterns):
                continue
            keep_dirs.append(dirname)
            dirs.add(rel_path.rstrip("/") + "/")
        dirnames[:] = keep_dirs

        for filename in filenames:
            rel_path = str(Path(rel_root_str, filename)) if rel_root_str else filename
            if should_ignore_path(rel_path, False, ignore_patterns):
                continue
            files.add(rel_path)
    return files, dirs


def classify_module(module: Any) -> Tuple[bool, bool, bool, Optional[str]]:
    file_path = getattr(module, "__file__", None)
    has_file = bool(file_path)
    is_package = bool(getattr(module, "__path__", None))
    spec = getattr(module, "__spec__", None)
    loader_name = None
    if spec and getattr(spec, "loader", None):
        loader_name = spec.loader.__class__.__name__
    is_stub = not has_file and not is_package and loader_name is None
    return has_file, is_package, is_stub, loader_name


def capture_singleton_snapshot() -> Dict[str, Dict[str, int]]:
    snapshot: Dict[str, Dict[str, int]] = {}
    for name, module in list(sys.modules.items()):
        if not name.startswith(("wepppy.", "tests.", "wepppy")):
            continue
        module_entries: Dict[str, int] = {}
        for attr in WATCHED_SINGLETON_ATTRS:
            if hasattr(module, attr):
                value = getattr(module, attr)
                try:
                    size = len(value)  # type: ignore[arg-type]
                except TypeError:
                    continue
                if size:
                    module_entries[attr] = int(size)
        if module_entries:
            snapshot[name] = module_entries
    return snapshot


def diff_singletons(
    before: Dict[str, Dict[str, int]], after: Dict[str, Dict[str, int]]
) -> SingletonDiff:
    entries: List[SingletonDiffEntry] = []
    modules = set(before) | set(after)
    for module in sorted(modules):
        before_attrs = before.get(module, {})
        after_attrs = after.get(module, {})
        for attr in sorted(set(before_attrs) | set(after_attrs)):
            b = before_attrs.get(attr, 0)
            a = after_attrs.get(attr, 0)
            if a != b:
                entries.append(SingletonDiffEntry(module=module, attribute=attr, before=b, after=a))
    return SingletonDiff(entries=entries)


def diff_env(before: Dict[str, str], after: Dict[str, str]) -> EnvDiff:
    added = {k: after[k] for k in after.keys() - before.keys()}
    removed = {k: before[k] for k in before.keys() - after.keys()}
    changed = {k: (before[k], after[k]) for k in before.keys() & after.keys() if before[k] != after[k]}
    return EnvDiff(added=added, removed=removed, changed=changed)


def module_diff(before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]) -> ModuleDiff:
    added: List[ModuleRecord] = []
    replaced: List[ModuleRecord] = []

    for name, info in after.items():
        if name not in before:
            added.append(
                ModuleRecord(
                    name=name,
                    file=info.get("file"),
                    has_file=bool(info.get("has_file")),
                    is_package=bool(info.get("is_package")),
                    is_stub=bool(info.get("is_stub")),
                    loader=info.get("loader"),
                    reason="Module added during run",
                )
            )
        else:
            if info["module_id"] != before[name]["module_id"]:
                replaced.append(
                    ModuleRecord(
                        name=name,
                        file=info.get("file"),
                        has_file=bool(info.get("has_file")),
                        is_package=bool(info.get("is_package")),
                        is_stub=bool(info.get("is_stub")),
                        loader=info.get("loader"),
                        reason="Module object replaced during run",
                    )
                )

    suspicious: List[ModuleRecord] = []
    for record in added + replaced:
        if not record.has_file and record.is_stub:
            suspicious.append(
                ModuleRecord(
                    name=record.name,
                    file=record.file,
                    has_file=record.has_file,
                    is_package=record.is_package,
                    is_stub=record.is_stub,
                    loader=record.loader,
                    reason="Module inserted without __file__ (likely sys.modules stub)",
                )
            )

    return ModuleDiff(added=added, replaced=replaced, suspicious=suspicious)


def diff_filesystem(
    before_files: Set[str],
    before_dirs: Set[str],
    after_files: Set[str],
    after_dirs: Set[str],
) -> FileSystemDiff:
    created_files = sorted(after_files - before_files)
    created_dirs = sorted(after_dirs - before_dirs)
    return FileSystemDiff(created_files=created_files, created_dirs=created_dirs)


def create_module_snapshot() -> Dict[str, Dict[str, Any]]:
    snapshot: Dict[str, Dict[str, Any]] = {}
    for name, module in list(sys.modules.items()):
        has_file, is_package, is_stub, loader_name = classify_module(module)
        file_path = getattr(module, "__file__", None)
        snapshot[name] = {
            "name": name,
            "file": file_path,
            "has_file": has_file,
            "is_package": is_package,
            "is_stub": is_stub,
            "loader": loader_name,
            "module_id": id(module),
        }
    return snapshot


@dataclass
class StateSnapshot:
    modules: Optional[Dict[str, Dict[str, Any]]] = None
    env: Optional[Dict[str, str]] = None
    singletons: Optional[Dict[str, Dict[str, int]]] = None
    filesystem_files: Optional[Set[str]] = None
    filesystem_dirs: Optional[Set[str]] = None


def capture_state(
    *,
    enable_state_scan: bool,
    enable_fs_scan: bool,
    ignore_patterns: Sequence[str],
) -> StateSnapshot:
    modules = create_module_snapshot() if enable_state_scan else None
    env = dict(os.environ) if enable_state_scan else None
    singletons = capture_singleton_snapshot() if enable_state_scan else None
    fs_files: Optional[Set[str]] = None
    fs_dirs: Optional[Set[str]] = None
    if enable_fs_scan:
        fs_files, fs_dirs = scan_filesystem(REPO_ROOT, ignore_patterns)
    return StateSnapshot(
        modules=modules,
        env=env,
        singletons=singletons,
        filesystem_files=fs_files,
        filesystem_dirs=fs_dirs,
    )


def compute_state_diff(before: StateSnapshot, after: StateSnapshot) -> StateDiff:
    modules = None
    env = None
    singletons = None
    filesystem = None

    if before.modules is not None and after.modules is not None:
        modules = module_diff(before.modules, after.modules)
    if before.env is not None and after.env is not None:
        env = diff_env(before.env, after.env)
    if before.singletons is not None and after.singletons is not None:
        singletons = diff_singletons(before.singletons, after.singletons)
    if before.filesystem_files is not None and after.filesystem_files is not None:
        filesystem = diff_filesystem(
            before.filesystem_files,
            before.filesystem_dirs or set(),
            after.filesystem_files,
            after.filesystem_dirs or set(),
        )
    return StateDiff(modules=modules, env=env, singletons=singletons, filesystem=filesystem)


class RecorderPlugin:
    """pytest plugin to capture outcome details."""

    def __init__(self) -> None:
        self.failures: List[FailureEntry] = []
        self.errors: List[FailureEntry] = []
        self.skips: List[str] = []
        self.xfails: List[str] = []
        self.files: Set[str] = set()
        self.collected: int = 0
        self._start = time.time()

    # pytest hooks
    def pytest_itemcollected(self, item: Any) -> None:  # pragma: no cover - exercised via pytest
        try:
            self.files.add(str(item.fspath))
        except Exception:
            pass

    def pytest_runtest_logreport(self, report: Any) -> None:  # pragma: no cover - exercised via pytest
        nodeid = getattr(report, "nodeid", "<unknown>")
        if report.when == "call":
            if report.failed:
                self.failures.append(
                    FailureEntry(nodeid=nodeid, when="call", longrepr=_safe_longrepr(report))
                )
            elif report.skipped:
                self.skips.append(nodeid)
            elif report.wasxfail:
                self.xfails.append(nodeid)
        elif report.failed:
            self.errors.append(
                FailureEntry(nodeid=nodeid, when=report.when, longrepr=_safe_longrepr(report))
            )

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:  # pragma: no cover - requires pytest run
        self.collected = getattr(session, "testscollected", self.collected)
        self.duration = time.time() - self._start


def _safe_longrepr(report: Any) -> Optional[str]:
    try:
        value = getattr(report, "longrepr", None)
        if value is None:
            return None
        if isinstance(value, (str, bytes)):
            return value if isinstance(value, str) else value.decode("utf-8", "replace")
        string_io = io.StringIO()
        try:
            value.toterminal(string_io)  # type: ignore[attr-defined]
            return string_io.getvalue()
        except Exception:
            return str(value)
    except Exception:
        return None


def run_pytest_worker(config: Dict[str, Any]) -> Tuple[PytestOutcome, int]:
    import pytest  # Imported lazily so CLI parsing paths do not require pytest

    recorder = RecorderPlugin()
    args: List[str] = list(config["targets"])
    args.extend(config.get("pytest_args", []))

    plugin: Optional[str] = config.get("random_plugin")
    seed = config.get("seed")
    shuffle_scope: Optional[str] = config.get("shuffle_scope")
    if plugin and seed is not None:
        if plugin == "pytest-randomly":
            args.append(f"--randomly-seed={seed}")
            if shuffle_scope == "module":
                args.append("--randomly-order-bucket=module")
        elif plugin == "pytest-random-order":
            args.append(f"--random-order-seed={seed}")
            if shuffle_scope == "module":
                args.append("--random-order-bucket=module")
        else:
            args.append(f"--randomly-seed={seed}")

    json_report_enabled = config.get("json_report", False)
    json_report_path: Optional[Path] = None
    tempdir: Optional[tempfile.TemporaryDirectory[str]] = None

    if json_report_enabled:
        tempdir = tempfile.TemporaryDirectory(prefix="check-test-isolation-")
        json_report_path = Path(tempdir.name) / "report.json"
        args.extend(
            [
                "--json-report",
                f"--json-report-file={json_report_path}",
                "--json-report-omit-streams",
            ]
        )

    enable_state_scan = bool(config.get("enable_state_scan", True))
    enable_fs_scan = bool(config.get("enable_fs_scan", False))
    ignore_patterns = config.get("ignore_patterns", list(DEFAULT_FS_IGNORE))

    before_snapshot = capture_state(
        enable_state_scan=enable_state_scan,
        enable_fs_scan=enable_fs_scan,
        ignore_patterns=ignore_patterns,
    )

    exit_code = pytest.main(args, plugins=[recorder])

    after_snapshot = capture_state(
        enable_state_scan=enable_state_scan,
        enable_fs_scan=enable_fs_scan,
        ignore_patterns=ignore_patterns,
    )

    state_diff = None
    if enable_state_scan or enable_fs_scan:
        state_diff = compute_state_diff(before_snapshot, after_snapshot)

    json_data: Optional[Dict[str, Any]] = None
    if json_report_enabled and json_report_path and json_report_path.exists():
        try:
            json_data = json.loads(json_report_path.read_text())
        except Exception:
            json_data = None

    if tempdir and not config.get("keep_temp"):
        tempdir.cleanup()

    outcome = PytestOutcome(
        exit_code=int(exit_code),
        failures=recorder.failures,
        errors=recorder.errors,
        skips=recorder.skips,
        xfails=recorder.xfails,
        collected=recorder.collected,
        duration_s=getattr(recorder, "duration", 0.0),
        files=sorted(recorder.files),
        json_report=json_data,
        state_diff=state_diff,
    )
    return outcome, int(exit_code)


def subprocess_run_worker(config: Dict[str, Any]) -> PytestOutcome:
    """Run the worker in a child process and return the outcome."""
    with tempfile.NamedTemporaryFile("w+", delete=False, prefix="check-test-isolation-config-", suffix=".json") as cfg:
        json.dump(config, cfg)
        cfg_path = Path(cfg.name)

    with tempfile.NamedTemporaryFile("r", delete=False, prefix="check-test-isolation-result-", suffix=".json") as result_file:
        result_path = Path(result_file.name)

    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        f"--config={cfg_path}",
        f"--result={result_path}",
    ]

    completed = run_subprocess(cmd)
    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""

    try:
        raw_payload = result_path.read_text()
        data = json.loads(raw_payload)
    except Exception as exc:
        cfg_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        details = "\n".join(
            [
                "Isolation worker failed to produce a valid result payload.",
                f"Command: {' '.join(cmd)}",
                f"Exit code: {completed.returncode}",
                "Captured stdout:",
                stdout_text or "  (empty)",
                "Captured stderr:",
                stderr_text or "  (empty)",
            ]
        )
        raise RuntimeError(details) from exc
    else:
        cfg_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)

    outcome = PytestOutcome(
        exit_code=int(data.get("exit_code", 0)),
        failures=[FailureEntry(**entry) for entry in data.get("failures", [])],
        errors=[FailureEntry(**entry) for entry in data.get("errors", [])],
        skips=[str(entry) for entry in data.get("skips", [])],
        xfails=[str(entry) for entry in data.get("xfails", [])],
        collected=int(data.get("collected", 0)),
        duration_s=float(data.get("duration_s", 0.0)),
        files=[str(entry) for entry in data.get("files", [])],
        json_report=data.get("json_report"),
        state_diff=_decode_state_diff(data.get("state_diff")),
        stdout=stdout_text,
        stderr=stderr_text,
    )
    return outcome


def _decode_state_diff(payload: Optional[Dict[str, Any]]) -> Optional[StateDiff]:
    if not payload:
        return None

    def decode_module_records(entries: Optional[List[Dict[str, Any]]]) -> List[ModuleRecord]:
        if not entries:
            return []
        return [
            ModuleRecord(
                name=entry.get("name"),
                file=entry.get("file"),
                has_file=bool(entry.get("has_file")),
                is_package=bool(entry.get("is_package")),
                is_stub=bool(entry.get("is_stub")),
                loader=entry.get("loader"),
                reason=entry.get("reason", ""),
            )
            for entry in entries
        ]

    modules_payload = payload.get("modules")
    modules = None
    if modules_payload:
        modules = ModuleDiff(
            added=decode_module_records(modules_payload.get("added")),
            replaced=decode_module_records(modules_payload.get("replaced")),
            suspicious=decode_module_records(modules_payload.get("suspicious")),
        )

    env_payload = payload.get("env")
    env = None
    if env_payload:
        env = EnvDiff(
            added=env_payload.get("added", {}),
            removed=env_payload.get("removed", {}),
            changed={k: tuple(v) for k, v in env_payload.get("changed", {}).items()},
        )

    singleton_payload = payload.get("singletons")
    singletons = None
    if singleton_payload:
        entries = [
            SingletonDiffEntry(
                module=entry["module"],
                attribute=entry["attribute"],
                before=int(entry["before"]),
                after=int(entry["after"]),
            )
            for entry in singleton_payload.get("entries", [])
        ]
        singletons = SingletonDiff(entries=entries)

    fs_payload = payload.get("filesystem")
    filesystem = None
    if fs_payload:
        filesystem = FileSystemDiff(
            created_files=fs_payload.get("created_files", []),
            created_dirs=fs_payload.get("created_dirs", []),
        )

    return StateDiff(modules=modules, env=env, singletons=singletons, filesystem=filesystem)


def run_subprocess(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed


def worker_entry(config_path: str, result_path: str) -> int:
    config = json.loads(Path(config_path).read_text())
    try:
        outcome, exit_code = run_pytest_worker(config)
    except Exception as exc:
        import traceback

        error_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        payload = {
            "exit_code": ExitCode.TOOL_ERROR.value,
            "failures": [],
            "errors": [
                {
                    "nodeid": "<worker-exception>",
                    "when": "internal",
                    "longrepr": error_trace,
                }
            ],
            "skips": [],
            "xfails": [],
            "collected": 0,
            "duration_s": 0.0,
            "files": [],
            "json_report": None,
            "state_diff": None,
        }
        Path(result_path).write_text(json.dumps(payload))
        return ExitCode.TOOL_ERROR.value

    payload = {
        "exit_code": exit_code,
        "failures": [dataclasses.asdict(entry) for entry in outcome.failures],
        "errors": [dataclasses.asdict(entry) for entry in outcome.errors],
        "skips": outcome.skips,
        "xfails": outcome.xfails,
        "collected": outcome.collected,
        "duration_s": outcome.duration_s,
        "files": outcome.files,
        "json_report": outcome.json_report,
        "state_diff": encode_state_diff(outcome.state_diff),
    }
    Path(result_path).write_text(json.dumps(payload))
    return exit_code


def encode_state_diff(diff: Optional[StateDiff]) -> Optional[Dict[str, Any]]:
    if diff is None:
        return None

    data: Dict[str, Any] = {}
    if diff.modules:
        data["modules"] = {
            "added": [dataclasses.asdict(record) for record in diff.modules.added],
            "replaced": [dataclasses.asdict(record) for record in diff.modules.replaced],
            "suspicious": [dataclasses.asdict(record) for record in diff.modules.suspicious],
        }
    if diff.env:
        data["env"] = {
            "added": diff.env.added,
            "removed": diff.env.removed,
            "changed": {k: list(v) for k, v in diff.env.changed.items()},
        }
    if diff.singletons:
        data["singletons"] = {
            "entries": [dataclasses.asdict(entry) for entry in diff.singletons.entries]
        }
    if diff.filesystem:
        data["filesystem"] = {
            "created_files": diff.filesystem.created_files,
            "created_dirs": diff.filesystem.created_dirs,
        }
    return data


def make_issue_key(*parts: str) -> str:
    normalized = [part.strip() for part in parts if part.strip()]
    return "|".join(normalized)


def summarize_random_runs(random_runs: List[RandomRunResult], *, verbose: bool) -> List[IssueRecord]:
    issues: List[IssueRecord] = []
    if not random_runs:
        return issues
    first_failures = random_runs[0].outcome.failed_nodeids()
    divergent = False
    for result in random_runs[1:]:
        if result.outcome.failed_nodeids() != first_failures:
            divergent = True
            break
    if divergent:
        description = "Order-dependent failures detected across random seeds"
        detail = {
            "runs": [
                {
                    "seed": run.seed,
                    "failures": sorted(run.outcome.failed_nodeids()),
                    "exit_code": run.outcome.exit_code,
                }
                for run in random_runs
            ]
        }
        issues.append(
            IssueRecord(
                key=make_issue_key("order-failure", *(str(run.seed) for run in random_runs)),
                description=description,
                details=detail,
            )
        )
    return issues


def summarize_file_isolation(
    file_results: List[FileIsolationResult],
    baseline_failures: Dict[str, Set[str]],
) -> List[IssueRecord]:
    issues: List[IssueRecord] = []
    for result in file_results:
        file_path = result.file_path
        baseline = baseline_failures.get(file_path, set())
        current = result.outcome.failed_nodeids()
        if current != baseline:
            details = {
                "file": file_path,
                "baseline_failures": sorted(baseline),
                "isolated_failures": sorted(current),
                "exit_code": result.outcome.exit_code,
            }
            issues.append(
                IssueRecord(
                    key=make_issue_key("file-isolation", file_path),
                    description=f"Isolation behaviour differs for {file_path}",
                    details=details,
                )
            )
    return issues


def summarize_pollution(file_results: List[FileIsolationResult]) -> List[IssueRecord]:
    issues: List[IssueRecord] = []
    for result in file_results:
        diff = result.outcome.state_diff
        if diff is None or diff.is_empty():
            continue
        file_path = result.file_path

        if diff.modules and not diff.modules.is_empty():
            for record in diff.modules.suspicious or diff.modules.added:
                issues.append(
                    IssueRecord(
                        key=make_issue_key("pollution", "module", file_path, record.name),
                        description=f"{file_path}: sys.modules pollution ({record.name})",
                        details={
                            "file": file_path,
                            "module": dataclasses.asdict(record),
                        },
                    )
                )
                break

        if diff.env and not diff.env.is_empty():
            issues.append(
                IssueRecord(
                    key=make_issue_key("pollution", "env", file_path),
                    description=f"{file_path}: environment variables changed",
                    details={
                        "file": file_path,
                        "added": diff.env.added,
                        "removed": diff.env.removed,
                        "changed": diff.env.changed,
                    },
                )
            )

        if diff.singletons and not diff.singletons.is_empty():
            issues.append(
                IssueRecord(
                    key=make_issue_key("pollution", "singleton", file_path),
                    description=f"{file_path}: singleton cache drift detected",
                    details={
                        "file": file_path,
                        "entries": [dataclasses.asdict(entry) for entry in diff.singletons.entries],
                    },
                )
            )

        if diff.filesystem and not diff.filesystem.is_empty():
            issues.append(
                IssueRecord(
                    key=make_issue_key("pollution", "filesystem", file_path),
                    description=f"{file_path}: filesystem changes detected",
                    details={
                        "file": file_path,
                        "created_files": diff.filesystem.created_files,
                        "created_dirs": diff.filesystem.created_dirs,
                    },
                )
            )
    return issues


def write_log(log_dir: Optional[Path], name: str, stdout: str, stderr: str) -> None:
    if log_dir is None:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(os.sep, "__")
    (log_dir / f"{safe_name}.out").write_text(stdout)
    (log_dir / f"{safe_name}.err").write_text(stderr)


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect pytest isolation issues.")
    parser.add_argument("paths", nargs="*", default=["tests"], help="Pytest targets to execute.")
    parser.add_argument("--iterations", type=int, default=5, help="Random-order iterations (default: 5).")
    parser.add_argument(
        "--shuffle-scope",
        choices=("module", "node"),
        default="module",
        help="Randomization bucket scope.",
    )
    parser.add_argument(
        "--random-plugin",
        choices=("pytest-randomly", "pytest-random-order"),
        default=None,
        help="Randomization plugin override.",
    )
    parser.add_argument("--quick", action="store_true", help="Fast pre-commit run.")
    parser.add_argument("--strict", action="store_true", help="Thorough run.")
    parser.add_argument("--enable-state-scan", dest="enable_state_scan", action="store_true", default=True)
    parser.add_argument("--skip-state-scan", dest="enable_state_scan", action="store_false")
    parser.add_argument("--enable-fs-scan", action="store_true", default=False, help="Diff filesystem changes.")
    parser.add_argument("--baseline", type=str, help="Suppress issues present in the baseline file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to stdout.")
    parser.add_argument("--log-dir", type=str, help="Persist per-run logs.")
    parser.add_argument("--allow-failures", action="store_true", help="Always exit 0 regardless of findings.")
    parser.add_argument("--max-workers", type=int, default=os.cpu_count() or 2, help="Concurrency for per-file runs.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary directories for debugging.")
    parser.add_argument("--pytest-args", type=str, help="Additional pytest arguments (quoted string).")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose diagnostic logging.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--config", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=str, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.quick:
        args.iterations = min(args.iterations, 2)
        args.shuffle_scope = "module"
        args.enable_state_scan = False
    if args.strict:
        args.iterations = max(args.iterations, 10)
        args.shuffle_scope = "node"
        args.enable_state_scan = True
        args.enable_fs_scan = True
    return args


def orchestrate(args: argparse.Namespace) -> int:
    args = normalize_args(args)
    verbose = bool(args.verbose)
    try:
        config_toml = load_config_toml(REPO_ROOT, verbose=verbose)
    except Exception as exc:
        print(f"⚠️  Failed to load configuration: {exc}", file=sys.stderr)
        return ExitCode.TOOL_ERROR.value

    random_plugin = discover_random_plugin(args.random_plugin, verbose=verbose)
    json_plugin_available = discover_json_report_plugin(verbose=verbose)
    if not random_plugin:
        print("⚠️  No randomization plugin detected; running without shuffle support.")

    pytest_args = shlex_split_optional(args.pytest_args)
    targets = args.paths or ["tests"]
    log_dir = Path(args.log_dir).resolve() if args.log_dir else None
    ignore_patterns = list(DEFAULT_FS_IGNORE)
    if config_toml.get("filesystem", {}).get("ignore_patterns"):
        ignore_patterns.extend(config_toml["filesystem"]["ignore_patterns"])
    if log_dir and log_dir.is_relative_to(REPO_ROOT):
        rel = str(log_dir.relative_to(REPO_ROOT))
        ignore_patterns.append(str(Path(rel, "*")))

    try:
        baseline = Baseline.from_path(Path(args.baseline)) if args.baseline else Baseline()
    except FileNotFoundError:
        print(f"⚠️  Baseline file not found: {args.baseline}", file=sys.stderr)
        return ExitCode.TOOL_ERROR.value
    except ValueError as exc:
        print(f"⚠️  Invalid baseline file: {exc}", file=sys.stderr)
        return ExitCode.TOOL_ERROR.value
    keep_temp = bool(args.keep_temp)

    seeds = list(DEFAULT_SEEDS)
    while len(seeds) < args.iterations:
        seeds.extend(seeds)
    seeds = seeds[: args.iterations]

    random_runs: List[RandomRunResult] = []

    print("🔍 Test Isolation Check")
    print("=====================================================================")
    print()
    print(f"Running {args.iterations} iterations with random ordering...")
    for idx, seed in enumerate(seeds, start=1):
        config = {
            "targets": targets,
            "pytest_args": pytest_args,
            "random_plugin": random_plugin,
            "seed": seed if random_plugin else None,
            "shuffle_scope": args.shuffle_scope,
            "json_report": json_plugin_available,
            "enable_state_scan": args.enable_state_scan,
            "enable_fs_scan": args.enable_fs_scan,
            "ignore_patterns": ignore_patterns,
            "keep_temp": keep_temp,
        }
        outcome = subprocess_run_worker(config)
        random_runs.append(RandomRunResult(seed=seed if random_plugin else None, shuffle_scope=args.shuffle_scope, outcome=outcome))
        status_symbol = "✓" if outcome.exit_code == 0 else "✗"
        failure_count = len(outcome.failures) + len(outcome.errors)
        message = f"  {status_symbol} Seed {seed}: "
        message += "All tests passed" if failure_count == 0 else f"{failure_count} failure(s)"
        print(message)
        write_log(log_dir, f"phaseA_seed{seed}", outcome.stdout, outcome.stderr)

    print()

    order_issues = summarize_random_runs(random_runs, verbose=verbose)
    baseline_failures_by_file: Dict[str, Set[str]] = {}
    reference_run = next((run for run in random_runs if run.outcome.exit_code == 0), random_runs[0] if random_runs else None)
    if reference_run:
        for nodeid in reference_run.outcome.failed_nodeids():
            parts = nodeid.split("::", 1)
            file_path = parts[0]
            baseline_failures_by_file.setdefault(file_path, set()).add(nodeid)
        for collected_file in reference_run.outcome.files:
            baseline_failures_by_file.setdefault(collected_file, set())
        collected_files = reference_run.outcome.files
    else:
        collected_files = []

    print("Checking file isolation...")
    file_results: List[FileIsolationResult] = []
    max_workers = max(1, int(args.max_workers))
    if collected_files:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for file_path in collected_files:
                config = {
                    "targets": [file_path],
                    "pytest_args": pytest_args,
                    "random_plugin": None,
                    "seed": None,
                    "shuffle_scope": args.shuffle_scope,
                    "json_report": json_plugin_available,
                    "enable_state_scan": args.enable_state_scan,
                    "enable_fs_scan": args.enable_fs_scan,
                    "ignore_patterns": ignore_patterns,
                    "keep_temp": keep_temp,
                }
                futures[executor.submit(subprocess_run_worker, config)] = file_path
            for future in as_completed(futures):
                file_path = futures[future]
                outcome = future.result()
                symbol = "✓" if outcome.exit_code == 0 else "✗"
                print(f"  {symbol} {file_path} - {'Isolated OK' if outcome.exit_code == 0 else 'Isolation issue'}")
                write_log(log_dir, f"phaseB_{file_path}", outcome.stdout, outcome.stderr)
                file_results.append(FileIsolationResult(file_path=file_path, outcome=outcome))
    else:
        print("  ⚠️  Unable to determine collected files; skipping per-file isolation.")

    print()

    file_issues = summarize_file_isolation(file_results, baseline_failures_by_file)
    pollution_issues = summarize_pollution(file_results)

    all_issues = []
    for issue in order_issues + file_issues + pollution_issues:
        if baseline.allows(issue.key):
            all_issues.append(issue)

    for issue in all_issues:
        print(f"⚠️  {issue.description}")

    if not all_issues:
        print("✅ No isolation issues detected.")

    if args.json:
        json_payload = {
            "random_runs": [
                {
                    "seed": run.seed,
                    "shuffle_scope": run.shuffle_scope,
                    "exit_code": run.outcome.exit_code,
                    "failures": [dataclasses.asdict(entry) for entry in run.outcome.failures],
                    "errors": [dataclasses.asdict(entry) for entry in run.outcome.errors],
                    "duration_s": run.outcome.duration_s,
                }
                for run in random_runs
            ],
            "issues": [
                {"key": issue.key, "description": issue.description, "details": issue.details}
                for issue in all_issues
            ],
        }
        print(json.dumps(json_payload, indent=2))

    return ExitCode.ISSUES_FOUND.value if (all_issues and not args.allow_failures) else ExitCode.CLEAN.value


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.worker:
        if not (args.config and args.result):
            raise SystemExit("Worker mode requires --config and --result")
        return worker_entry(args.config, args.result)
    return orchestrate(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
