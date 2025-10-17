from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable

import pandas as pd


def _discover_run_dirs(root: Path) -> Iterable[Path]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path '{root}' is not a directory")

    for landuse_dir in root.rglob("landuse"):
        if landuse_dir.is_dir():
            yield landuse_dir.parent


def _matches_filters(run_dir: Path, substrings: Iterable[str]) -> bool:
    if not substrings:
        return True
    text = str(run_dir)
    return any(substring in text for substring in substrings)


def _translator_for_run(run_dir: Path):
    try:
        from wepppy.nodb.core import Watershed  # local import to avoid heavy dependencies at module import time
    except ModuleNotFoundError:
        return None

    try:
        watershed = Watershed.tryGetInstance(str(run_dir), ignore_lock=True)
        if watershed is None:
            return None
        return watershed.translator_factory()
    except Exception:
        return None


def _coerce_int32(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int32")


def _augment_dataframe(df: pd.DataFrame, translator):
    metrics: Dict[str, object] = {}
    changed = False

    if "topaz_id" not in df.columns and "TopazID" in df.columns:
        df["topaz_id"] = df["TopazID"]
        changed = True
    if "topaz_id" in df.columns:
        if str(df["topaz_id"].dtype) != "Int32":
            df["topaz_id"] = _coerce_int32(df["topaz_id"])
            changed = True
    metrics["topaz_id_column"] = int("topaz_id" in df.columns)

    if "wepp_id" in df.columns:
        if str(df["wepp_id"].dtype) != "Int32":
            df["wepp_id"] = _coerce_int32(df["wepp_id"])
            changed = True
    elif translator is not None and "topaz_id" in df.columns:
        wepp_values = []
        for top in df["topaz_id"]:
            if pd.isna(top):
                wepp_values.append(pd.NA)
            else:
                try:
                    value = translator.wepp(top=int(top))
                except Exception:
                    value = None
                wepp_values.append(value if value is not None else pd.NA)
        df["wepp_id"] = pd.Series(pd.array(wepp_values, dtype="Int32"))
        changed = True
    else:
        df["wepp_id"] = pd.Series(pd.array([pd.NA] * len(df), dtype="Int32"))
        changed = True

    metrics["wepp_id_nulls"] = int(pd.isna(df["wepp_id"]).sum())

    for legacy in ("TopazID", "WeppID"):
        if legacy in df.columns:
            df.drop(columns=[legacy], inplace=True)
            changed = True

    preferred = ["topaz_id", "wepp_id"]
    remaining = [c for c in df.columns if c not in preferred]
    df = df.loc[:, preferred + remaining]

    return df, metrics, changed


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standardize landuse parquet identifier columns.")
    parser.add_argument("--root", type=Path, default=Path("/wc1/runs"))
    parser.add_argument("--contains", action="append", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-file", type=Path, default=Path("migrate_landuse.log"))
    parser.add_argument("--verbose", action="store_true")
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

            landuse_fn = run_dir / "landuse" / "landuse.parquet"
            if not landuse_fn.exists():
                _log(log_fp, run_dir, "missing", 0, {}, None)
                skipped += 1
                continue

            start = perf_counter()
            status = "unchecked"
            error_text = None
            metrics: Dict[str, object] = {}

            try:
                df = pd.read_parquet(landuse_fn)
                metrics["rows"] = len(df)

                translator = _translator_for_run(run_dir)
                df, extra_metrics, changed = _augment_dataframe(df, translator)
                metrics.update(extra_metrics)

                if args.dry_run:
                    status = "dry-run"
                    skipped += 1
                elif changed:
                    df.to_parquet(landuse_fn, index=False)
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
            _log(log_fp, run_dir, status, duration_ms, metrics, error_text)

    summary = (
        f"Runs processed: {total}, migrated: {migrated}, "
        f"unchanged/dry-run: {skipped}, failed: {failed}"
    )
    print(summary)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
