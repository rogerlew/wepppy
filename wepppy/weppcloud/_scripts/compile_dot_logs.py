#!/usr/bin/env python3
"""
Compile per-run access logs into access.csv and run-locations.json.

This script scans the .<runid> access logs under /wc1/runs (and optional
legacy roots) and produces:
- access.csv (used by stats + landing page refresh)
- runid-locations.json (deck.gl landing map)
- runs_counter.json (stats summaries)
- run_counts.csv (unique run metrics)
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import logging
import os
import sys
import time
import uuid
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Iterable, Iterator, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.nodb import Ron, Watershed

# NOTE for AGENTS: OK to edit (requested). Keep outputs compatible.

DEFAULT_ACCESS_LOG_PATHS = [
    os.environ.get("WEPP_ACCESS_LOG_PATH"),
    "/geodata/weppcloud_runs/access.csv",
    "/wc1/geodata/weppcloud_runs/access.csv",
]

DEFAULT_RUN_ROOTS = ["/wc1/runs"]
DEFAULT_LEGACY_ROOTS = ["/geodata/weppcloud_runs"]
DEFAULT_PROGRESS_EVERY = 250

ACCESS_LOG_HEADER = [
    "runid",
    "config",
    "has_sbs",
    "hillslopes",
    "ash_hillslopes",
    "centroid_longitude",
    "centroid_latitude",
    "year",
    "user",
    "ip",
    "date",
]

RUN_COUNTS_HEADER = ["runid", "hillslopes", "ash_hillslopes", "year", "config"]


@dataclass(frozen=True)
class RunLog:
    runid: str
    run_dir: Path
    log_path: Path


@dataclass
class RunMetrics:
    runid: str
    run_name: str
    run_dir: Path
    config: Optional[str]
    has_sbs: Optional[bool]
    hillslopes: int
    ash_hillslopes: int
    centroid_longitude: Optional[float]
    centroid_latitude: Optional[float]
    access_count: int
    last_accessed: Optional[datetime]
    first_accessed: Optional[datetime]


@dataclass
class ArtifactHealth:
    watershed_readable: int = 0
    watershed_missing: int = 0
    watershed_errors: int = 0
    ash_readable: int = 0
    ash_missing: int = 0
    ash_errors: int = 0


def _log_info(logger: Optional[logging.Logger], message: str, *args: object) -> None:
    if logger is not None:
        logger.info(message, *args)


def _log_warning(logger: Optional[logging.Logger], message: str, *args: object) -> None:
    if logger is not None:
        logger.warning(message, *args)
        return
    if args:
        message = message % args
    print(f"Warning: {message}", file=sys.stderr)


def _resolve_access_log_path(override: Optional[str] = None) -> Path:
    if override:
        return Path(override)
    for candidate in DEFAULT_ACCESS_LOG_PATHS:
        if not candidate:
            continue
        path = Path(candidate)
        if path.parent.exists():
            return path
    return Path("/tmp/access.csv")


def _resolve_run_locations_path(access_log_path: Path, override: Optional[str] = None) -> Path:
    if override:
        return Path(override)
    return access_log_path.parent / "runid-locations.json"


def _resolve_runs_counter_path(access_log_path: Path) -> Path:
    return access_log_path.parent / "runs_counter.json"


def _resolve_run_counts_path(access_log_path: Path) -> Path:
    return access_log_path.parent / "run_counts.csv"


def _iter_log_files(
    run_roots: Iterable[Path],
    legacy_roots: Iterable[Path],
) -> list[RunLog]:
    seen: set[str] = set()
    logs: list[RunLog] = []

    for root in run_roots:
        if not root.exists():
            continue
        pattern = str(root / "*" / ".*")
        for raw_path in glob(pattern):
            path = Path(raw_path)
            if path.name.endswith(('.swp', '.swo')):
                continue
            if not path.name.startswith('.'):
                continue
            try:
                resolved = str(path.resolve())
            except FileNotFoundError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            runid = path.name[1:]
            if not runid:
                continue
            prefix_dir = path.parent
            run_dir = prefix_dir / runid
            if not run_dir.is_dir():
                continue
            logs.append(RunLog(runid=runid, run_dir=run_dir, log_path=path))

    for root in legacy_roots:
        if not root.exists():
            continue
        pattern = str(root / ".*")
        for raw_path in glob(pattern):
            path = Path(raw_path)
            if path.name in {".", ".."}:
                continue
            if path.name.endswith(('.swp', '.swo')):
                continue
            if not path.name.startswith('.'):
                continue
            try:
                resolved = str(path.resolve())
            except FileNotFoundError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            runid = path.name[1:]
            if not runid:
                continue
            run_dir = root / runid
            if not run_dir.is_dir():
                continue
            logs.append(RunLog(runid=runid, run_dir=run_dir, log_path=path))

    return logs


def _parse_access_line(line: str) -> Optional[tuple[str, str, datetime]]:
    raw = line.strip()
    if not raw:
        return None
    parts = raw.split(',')
    if len(parts) < 3:
        return None
    email = parts[0].strip()
    ip = parts[1].strip()
    date_str = parts[2].strip()
    try:
        timestamp = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        try:
            timestamp = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return email, ip, timestamp


def _parquet_row_count(
    path: Path,
    runid: str,
    artifact: str,
    health: ArtifactHealth,
    *,
    logger: Optional[logging.Logger] = None,
) -> int:
    try:
        path.stat()
    except FileNotFoundError:
        setattr(health, f"{artifact}_missing", getattr(health, f"{artifact}_missing") + 1)
        return 0
    except OSError as exc:
        setattr(health, f"{artifact}_errors", getattr(health, f"{artifact}_errors") + 1)
        _log_warning(logger, "failed to stat %s parquet for %s (%s): %s", artifact, runid, path, exc)
        return 0

    try:
        row_count = pq.ParquetFile(path).metadata.num_rows
    except (FileNotFoundError, OSError, pa.ArrowException) as exc:
        setattr(health, f"{artifact}_errors", getattr(health, f"{artifact}_errors") + 1)
        _log_warning(logger, "failed to read %s parquet for %s (%s): %s", artifact, runid, path, exc)
        return 0

    setattr(health, f"{artifact}_readable", getattr(health, f"{artifact}_readable") + 1)
    return row_count


def _validate_artifact_health(log_count: int, health: ArtifactHealth) -> None:
    if log_count == 0:
        return
    if health.watershed_readable == 0:
        raise RuntimeError("refusing to publish: no watershed hillslopes parquet was readable")

    if health.watershed_errors >= 10 and health.watershed_errors / log_count >= 0.25:
        raise RuntimeError(
            "refusing to publish: systemic watershed parquet errors "
            f"({health.watershed_errors}/{log_count} runs)"
        )

    if health.ash_errors >= 10 and health.ash_errors / log_count >= 0.25:
        raise RuntimeError(
            "refusing to publish: systemic ash parquet errors "
            f"({health.ash_errors}/{log_count} runs)"
        )


def _load_run_metadata(
    run_dir: Path,
    runid: str,
    *,
    artifact_health: Optional[ArtifactHealth] = None,
    logger: Optional[logging.Logger] = None,
) -> tuple[Optional[str], Optional[bool], int, int, Optional[float], Optional[float]]:
    config = None
    has_sbs: Optional[bool] = None

    try:
        ron = Ron.getInstance(str(run_dir))
        config = ron.config_stem
        has_sbs = bool(getattr(ron, 'has_sbs', False))
    except Exception as exc:
        _log_warning(logger, "failed to load Ron for %s (%s): %s", runid, run_dir, exc)

    health = artifact_health if artifact_health is not None else ArtifactHealth()
    hillslopes = _parquet_row_count(
        run_dir / "watershed" / "hillslopes.parquet",
        runid,
        "watershed",
        health,
        logger=logger,
    )
    ash_hillslopes = _parquet_row_count(
        run_dir / "ash" / "post" / "hillslope_annuals.parquet",
        runid,
        "ash",
        health,
        logger=logger,
    )

    centroid_longitude: Optional[float] = None
    centroid_latitude: Optional[float] = None
    try:
        watershed = Watershed.getInstance(str(run_dir))
        centroid = watershed.centroid
        if centroid is not None:
            centroid_longitude, centroid_latitude = centroid
    except Exception as exc:
        _log_warning(logger, "failed to load centroid for %s (%s): %s", runid, run_dir, exc)

    return config, has_sbs, hillslopes, ash_hillslopes, centroid_longitude, centroid_latitude


def _derive_run_name(runid: str) -> str:
    slug = runid.strip().split('/')[-1]
    slug = slug.lstrip('.')
    if not slug:
        return runid
    return slug.replace('-', ' ')


def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
    tmp_path.replace(path)


def _write_csv(path: Path, rows: list[list[object]], header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    tmp_path.replace(path)


def _candidate_path(path: Path, generation_id: str) -> Path:
    return path.with_name(f"{path.name}.candidate.{generation_id}")


@contextmanager
def _compile_lock(output_dir: Path) -> Iterator[None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / ".compile_dot_logs.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("compile_dot_logs is already running for this output directory") from exc
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _compile_locks(output_dirs: Iterable[Path]) -> Iterator[None]:
    unique_dirs = sorted({path.resolve() for path in output_dirs}, key=str)
    with ExitStack() as stack:
        for output_dir in unique_dirs:
            stack.enter_context(_compile_lock(output_dir))
        yield


def _publish_candidates(
    publications: tuple[tuple[Path, Path], ...],
    generation_id: str,
    *,
    logger: Optional[logging.Logger] = None,
) -> None:
    output_dir = publications[0][1].parent
    journal_path = output_dir / f".compile_dot_logs.publish.{generation_id}.json"
    publication_states = [
        {"candidate": str(candidate), "target": str(target), "existed": target.exists()}
        for candidate, target in publications
    ]
    _write_json(
        journal_path,
        {"publications": publication_states},
    )
    backups = {
        Path(state["target"]): Path(state["target"]).with_name(
            f"{Path(state['target']).name}.last-good.{generation_id}"
        )
        for state in publication_states
        if state["existed"]
    }
    try:
        for candidate, target in publications:
            backup = backups.get(target)
            if backup is not None:
                target.replace(backup)
            candidate.replace(target)
    except Exception as promotion_exc:
        # Transaction boundary: RQ timeouts are Exception subclasses and must
        # leave a durable journal if any rollback operation also fails.
        rollback_error: Optional[OSError] = None
        for _candidate, target in reversed(publications):
            backup = backups.get(target)
            try:
                if backup is not None and backup.exists():
                    backup.replace(target)
                elif backup is None:
                    target.unlink(missing_ok=True)
            except OSError as exc:
                rollback_error = rollback_error or exc
        if rollback_error is None:
            journal_path.unlink(missing_ok=True)
        raise promotion_exc
    finally:
        for candidate, _target in publications:
            candidate.unlink(missing_ok=True)

    journal_path.unlink(missing_ok=True)
    for backup in backups.values():
        try:
            backup.unlink(missing_ok=True)
        except OSError as exc:
            _log_warning(logger, "failed to remove publication backup %s: %s", backup, exc)


def _recover_interrupted_publications(
    output_dirs: Iterable[Path],
    *,
    logger: Optional[logging.Logger] = None,
) -> None:
    resolved_output_dirs = {output_dir.resolve() for output_dir in output_dirs}
    for output_dir in resolved_output_dirs:
        for journal_path in output_dir.glob(".compile_dot_logs.publish.*.json"):
            _recover_publication_journal(journal_path, resolved_output_dirs, logger=logger)


def _recover_publication_journal(
    journal_path: Path,
    resolved_output_dirs: set[Path],
    *,
    logger: Optional[logging.Logger] = None,
) -> None:
        with journal_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for publication in payload.get("publications", []):
            candidate = Path(publication["candidate"])
            target = Path(publication["target"])
            if candidate.parent.resolve() not in resolved_output_dirs or target.parent.resolve() not in resolved_output_dirs:
                raise RuntimeError(f"unsafe compile_dot_logs publication journal path in {journal_path}")
            generation_id = journal_path.name.removeprefix(".compile_dot_logs.publish.").removesuffix(".json")
            backup = target.with_name(f"{target.name}.last-good.{generation_id}")
            if backup.exists():
                backup.replace(target)
            elif not publication["existed"]:
                target.unlink(missing_ok=True)
            candidate.unlink(missing_ok=True)
        journal_path.unlink(missing_ok=True)
        _log_warning(logger, "recovered interrupted compile_dot_logs publication %s", journal_path)


def _cleanup_generation_files(output_dirs: Iterable[Path], generation_id: str) -> None:
    for output_dir in {path.resolve() for path in output_dirs}:
        for path in output_dir.glob(f"*.candidate.{generation_id}*"):
            path.unlink(missing_ok=True)


def _compile_dot_logs_locked(
    *,
    access_log_path: Optional[str] = None,
    run_locations_path: Optional[str] = None,
    run_roots: Optional[list[str]] = None,
    legacy_roots: Optional[list[str]] = None,
    logger: Optional[logging.Logger] = None,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
    generation_id: str,
) -> dict[str, int]:
    started_at = time.perf_counter()
    access_path = _resolve_access_log_path(access_log_path)
    run_locations_path = _resolve_run_locations_path(access_path, run_locations_path)
    runs_counter_path = _resolve_runs_counter_path(access_path)
    run_counts_path = _resolve_run_counts_path(access_path)

    run_root_paths = [Path(root) for root in (run_roots or DEFAULT_RUN_ROOTS)]
    legacy_root_paths = [Path(root) for root in (legacy_roots or DEFAULT_LEGACY_ROOTS)]

    _log_info(
        logger,
        "compile_dot_logs starting: access_path=%s run_locations_path=%s run_roots=%s legacy_roots=%s",
        access_path,
        run_locations_path,
        [str(root) for root in run_root_paths],
        [str(root) for root in legacy_root_paths],
    )

    discover_started_at = time.perf_counter()
    logs = _iter_log_files(run_root_paths, legacy_root_paths)
    discover_elapsed = time.perf_counter() - discover_started_at
    _log_info(
        logger,
        "compile_dot_logs discovered %d access logs in %.1fs",
        len(logs),
        discover_elapsed,
    )

    output_paths = (access_path, run_locations_path, runs_counter_path, run_counts_path)
    if not logs and any(path.exists() for path in output_paths):
        raise RuntimeError("refusing to replace existing outputs after zero-log discovery")

    run_metrics: dict[str, RunMetrics] = {}
    access_rows_count = 0
    artifact_health = ArtifactHealth()

    parse_started_at = time.perf_counter()
    access_path.parent.mkdir(parents=True, exist_ok=True)
    access_candidate_path = _candidate_path(access_path, generation_id)
    with access_candidate_path.open('w', newline='', encoding='utf-8') as access_handle:
        access_writer = csv.writer(access_handle)
        access_writer.writerow(ACCESS_LOG_HEADER)

        for index, log in enumerate(logs, start=1):
            metrics = run_metrics.get(log.runid)
            if metrics is None:
                config, has_sbs, hillslopes, ash_hillslopes, centroid_longitude, centroid_latitude = _load_run_metadata(
                    log.run_dir,
                    log.runid,
                    artifact_health=artifact_health,
                    logger=logger,
                )
                metrics = RunMetrics(
                    runid=log.runid,
                    run_name=_derive_run_name(log.runid),
                    run_dir=log.run_dir,
                    config=config,
                    has_sbs=has_sbs,
                    hillslopes=hillslopes,
                    ash_hillslopes=ash_hillslopes,
                    centroid_longitude=centroid_longitude,
                    centroid_latitude=centroid_latitude,
                    access_count=0,
                    last_accessed=None,
                    first_accessed=None,
                )
                run_metrics[log.runid] = metrics

            try:
                with log.log_path.open('r', encoding='utf-8') as handle:
                    for raw_line in handle:
                        parsed = _parse_access_line(raw_line)
                        if parsed is None:
                            continue
                        email, ip, timestamp = parsed
                        metrics.access_count += 1
                        if metrics.last_accessed is None or timestamp > metrics.last_accessed:
                            metrics.last_accessed = timestamp
                        if metrics.first_accessed is None or timestamp < metrics.first_accessed:
                            metrics.first_accessed = timestamp
                        access_writer.writerow([
                            log.runid,
                            metrics.config,
                            metrics.has_sbs,
                            metrics.hillslopes,
                            metrics.ash_hillslopes,
                            metrics.centroid_longitude,
                            metrics.centroid_latitude,
                            timestamp.year,
                            email,
                            ip,
                            timestamp.isoformat(sep=' '),
                        ])
                        access_rows_count += 1
            except OSError as exc:
                _log_warning(logger, "failed to read %s: %s", log.log_path, exc)

            if progress_every > 0 and index % progress_every == 0:
                _log_info(
                    logger,
                    "compile_dot_logs progress(parse): processed_logs=%d/%d runs=%d access_rows=%d elapsed_s=%.1f",
                    index,
                    len(logs),
                    len(run_metrics),
                    access_rows_count,
                    time.perf_counter() - parse_started_at,
                )

    parse_elapsed = time.perf_counter() - parse_started_at
    _log_info(
        logger,
        "compile_dot_logs staged access.csv rows=%d in %.1fs",
        access_rows_count,
        parse_elapsed,
    )

    _log_info(
        logger,
        "compile_dot_logs artifact health: watershed_readable=%d watershed_missing=%d watershed_errors=%d ash_readable=%d ash_missing=%d ash_errors=%d",
        artifact_health.watershed_readable,
        artifact_health.watershed_missing,
        artifact_health.watershed_errors,
        artifact_health.ash_readable,
        artifact_health.ash_missing,
        artifact_health.ash_errors,
    )
    _validate_artifact_health(len(run_metrics), artifact_health)

    try:
        from wepppy.weppcloud.utils.run_ttl import read_ttl_state, touch_ttl, DELETE_STATE_ACTIVE
    except Exception as exc:
        _log_warning(logger, "run TTL helpers unavailable (%s)", exc)
        read_ttl_state = None
        touch_ttl = None
        DELETE_STATE_ACTIVE = None

    run_locations: list[dict[str, object]] = []
    runs_counter = Counter()

    build_started_at = time.perf_counter()
    for index, metrics in enumerate(run_metrics.values(), start=1):
        if metrics.last_accessed and touch_ttl is not None:
            try:
                touch_ttl(str(metrics.run_dir), accessed_at=metrics.last_accessed, touched_by="access_log")
            except Exception as exc:
                _log_warning(logger, "failed to touch TTL for %s: %s", metrics.runid, exc)

        if read_ttl_state is not None and DELETE_STATE_ACTIVE is not None:
            try:
                ttl_state = read_ttl_state(str(metrics.run_dir))
                if ttl_state and ttl_state.get("delete_state") != DELETE_STATE_ACTIVE:
                    continue
            except Exception as exc:
                _log_warning(logger, "failed to read TTL for %s: %s", metrics.runid, exc)

        first_access = metrics.first_accessed
        if metrics.config and first_access and first_access > datetime(2024, 1, 1):
            config = metrics.config.split('?')[0]
            if 'rhem' in config and 'eu' not in config:
                runs_counter['rhem_projects'] += 1
                runs_counter['rhem_hillruns'] += metrics.hillslopes
            elif 'eu' in config:
                runs_counter['eu_projects'] += 1
                runs_counter['eu_hillruns'] += metrics.hillslopes
                runs_counter['eu_ash_hillruns'] += metrics.ash_hillslopes
            elif 'au' in config:
                runs_counter['au_projects'] += 1
                runs_counter['au_hillruns'] += metrics.hillslopes
                runs_counter['au_ash_hillruns'] += metrics.ash_hillslopes
            elif 'reveg' in config:
                runs_counter['reveg_projects'] += 1
                runs_counter['reveg_hillruns'] += metrics.hillslopes
            else:
                runs_counter['disturbed_projects'] += 1
                runs_counter['disturbed_hillruns'] += metrics.hillslopes
                runs_counter['disturbed_ash_hillruns'] += metrics.ash_hillslopes

            runs_counter['projects'] += 1
            runs_counter['hillruns'] += metrics.hillslopes
            runs_counter['ash_hillruns'] += metrics.ash_hillslopes

        if metrics.centroid_longitude is None or metrics.centroid_latitude is None:
            continue

        last_accessed = _format_datetime(metrics.last_accessed)
        run_locations.append({
            "runid": metrics.runid,
            "run_name": metrics.run_name,
            "coordinates": [metrics.centroid_longitude, metrics.centroid_latitude],
            "config": metrics.config,
            "year": metrics.last_accessed.year if metrics.last_accessed else None,
            "has_sbs": bool(metrics.has_sbs) if metrics.has_sbs is not None else False,
            "hillslopes": metrics.hillslopes,
            "ash_hillslopes": metrics.ash_hillslopes,
            "access_count": metrics.access_count,
            "last_accessed": last_accessed,
        })

        if progress_every > 0 and index % progress_every == 0:
            _log_info(
                logger,
                "compile_dot_logs progress(locations): processed_runs=%d/%d run_locations=%d elapsed_s=%.1f",
                index,
                len(run_metrics),
                len(run_locations),
                time.perf_counter() - build_started_at,
            )

    run_locations.sort(key=lambda entry: entry.get("last_accessed") or "", reverse=True)
    run_locations_candidate_path = _candidate_path(run_locations_path, generation_id)
    runs_counter_candidate_path = _candidate_path(runs_counter_path, generation_id)
    run_counts_candidate_path = _candidate_path(run_counts_path, generation_id)
    _write_json(run_locations_candidate_path, run_locations)
    _write_json(runs_counter_candidate_path, runs_counter)

    run_counts_rows = [
        [
            metrics.runid,
            metrics.hillslopes,
            metrics.ash_hillslopes,
            metrics.last_accessed.year if metrics.last_accessed else None,
            metrics.config,
        ]
        for metrics in run_metrics.values()
        if metrics.config
    ]
    run_counts_rows.sort(key=lambda row: row[0])
    _write_csv(
        run_counts_candidate_path,
        run_counts_rows,
        header=RUN_COUNTS_HEADER,
    )

    _publish_candidates((
        (access_candidate_path, access_path),
        (run_locations_candidate_path, run_locations_path),
        (runs_counter_candidate_path, runs_counter_path),
        (run_counts_candidate_path, run_counts_path),
    ), generation_id, logger=logger)

    build_elapsed = time.perf_counter() - build_started_at
    total_elapsed = time.perf_counter() - started_at
    _log_info(
        logger,
        "compile_dot_logs completed: logs=%d runs=%d access_rows=%d run_locations=%d elapsed_s=%.1f discover_s=%.1f parse_s=%.1f build_s=%.1f",
        len(logs),
        len(run_metrics),
        access_rows_count,
        len(run_locations),
        total_elapsed,
        discover_elapsed,
        parse_elapsed,
        build_elapsed,
    )

    return {
        "logs": len(logs),
        "access_rows": access_rows_count,
        "run_locations": len(run_locations),
        "runs": len(run_metrics),
    }


def compile_dot_logs(
    *,
    access_log_path: Optional[str] = None,
    run_locations_path: Optional[str] = None,
    run_roots: Optional[list[str]] = None,
    legacy_roots: Optional[list[str]] = None,
    logger: Optional[logging.Logger] = None,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
) -> dict[str, int]:
    access_path = _resolve_access_log_path(access_log_path)
    locations_path = _resolve_run_locations_path(access_path, run_locations_path)
    output_dirs = {access_path.parent, locations_path.parent}
    generation_id = uuid.uuid4().hex
    with _compile_locks(output_dirs):
        _recover_interrupted_publications(output_dirs, logger=logger)
        try:
            return _compile_dot_logs_locked(
                access_log_path=str(access_path),
                run_locations_path=str(locations_path),
                run_roots=run_roots,
                legacy_roots=legacy_roots,
                logger=logger,
                progress_every=progress_every,
                generation_id=generation_id,
            )
        finally:
            _cleanup_generation_files(output_dirs, generation_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile access logs and landing map data.")
    parser.add_argument("--access-log", default=None, help="Path to access.csv output")
    parser.add_argument("--run-locations", default=None, help="Path to runid-locations.json output")
    parser.add_argument("--run-root", action="append", dest="run_roots", default=None, help="Run root like /wc1/runs")
    parser.add_argument("--legacy-root", action="append", dest="legacy_roots", default=None, help="Legacy root like /geodata/weppcloud_runs")

    args = parser.parse_args()
    result = compile_dot_logs(
        access_log_path=args.access_log,
        run_locations_path=args.run_locations,
        run_roots=args.run_roots,
        legacy_roots=args.legacy_roots,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
