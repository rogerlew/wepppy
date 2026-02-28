from __future__ import annotations

import argparse
import configparser
import errno
import json
import os
import re
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Literal
from urllib.parse import parse_qsl

HostName = Literal["forest", "wepp1"]
ModeName = Literal["dry-run", "apply"]

HOST_DEFAULT_ROOTS: dict[HostName, tuple[str, str]] = {
    "forest": ("/wc1/runs", "/wc1/batch"),
    "wepp1": ("/geodata/wc1/runs", "/geodata/wc1/batch"),
}

_LOCK_FILENAME = ".root_resource_unroll_batch.lock"
_RUN_RECORD_TYPE = "run_summary"
_FILE_RECORD_TYPE = "file_action"
_ROOT_RECORD_TYPE = "root_validation"

_CLIMATE_RE = re.compile(r"^climate\.(?P<name>.+)\.parquet$")
_WATERSHED_RE = re.compile(r"^watershed\.(?P<name>.+)\.parquet$")
_RESOURCE_SORT_KEY = {
    "landuse": 0,
    "soils": 1,
    "climate": 2,
    "watershed": 3,
    "climate_metric_csv": 4,
}


@dataclass(frozen=True)
class ResourceCandidate:
    source_relpath: str
    target_relpath: str
    resource_type: str


@dataclass(frozen=True)
class ApplyNoDirResolution:
    value: bool | None
    source: str
    message: str


@dataclass
class RunResult:
    runid: str
    run_path: str
    eligible: bool
    files_discovered: int
    files_moved: int
    files_dedup_deleted: int
    files_conflict: int
    files_error: int
    final_status: str
    apply_nodir: bool | None
    records: list[dict[str, Any]]


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_path(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _parse_bool(value: str) -> bool:
    normalized = value.strip().strip('"').strip("'").lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"unsupported boolean value: {value!r}")


def _parse_cfg_spec(cfg_spec: str) -> tuple[str, dict[tuple[str, str], str]]:
    if "?" not in cfg_spec:
        return cfg_spec, {}
    base, query = cfg_spec.split("?", 1)
    overrides: dict[tuple[str, str], str] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        if ":" not in key:
            continue
        section, name = key.split(":", 1)
        overrides[(section, name)] = value
    return base, overrides


def _resolve_config_path(wd: Path, cfg_filename: str) -> Path:
    cfg_path = Path(cfg_filename)
    if not cfg_path.suffix:
        cfg_path = cfg_path.with_suffix(".cfg")
    if cfg_path.is_absolute():
        return cfg_path

    wd_candidate = wd / cfg_path.name
    if wd_candidate.exists():
        return wd_candidate

    configs_root = Path(__file__).resolve().parents[2] / "nodb" / "configs"
    nested_candidate = configs_root / cfg_path
    if nested_candidate.exists():
        return nested_candidate

    return configs_root / cfg_path.name


