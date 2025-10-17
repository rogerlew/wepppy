from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable, Iterator, List, Tuple


TARGET_FILES = (
    "channels.geojson",
    "channels.WGS.geojson",
    "subcatchments.geojson",
    "subcatchments.WGS.geojson",
)


def _discover_run_dirs(root: Path) -> Iterator[Path]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path '{root}' is not a directory")

    for watersheds in root.rglob("watershed"):
        if watersheds.is_dir():
            yield watersheds.parent


def _matches_filters(run_dir: Path, substrings: Iterable[str]) -> bool:
    if not substrings:
        return True
    text = str(run_dir)
    return any(substring in text for substring in substrings)


def _existing_geojsons(run_dir: Path) -> List[Path]:
    wbt_dir = run_dir / "dem" / "wbt"
    if not wbt_dir.exists():
        return []
    paths = []
    for name in TARGET_FILES:
        path = wbt_dir / name
        if path.exists():
            paths.append(path)
    return paths


def _coerce_int(value) -> Tuple[bool, object]:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        try:
            ivalue = int(str(value))
        except (TypeError, ValueError):
            return False, value
    return (ivalue != value), ivalue


def _normalize_feature(props: Dict[str, object]) -> bool:
    changed = False
    for key in ("TopazID", "WeppID"):
        if key in props:
            delta, coerced = _coerce_int(props[key])
            if delta:
                props[key] = coerced
                changed = True
    if "Order" in props:
        delta, coerced = _coerce_int(props["Order"])
        if delta:
            props["Order"] = coerced
            changed = True
    return changed


def _process_geojson(path: Path, *, dry_run: bool) -> Tuple[int, int, bool]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    features = data.get("features")
    if not isinstance(features, list):
        return 0, 0, False

    total = len(features)
    changed_features = 0
    any_changes = False

    for feature in features:
        props = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(props, dict):
            continue
        if _normalize_feature(props):
            changed_features += 1
            any_changes = True

    if any_changes and not dry_run:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, allow_nan=False)

    return total, changed_features, any_changes


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize TopazID/WeppID numeric values in WBT GeoJSON assets."
    )
    parser.add_argument("--root", type=Path, default=Path("/wc1/runs"))
    parser.add_argument("--contains", action="append", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-file", type=Path, default=Path("migrate_wbt_geojson.log"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(list(argv))


def _log_run_event(log_fp, run_dir: Path, status: str, duration_ms: int, metrics: Dict[str, object], error: str | None) -> None:
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

            geojson_paths = _existing_geojsons(run_dir)
            if not geojson_paths:
                _log_run_event(log_fp, run_dir, "no-assets", 0, {}, None)
                skipped += 1
                continue

            start = perf_counter()
            run_metrics: Dict[str, object] = {}
            status = "unchecked"
            error_text = None
            any_changes = False

            try:
                for path in geojson_paths:
                    total_rows, modified_rows, changed = _process_geojson(path, dry_run=args.dry_run)
                    key_prefix = path.name.replace(".", "_")
                    run_metrics[f"{key_prefix}_features"] = total_rows
                    run_metrics[f"{key_prefix}_updated"] = modified_rows
                    any_changes = any_changes or changed
                if args.dry_run:
                    status = "dry-run"
                    skipped += 1
                else:
                    if any_changes:
                        status = "migrated"
                        migrated += 1
                    else:
                        status = "unchanged"
                        skipped += 1
            except Exception as exc:  # pragma: no cover - defensive logging
                status = "failed"
                error_text = str(exc)
                failed += 1
                print(f"  ! Failed to process {run_dir}: {exc}", file=sys.stderr)
                if args.verbose:
                    traceback.print_exc()

            duration_ms = int((perf_counter() - start) * 1000)
            _log_run_event(log_fp, run_dir, status, duration_ms, run_metrics, error_text)

    summary = (
        f"Runs processed: {total}, migrated: {migrated}, "
        f"unchanged/dry-run: {skipped}, failed: {failed}"
    )
    print(summary)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

