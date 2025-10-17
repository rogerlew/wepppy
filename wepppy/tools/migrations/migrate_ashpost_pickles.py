from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable


TARGET_PICKLES = ("*.pkl",)
RAW_ASH_PATTERNS = ("H*.parquet",)


def _discover_run_dirs(root: Path) -> Iterable[Path]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path '{root}' is not a directory")

    for ash_dir in root.rglob("ash"):
        if ash_dir.is_dir():
            yield ash_dir.parent


def _matches_filters(run_dir: Path, substrings: Iterable[str]) -> bool:
    if not substrings:
        return True
    text = str(run_dir)
    return any(substring in text for substring in substrings)


def _collect_pickles(post_dir: Path) -> list[Path]:
    pickles: list[Path] = []
    for pattern in TARGET_PICKLES:
        pickles.extend(post_dir.glob(pattern))
    return pickles


def _has_raw_parquet(ash_dir: Path) -> bool:
    for pattern in RAW_ASH_PATTERNS:
        if any(ash_dir.glob(pattern)):
            return True
    return False


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild ashpost parquet outputs when legacy .pkl artifacts are present.")
    parser.add_argument("--root", type=Path, default=Path("/wc1/runs"))
    parser.add_argument("--contains", action="append", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-file", type=Path, default=Path("migrate_ashpost.log"))
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--remove-pickles", action="store_true", help="Delete legacy .pkl files after successful migration.")
    return parser.parse_args(list(argv))


def _log(log_fp, run_dir: Path, status: str, duration_ms: int, metrics: Dict[str, object], error: str | None) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    parts = [
        f"time={timestamp}",
        f"run={run_dir}",
        f"status={status}",
        f"duration_ms={duration_ms}",
    ]
    for key in sorted(metrics):
        parts.append(f"{key}={metrics[key]}")
    if error:
        parts.append(f"error={error}")
    log_fp.write(" ".join(parts) + "\n")
    log_fp.flush()


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        run_dirs = list(_discover_run_dirs(args.root))
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.limit is not None:
        run_dirs = run_dirs[: args.limit]

    log_path = args.log_file.expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    total = migrated = skipped = failed = 0

    with log_path.open("a", encoding="utf-8") as log_fp:
        for idx, run_dir in enumerate(run_dirs, start=1):
            if not _matches_filters(run_dir, args.contains):
                continue

            total += 1
            if args.verbose:
                print(f"[{total}/{len(run_dirs)}] {run_dir}")

            ash_dir = run_dir / "ash"
            post_dir = ash_dir / "post"
            pickle_paths = _collect_pickles(post_dir)
            if not pickle_paths:
                _log(log_fp, run_dir, "no-pickles", 0, {}, None)
                skipped += 1
                continue

            start = perf_counter()
            status = "unchecked"
            error_text = None
            metrics: Dict[str, object] = {
                "pickles": len(pickle_paths),
                "raw_parquet": int(_has_raw_parquet(ash_dir)),
            }

            if args.dry_run:
                status = "dry-run"
                skipped += 1
            else:
                try:
                    from wepppy.nodb.mods.ash_transport import Ash, AshPost  # pylint: disable=import-error
                except ModuleNotFoundError as exc:  # likely redis dependency missing
                    status = "failed"
                    error_text = f"Missing dependency while importing ash modules: {exc}"
                    failed += 1
                else:
                    try:
                        ash = Ash.getInstance(str(run_dir))
                        try:
                            ashpost = AshPost.getInstance(str(run_dir))
                        except FileNotFoundError:
                            cfg_name = f"{ash.config_stem}.cfg"
                            ashpost = AshPost(str(run_dir), cfg_name)
                        ashpost.run_post()
                        new_parquets = len(list(post_dir.glob("*.parquet")))
                        metrics["parquet_outputs"] = new_parquets
                        status = "migrated"
                        migrated += 1
                        if args.remove_pickles:
                            for path in pickle_paths:
                                try:
                                    path.unlink()
                                except OSError:
                                    pass
                    except Exception as exc:  # pragma: no cover - best effort logging
                        status = "failed"
                        error_text = str(exc)
                        failed += 1
                        print(f"  ! Failed to migrate {run_dir}: {exc}", file=sys.stderr)
                        if args.verbose:
                            traceback.print_exc()

            duration_ms = int((perf_counter() - start) * 1000)
            _log(log_fp, run_dir, status, duration_ms, metrics, error_text)

    summary = (
        f"Runs processed: {total}, migrated: {migrated}, "
        f"unchanged/dry-run: {skipped}, failed: {failed}"
    )
    print(summary)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

