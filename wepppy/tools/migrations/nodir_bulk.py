from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Literal

from wepppy.nodb.base import lock_statuses
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.paths import NODIR_ROOTS, NoDirRoot
from wepppy.runtime_paths.thaw_freeze import maintenance_lock, thaw_locked

__all__ = [
    "crawl_runs",
    "main",
]

MigrationMode = Literal["archive", "restore"]

_COMPLETE_STATUSES = frozenset(
    {
        "archived",
        "already_archive",
        "restored",
        "already_directory",
        "missing_root",
    }
)
_MODE_COMPLETE_STATUSES: dict[MigrationMode, frozenset[str]] = {
    "archive": frozenset({"archived", "already_archive", "missing_root"}),
    "restore": frozenset({"restored", "already_directory", "missing_root"}),
}
_FAILURE_STATUSES = frozenset(
    {
        "active_run_locked",
        "root_lock_failed",
        "readonly_required",
        "nodir_error",
        "exception",
    }
)
_RECOVERABLE_EXCEPTIONS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    LookupError,
    AssertionError,
    zipfile.BadZipFile,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_roots(roots: Iterable[str]) -> tuple[NoDirRoot, ...]:
    normalized: set[NoDirRoot] = set()
    for root in roots:
        if root not in NODIR_ROOTS:
            raise ValueError(f"unsupported NoDir root: {root}")
        normalized.add(root)
    if not normalized:
        raise ValueError("at least one --root is required")
    return tuple(sorted(normalized))


def _is_run_directory(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "ron.nodb").exists():
        return True
    return any(path.glob("*.nodb"))


