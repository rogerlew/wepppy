# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Author: Roger Lew (rogerlew@gmail.com)

"""
`wepp_runner` a Python wrapper for running WEPP simulations.

============================================================================

This module provides functions for running WEPP simulations for hillslopes, flowpaths, and watersheds
with continuous, single storm (ss), and batch single storm (ss_batch) climates.

### General workflow for running WEPP simulations:
0. assumes you already have p<wepp_id>.sol, p<wepp_id>.cli, p<wepp_id>.slp, and p<wepp_id>.man
   files in the runs_dir

1. generate the hillslope .run files using one of the `make*_hillslope_run` functions
2. run the hillslope simulations using `run_hillslope`, `run_ss_hillslope`, or `run_ss_batch_hillslope`
3. generate the watershed .run file using one of the `make*_watershed_run` functions
4. run the watershed simulation using `run_watershed` or `run_ss_batch_watershed`

The module is implemented in a manner that allows for parallel execution of the hillslope simulations
using the `concurrent.futures.ThreadPoolExecutor`

### Flowpaths
support for continuous and single storm flowpath simulations
flowpaths are independent from the hillslope/watershed simulations and WEPP does not support watershed 
routing of flowpaths.

### `*_relpath`s for hillslope running functions
wepp.cloud has an Omni functionality that builds scenarios as child projects within a parent.
The `make*_hillslope_run` functions have optional arguments to specify relative paths to the
management, climate, slope, and soil files from the runs_dir. This embeds the relative paths
in the .run files so that wepp can find files from the parent project. This prevents the climates,
and slopes from being copied into each child project.

### `make_watershed_omni_contrasts_run`
This supports mix and matching the hillslope outputs from different sibling and parent projects for
watershed simulations. The `wepp_path_ids` is a list of relative paths to the hillslope pass files
with the wepp_id included (without the .pass.dat). 
  e.g. ['H1', '../../<scenario>/wepp/output/H2', 'H3', 'H4', ...]
"""

import os
import errno
import hashlib
import json
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
import random
import math
import re
import sys
import threading

from glob import glob

_IS_WINDOWS = os.name == 'nt'

from time import monotonic, sleep, time

import subprocess

from .status_messenger import StatusMessenger

__all__ = [
    "wepp_bin_dir",
    "linux_wepp_bin_opts",
    "get_linux_wepp_bin_opts",
    "make_flowpath_run",
    "make_ss_flowpath_run",
    "make_hillslope_run",
    "make_ss_hillslope_run",
    "make_ss_batch_hillslope_run",
    "run_ss_batch_hillslope",
    "run_hillslope",
    "run_flowpath",
    "make_watershed_omni_contrasts_run",
    "make_watershed_run",
    "make_ss_watershed_run",
    "make_ss_batch_watershed_run",
    "run_watershed",
    "run_ss_batch_watershed",
]

# rq worker-pool -n 4 run_ss_batch_hillslope run_hillslope run_flowpath run_watershed run_ss_batch_watershed

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")

wepp_bin_dir = os.path.abspath(_join(_thisdir, "bin"))

def _compute_linux_wepp_bin_opts():
    opts = glob(_join(wepp_bin_dir, "wepp_*"))
    opts = [_split(p)[1] for p in opts]
    opts = [p for p in opts if '.' not in p]
    opts = [p for p in opts if not p.endswith('_hill')]
    opts.append('latest')
    opts.sort()
    return opts

# this is a list of available linux wepp binaries that can be specified for wepp_bin argument
linux_wepp_bin_opts = _compute_linux_wepp_bin_opts()

_HILLSLOPE_INPUT_WAIT_S_DEFAULT = 30.0
_HILLSLOPE_INPUT_WAIT_POLL_S_DEFAULT = 0.25

_EXPECTED_ELF_INTERPRETER = "/lib64/ld-linux-x86-64.so.2"
_ALLOWED_LIBRARY_PREFIXES = ("/lib/", "/lib64/", "/usr/lib/", "/usr/lib64/")
_BANNED_RUNTIME_PATHS_PATTERN = re.compile(
    r"(/home/linuxbrew/\.linuxbrew/lib/ld\.so|/opt/homebrew/|/home/\S*/miniconda\S*/|/home/\S*/miniforge\S*/)"
)
_SKIP_RUNTIME_CHECK_ENV_VAR = "WEPP_RUNNER_SKIP_BINARY_PROVENANCE_CHECK"
_PROVENANCE_OK_BINARY_PATHS = set()
_BINARY_IDENTITY_CACHE = {}
_BINARY_IDENTITY_CHUNK_BYTES = 1024 * 1024
_BINARY_RELEASE_METADATA_CACHE = {}
_BINARY_PROMPT_CONTRACT_CACHE = {}

PASS_FAMILY_LEGACY_ASCII = "legacy_ascii"
PASS_FAMILY_HBP = "hbp"
PASS_FAMILY_CHOICES = {PASS_FAMILY_LEGACY_ASCII, PASS_FAMILY_HBP}
_HBP_METADATA_SCHEMA = "wepp-binary-release-metadata-v1"
_INVALID_PROCESS_HBP_SUFFIXES = (".pass.hbp", ".pass.dat.hbp")
_SKIP_TEMPLATE_LINE = "__WEPP_RUNNER_SKIP_LINE__"

_DSTATE_WATCHDOG_ENABLED_ENV = "WEPP_RUNNER_DSTATE_WATCHDOG_ENABLED"
_DSTATE_WATCHDOG_INTERVAL_ENV = "WEPP_RUNNER_DSTATE_WATCHDOG_INTERVAL_S"
_DSTATE_WATCHDOG_THRESHOLD_ENV = "WEPP_RUNNER_DSTATE_WATCHDOG_THRESHOLD_S"
_DSTATE_WATCHDOG_MAX_EVENTS_ENV = "WEPP_RUNNER_DSTATE_WATCHDOG_MAX_EVENTS"
_DSTATE_WATCHDOG_INTERVAL_S_DEFAULT = 30.0
_DSTATE_WATCHDOG_THRESHOLD_S_DEFAULT = 180.0
_DSTATE_WATCHDOG_MAX_EVENTS_DEFAULT = 3


def get_linux_wepp_bin_opts():
    """Return the current linux WEPP binaries available on disk."""
    return _compute_linux_wepp_bin_opts()