def _load_ron_cfg_spec(run_dir: Path) -> str:
    ron_path = run_dir / "ron.nodb"
    payload = json.loads(ron_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ron.nodb payload is not a JSON object")

    state = payload.get("py/state")
    if isinstance(state, dict):
        for key in ("_config", "cfg_fn", "config"):
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("_config", "cfg_fn", "config"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise ValueError("ron.nodb has no config reference")


def resolve_apply_nodir(run_dir: Path) -> ApplyNoDirResolution:
    ron_path = run_dir / "ron.nodb"
    if not ron_path.exists():
        return ApplyNoDirResolution(
            value=None,
            source="missing_ron",
            message="ron.nodb is missing",
        )

    try:
        cfg_spec = _load_ron_cfg_spec(run_dir)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return ApplyNoDirResolution(
            value=None,
            source="ron_parse_error",
            message=f"failed to read config from ron.nodb: {exc}",
        )

    cfg_filename, overrides = _parse_cfg_spec(cfg_spec)
    override_value = overrides.get(("nodb", "apply_nodir"))
    if override_value is not None:
        try:
            return ApplyNoDirResolution(
                value=_parse_bool(override_value),
                source="cfg_override",
                message=f"resolved from cfg override in {cfg_spec}",
            )
        except ValueError as exc:
            return ApplyNoDirResolution(
                value=None,
                source="cfg_override_error",
                message=f"invalid nodb:apply_nodir override: {exc}",
            )

    defaults_path = run_dir / "_defaults.toml"
    if not defaults_path.exists():
        defaults_path = Path(__file__).resolve().parents[2] / "nodb" / "configs" / "_defaults.toml"
    cfg_path = _resolve_config_path(run_dir, cfg_filename)

    parser = configparser.RawConfigParser()
    try:
        with defaults_path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except OSError as exc:
        return ApplyNoDirResolution(
            value=None,
            source="defaults_read_error",
            message=f"failed reading defaults file {defaults_path}: {exc}",
        )

    try:
        with cfg_path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except OSError as exc:
        return ApplyNoDirResolution(
            value=None,
            source="cfg_read_error",
            message=f"failed reading cfg file {cfg_path}: {exc}",
        )

    try:
        raw_value = parser.get("nodb", "apply_nodir")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return ApplyNoDirResolution(
            value=None,
            source="cfg_missing_option",
            message=f"nodb.apply_nodir is missing in {cfg_path}",
        )

    try:
        parsed = _parse_bool(raw_value)
    except ValueError as exc:
        return ApplyNoDirResolution(
            value=None,
            source="cfg_value_error",
            message=f"invalid nodb.apply_nodir value {raw_value!r}: {exc}",
        )

    return ApplyNoDirResolution(
        value=parsed,
        source="cfg_file",
        message=f"resolved from cfg {cfg_path}",
    )


def _map_root_resource(filename: str) -> ResourceCandidate | None:
    if filename == "landuse.parquet":
        return ResourceCandidate(filename, "landuse/landuse.parquet", "landuse")
    if filename == "soils.parquet":
        return ResourceCandidate(filename, "soils/soils.parquet", "soils")
    if filename == "wepp_cli_pds_mean_metric.csv":
        return ResourceCandidate(filename, "climate/wepp_cli_pds_mean_metric.csv", "climate_metric_csv")

    climate_match = _CLIMATE_RE.match(filename)
    if climate_match:
        return ResourceCandidate(filename, f"climate/{climate_match.group('name')}.parquet", "climate")

    watershed_match = _WATERSHED_RE.match(filename)
    if watershed_match:
        return ResourceCandidate(filename, f"watershed/{watershed_match.group('name')}.parquet", "watershed")
    return None


def discover_root_resources(run_dir: Path) -> list[ResourceCandidate]:
    discovered: list[ResourceCandidate] = []
    for entry in run_dir.iterdir():
        if not entry.is_file():
            continue
        candidate = _map_root_resource(entry.name)
        if candidate is not None:
            discovered.append(candidate)

    return sorted(discovered, key=lambda item: (_RESOURCE_SORT_KEY[item.resource_type], item.source_relpath))


def discover_project_dirs(roots: Iterable[Path]) -> list[Path]:
    discovered: set[Path] = set()
    prune_dir_names = (
        "wepp",
        "dem",
        "climate",
        "soils",
        "landuse",
        "watershed",
        "_query_engine",
        "export",
        "disturbed",
        "ash",
        "openet",
        "rap",
        "treatments",
        "logs",
        "_logs",
    )
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        if root.name == "runs":
            find_cmd = [
                "find",
                str(root),
                "-mindepth",
                "3",
                "-maxdepth",
                "3",
                "-type",
                "f",
                "-name",
                "ron.nodb",
            ]
        else:
            find_cmd = [
                "find",
                str(root),
                "(",
                "-type",
                "d",
                "(",
                "-name",
                prune_dir_names[0],
            ]
            for name in prune_dir_names[1:]:
                find_cmd.extend(["-o", "-name", name])
            find_cmd.extend(
                [
                    ")",
                    "-prune",
                    ")",
                    "-o",
                    "-type",
                    "f",
                    "-name",
                    "ron.nodb",
                    "-print",
                ]
            )

        result = subprocess.run(
            find_cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or f"find command failed with code {result.returncode}"
            if result.returncode < 0:
                signal_num = -result.returncode
                message = f"{message} (terminated by signal {signal_num})"
            raise OSError(message)

        for line in result.stdout.splitlines():
            ron_path = line.strip()
            if not ron_path:
                continue
            discovered.add(Path(ron_path).parent.resolve())
    return sorted(discovered)


@contextmanager
def _run_lock(run_dir: Path, *, host: HostName) -> Iterable[Path]:
    lock_path = run_dir / _LOCK_FILENAME
    payload = {
        "host": host,
        "pid": os.getpid(),
        "timestamp_utc": _now_iso_utc(),
        "tool": "unroll_root_resources_batch.py",
    }
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        yield lock_path
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _file_record(
    *,
    host: HostName,
    mode: ModeName,
    runid: str,
    run_path: Path,
    apply_nodir: bool | None,
    source_relpath: str,
    target_relpath: str,
    action: str,
    status: str,
    source_sha256: str | None,
    target_sha256: str | None,
    message: str,
    resource_type: str | None,
) -> dict[str, Any]:
    return {
        "record_type": _FILE_RECORD_TYPE,
        "host": host,
        "mode": mode,
        "runid": runid,
        "run_path": str(run_path),
        "apply_nodir": apply_nodir,
        "source_relpath": source_relpath,
        "target_relpath": target_relpath,
        "resource_type": resource_type,
        "action": action,
        "status": status,
        "source_sha256": source_sha256,
        "target_sha256": target_sha256,
        "message": message,
        "timestamp_utc": _now_iso_utc(),
    }


def _run_record(
    *,
    host: HostName,
    mode: ModeName,
    runid: str,
    run_path: Path,
    eligible: bool,
    apply_nodir: bool | None,
    files_discovered: int,
    files_moved: int,
    files_dedup_deleted: int,
    files_conflict: int,
    files_error: int,
    final_status: str,
    message: str,
) -> dict[str, Any]:
    return {
        "record_type": _RUN_RECORD_TYPE,
        "host": host,
        "mode": mode,
        "runid": runid,
        "run_path": str(run_path),
        "eligible": eligible,
        "apply_nodir": apply_nodir,
        "files_discovered": files_discovered,
        "files_moved": files_moved,
        "files_dedup_deleted": files_dedup_deleted,
        "files_conflict": files_conflict,
        "files_error": files_error,
        "final_status": final_status,
        "message": message,
        "timestamp_utc": _now_iso_utc(),
    }


def _root_record(*, host: HostName, mode: ModeName, root: Path, status: str, message: str) -> dict[str, Any]:
    return {
        "record_type": _ROOT_RECORD_TYPE,
        "host": host,
        "mode": mode,
        "root": str(root),
        "status": status,
        "message": message,
        "timestamp_utc": _now_iso_utc(),
    }


def _apply_move(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    os.link(str(source_path), str(target_path))
    source_path.unlink()


def _refresh_query_catalog_entry(run_dir: Path, target_relpath: str) -> str:
    if not target_relpath.endswith(".parquet"):
        return "catalog_refresh=not_required"
    try:
        from wepppy.query_engine import update_catalog_entry
    except ImportError:
        return "catalog_refresh=skipped_import_error"

    try:
        update_catalog_entry(run_dir, target_relpath)
        return "catalog_refresh=updated"
    except Exception as exc:
        # Deliberate best-effort boundary: catalog refresh must never abort file migration.
        return f"catalog_refresh=deferred:{exc}"


def _process_candidates_for_run(
    *,
    host: HostName,
    mode: ModeName,
    runid: str,
    run_dir: Path,
    apply_nodir: bool,
    discovered: list[ResourceCandidate],
    records: list[dict[str, Any]],
) -> tuple[int, int, int, int]:
    moved = 0
    dedup_deleted = 0
    conflict = 0
    error = 0

    for candidate in discovered:
        source_path = run_dir / candidate.source_relpath
        target_path = run_dir / candidate.target_relpath

        if not source_path.exists():
            records.append(
                _file_record(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_path=run_dir,
                    apply_nodir=apply_nodir,
                    source_relpath=candidate.source_relpath,
                    target_relpath=candidate.target_relpath,
                    action="skipped",
                    status="skipped",
                    source_sha256=None,
                    target_sha256=None,
                    message="source file missing before action; treating as no-op",
                    resource_type=candidate.resource_type,
                )
            )
            continue

        source_hash: str | None = None
        target_hash: str | None = None

        try:
            source_hash = _sha256_path(source_path)
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="skipped",
                        status="skipped",
                        source_sha256=None,
                        target_sha256=None,
                        message="source file disappeared during hash; treating as no-op",
                        resource_type=candidate.resource_type,
                    )
                )
                continue
            records.append(
                _file_record(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_path=run_dir,
                    apply_nodir=apply_nodir,
                    source_relpath=candidate.source_relpath,
                    target_relpath=candidate.target_relpath,
                    action="skipped",
                    status="error",
                    source_sha256=None,
                    target_sha256=None,
                    message=f"failed hashing source file: {exc}",
                    resource_type=candidate.resource_type,
                )
            )
            error += 1
            continue

        if target_path.exists():
            try:
                target_hash = _sha256_path(target_path)
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    target_hash = None
                else:
                    records.append(
                        _file_record(
                            host=host,
                            mode=mode,
                            runid=runid,
                            run_path=run_dir,
                            apply_nodir=apply_nodir,
                            source_relpath=candidate.source_relpath,
                            target_relpath=candidate.target_relpath,
                            action="skipped",
                            status="error",
                            source_sha256=source_hash,
                            target_sha256=None,
                            message=f"failed hashing target file: {exc}",
                            resource_type=candidate.resource_type,
                        )
                    )
                    error += 1
                    continue

        if mode == "dry-run":
            if target_hash is None:
                action = "planned"
                message = "would move source to canonical target"
            elif source_hash == target_hash:
                action = "dedup_deleted_source"
                message = "target already matches source; would delete root source"
            else:
                action = "conflict"
                message = "target exists with different hash; manual resolution required"
                conflict += 1
            records.append(
                _file_record(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_path=run_dir,
                    apply_nodir=apply_nodir,
                    source_relpath=candidate.source_relpath,
                    target_relpath=candidate.target_relpath,
                    action=action,
                    status="dry_run",
                    source_sha256=source_hash,
                    target_sha256=target_hash,
                    message=message,
                    resource_type=candidate.resource_type,
                )
            )
            continue

        if target_hash is None:
            try:
                _apply_move(source_path, target_path)
                moved += 1
                refresh_note = _refresh_query_catalog_entry(run_dir, candidate.target_relpath)
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="moved",
                        status="ok",
                        source_sha256=source_hash,
                        target_sha256=source_hash,
                        message=f"moved source to canonical target; {refresh_note}",
                        resource_type=candidate.resource_type,
                    )
                )
            except FileExistsError:
                try:
                    post_target_hash = _sha256_path(target_path)
                except OSError:
                    post_target_hash = None
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="conflict",
                        status="conflict",
                        source_sha256=source_hash,
                        target_sha256=post_target_hash,
                        message="target appeared during move; leaving files untouched",
                        resource_type=candidate.resource_type,
                    )
                )
                conflict += 1
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    records.append(
                        _file_record(
                            host=host,
                            mode=mode,
                            runid=runid,
                            run_path=run_dir,
                            apply_nodir=apply_nodir,
                            source_relpath=candidate.source_relpath,
                            target_relpath=candidate.target_relpath,
                            action="skipped",
                            status="skipped",
                            source_sha256=source_hash,
                            target_sha256=None,
                            message="source disappeared during move; treating as no-op",
                            resource_type=candidate.resource_type,
                        )
                    )
                    continue
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="skipped",
                        status="error",
                        source_sha256=source_hash,
                        target_sha256=None,
                        message=f"move failed: {exc}",
                        resource_type=candidate.resource_type,
                    )
                )
                error += 1
            continue

        if source_hash == target_hash:
            try:
                source_path.unlink()
                dedup_deleted += 1
                refresh_note = _refresh_query_catalog_entry(run_dir, candidate.target_relpath)
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="dedup_deleted_source",
                        status="ok",
                        source_sha256=source_hash,
                        target_sha256=target_hash,
                        message=f"target matches source; deleted root source; {refresh_note}",
                        resource_type=candidate.resource_type,
                    )
                )
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    records.append(
                        _file_record(
                            host=host,
                            mode=mode,
                            runid=runid,
                            run_path=run_dir,
                            apply_nodir=apply_nodir,
                            source_relpath=candidate.source_relpath,
                            target_relpath=candidate.target_relpath,
                            action="dedup_deleted_source",
                            status="ok",
                            source_sha256=source_hash,
                            target_sha256=target_hash,
                            message="source already absent during dedup delete; treated as already deduplicated",
                            resource_type=candidate.resource_type,
                        )
                    )
                    dedup_deleted += 1
                    continue
                records.append(
                    _file_record(
                        host=host,
                        mode=mode,
                        runid=runid,
                        run_path=run_dir,
                        apply_nodir=apply_nodir,
                        source_relpath=candidate.source_relpath,
                        target_relpath=candidate.target_relpath,
                        action="skipped",
                        status="error",
                        source_sha256=source_hash,
                        target_sha256=target_hash,
                        message=f"failed deleting dedup source: {exc}",
                        resource_type=candidate.resource_type,
                    )
                )
                error += 1
            continue

        records.append(
            _file_record(
                host=host,
                mode=mode,
                runid=runid,
                run_path=run_dir,
                apply_nodir=apply_nodir,
                source_relpath=candidate.source_relpath,
                target_relpath=candidate.target_relpath,
                action="conflict",
                status="conflict",
                source_sha256=source_hash,
                target_sha256=target_hash,
                message="target exists with different hash; leaving files untouched",
                resource_type=candidate.resource_type,
            )
        )
        conflict += 1

    return moved, dedup_deleted, conflict, error