def _discover_run_dirs(scan_roots: Iterable[Path]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for scan_root in scan_roots:
        root = scan_root.expanduser().resolve()
        if not root.exists():
            continue
        if not root.is_dir():
            continue

        if _is_run_directory(root) and root not in seen:
            discovered.append(root)
            seen.add(root)
            continue

        with suppress(OSError):
            for prefix in sorted(root.iterdir()):
                if not prefix.is_dir():
                    continue
                with suppress(OSError):
                    for candidate in sorted(prefix.iterdir()):
                        if candidate in seen or not _is_run_directory(candidate):
                            continue
                        discovered.append(candidate)
                        seen.add(candidate)

    return sorted(discovered)


def _load_resume_pairs(audit_log: Path, *, mode: MigrationMode) -> set[tuple[str, str]]:
    completed: set[tuple[str, str]] = set()
    if not audit_log.exists():
        return completed

    allowed_statuses = _MODE_COMPLETE_STATUSES[mode]

    with audit_log.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("dry_run"):
                continue

            status = payload.get("status")
            if status not in allowed_statuses:
                continue

            payload_mode = payload.get("mode")
            if payload_mode is not None and payload_mode != mode:
                continue

            runid = payload.get("runid")
            root = payload.get("root")
            if isinstance(runid, str) and isinstance(root, str):
                completed.add((runid, root))

    return completed


def _append_audit(audit_log: Path, payload: dict[str, Any]) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _active_run_lock_keys(runid: str) -> list[str]:
    statuses = lock_statuses(runid)
    return sorted(name for name, locked in statuses.items() if locked)


def _remove_archive_after_restore(archive_path: Path) -> bool:
    if not archive_path.exists():
        return False
    if archive_path.is_dir():
        raise RuntimeError(f"expected archive file at {archive_path}, found directory")
    archive_path.unlink()
    return True


def _base_event(
    *,
    runid: str,
    wd: Path,
    root: str,
    dry_run: bool,
    mode: MigrationMode,
) -> dict[str, Any]:
    return {
        "ts": _now_iso(),
        "runid": runid,
        "wd": str(wd),
        "root": root,
        "dry_run": dry_run,
        "mode": mode,
    }


def _process_run(
    *,
    wd: Path,
    roots: tuple[NoDirRoot, ...],
    mode: MigrationMode,
    remove_archive_on_restore: bool,
    dry_run: bool,
    resume_pairs: set[tuple[str, str]],
    resume_enabled: bool,
    audit_log: Path,
    verbose: bool,
) -> dict[str, int]:
    runid = wd.name
    counters: dict[str, int] = {
        "processed": 0,
        "completed": 0,
        "failed": 0,
        "resumed": 0,
    }

    readonly = (wd / "READONLY").exists()

    if not dry_run:
        try:
            active_locks = _active_run_lock_keys(runid)
        except _RECOVERABLE_EXCEPTIONS as exc:
            for root in roots:
                event = _base_event(runid=runid, wd=wd, root=root, dry_run=dry_run, mode=mode)
                event.update(
                    {
                        "status": "exception",
                        "message": f"failed reading run lock state: {exc}",
                        "details": str(exc),
                        "duration_ms": 0,
                    }
                )
                _append_audit(audit_log, event)
                counters["processed"] += 1
                counters["failed"] += 1
            return counters

        if active_locks:
            for root in roots:
                event = _base_event(runid=runid, wd=wd, root=root, dry_run=dry_run, mode=mode)
                event.update(
                    {
                        "status": "active_run_locked",
                        "message": "run has active NoDb lock(s)",
                        "active_locks": active_locks,
                        "duration_ms": 0,
                    }
                )
                _append_audit(audit_log, event)
                counters["processed"] += 1
                counters["failed"] += 1
            return counters

    for root in roots:
        if resume_enabled and not dry_run and (runid, root) in resume_pairs:
            event = _base_event(runid=runid, wd=wd, root=root, dry_run=dry_run, mode=mode)
            event.update(
                {
                    "status": "resume_skipped",
                    "message": "already completed in prior audit log",
                    "duration_ms": 0,
                }
            )
            _append_audit(audit_log, event)
            counters["processed"] += 1
            counters["resumed"] += 1
            continue

        started = perf_counter()
        event = _base_event(runid=runid, wd=wd, root=root, dry_run=dry_run, mode=mode)

        if not readonly and not dry_run:
            event.update(
                {
                    "status": "readonly_required",
                    "message": "WD/READONLY is required before NoDir bulk migration",
                    "duration_ms": 0,
                }
            )
            _append_audit(audit_log, event)
            counters["processed"] += 1
            counters["failed"] += 1
            continue

        try:
            if dry_run:
                target = nodir_resolve(str(wd), root, view="effective")
                if target is None:
                    event.update(
                        {
                            "status": "missing_root",
                            "message": "root is missing; nothing to migrate",
                        }
                    )
                    counters["completed"] += 1
                elif mode == "archive" and target.form == "archive":
                    event.update(
                        {
                            "status": "already_archive",
                            "message": "root already archived",
                        }
                    )
                    counters["completed"] += 1
                elif mode == "archive":
                    event.update(
                        {
                            "status": "archive_mode_retired",
                            "message": "archive mode is retired in directory-only runtime; no mutation will run",
                        }
                    )
                elif target.form == "dir":
                    event.update(
                        {
                            "status": "already_directory",
                            "message": "root already in directory form",
                        }
                    )
                    counters["completed"] += 1
                else:
                    event.update(
                        {
                            "status": "would_restore",
                            "message": "root is archived and would be restored to directory form",
                        }
                    )
            else:
                with maintenance_lock(str(wd), root, purpose="nodir-bulk-migration") as lock:
                    target = nodir_resolve(str(wd), root, view="effective")
                    if target is None:
                        event.update(
                            {
                                "status": "missing_root",
                                "message": "root is missing; nothing to migrate",
                            }
                        )
                        counters["completed"] += 1
                    elif mode == "archive" and target.form == "archive":
                        event.update(
                            {
                                "status": "already_archive",
                                "message": "root already archived",
                            }
                        )
                        counters["completed"] += 1
                    elif mode == "archive":
                        raise NoDirError(
                            http_status=409,
                            code="NODIR_ARCHIVE_RETIRED",
                            message=(
                                "archive mode is retired in directory-only runtime; "
                                "no mutation was performed"
                            ),
                        )
                    elif target.form == "dir":
                        event.update(
                            {
                                "status": "already_directory",
                                "message": "root already in directory form",
                            }
                        )
                        counters["completed"] += 1
                        resume_pairs.add((runid, root))
                    else:
                        thaw_locked(str(wd), root, lock=lock)
                        archive_path = wd / f"{root}.nodir"
                        archive_removed = False
                        if remove_archive_on_restore:
                            archive_removed = _remove_archive_after_restore(archive_path)

                        event.update(
                            {
                                "status": "restored",
                                "message": (
                                    "root restored to directory form and archive removed"
                                    if remove_archive_on_restore and archive_removed
                                    else "root restored to directory form"
                                ),
                            }
                        )
                        if remove_archive_on_restore:
                            event["archive_removed"] = archive_removed
                        counters["completed"] += 1
                        resume_pairs.add((runid, root))
        except NoDirError as err:
            if err.code == "NODIR_LOCKED":
                event.update(
                    {
                        "status": "root_lock_failed",
                        "code": err.code,
                        "http_status": err.http_status,
                        "message": err.message,
                    }
                )
            else:
                event.update(
                    {
                        "status": "nodir_error",
                        "code": err.code,
                        "http_status": err.http_status,
                        "message": err.message,
                    }
                )
            counters["failed"] += 1
        except _RECOVERABLE_EXCEPTIONS as exc:
            event.update(
                {
                    "status": "exception",
                    "message": str(exc),
                    "details": str(exc),
                }
            )
            counters["failed"] += 1
        finally:
            duration_ms = int((perf_counter() - started) * 1000)
            event["duration_ms"] = duration_ms
            _append_audit(audit_log, event)
            counters["processed"] += 1
            if verbose:
                print(
                    f"[{runid}:{root}] {event.get('status')}"
                    f" ({duration_ms} ms): {event.get('message')}"
                )

    return counters


def crawl_runs(
    *,
    scan_roots: Iterable[Path],
    roots: Iterable[str],
    mode: MigrationMode = "archive",
    remove_archive_on_restore: bool = False,
    runids: Iterable[str] = (),
    limit: int | None = None,
    dry_run: bool = False,
    audit_log: Path,
    resume: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    if remove_archive_on_restore and mode != "restore":
        raise ValueError("--remove-archive-on-restore requires mode=restore")

    selected_roots = _normalize_roots(roots)
    runid_filter = {value for value in runids if value}

    run_dirs = _discover_run_dirs(scan_roots)
    if runid_filter:
        run_dirs = [path for path in run_dirs if path.name in runid_filter]

    if limit is not None:
        run_dirs = run_dirs[: max(0, limit)]

    resume_pairs = _load_resume_pairs(audit_log, mode=mode) if resume and not dry_run else set()

    totals = {
        "runs": len(run_dirs),
        "processed": 0,
        "completed": 0,
        "failed": 0,
        "resumed": 0,
    }

    for run_dir in run_dirs:
        run_counts = _process_run(
            wd=run_dir,
            roots=selected_roots,
            mode=mode,
            remove_archive_on_restore=remove_archive_on_restore,
            dry_run=dry_run,
            resume_pairs=resume_pairs,
            resume_enabled=resume,
            audit_log=audit_log,
            verbose=verbose,
        )
        totals["processed"] += run_counts["processed"]
        totals["completed"] += run_counts["completed"]
        totals["failed"] += run_counts["failed"]
        totals["resumed"] += run_counts["resumed"]

    totals["audit_log"] = str(audit_log)
    totals["dry_run"] = dry_run
    totals["roots"] = list(selected_roots)
    totals["mode"] = mode
    totals["remove_archive_on_restore"] = bool(remove_archive_on_restore)
    return totals


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bulk-migrate NoDir roots across runs with safety gates and resumable JSONL audit logs."
    )
    parser.add_argument(
        "--runs-root",
        action="append",
        dest="runs_roots",
        default=[],
        help="Root directory to crawl for runs (repeatable). Default: /wc1/runs",
    )
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        default=[],
        choices=sorted(NODIR_ROOTS),
        help="NoDir root name to migrate (repeatable). Defaults to all allowlisted roots.",
    )
    parser.add_argument(
        "--mode",
        choices=("archive", "restore"),
        default="archive",
        help="Migration direction: archive directory roots or restore archives to directories.",
    )
    parser.add_argument(
        "--remove-archive-on-restore",
        action="store_true",
        help="After successful restore, delete `<root>.nodir` archive (restore mode only).",
    )
    parser.add_argument(
        "--runid",
        action="append",
        default=[],
        help="Only process these run IDs (repeatable).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of discovered runs to process after filtering.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and audit without mutating any runs.",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("nodir_bulk_migration_audit.jsonl"),
        help="JSONL audit log path used for evidence and resume tracking.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip run/root pairs that were already completed in prior audit logs.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-root status lines.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.remove_archive_on_restore and args.mode != "restore":
        parser.error("--remove-archive-on-restore requires --mode restore")

    roots = args.roots or list(NODIR_ROOTS)
    scan_roots = [Path(value) for value in args.runs_roots if value]
    if not scan_roots:
        scan_roots = [Path("/wc1/runs")]

    try:
        summary = crawl_runs(
            scan_roots=scan_roots,
            roots=roots,
            mode=args.mode,
            remove_archive_on_restore=args.remove_archive_on_restore,
            runids=args.runid,
            limit=args.limit,
            dry_run=args.dry_run,
            audit_log=args.audit_log.expanduser().resolve(),
            resume=not args.no_resume,
            verbose=args.verbose,
        )
    except _RECOVERABLE_EXCEPTIONS as exc:  # pragma: no cover - CLI safety
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, sort_keys=True))

    if args.dry_run:
        return 0
    if summary.get("failed", 0):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