def _normalize_pass_family(pass_family):
    if pass_family is None:
        return PASS_FAMILY_LEGACY_ASCII
    normalized = str(pass_family).strip().lower()
    if normalized not in PASS_FAMILY_CHOICES:
        options = ", ".join(sorted(PASS_FAMILY_CHOICES))
        raise ValueError(f"Unsupported pass_family '{pass_family}'. Expected one of: {options}")
    return normalized


def _pass_suffix(pass_family):
    normalized = _normalize_pass_family(pass_family)
    if normalized == PASS_FAMILY_HBP:
        return ".hbp"
    return ".pass.dat"


def _is_invalid_process_hbp_name(path_text):
    lowered = str(path_text).lower()
    return any(lowered.endswith(suffix) for suffix in _INVALID_PROCESS_HBP_SUFFIXES)


def _coerce_omni_pass_path(wepp_id_path, pass_family):
    normalized_family = _normalize_pass_family(pass_family)
    path_text = str(wepp_id_path)
    lowered = path_text.lower()

    if normalized_family == PASS_FAMILY_LEGACY_ASCII:
        if lowered.endswith(".pass.dat"):
            return path_text
        if lowered.endswith(".hbp"):
            if _is_invalid_process_hbp_name(path_text):
                raise ValueError(
                    "Invalid process HBP name. Use H*.hbp and reject H*.pass.hbp / H*.pass.dat.hbp."
                )
            raise ValueError("legacy_ascii pass_family requires H*.pass.dat pass paths.")
        return f"{path_text}.pass.dat"

    if _is_invalid_process_hbp_name(path_text):
        raise ValueError(
            "Invalid process HBP name. Use H*.hbp and reject H*.pass.hbp / H*.pass.dat.hbp."
        )
    if lowered.endswith(".pass"):
        raise ValueError(
            "Invalid process HBP name. Use H*.hbp and reject H*.pass.hbp / H*.pass.dat.hbp."
        )
    if lowered.endswith(".hbp"):
        return path_text
    if lowered.endswith(".pass.dat"):
        return f"{path_text[:-len('.pass.dat')]}.hbp"
    return f"{path_text}.hbp"


def _resolve_binary_for_role(wepp_bin, *, prefer_hill):
    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=prefer_hill)
    if isinstance(cmd, (list, tuple)):
        return os.path.abspath(cmd[0])
    return os.path.abspath(cmd)


def _binary_sidecar_path(binary_path):
    return f"{binary_path}.json"