def _process_run(
    *,
    host: HostName,
    mode: ModeName,
    run_dir: Path,
) -> RunResult:
    runid = run_dir.name
    records: list[dict[str, Any]] = []

    apply_resolution = resolve_apply_nodir(run_dir)
    apply_nodir = apply_resolution.value
    if apply_nodir is None:
        records.append(
            _run_record(
                host=host,
                mode=mode,
                runid=runid,
                run_path=run_dir,
                eligible=False,
                apply_nodir=apply_nodir,
                files_discovered=0,
                files_moved=0,
                files_dedup_deleted=0,
                files_conflict=0,
                files_error=1,
                final_status="error",
                message=apply_resolution.message,
            )
        )
        return RunResult(
            runid=runid,
            run_path=str(run_dir),
            eligible=False,
            files_discovered=0,
            files_moved=0,
            files_dedup_deleted=0,
            files_conflict=0,
            files_error=1,
            final_status="error",
            apply_nodir=apply_nodir,
            records=records,
        )

    try:
        discovered = discover_root_resources(run_dir)
    except OSError as exc:
        records.append(
            _run_record(
                host=host,
                mode=mode,
                runid=runid,
                run_path=run_dir,
                eligible=False,
                apply_nodir=apply_nodir,
                files_discovered=0,
                files_moved=0,
                files_dedup_deleted=0,
                files_conflict=0,
                files_error=1,
                final_status="error",
                message=f"failed scanning run root resources: {exc}",
            )
        )
        return RunResult(
            runid=runid,
            run_path=str(run_dir),
            eligible=False,
            files_discovered=0,
            files_moved=0,
            files_dedup_deleted=0,
            files_conflict=0,
            files_error=1,
            final_status="error",
            apply_nodir=apply_nodir,
            records=records,
        )

    files_discovered = len(discovered)
    eligible = apply_nodir is False and files_discovered > 0

    if not eligible:
        reason = (
            "apply_nodir=true; migration scope is apply_nodir=false only"
            if apply_nodir
            else "no in-scope WD-root resources discovered"
        )
        records.append(
            _file_record(
                host=host,
                mode=mode,
                runid=runid,
                run_path=run_dir,
                apply_nodir=apply_nodir,
                source_relpath="",
                target_relpath="",
                action="skipped",
                status="skipped",
                source_sha256=None,
                target_sha256=None,
                message=reason,
                resource_type=None,
            )
        )
        records.append(
            _run_record(
                host=host,
                mode=mode,
                runid=runid,
                run_path=run_dir,
                eligible=False,
                apply_nodir=apply_nodir,
                files_discovered=files_discovered,
                files_moved=0,
                files_dedup_deleted=0,
                files_conflict=0,
                files_error=0,
                final_status="skipped",
                message=reason,
            )
        )
        return RunResult(
            runid=runid,
            run_path=str(run_dir),
            eligible=False,
            files_discovered=files_discovered,
            files_moved=0,
            files_dedup_deleted=0,
            files_conflict=0,
            files_error=0,
            final_status="skipped",
            apply_nodir=apply_nodir,
            records=records,
        )

    moved = 0
    dedup_deleted = 0
    conflict = 0
    error = 0

    if mode == "apply":
        try:
            with _run_lock(run_dir, host=host):
                moved, dedup_deleted, conflict, error = _process_candidates_for_run(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_dir=run_dir,
                    apply_nodir=apply_nodir,
                    discovered=discovered,
                    records=records,
                )
        except FileExistsError:
            records.append(
                _run_record(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_path=run_dir,
                    eligible=True,
                    apply_nodir=apply_nodir,
                    files_discovered=files_discovered,
                    files_moved=0,
                    files_dedup_deleted=0,
                    files_conflict=0,
                    files_error=1,
                    final_status="error",
                    message=f"maintenance lock file already exists: {run_dir / _LOCK_FILENAME}",
                )
            )
            return RunResult(
                runid=runid,
                run_path=str(run_dir),
                eligible=True,
                files_discovered=files_discovered,
                files_moved=0,
                files_dedup_deleted=0,
                files_conflict=0,
                files_error=1,
                final_status="error",
                apply_nodir=apply_nodir,
                records=records,
            )
        except OSError as exc:
            records.append(
                _run_record(
                    host=host,
                    mode=mode,
                    runid=runid,
                    run_path=run_dir,
                    eligible=True,
                    apply_nodir=apply_nodir,
                    files_discovered=files_discovered,
                    files_moved=0,
                    files_dedup_deleted=0,
                    files_conflict=0,
                    files_error=1,
                    final_status="error",
                    message=f"failed to acquire lock file: {exc}",
                )
            )
            return RunResult(
                runid=runid,
                run_path=str(run_dir),
                eligible=True,
                files_discovered=files_discovered,
                files_moved=0,
                files_dedup_deleted=0,
                files_conflict=0,
                files_error=1,
                final_status="error",
                apply_nodir=apply_nodir,
                records=records,
            )
    else:
        moved, dedup_deleted, conflict, error = _process_candidates_for_run(
            host=host,
            mode=mode,
            runid=runid,
            run_dir=run_dir,
            apply_nodir=apply_nodir,
            discovered=discovered,
            records=records,
        )

    if mode == "dry-run" and error > 0:
        final_status = "error"
        final_message = "dry-run encountered one or more file-action errors"
    elif mode == "dry-run":
        final_status = "dry_run"
        final_message = "dry-run completed for eligible run"
    elif error > 0:
        final_status = "error"
        final_message = "one or more file actions failed"
    elif conflict > 0:
        final_status = "conflict_requires_manual_resolution"
        final_message = "one or more conflicts detected; files left untouched"
    else:
        final_status = "ok"
        final_message = "apply migration completed"

    records.append(
        _run_record(
            host=host,
            mode=mode,
            runid=runid,
            run_path=run_dir,
            eligible=eligible,
            apply_nodir=apply_nodir,
            files_discovered=files_discovered,
            files_moved=moved,
            files_dedup_deleted=dedup_deleted,
            files_conflict=conflict,
            files_error=error,
            final_status=final_status,
            message=final_message,
        )
    )
    return RunResult(
        runid=runid,
        run_path=str(run_dir),
        eligible=eligible,
        files_discovered=files_discovered,
        files_moved=moved,
        files_dedup_deleted=dedup_deleted,
        files_conflict=conflict,
        files_error=error,
        final_status=final_status,
        apply_nodir=apply_nodir,
        records=records,
    )


