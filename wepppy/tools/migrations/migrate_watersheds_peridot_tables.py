from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Iterable, Iterator

import pyarrow.parquet as pq


def _discover_run_dirs(root: Path, *, max_depth: int | None) -> Iterator[Path]:
    """Yield run directories that contain a ``watershed`` subdirectory."""
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path '{root}' is not a directory")

    seen: set[Path] = set()
    for watersheds in root.rglob("watershed"):
        if not watersheds.is_dir():
            continue
        try:
            rel_parts = watersheds.relative_to(root).parts
        except ValueError:
            continue

        if max_depth is not None and len(rel_parts) > max_depth:
            continue

        run_dir = watersheds.parent
        if run_dir in seen:
            continue
        seen.add(run_dir)
        yield run_dir


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standardize watershed tables for Peridot-backed runs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/wc1/runs"),
        help="Root directory containing run workspaces (default: /wc1/runs).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum depth (relative to root) to search for watershed directories.",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="Only process run paths that contain this substring. "
        "May be provided multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of runs processed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List runs that would be migrated without making changes.",
    )
    parser.add_argument(
        "--keep-csv",
        action="store_true",
        help="Do not delete legacy CSV files after migration.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress information for each run.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("migrate_watersheds.log"),
        help="Path to append migration metrics (default: migrate_watersheds.log in CWD).",
    )
    return parser.parse_args(list(argv))


def _matches_filters(run_dir: Path, substrings: Iterable[str]) -> bool:
    if not substrings:
        return True
    text = str(run_dir)
    return any(substring in text for substring in substrings)


def _collect_metrics(run_dir: Path) -> dict[str, object]:
    """Capture simple row-count metrics for watershed parquet outputs."""
    metrics: dict[str, object] = {}
    watershed_dir = run_dir / "watershed"
    if not watershed_dir.exists():
        return metrics

    for stem in ("hillslopes", "channels", "flowpaths"):
        path = watershed_dir / f"{stem}.parquet"
        key = f"{stem}_rows"
        if not path.exists():
            metrics[key] = 0
            continue
        try:
            meta = pq.read_metadata(path)
            metrics[key] = meta.num_rows
        except Exception:
            metrics[key] = "metadata_error"
    return metrics


def _log_run_event(
    log_fp,
    run_dir: Path,
    status: str,
    duration: float,
    metrics: dict[str, object],
    error_text: str | None,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    parts = [
        f"time={timestamp}",
        f"run={run_dir}",
        f"status={status}",
        f"duration_ms={int(duration * 1000)}",
    ]
    for key in sorted(metrics):
        parts.append(f"{key}={metrics[key]}")
    if error_text:
        parts.append(f"error={error_text}")
    log_fp.write(" ".join(parts) + "\n")
    log_fp.flush()


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    total = migrated = skipped = failed = 0
    migrate_fn = None
    try:
        run_dirs = list(_discover_run_dirs(args.root, max_depth=args.max_depth))
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.limit is not None:
        run_dirs = run_dirs[: args.limit]

    log_path = args.log_file.expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as log_fp:
        for idx, run_dir in enumerate(run_dirs, start=1):
            if not _matches_filters(run_dir, args.contains):
                continue

            total += 1
            if args.verbose or args.dry_run:
                print(f"[{total}/{len(run_dirs)}] {run_dir}")

            status = "pending"
            error_text = None
            metrics: dict[str, object] = {}
            start = perf_counter()

            try:
                if args.dry_run:
                    status = "dry-run"
                    metrics = _collect_metrics(run_dir)
                    skipped += 1
                else:
                    if migrate_fn is None:
                        from wepppy.topo.peridot.peridot_runner import migrate_watershed_outputs

                        migrate_fn = migrate_watershed_outputs

                    changed = migrate_fn(
                        str(run_dir),
                        remove_csv=not args.keep_csv,
                        verbose=args.verbose,
                    )
                    metrics = _collect_metrics(run_dir)
                    if changed:
                        status = "migrated"
                        migrated += 1
                        if args.verbose:
                            print("  ✓ migrated")
                    else:
                        status = "unchanged"
                        skipped += 1
                        if args.verbose:
                            print("  → already up to date")
            except Exception as exc:  # pragma: no cover - operational script safeguard
                failed += 1
                status = "failed"
                error_text = str(exc)
                print(f"  ! Failed to migrate {run_dir}: {exc}", file=sys.stderr)
                if args.verbose:
                    traceback.print_exc()
            finally:
                if not metrics:
                    metrics = _collect_metrics(run_dir)
                duration = perf_counter() - start
                _log_run_event(log_fp, run_dir, status, duration, metrics, error_text)

        summary = (
            f"Runs processed: {total}, migrated: {migrated}, "
            f"unchanged: {skipped}, failed: {failed}"
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        log_fp.write(f"time={timestamp} event=summary {summary}\n")
        log_fp.flush()

    print(summary)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