def _load_binary_release_metadata(binary_path):
    sidecar_path = _binary_sidecar_path(os.path.abspath(binary_path))
    if sidecar_path in _BINARY_RELEASE_METADATA_CACHE:
        return _BINARY_RELEASE_METADATA_CACHE[sidecar_path]

    if not _exists(sidecar_path):
        _BINARY_RELEASE_METADATA_CACHE[sidecar_path] = None
        return None

    try:
        with open(sidecar_path, encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f'Invalid WEPP release metadata sidecar "{sidecar_path}": {exc}'
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(f'Invalid WEPP release metadata sidecar "{sidecar_path}": expected JSON object')
    if data.get("schema") != _HBP_METADATA_SCHEMA:
        raise RuntimeError(
            f'Invalid WEPP release metadata sidecar "{sidecar_path}": '
            f'expected schema "{_HBP_METADATA_SCHEMA}"'
        )

    _BINARY_RELEASE_METADATA_CACHE[sidecar_path] = data
    return data


def _sidecar_hbp_supported(metadata):
    features = metadata.get("features")
    if not isinstance(features, dict):
        return False
    return features.get("hbp_supported") is True


def _mode2_master_pass_prompt_required(metadata):
    if not isinstance(metadata, dict):
        return True
    features = metadata.get("features")
    if not isinstance(features, dict):
        return True
    value = features.get("mode2_master_pass_prompt_required")
    if isinstance(value, bool):
        return value
    return True


def _assert_hbp_supported_binary(binary_path, *, role):
    metadata = _load_binary_release_metadata(binary_path)
    sidecar_path = _binary_sidecar_path(binary_path)
    if metadata is None:
        raise RuntimeError(
            f'HBP pass_family requested but {role} WEPP binary sidecar is missing: {sidecar_path}. '
            "Sidecar absence defaults to legacy/no-HBP."
        )
    if not _sidecar_hbp_supported(metadata):
        raise RuntimeError(
            f'HBP pass_family requested but {role} WEPP binary sidecar does not declare '
            f"features.hbp_supported=true: {sidecar_path}"
        )


def _assert_pass_family_release_support(pass_family, *, wepp_bin):
    normalized = _normalize_pass_family(pass_family)
    if normalized != PASS_FAMILY_HBP:
        return normalized

    watershed_binary = _resolve_binary_for_role(wepp_bin, prefer_hill=False)
    hillslope_binary = _resolve_binary_for_role(wepp_bin, prefer_hill=True)
    checked = {}
    checked[watershed_binary] = "watershed"
    checked[hillslope_binary] = "hillslope"
    for path, role in checked.items():
        _assert_hbp_supported_binary(path, role=role)
    return normalized


def _uses_modern_watershed_prompt_contract(*, wepp_bin):
    watershed_binary = _resolve_binary_for_role(wepp_bin, prefer_hill=False)
    cache_key = os.path.abspath(watershed_binary)
    if cache_key in _BINARY_PROMPT_CONTRACT_CACHE:
        return _BINARY_PROMPT_CONTRACT_CACHE[cache_key]

    metadata = _load_binary_release_metadata(watershed_binary)
    modern = bool(metadata and _sidecar_hbp_supported(metadata))
    _BINARY_PROMPT_CONTRACT_CACHE[cache_key] = modern
    return modern


def _watershed_prompt_contract_lines(*, wepp_bin):
    watershed_binary = _resolve_binary_for_role(wepp_bin, prefer_hill=False)
    metadata = _load_binary_release_metadata(watershed_binary)

    master_pass_file = "../output/pass_pw0.txt"
    if not _mode2_master_pass_prompt_required(metadata):
        master_pass_file = _SKIP_TEMPLATE_LINE

    if metadata and _sidecar_hbp_supported(metadata):
        return {
            "master_pass_file": master_pass_file,
            "initial_condition_output_file": _SKIP_TEMPLATE_LINE,
            "impoundment_output": "No",
            "impoundment_data_file": "pw0.imp",
        }

    # Legacy binaries consume an initial-condition filename slot even when
    # scenario output is disabled and do not prompt for impoundment output/data.
    return {
        "master_pass_file": master_pass_file,
        "initial_condition_output_file": "../output/initcond_pw0.txt",
        "impoundment_output": _SKIP_TEMPLATE_LINE,
        "impoundment_data_file": _SKIP_TEMPLATE_LINE,
    }


def _drop_template_skip_lines(text):
    lines = []
    for line in text.splitlines():
        if line.strip() == _SKIP_TEMPLATE_LINE:
            continue
        lines.append(line)
    return "\n".join(lines)


def _run_text_command(args):
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _env_bool_or_default(name, default):
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int_or_default(name, default, *, min_value=None):
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if min_value is not None and value < min_value:
        return default
    return value


def _trace_quote(value):
    text = str(value)
    text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{text}"'


def _cmd_text(cmd):
    return " ".join(str(arg) for arg in cmd)


def _collect_binary_identity(binary_path):
    requested_path = os.path.abspath(binary_path)
    resolved_path = os.path.realpath(requested_path)
    try:
        stat_result = os.stat(resolved_path)
    except OSError as exc:
        return {
            "binary_path": resolved_path,
            "binary_sha256": "<unavailable>",
            "binary_size_bytes": "<unavailable>",
            "binary_mtime_ns": "<unavailable>",
            "binary_identity_status": "unavailable",
            "binary_identity_error": (
                f"{exc.__class__.__name__}:errno={exc.errno}:strerror={exc.strerror}"
            ),
        }

    cache_key = (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )
    cached = _BINARY_IDENTITY_CACHE.get(resolved_path)
    if cached is not None and cached.get("cache_key") == cache_key:
        return dict(cached["identity"])

    identity = {
        "binary_path": resolved_path,
        "binary_sha256": "<unavailable>",
        "binary_size_bytes": "<unavailable>",
        "binary_mtime_ns": "<unavailable>",
        "binary_identity_status": "unavailable",
        "binary_identity_error": "",
    }

    try:
        digest = hashlib.sha256()
        with open(resolved_path, "rb") as fp:
            while True:
                chunk = fp.read(_BINARY_IDENTITY_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        identity["binary_identity_error"] = (
            f"{exc.__class__.__name__}:errno={exc.errno}:strerror={exc.strerror}"
        )
    else:
        identity.update(
            {
                "binary_sha256": digest.hexdigest(),
                "binary_size_bytes": stat_result.st_size,
                "binary_mtime_ns": stat_result.st_mtime_ns,
                "binary_identity_status": "ok",
            }
        )
        _BINARY_IDENTITY_CACHE[resolved_path] = {
            "cache_key": cache_key,
            "identity": dict(identity),
        }

    return dict(identity)


def _format_binary_identity_fields(identity):
    return (
        f'binary_path={_trace_quote(identity["binary_path"])} '
        f'binary_sha256={identity["binary_sha256"]} '
        f'binary_size_bytes={identity["binary_size_bytes"]} '
        f'binary_mtime_ns={identity["binary_mtime_ns"]} '
        f'binary_identity_status={identity["binary_identity_status"]} '
        f'binary_identity_error={_trace_quote(identity["binary_identity_error"])}'
    )


def _write_binary_identity_trace(log, runner_name, binary_path):
    identity = _collect_binary_identity(binary_path)
    log.write(f'[{runner_name}] binary_identity {_format_binary_identity_fields(identity)}\n')
    log.flush()


def _binary_provenance_error(binary_path, reason):
    return RuntimeError(
        f'WEPP binary runtime provenance check failed for "{binary_path}": {reason}. '
        f"Rebuild with /usr/bin/gfortran and run tools/check_wepp_binary_provenance.sh on the candidate binary. "
        f"Break-glass override only: set {_SKIP_RUNTIME_CHECK_ENV_VAR}=1."
    )


def _runtime_path_is_allowed(path):
    return path.startswith(_ALLOWED_LIBRARY_PREFIXES)


def _extract_elf_interpreter(readelf_program_headers):
    match = re.search(
        r"Requesting program interpreter:\s*(.*?)\]",
        readelf_program_headers,
        flags=re.MULTILINE,
    )
    if not match:
        return ""
    return match.group(1).strip()


def _extract_rpath_entries(readelf_dynamic_tags):
    entries = []
    for match in re.finditer(r"\((?:RPATH|RUNPATH)\).*?\[(.*?)\]", readelf_dynamic_tags):
        blob = match.group(1).strip()
        if not blob:
            continue
        entries.extend(path.strip() for path in blob.split(":") if path.strip())
    return entries


def _extract_resolved_ldd_paths(ldd_output):
    resolved_paths = []
    for line in ldd_output.splitlines():
        match = re.search(r"=>\s+(\S+)\s+\(", line)
        if match:
            resolved_paths.append(match.group(1))
    return resolved_paths


def _extract_libgfortran_paths(ldd_output):
    resolved_paths = []
    for line in ldd_output.splitlines():
        if "libgfortran" not in line:
            continue
        match = re.search(r"=>\s+(\S+)\s+\(", line)
        if match:
            resolved_paths.append(match.group(1))
    return resolved_paths


def _assert_binary_runtime_provenance(binary_path):
    if _IS_WINDOWS:
        return

    binary_path = os.path.abspath(binary_path)

    if os.getenv(_SKIP_RUNTIME_CHECK_ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    if binary_path in _PROVENANCE_OK_BINARY_PATHS:
        return

    if not _exists(binary_path):
        raise FileNotFoundError(f"WEPP binary does not exist: {binary_path}")
    if not os.access(binary_path, os.X_OK):
        raise PermissionError(f"WEPP binary is not executable: {binary_path}")

    try:
        readelf_program_headers = _run_text_command(["readelf", "-l", binary_path])
    except FileNotFoundError as exc:
        raise _binary_provenance_error(binary_path, "required tool readelf is not available") from exc
    if readelf_program_headers.returncode != 0:
        stderr = (readelf_program_headers.stderr or "").strip() or "<no stderr>"
        raise _binary_provenance_error(binary_path, f"readelf -l failed ({stderr})")

    interpreter = _extract_elf_interpreter(readelf_program_headers.stdout or "")
    missing_interpreter = not interpreter
    if interpreter:
        if interpreter != _EXPECTED_ELF_INTERPRETER:
            raise _binary_provenance_error(
                binary_path,
                f"unexpected ELF interpreter {interpreter}; expected {_EXPECTED_ELF_INTERPRETER}",
            )
        if _BANNED_RUNTIME_PATHS_PATTERN.search(interpreter):
            raise _binary_provenance_error(binary_path, f"interpreter path is blocked by policy ({interpreter})")

    try:
        readelf_dynamic = _run_text_command(["readelf", "-d", binary_path])
    except FileNotFoundError as exc:
        raise _binary_provenance_error(binary_path, "required tool readelf is not available") from exc
    if readelf_dynamic.returncode == 0:
        for runtime_path in _extract_rpath_entries(readelf_dynamic.stdout or ""):
            if _BANNED_RUNTIME_PATHS_PATTERN.search(runtime_path):
                raise _binary_provenance_error(
                    binary_path,
                    f"RPATH/RUNPATH includes blocked path ({runtime_path})",
                )
            if not _runtime_path_is_allowed(runtime_path):
                raise _binary_provenance_error(
                    binary_path,
                    f"RPATH/RUNPATH includes non-system path ({runtime_path})",
                )

    try:
        ldd_result = _run_text_command(["ldd", binary_path])
    except FileNotFoundError as exc:
        raise _binary_provenance_error(binary_path, "required tool ldd is not available") from exc
    ldd_output = "\n".join(
        part.strip() for part in ((ldd_result.stdout or ""), (ldd_result.stderr or "")) if part.strip()
    )
    is_static_binary = "not a dynamic executable" in ldd_output
    if ldd_result.returncode != 0 and not is_static_binary:
        raise _binary_provenance_error(binary_path, f"ldd failed ({ldd_output or '<no output>'})")
    if missing_interpreter and not is_static_binary:
        raise _binary_provenance_error(binary_path, "missing ELF interpreter entry")

    if not is_static_binary and _BANNED_RUNTIME_PATHS_PATTERN.search(ldd_output):
        raise _binary_provenance_error(binary_path, "ldd output includes blocked Homebrew/Conda runtime paths")

    resolved_paths = _extract_resolved_ldd_paths(ldd_output)
    for resolved in resolved_paths:
        if not is_static_binary and not _runtime_path_is_allowed(resolved):
            raise _binary_provenance_error(
                binary_path,
                f"ldd resolved non-system dependency path ({resolved})",
            )

    if not is_static_binary:
        libgfortran_paths = _extract_libgfortran_paths(ldd_output)
        if not libgfortran_paths:
            raise _binary_provenance_error(binary_path, "ldd did not resolve libgfortran")
        for libgfortran_path in libgfortran_paths:
            if not _runtime_path_is_allowed(libgfortran_path):
                raise _binary_provenance_error(
                    binary_path,
                    f"libgfortran resolved outside system paths ({libgfortran_path})",
                )

    _PROVENANCE_OK_BINARY_PATHS.add(binary_path)


def _resolve_wepp_cmd(wepp_bin, *, prefer_hill):
    if wepp_bin is not None:
        hill_candidate = os.path.abspath(_join(wepp_bin_dir, f"{wepp_bin}_hill"))
        plain_candidate = os.path.abspath(_join(wepp_bin_dir, wepp_bin))
        selected_binary = hill_candidate if prefer_hill and _exists(hill_candidate) else plain_candidate
    else:
        selected_binary = os.path.abspath(_wepp)

    _assert_binary_runtime_provenance(selected_binary)
    return [selected_binary]


def _env_float_or_default(name, default, *, min_value=None):
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if not math.isfinite(value):
        return default
    if min_value is not None and value < min_value:
        return default
    return value


def _linux_proc_available():
    return not _IS_WINDOWS and _exists("/proc")


def _read_linux_process_state(pid):
    with open(f"/proc/{pid}/status", encoding="ascii") as fp:
        for line in fp:
            if line.startswith("State:"):
                fields = line.split()
                if len(fields) >= 2:
                    return fields[1]
                return ""
    return ""


def _dstate_watchdog_config():
    default_enabled = _linux_proc_available()
    enabled = _env_bool_or_default(_DSTATE_WATCHDOG_ENABLED_ENV, default_enabled)
    if not enabled or not default_enabled:
        return {
            "enabled": False,
            "interval_s": _DSTATE_WATCHDOG_INTERVAL_S_DEFAULT,
            "threshold_s": _DSTATE_WATCHDOG_THRESHOLD_S_DEFAULT,
            "max_events": _DSTATE_WATCHDOG_MAX_EVENTS_DEFAULT,
        }

    return {
        "enabled": True,
        "interval_s": _env_float_or_default(
            _DSTATE_WATCHDOG_INTERVAL_ENV,
            _DSTATE_WATCHDOG_INTERVAL_S_DEFAULT,
            min_value=0.1,
        ),
        "threshold_s": _env_float_or_default(
            _DSTATE_WATCHDOG_THRESHOLD_ENV,
            _DSTATE_WATCHDOG_THRESHOLD_S_DEFAULT,
            min_value=0.0,
        ),
        "max_events": _env_int_or_default(
            _DSTATE_WATCHDOG_MAX_EVENTS_ENV,
            _DSTATE_WATCHDOG_MAX_EVENTS_DEFAULT,
            min_value=0,
        ),
    }


class _DStateWatchdog:
    def __init__(
        self,
        *,
        runner_name,
        pid,
        log,
        runs_dir,
        run_file,
        err_file,
        cmd_text,
        interval_s,
        threshold_s,
        max_events,
        state_reader=_read_linux_process_state,
        clock=monotonic,
    ):
        self.runner_name = runner_name
        self.pid = pid
        self.log = log
        self.runs_dir = runs_dir
        self.run_file = run_file
        self.err_file = err_file
        self.cmd_text = cmd_text
        self.interval_s = interval_s
        self.threshold_s = threshold_s
        self.max_events = max_events
        self.state_reader = state_reader
        self.clock = clock
        self.dstate_started_at = None
        self.last_emit_at = None
        self.event_count = 0
        self.disabled = max_events == 0
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self.disabled:
            return self
        self._thread = threading.Thread(
            target=self._run,
            name=f"wepp-runner-dstate-watchdog-{self.pid}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=min(max(self.interval_s, 0.1), 1.0))

    def _run(self):
        while not self._stop_event.wait(self.interval_s):
            self.poll_once()

    def poll_once(self, now=None):
        if self.disabled:
            return False

        now = self.clock() if now is None else now
        try:
            state = self.state_reader(self.pid)
        except OSError:
            # /proc entries can disappear as the child exits; the watchdog is advisory only.
            self.disabled = True
            return False

        if state != "D":
            self.dstate_started_at = None
            return False

        if self.dstate_started_at is None:
            self.dstate_started_at = now
            return False

        duration_s = now - self.dstate_started_at
        if duration_s < self.threshold_s:
            return False
        if self.event_count >= self.max_events:
            return False
        if self.last_emit_at is not None and now - self.last_emit_at < self.threshold_s:
            return False

        self.event_count += 1
        self.last_emit_at = now
        line = (
            f'[{self.runner_name}] dstate_watchdog pid={self.pid} state=D '
            f'duration={duration_s:.2f}s threshold={self.threshold_s:.2f}s '
            f'interval={self.interval_s:.2f}s event={self.event_count}/{self.max_events} '
            f'runs_dir={_trace_quote(self.runs_dir)} run_file={_trace_quote(self.run_file)} '
            f'err_file={_trace_quote(self.err_file)} cmd={_trace_quote(self.cmd_text)}'
        )
        try:
            self.log.write(line + "\n")
            self.log.flush()
        except OSError:
            self.disabled = True
            return False
        return True


class _DisabledDStateWatchdog:
    def start(self):
        return self

    def stop(self):
        return None


def _start_dstate_watchdog(runner_name, process, log, *, runs_dir, run_file, err_file, cmd_text):
    pid = getattr(process, "pid", None)
    if pid is None:
        return _DisabledDStateWatchdog()

    config = _dstate_watchdog_config()
    if not config["enabled"]:
        return _DisabledDStateWatchdog()

    return _DStateWatchdog(
        runner_name=runner_name,
        pid=pid,
        log=log,
        runs_dir=runs_dir,
        run_file=run_file,
        err_file=err_file,
        cmd_text=cmd_text,
        interval_s=config["interval_s"],
        threshold_s=config["threshold_s"],
        max_events=config["max_events"],
    ).start()


def _classify_close_path_error(exc):
    if isinstance(exc, OSError):
        stale_errno = getattr(errno, "ESTALE", 116)
        if exc.errno == stale_errno:
            return "stale_file_handle"
        if exc.errno is not None:
            return f"os_error_errno_{exc.errno}"
        return "os_error"
    return exc.__class__.__name__


def _emit_close_path_failure(runner_name, *, stream_name, path, exc, log=None):
    classification = _classify_close_path_error(exc)
    errno_value = getattr(exc, "errno", None)
    line = (
        f'[{runner_name}] close_path_failure stream={stream_name} '
        f'path={_trace_quote(path)} classification={classification} '
        f'errno={errno_value} error={_trace_quote(exc)}'
    )
    if log is not None and not getattr(log, "closed", False):
        try:
            log.write(line + "\n")
            log.flush()
        except OSError:
            # Keep the original close-path failure as the canonical exception.
            pass
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except OSError:
        # There is no safer fallback sink from this cleanup boundary.
        pass


def _close_stream_with_diagnostics(stream, runner_name, *, stream_name, path, log=None):
    if stream is None:
        return
    try:
        stream.close()
    except OSError as exc:
        _emit_close_path_failure(
            runner_name,
            stream_name=stream_name,
            path=path,
            exc=exc,
            log=log,
        )
        raise


def _wait_for_required_files(paths, *, timeout_s, poll_s):
    deadline = monotonic() + timeout_s
    for path in paths:
        while not _exists(path):
            if monotonic() >= deadline:
                raise FileNotFoundError(
                    f"Required WEPP hillslope input file was not available within {timeout_s:.2f}s: {path}"
                )
            sleep(poll_s)

if _IS_WINDOWS:
    _wepp = _join(wepp_bin_dir, "wepp2014.exe")
else:
    _wepp = _join(wepp_bin_dir, "wepp")


def _template_loader(fn):
    global _template_dir

    with open(_join(_template_dir, fn)) as fp:
        _template = fp.readlines()

        # the watershedslope.template contains comments.
        # here we strip those out
        _template = [L[:L.find('#')] for L in _template]
        _template = [L.strip() for L in _template]
        _template = '\n'.join(_template)

    return _template


def _ss_hill_template_loader():
    return _template_loader("ss_hillslope.template")

def _ss_batch_hill_template_loader():
    return _template_loader("ss_batch_hillslope.template")


def _hill_template_loader():
    return _template_loader("hillslope.template")

def _reveg_hill_template_loader():
    return _template_loader("reveg_hillslope.template")


def _ss_flowpath_template_loader():
    return _template_loader("ss_flowpath.template")


def _flowpath_template_loader():
    return _template_loader("flowpath.template")


def _watershed_template_loader():
    return _template_loader("watershed.template")


def _ss_watershed_template_loader():
    return _template_loader("ss_watershed.template")


def _ss_batch_watershed_template_loader():
    return _template_loader("ss_batch_watershed.template")


def _normalize_yes_no(value):
    return "Yes" if value else "No"


def _resolve_output_flag(options, key, default):
    if not options:
        return default
    if key not in options:
        return default
    value = options.get(key)
    if value is None:
        return default
    return bool(value)



def _hillstub_omni_contrasts_template_loader(wepp_id_path, *, pass_family):
    pass_path = _coerce_omni_pass_path(wepp_id_path, pass_family)
    return f"""
M
Y
{pass_path}"""


def _hillstub_template_loader(wepp_id, *, pass_family):
    suffix = _pass_suffix(pass_family)
    return f"""
M
Y
../output/H{wepp_id}{suffix}"""


def _hillstub_ss_batch_template_loader(wepp_id, ss_batch_key, *, pass_family):
    suffix = _pass_suffix(pass_family)
    return f"""
M
Y
../output/{ss_batch_key}/H{wepp_id}{suffix}"""


def make_flowpath_run(fp, wepp_id, sim_years, fp_runs_dir):
    _fp_template = _flowpath_template_loader()

    s = _fp_template.format(fp=fp,
                            wepp_id=wepp_id,
                            sim_years=sim_years)

    fn = _join(fp_runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_flowpath_run(fp, wepp_id, runs_dir):
    _fp_template = _ss_flowpath_template_loader()

    s = _fp_template.format(fp=fp, wepp_id=wepp_id, runs_dir=os.path.abspath(runs_dir))

    fn = _join(runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_hillslope_run(wepp_id, sim_years, runs_dir, reveg=True,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                       pass_family=PASS_FAMILY_LEGACY_ASCII, wepp_bin=None):
    
    if man_relpath != '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath != '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath != '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath != '':
        assert sol_relpath.endswith('/'), sol_relpath
    
    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)

    if reveg:
        _hill_template = _reveg_hill_template_loader()
    else:
        _hill_template = _hill_template_loader()

    pass_file = f"../output/H{wepp_id}{_pass_suffix(normalized_pass_family)}"
    s = _hill_template.format(wepp_id=wepp_id,
                              sim_years=sim_years,
                              pass_file=pass_file,
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_hillslope_run(wepp_id, runs_dir,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                       pass_family=PASS_FAMILY_LEGACY_ASCII, wepp_bin=None):
    if man_relpath != '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath != '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath != '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath != '':
        assert sol_relpath.endswith('/'), sol_relpath

    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)
    _hill_template = _ss_hill_template_loader()

    pass_file = f"../output/H{wepp_id}{_pass_suffix(normalized_pass_family)}"
    s = _hill_template.format(wepp_id=wepp_id, 
                              pass_file=pass_file,
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_hillslope_run(wepp_id, runs_dir, ss_batch_key, ss_batch_id,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                       pass_family=PASS_FAMILY_LEGACY_ASCII, wepp_bin=None):
    if man_relpath != '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath != '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath != '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath != '':
        assert sol_relpath.endswith('/'), sol_relpath

    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)
    _hill_template = _ss_batch_hill_template_loader()

    pass_file = f"../output/{ss_batch_key}/H{wepp_id}{_pass_suffix(normalized_pass_family)}"
    s = _hill_template.format(wepp_id=wepp_id,
                              ss_batch_id=ss_batch_id,
                              ss_batch_key=ss_batch_key,
                              pass_file=pass_file,
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=None, ss_batch_id=None, status_channel=None, 
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    if man_relpath != '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath != '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath != '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath != '':
        assert sol_relpath.endswith('/'), sol_relpath

    assert ss_batch_id is not None
    t0 = time()

    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=True)

    assert _exists(_join(runs_dir, man_relpath, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, slp_relpath, f'p{wepp_id}.slp'))
    assert _exists(_join(runs_dir, cli_relpath, f'p{wepp_id}.{ss_batch_id}.cli'))
    assert _exists(_join(runs_dir, sol_relpath, f'p{wepp_id}.sol'))

    _stderr_fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.err')
    _run = open(_join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        return True, wepp_id, time() - t0

    raise Exception('Error running wepp for wepp_id %i\nSee %s'
                    % (wepp_id, _stderr_fn))


def run_hillslope(wepp_id, runs_dir, wepp_bin=None, status_channel=None,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath='',
                  no_file_checks=False, timeout=60, timeout_retries=3):
    
    if man_relpath != '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath != '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath != '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath != '':
        assert sol_relpath.endswith('/'), sol_relpath

    t0 = time()

    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=True)

    if not no_file_checks:
        input_wait_s = _env_float_or_default(
            "WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_S",
            _HILLSLOPE_INPUT_WAIT_S_DEFAULT,
            min_value=0.0,
        )
        input_poll_s = _env_float_or_default(
            "WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_POLL_S",
            _HILLSLOPE_INPUT_WAIT_POLL_S_DEFAULT,
            min_value=0.01,
        )

        required_inputs = [
            _join(runs_dir, f'p{wepp_id}.man'),
            _join(runs_dir, f'p{wepp_id}.sol'),
            _join(runs_dir, man_relpath, f'p{wepp_id}.man'),
            _join(runs_dir, slp_relpath, f'p{wepp_id}.slp'),
            _join(runs_dir, cli_relpath, f'p{wepp_id}.cli'),
            _join(runs_dir, sol_relpath, f'p{wepp_id}.sol'),
        ]
        unique_required_inputs = list(dict.fromkeys(required_inputs))
        _wait_for_required_files(
            unique_required_inputs,
            timeout_s=input_wait_s,
            poll_s=input_poll_s,
        )

    if timeout_retries < 0:
        raise ValueError(f"timeout_retries must be >= 0 (received {timeout_retries})")

    _stderr_fn = _join(runs_dir, f'p{wepp_id}.err')
    _run_fn = _join(runs_dir, f'p{wepp_id}.run')
    _log = open(_stderr_fn, 'w')
    success = False
    total_attempts = timeout_retries + 1
    timeout_attempts = []
    last_returncode = None
    runs_dir_abs = os.path.abspath(runs_dir)
    cmd_text = _cmd_text(cmd)
    backoff_base_seconds = 0.5
    backoff_cap_seconds = 5.0

    def _clip_log_line(line, max_len=240):
        if len(line) <= max_len:
            return line
        return line[: max_len - 3] + "..."

    def _emit_flake_metric(final_state):
        if not status_channel or not timeout_attempts:
            return
        success_on_retry = int(success and len(timeout_attempts) > 0)
        metric_line = (
            f'metric:run_hillslope wepp_id={wepp_id} '
            f'timeout_attempts={len(timeout_attempts)} '
            f'success_on_retry={success_on_retry} '
            f'final_state={final_state}'
        )
        _log.write(f'[run_hillslope] {metric_line}\n')
        _log.flush()
        StatusMessenger.publish(status_channel, metric_line)

    try:
        _log.write(
            f'[run_hillslope] wepp_id={wepp_id} runs_dir={runs_dir_abs} run_file={_run_fn} '
            f'err_file={_stderr_fn} cmd="{cmd_text}" timeout={timeout}s '
            f'timeout_retries={timeout_retries}\n'
        )
        _write_binary_identity_trace(_log, "run_hillslope", cmd[0])
        _log.flush()

        for attempt in range(1, total_attempts + 1):
            attempt_started = time()
            _log.write(f'[run_hillslope] attempt {attempt}/{total_attempts} start\n')
            _log.flush()

            with open(_run_fn) as _run:
                p = subprocess.Popen(
                    cmd,
                    stdin=_run,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=runs_dir,
                    universal_newlines=True,
                )

                timed_out = False
                timeout_exc = None
                stdout_data = ""
                watchdog = _start_dstate_watchdog(
                    "run_hillslope",
                    p,
                    _log,
                    runs_dir=runs_dir_abs,
                    run_file=_run_fn,
                    err_file=_stderr_fn,
                    cmd_text=cmd_text,
                )
                try:
                    stdout_data, _ = p.communicate(timeout=timeout)
                except subprocess.TimeoutExpired as exc:
                    timed_out = True
                    timeout_exc = exc
                    p.kill()
                    stdout_data, _ = p.communicate()
                finally:
                    watchdog.stop()

            last_returncode = p.returncode
            output_lines = []

            for output in stdout_data.splitlines():
                output = output.strip()
                if output:
                    output_lines.append(output)
                    if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                        success = True
                    _log.write(output + '\n')
            _log.flush()

            attempt_elapsed = time() - attempt_started
            last_output = _clip_log_line(output_lines[-1]) if output_lines else '<no output>'

            if timed_out and not success:
                timeout_attempts.append(
                    {
                        "attempt": attempt,
                        "elapsed": attempt_elapsed,
                        "last_output": last_output,
                    }
                )
                _log.write(
                    f'[run_hillslope] timeout attempt={attempt}/{total_attempts} '
                    f'elapsed={attempt_elapsed:.2f}s timeout={timeout}s '
                    f'returncode={last_returncode} last_output="{last_output}"\n'
                )
                if attempt < total_attempts:
                    backoff_seconds = min(
                        backoff_cap_seconds,
                        backoff_base_seconds * (2 ** (attempt - 1)),
                    )
                    jitter_seconds = random.uniform(0.0, backoff_base_seconds)
                    delay_seconds = backoff_seconds + jitter_seconds
                    _log.write(
                        f'[run_hillslope] retrying after timeout '
                        f'(next_attempt={attempt + 1}/{total_attempts}) '
                        f'backoff={delay_seconds:.2f}s '
                        f'(base={backoff_seconds:.2f}s jitter={jitter_seconds:.2f}s)\n'
                    )
                    _log.flush()
                    sleep(delay_seconds)
                else:
                    _log.flush()

                if attempt == total_attempts:
                    _emit_flake_metric(final_state="timeout")
                    timeout_summary = "; ".join(
                        (
                            f'a{entry["attempt"]}:{entry["elapsed"]:.2f}s '
                            f'last="{entry["last_output"]}"'
                        )
                        for entry in timeout_attempts
                    )
                    raise TimeoutError(
                        f'Hillslope simulation timed out for wepp_id={wepp_id}; '
                        f'runs_dir={runs_dir_abs}; run_file={_run_fn}; err_file={_stderr_fn}; '
                        f'cmd="{cmd_text}"; timeout={timeout}s; attempts={total_attempts}; '
                        f'timeout_summary=[{timeout_summary}]'
                    ) from timeout_exc
                continue

            if success:
                if timeout_attempts:
                    _log.write(
                        f'[run_hillslope] flake_detected wepp_id={wepp_id} '
                        f'timeout_attempts={len(timeout_attempts)} '
                        f'success_attempt={attempt}/{total_attempts}\n'
                    )
                    _log.flush()
                    _emit_flake_metric(final_state="success")
                break

            _log.write(
                f'[run_hillslope] attempt {attempt}/{total_attempts} finished without success marker '
                f'returncode={last_returncode}\n'
            )
            _log.flush()
            break
    finally:
        _log.close()

    if success:
        return True, wepp_id, time() - t0

    raise Exception(
        f'Error running WEPP hillslope for wepp_id={wepp_id}; runs_dir={runs_dir_abs}; '
        f'run_file={_run_fn}; err_file={_stderr_fn}; cmd="{cmd_text}"; '
        f'returncode={last_returncode}'
    )


def run_flowpath(fp_id, wepp_id, runs_dir, fp_runs_dir, wepp_bin=None, status_channel=None):
    t0 = time()

    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=True)

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(fp_runs_dir, f'{fp_id}.slp'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.cli'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    _stderr_fn = _join(fp_runs_dir, f'{fp_id}.err')
    _run = open(_join(fp_runs_dir, f'{fp_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=fp_runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        #os.remove(_join(fp_runs_dir, f'{fp_id}.slp'))
        os.remove(_join(fp_runs_dir, f'{fp_id}.run'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.loss.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.loss.dat'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.single_event.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.single_event.dat'))
        os.remove(_stderr_fn)
        return True, fp_id, time() - t0

    raise Exception(f'Error running wepp for {fp_id}\nSee {_stderr_fn}')


def make_watershed_omni_contrasts_run(
    sim_years,
    wepp_path_ids,
    runs_dir,
    *,
    output_options=None,
    pass_family=PASS_FAMILY_LEGACY_ASCII,
    wepp_bin=None,
):
    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)

    block = []
    for wepp_path_id in wepp_path_ids:
        block.append(
            _hillstub_omni_contrasts_template_loader(
                wepp_path_id,
                pass_family=normalized_pass_family,
            )
        )
    block = ''.join(block)

    _watershed_template = _watershed_template_loader()

    water_balance_output = _normalize_yes_no(_resolve_output_flag(output_options, "chnwb", False))
    soil_output = _normalize_yes_no(_resolve_output_flag(output_options, "soil_pw0", False))
    plot_output = _normalize_yes_no(_resolve_output_flag(output_options, "plot_pw0", False))
    event_output = _normalize_yes_no(_resolve_output_flag(output_options, "ebe_pw0", True))
    loss_output_option = 1
    contract_lines = _watershed_prompt_contract_lines(wepp_bin=wepp_bin)

    s = _watershed_template.format(sub_n=len(wepp_path_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years,
                                   soil_loss_output_option=loss_output_option,
                                   master_pass_file=contract_lines["master_pass_file"],
                                   water_balance_output=water_balance_output,
                                   soil_output=soil_output,
                                   plot_output=plot_output,
                                   event_output=event_output,
                                   initial_condition_output_file=contract_lines["initial_condition_output_file"],
                                   impoundment_output=contract_lines["impoundment_output"],
                                   impoundment_data_file=contract_lines["impoundment_data_file"])
    s = _drop_template_skip_lines(s)

    disabled_outputs = set()
    if water_balance_output == "No":
        disabled_outputs.add("../output/chnwb.txt")
    if soil_output == "No":
        disabled_outputs.add("../output/soil_pw0.txt")
    if plot_output == "No":
        disabled_outputs.add("../output/plot_pw0.txt")
    if event_output == "No":
        disabled_outputs.add("../output/ebe_pw0.txt")

    if disabled_outputs:
        lines = []
        for line in s.splitlines():
            if line.strip() in disabled_outputs:
                continue
            lines.append(line)
        s = "\n".join(lines)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)

    

def make_watershed_run(
    sim_years,
    wepp_ids,
    runs_dir,
    *,
    pass_family=PASS_FAMILY_LEGACY_ASCII,
    wepp_bin=None,
):
    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)

    block = []
    for wepp_id in wepp_ids:
        block.append(_hillstub_template_loader(wepp_id, pass_family=normalized_pass_family))
    block = ''.join(block)

    _watershed_template = _watershed_template_loader()

    water_balance_output = _normalize_yes_no(True)
    soil_output = _normalize_yes_no(True)
    plot_output = _normalize_yes_no(True)
    event_output = _normalize_yes_no(True)
    loss_output_option = 1
    contract_lines = _watershed_prompt_contract_lines(wepp_bin=wepp_bin)

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years,
                                   soil_loss_output_option=loss_output_option,
                                   master_pass_file=contract_lines["master_pass_file"],
                                   water_balance_output=water_balance_output,
                                   soil_output=soil_output,
                                   plot_output=plot_output,
                                   event_output=event_output,
                                   initial_condition_output_file=contract_lines["initial_condition_output_file"],
                                   impoundment_output=contract_lines["impoundment_output"],
                                   impoundment_data_file=contract_lines["impoundment_data_file"])
    s = _drop_template_skip_lines(s)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_watershed_run(
    wepp_ids,
    runs_dir,
    *,
    pass_family=PASS_FAMILY_LEGACY_ASCII,
    wepp_bin=None,
):
    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)
    block = []
    for wepp_id in wepp_ids:
        block.append(_hillstub_template_loader(wepp_id, pass_family=normalized_pass_family))
    block = ''.join(block)

    _watershed_template = _ss_watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_watershed_run(
    wepp_ids,
    runs_dir,
    ss_batch_key,
    ss_batch_id,
    *,
    pass_family=PASS_FAMILY_LEGACY_ASCII,
    wepp_bin=None,
):
    normalized_pass_family = _assert_pass_family_release_support(pass_family, wepp_bin=wepp_bin)
    block = []
    for wepp_id in wepp_ids:
        block.append(
            _hillstub_ss_batch_template_loader(
                wepp_id,
                ss_batch_key,
                pass_family=normalized_pass_family,
            )
        )
    block = ''.join(block)

    _watershed_template = _ss_batch_watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block,
                                   ss_batch_id=ss_batch_id,
                                   ss_batch_key=ss_batch_key)

    fn = _join(runs_dir, f'pw0.{ss_batch_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def run_watershed(runs_dir, wepp_bin=None, status_channel=None):
    t0 = time()

    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=False)
    cmd_text = _cmd_text(cmd)
    runs_dir_abs = os.path.abspath(runs_dir)
    _run_fn = os.path.join(runs_dir, 'pw0.run')
    _stderr_fn = os.path.join(runs_dir, 'pw0.err')
    _run = None
    _log = None
    watchdog = _DisabledDStateWatchdog()
    success = False

    try:
        _run = open(_run_fn)
        _log = open(_stderr_fn, 'w')
        _log.write(
            f'[run_watershed] runs_dir={runs_dir_abs} run_file={_run_fn} '
            f'err_file={_stderr_fn} cmd="{cmd_text}" attempt=1/1\n'
        )
        _write_binary_identity_trace(_log, "run_watershed", cmd[0])

        # for python3.7+ universal_newlines=True -> text=True
        p = subprocess.Popen(cmd, stdin=_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             cwd=runs_dir, universal_newlines=True)
        watchdog = _start_dstate_watchdog(
            "run_watershed",
            p,
            _log,
            runs_dir=runs_dir_abs,
            run_file=_run_fn,
            err_file=_stderr_fn,
            cmd_text=cmd_text,
        )

        # Streaming the output to _log and, if provided, to the status channel
        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()

            if output != '':
                if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()
                if status_channel:
                    StatusMessenger.publish(status_channel, output)

        p.wait()
    finally:
        active_exc = sys.exc_info()[1]
        watchdog.stop()
        close_error = None
        close_traceback = None
        try:
            _close_stream_with_diagnostics(
                _run,
                "run_watershed",
                stream_name="run_file",
                path=_run_fn,
                log=_log,
            )
        except OSError as exc:
            close_error = exc
            close_traceback = exc.__traceback__
        try:
            _close_stream_with_diagnostics(
                _log,
                "run_watershed",
                stream_name="err_file",
                path=_stderr_fn,
                log=_log,
            )
        except OSError as exc:
            if close_error is None:
                close_error = exc
                close_traceback = exc.__traceback__
        if close_error is not None and active_exc is None:
            raise close_error.with_traceback(close_traceback)

    if success:
        return True, time() - t0

    # need to identify if _pup project to set the correct browse link
    _runs_dir = runs_dir_abs.split(os.sep)
    try:
        rel_path = _runs_dir[_runs_dir.index('_pups'):]
        href = 'browse/' + '/'.join(rel_path) + '/pw0.err'
    except ValueError:
        href = 'browse/wepp/runs/pw0.err'
    raise Exception(f'Error running wepp for watershed \nSee <a href="{href}">{_stderr_fn}</a>')


def run_ss_batch_watershed(runs_dir, wepp_bin=None, ss_batch_id=None, status_channel=None):
    assert ss_batch_id is not None

    t0 = time()

    cmd = _resolve_wepp_cmd(wepp_bin, prefer_hill=False)

    assert _exists(_join(runs_dir, 'pw0.str'))
    assert _exists(_join(runs_dir, 'pw0.chn'))
    assert _exists(_join(runs_dir, 'pw0.imp'))
    assert _exists(_join(runs_dir, 'pw0.man'))
    assert _exists(_join(runs_dir, 'pw0.slp'))
    assert _exists(_join(runs_dir, f'pw0.{ss_batch_id}.cli'))
    assert _exists(_join(runs_dir, 'pw0.sol'))
    assert _exists(_join(runs_dir, f'pw0.{ss_batch_id}.run'))

    _stderr_fn = _join(runs_dir, f'pw0.{ss_batch_id}.err')
    _run = open(_join(runs_dir, f'pw0.{ss_batch_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        return True, time() - t0

    runs_dir = os.path.abspath(runs_dir)
    _runs_dir = runs_dir.split(os.sep)
    try:
        rel_path = _runs_dir[_runs_dir.index('_pups'):]
        href = 'browse/' + '/'.join(rel_path) + '/pw0.err'
    except:
        href = 'browse/wepp/runs/pw0.err'
    raise Exception(f'Error running wepp for watershed \nSee <a href="{href}">{_stderr_fn}</a>')
