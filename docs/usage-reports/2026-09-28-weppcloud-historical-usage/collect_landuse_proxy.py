"""Collect a throttled, privacy-safe land-cover proxy from production Parquet files.

Run inside the WEPPcloud container. The script reads one small Parquet file at a
time, sleeps between reads, and emits aggregate JSON only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.weppcloud.app import Run, User, app


AGRICULTURE_KEYS = {61, 81, 82}
NATURAL_KEYS = {
    41, 42, 43, 44, 51, 52, 71, 72, 73, 74, 90, 95,
    *range(105, 159),
}
DEVELOPED_KEYS = {21, 22, 23, 24}
WATER_SNOW_BARREN_KEYS = {11, 12, 31}
EXCLUDED_CONFIG_TOKENS = (
    "au", "canada", "chile", "earth", "eu", "nigeria", "tenerife",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--access-csv", default="/geodata/weppcloud_runs/access.csv")
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--batch-sleep-seconds", type=float, default=3.0)
    parser.add_argument("--progress-every", type=int, default=100)
    return parser.parse_args()


def authenticated_access(path: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            email = (row.get("user") or "").strip().lower()
            if email and email != "<anonymous>" and "@" in email:
                result[row["runid"]].add(email)
    return result


def is_supported_config(config: str | None) -> bool:
    value = (config or "").split("?", 1)[0].lower()
    return not any(
        value == token or value.startswith(f"{token}-")
        for token in EXCLUDED_CONFIG_TOKENS
    )


def parquet_path(run: Run) -> Path | None:
    wd = Path(run.wd)
    for candidate in (wd / "landuse" / "landuse.parquet", wd / "landuse.parquet"):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def class_shares(path: Path) -> dict[str, float] | None:
    table = pq.read_table(path, columns=["key", "pct_coverage"])
    frame = table.to_pandas()
    by_key: dict[int, float] = {}
    for row in frame.itertuples(index=False):
        try:
            key = int(row.key)
            coverage = float(row.pct_coverage)
        except (TypeError, ValueError):
            continue
        by_key[key] = max(coverage, by_key.get(key, 0.0))
    total = sum(by_key.values())
    if total <= 0:
        return None

    def share(keys: set[int]) -> float:
        return 100.0 * sum(value for key, value in by_key.items() if key in keys) / total

    known = AGRICULTURE_KEYS | NATURAL_KEYS | DEVELOPED_KEYS | WATER_SNOW_BARREN_KEYS
    return {
        "agriculture": share(AGRICULTURE_KEYS),
        "natural_seminatural": share(NATURAL_KEYS),
        "developed": share(DEVELOPED_KEYS),
        "water_snow_barren": share(WATER_SNOW_BARREN_KEYS),
        "other": 100.0 * sum(value for key, value in by_key.items() if key not in known) / total,
    }


def classification(shares: dict[str, float]) -> str:
    if shares["agriculture"] >= 50.0:
        return "agriculture_dominant"
    if shares["natural_seminatural"] >= 50.0:
        return "natural_seminatural_dominant"
    if shares["developed"] >= 50.0:
        return "developed_dominant"
    if shares["water_snow_barren"] >= 50.0:
        return "water_snow_barren_dominant"
    if shares["agriculture"] > 0 and shares["natural_seminatural"] > 0:
        return "mixed_agriculture_natural"
    return "mixed_or_other"


def main() -> None:
    args = parse_args()
    auth_by_run = authenticated_access(args.access_csv)

    with app.app_context():
        users = {str(user.id): user.email for user in User.query.all()}
        runs = Run.query.all()
        owner_days: dict[tuple[str, object], list[Run]] = defaultdict(list)
        for run in runs:
            if run.owner_id and run.date_created:
                owner_days[(str(run.owner_id), run.date_created.date())].append(run)

        sweep_ids: set[int] = set()
        for day_runs in owner_days.values():
            configs = {(run.config or "").split("?", 1)[0] for run in day_runs}
            if (
                len(day_runs) >= 10
                and len(configs) >= 10
                and len(configs) / len(day_runs) >= 0.70
            ):
                sweep_ids.update(run.id for run in day_runs)

        candidates: list[Run] = []
        for run in runs:
            if not run.date_created or run.id in sweep_ids:
                continue
            owner_email = users.get(str(run.owner_id)) if run.owner_id else None
            if not owner_email and not auth_by_run.get(run.runid):
                continue
            candidates.append(run)

        totals = Counter()
        by_year: dict[str, Counter[str]] = defaultdict(Counter)
        started = time.monotonic()

        for index, run in enumerate(candidates, start=1):
            year = str(run.date_created.year)
            if not is_supported_config(run.config):
                totals["unsupported_locale_or_source"] += 1
                by_year[year]["unsupported_locale_or_source"] += 1
                continue

            path = parquet_path(run)
            if path is None:
                totals["missing_landuse_parquet"] += 1
                by_year[year]["missing_landuse_parquet"] += 1
            else:
                try:
                    shares = class_shares(path)
                except (OSError, ValueError, TypeError, pa.ArrowException) as exc:
                    totals["read_error"] += 1
                    by_year[year]["read_error"] += 1
                    print(f"read error for {run.runid}: {exc}", file=sys.stderr)
                else:
                    if shares is None:
                        totals["unclassified_parquet"] += 1
                        by_year[year]["unclassified_parquet"] += 1
                    else:
                        category = classification(shares)
                        totals["classified_projects"] += 1
                        totals[category] += 1
                        by_year[year]["classified_projects"] += 1
                        by_year[year][category] += 1
                        if shares["agriculture"] >= 10.0:
                            totals["projects_with_at_least_10pct_agriculture"] += 1
                            by_year[year]["projects_with_at_least_10pct_agriculture"] += 1

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            if args.batch_size > 0 and index % args.batch_size == 0:
                if args.batch_sleep_seconds > 0:
                    time.sleep(args.batch_sleep_seconds)
            if args.progress_every > 0 and index % args.progress_every == 0:
                print(
                    f"processed={index}/{len(candidates)} "
                    f"classified={totals['classified_projects']} "
                    f"elapsed_s={time.monotonic() - started:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

    classified = totals["classified_projects"]
    result = {
        "method": "dominant-hillslope land-cover proxy from landuse/landuse.parquet",
        "taxonomy": {
            "agriculture": sorted(AGRICULTURE_KEYS),
            "natural_seminatural": sorted(NATURAL_KEYS),
            "developed": sorted(DEVELOPED_KEYS),
            "water_snow_barren": sorted(WATER_SNOW_BARREN_KEYS),
            "dominant_threshold_pct": 50,
        },
        "candidate_human_evidenced_projects": len(candidates),
        "totals": dict(totals),
        "by_year": {year: dict(counts) for year, counts in sorted(by_year.items())},
        "elapsed_seconds": time.monotonic() - started,
        "limitations": [
            "Parquet classes represent dominant hillslope assignments, not full raster pixels.",
            "Natural/semi-natural does not prove native vegetation.",
            "Historical files removed by TTL cannot be classified.",
            "Non-U.S. and known non-NLCD configurations are reported as unsupported.",
            "Post-fire and treatment keys are grouped with disturbed natural/semi-natural cover.",
            "Projects with non-finite coverage values fall into mixed/other/indeterminate.",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