def _validate_wepp1_approval(path: Path, approval_token: str | None) -> tuple[bool, str]:
    if not path.exists():
        return False, f"approval file missing: {path}"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"failed reading approval file: {exc}"

    if "wepp1 apply approved" not in content.lower():
        return False, "approval file missing required statement: wepp1 apply approved"

    if approval_token is not None and approval_token not in content:
        return False, "approval token mismatch: token not found in approval file"

    return True, "wepp1 approval gate satisfied"


def _append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _parse_roots_csv(host: HostName, roots_csv: str | None) -> list[Path]:
    if roots_csv is None:
        return [Path(value) for value in HOST_DEFAULT_ROOTS[host]]
    roots = [Path(value.strip()) for value in roots_csv.split(",") if value.strip()]
    if not roots:
        raise ValueError("at least one root path is required")
    return roots


def run_batch_migration(
    *,
    host: HostName,
    mode: ModeName,
    roots_csv: str | None,
    audit_jsonl: Path,
    summary_json: Path,
    max_workers: int,
    wepp1_approval_file: Path | None,
    approval_token: str | None,
) -> int:
    started = perf_counter()
    started_utc = _now_iso_utc()
    roots = _parse_roots_csv(host, roots_csv)

    audit_jsonl.parent.mkdir(parents=True, exist_ok=True)
    audit_jsonl.write_text("", encoding="utf-8")

    if mode == "apply" and host == "wepp1":
        if wepp1_approval_file is None:
            summary = {
                "host": host,
                "mode": mode,
                "roots": [str(path) for path in roots],
                "started_utc": started_utc,
                "ended_utc": _now_iso_utc(),
                "duration_seconds": round(perf_counter() - started, 3),
                "status": "error",
                "errors": ["--wepp1-approval-file is required for --host wepp1 --mode apply"],
            }
            _write_summary(summary_json, summary)
            return 2
        approved, approval_message = _validate_wepp1_approval(wepp1_approval_file, approval_token)
        if not approved:
            summary = {
                "host": host,
                "mode": mode,
                "roots": [str(path) for path in roots],
                "started_utc": started_utc,
                "ended_utc": _now_iso_utc(),
                "duration_seconds": round(perf_counter() - started, 3),
                "status": "error",
                "errors": [approval_message],
            }
            _write_summary(summary_json, summary)
            return 2

    valid_roots: list[Path] = []
    root_errors: list[str] = []
    root_records: list[dict[str, Any]] = []
    for root in roots:
        resolved = root.expanduser().resolve()
        if not resolved.exists():
            msg = f"root does not exist: {resolved}"
            root_errors.append(msg)
            root_records.append(_root_record(host=host, mode=mode, root=resolved, status="missing", message=msg))
            continue
        if not resolved.is_dir():
            msg = f"root is not a directory: {resolved}"
            root_errors.append(msg)
            root_records.append(_root_record(host=host, mode=mode, root=resolved, status="invalid", message=msg))
            continue
        valid_roots.append(resolved)
        root_records.append(_root_record(host=host, mode=mode, root=resolved, status="ok", message="root accessible"))

    _append_jsonl(audit_jsonl, root_records)

    if root_errors:
        summary = {
            "host": host,
            "mode": mode,
            "roots": [str(path) for path in roots],
            "valid_roots": [str(path) for path in valid_roots],
            "started_utc": started_utc,
            "ended_utc": _now_iso_utc(),
            "duration_seconds": round(perf_counter() - started, 3),
            "status": "error",
            "errors": root_errors,
            "totals": {
                "runs_discovered": 0,
                "runs_processed": 0,
                "runs_eligible": 0,
                "runs_skipped": 0,
                "runs_ok": 0,
                "runs_dry_run": 0,
                "runs_conflict": 0,
                "runs_error": 0,
                "files_discovered": 0,
                "files_moved": 0,
                "files_dedup_deleted": 0,
                "files_conflict": 0,
                "files_error": 0,
            },
        }
        _write_summary(summary_json, summary)
        return 2

    try:
        run_dirs = discover_project_dirs(valid_roots)
    except OSError as exc:
        summary = {
            "host": host,
            "mode": mode,
            "roots": [str(path) for path in roots],
            "valid_roots": [str(path) for path in valid_roots],
            "started_utc": started_utc,
            "ended_utc": _now_iso_utc(),
            "duration_seconds": round(perf_counter() - started, 3),
            "status": "error",
            "errors": [f"failed discovering project directories: {exc}"],
            "totals": {
                "runs_discovered": 0,
                "runs_processed": 0,
                "runs_eligible": 0,
                "runs_skipped": 0,
                "runs_ok": 0,
                "runs_dry_run": 0,
                "runs_conflict": 0,
                "runs_error": 0,
                "files_discovered": 0,
                "files_moved": 0,
                "files_dedup_deleted": 0,
                "files_conflict": 0,
                "files_error": 0,
            },
        }
        _write_summary(summary_json, summary)
        return 2
    totals = {
        "runs_discovered": len(run_dirs),
        "runs_processed": 0,
        "runs_eligible": 0,
        "runs_skipped": 0,
        "runs_ok": 0,
        "runs_dry_run": 0,
        "runs_conflict": 0,
        "runs_error": 0,
        "files_discovered": 0,
        "files_moved": 0,
        "files_dedup_deleted": 0,
        "files_conflict": 0,
        "files_error": 0,
    }
    run_status_counts: dict[str, int] = {}
    file_action_counts: dict[str, int] = {}
    resource_action_counts: dict[str, dict[str, int]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_run, host=host, mode=mode, run_dir=run_dir) for run_dir in run_dirs]
        for future in as_completed(futures):
            result = future.result()
            _append_jsonl(audit_jsonl, result.records)

            totals["runs_processed"] += 1
            totals["runs_eligible"] += 1 if result.eligible else 0
            totals["files_discovered"] += result.files_discovered
            totals["files_moved"] += result.files_moved
            totals["files_dedup_deleted"] += result.files_dedup_deleted
            totals["files_conflict"] += result.files_conflict
            totals["files_error"] += result.files_error

            status = result.final_status
            run_status_counts[status] = run_status_counts.get(status, 0) + 1
            if status == "skipped":
                totals["runs_skipped"] += 1
            elif status == "ok":
                totals["runs_ok"] += 1
            elif status == "dry_run":
                totals["runs_dry_run"] += 1
            elif status == "conflict_requires_manual_resolution":
                totals["runs_conflict"] += 1
            elif status == "error":
                totals["runs_error"] += 1

            for record in result.records:
                if record.get("record_type") != _FILE_RECORD_TYPE:
                    continue
                action = str(record.get("action"))
                file_action_counts[action] = file_action_counts.get(action, 0) + 1
                resource_type = record.get("resource_type")
                if not isinstance(resource_type, str):
                    continue
                resource_actions = resource_action_counts.setdefault(resource_type, {})
                resource_actions[action] = resource_actions.get(action, 0) + 1

    ended_utc = _now_iso_utc()
    summary = {
        "host": host,
        "mode": mode,
        "roots": [str(path) for path in roots],
        "valid_roots": [str(path) for path in valid_roots],
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "duration_seconds": round(perf_counter() - started, 3),
        "status": "ok" if totals["runs_error"] == 0 else "error",
        "totals": totals,
        "run_status_counts": run_status_counts,
        "file_action_counts": file_action_counts,
        "resource_action_counts": resource_action_counts,
        "audit_jsonl": str(audit_jsonl),
    }
    _write_summary(summary_json, summary)

    if totals["runs_error"] > 0:
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk-unroll in-scope WD-root resources to canonical directories for apply_nodir=false "
            "runs under host run/batch roots."
        )
    )
    parser.add_argument("--host", required=True, choices=("forest", "wepp1"))
    parser.add_argument("--mode", required=True, choices=("dry-run", "apply"))
    parser.add_argument(
        "--roots",
        default=None,
        help=(
            "Comma-separated roots to scan. Defaults by host: "
            "forest=/wc1/runs,/wc1/batch and wepp1=/geodata/wc1/runs,/geodata/wc1/batch."
        ),
    )
    parser.add_argument("--audit-jsonl", type=Path, required=True, help="Path for JSONL audit records.")
    parser.add_argument("--summary-json", type=Path, required=True, help="Path for JSON summary output.")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=max(1, min(8, (os.cpu_count() or 4))),
        help="Maximum number of concurrent run workers.",
    )
    parser.add_argument(
        "--wepp1-approval-file",
        type=Path,
        default=None,
        help="Required when --host wepp1 --mode apply. Must contain: wepp1 apply approved.",
    )
    parser.add_argument(
        "--approval-token",
        default=None,
        help="Optional token that must be present in the approval file when provided.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit_jsonl = args.audit_jsonl.expanduser().resolve()
    summary_json = args.summary_json.expanduser().resolve()
    approval_file = args.wepp1_approval_file.expanduser().resolve() if args.wepp1_approval_file else None

    try:
        code = run_batch_migration(
            host=args.host,
            mode=args.mode,
            roots_csv=args.roots,
            audit_jsonl=audit_jsonl,
            summary_json=summary_json,
            max_workers=max(1, int(args.max_workers)),
            wepp1_approval_file=approval_file,
            approval_token=args.approval_token,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        summary_payload = json.loads(summary_json.read_text(encoding="utf-8"))
        print(json.dumps(summary_payload, sort_keys=True))
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
