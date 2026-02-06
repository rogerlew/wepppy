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
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Iterable, Optional

from wepppy.nodb import Ron, Watershed

# NOTE for AGENTS: OK to edit (requested). Keep outputs compatible.

DEFAULT_ACCESS_LOG_PATHS = [
    os.environ.get("WEPP_ACCESS_LOG_PATH"),
    "/geodata/weppcloud_runs/access.csv",
    "/wc1/geodata/weppcloud_runs/access.csv",
]

DEFAULT_RUN_ROOTS = ["/wc1/runs"]
DEFAULT_LEGACY_ROOTS = ["/geodata/weppcloud_runs"]


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


def _load_run_metadata(run_dir: Path, runid: str) -> tuple[Optional[str], Optional[bool], int, int, Optional[float], Optional[float]]:
    config = None
    has_sbs: Optional[bool] = None

    try:
        ron = Ron.getInstance(str(run_dir))
        config = ron.config_stem
        has_sbs = bool(getattr(ron, 'has_sbs', False))
    except Exception as exc:
        print(f"Warning: failed to load Ron for {run_dir}: {exc}", file=sys.stderr)

    hillslopes = len(glob(str(run_dir / "wepp" / "runs" / "*.slp")))
    ash_hillslopes = len(glob(str(run_dir / "ash" / "*ash.csv")))

    centroid_longitude: Optional[float] = None
    centroid_latitude: Optional[float] = None
    if hillslopes > 0:
        try:
            watershed = Watershed.getInstance(str(run_dir))
            centroid = watershed.centroid
            if centroid is not None:
                centroid_longitude, centroid_latitude = centroid
        except Exception as exc:
            print(f"Warning: failed to load centroid for {run_dir}: {exc}", file=sys.stderr)

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


def compile_dot_logs(
    *,
    access_log_path: Optional[str] = None,
    run_locations_path: Optional[str] = None,
    run_roots: Optional[list[str]] = None,
    legacy_roots: Optional[list[str]] = None,
) -> dict[str, int]:
    access_path = _resolve_access_log_path(access_log_path)
    run_locations_path = _resolve_run_locations_path(access_path, run_locations_path)
    runs_counter_path = _resolve_runs_counter_path(access_path)
    run_counts_path = _resolve_run_counts_path(access_path)

    run_root_paths = [Path(root) for root in (run_roots or DEFAULT_RUN_ROOTS)]
    legacy_root_paths = [Path(root) for root in (legacy_roots or DEFAULT_LEGACY_ROOTS)]

    logs = _iter_log_files(run_root_paths, legacy_root_paths)

    access_rows: list[list[object]] = []
    run_metrics: dict[str, RunMetrics] = {}

    for log in logs:
        config, has_sbs, hillslopes, ash_hillslopes, centroid_longitude, centroid_latitude = _load_run_metadata(
            log.run_dir,
            log.runid,
        )

        metrics = run_metrics.get(log.runid)
        if metrics is None:
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
                    access_rows.append([
                        log.runid,
                        config,
                        has_sbs,
                        hillslopes,
                        ash_hillslopes,
                        centroid_longitude,
                        centroid_latitude,
                        timestamp.year,
                        email,
                        ip,
                        timestamp.isoformat(sep=' '),
                    ])
        except OSError as exc:
            print(f"Warning: failed to read {log.log_path}: {exc}", file=sys.stderr)

    access_rows.sort(key=lambda row: (row[0], row[10]))

    _write_csv(
        access_path,
        access_rows,
        header=[
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
        ],
    )

    try:
        from wepppy.weppcloud.utils.run_ttl import read_ttl_state, touch_ttl, DELETE_STATE_ACTIVE
    except Exception as exc:
        print(f"Warning: run TTL helpers unavailable ({exc})", file=sys.stderr)
        read_ttl_state = None
        touch_ttl = None
        DELETE_STATE_ACTIVE = None

    run_locations: list[dict[str, object]] = []
    runs_counter = Counter()

    for metrics in run_metrics.values():
        if metrics.last_accessed and touch_ttl is not None:
            try:
                touch_ttl(str(metrics.run_dir), accessed_at=metrics.last_accessed, touched_by="access_log")
            except Exception as exc:
                print(f"Warning: failed to touch TTL for {metrics.runid}: {exc}", file=sys.stderr)

        if read_ttl_state is not None and DELETE_STATE_ACTIVE is not None:
            try:
                ttl_state = read_ttl_state(str(metrics.run_dir))
                if ttl_state and ttl_state.get("delete_state") != DELETE_STATE_ACTIVE:
                    continue
            except Exception as exc:
                print(f"Warning: failed to read TTL for {metrics.runid}: {exc}", file=sys.stderr)

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

    run_locations.sort(key=lambda entry: entry.get("last_accessed") or "", reverse=True)
    _write_json(run_locations_path, run_locations)
    _write_json(runs_counter_path, runs_counter)

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
        run_counts_path,
        run_counts_rows,
        header=["runid", "hillslopes", "ash_hillslopes", "year", "config"],
    )

    return {
        "logs": len(logs),
        "access_rows": len(access_rows),
        "run_locations": len(run_locations),
        "runs": len(run_metrics),
    }


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
