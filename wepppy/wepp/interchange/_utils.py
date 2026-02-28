from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from wepppy.io_wait import wait_for_path
from wepppy.runtime_paths.errors import nodir_migration_required

logger = logging.getLogger(__name__)

CalendarLookup = Dict[int, List[Tuple[int, int]]]

def _wait_for_path(path: Path | str, timeout=60.0, poll=0.5):
    """
    Wait for ``path`` to become available before attempting to read it.
    Dockerized deployments occasionally surface slower I/O, so give the
    filesystem a chance to catch up before raising.
    """
    wait_for_path(
        path,
        timeout_s=float(timeout),
        poll_s=float(poll),
        require_stable_size=True,
        logger=logger,
    )

def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 0.0
    # Fortran overflow placeholders ("*****") should round-trip as NaN.
    if set(stripped) == {"*"}:
        return float("nan")
    if stripped[0] == ".":
        stripped = f"0{stripped}"
    try:
        return float(stripped)
    except ValueError:
        if "E" not in stripped.upper():
            if "-" in stripped[1:]:
                return float(stripped.replace("-", "E-", 1))
            if "+" in stripped[1:]:
                return float(stripped.replace("+", "E+", 1))
        return float(stripped)


def _julian_to_calendar(
    year: int,
    julian: int,
    *,
    calendar_lookup: Optional[CalendarLookup] = None,
) -> tuple[int, int]:
    """Convert a Julian day to month/day-of-month, honoring CLI calendars when available."""
    if calendar_lookup:
        lookup_year = int(year)
        if lookup_year in calendar_lookup:
            days = calendar_lookup.get(lookup_year, [])
            if 0 < julian <= len(days):
                month, day = days[julian - 1]
                return int(month), int(day)

    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


def _calendar_day_to_julian(
    year: int,
    month: int,
    day_of_month: int,
    *,
    calendar_lookup: Optional[CalendarLookup] = None,
) -> int:
    """Convert calendar day to julian using CLI calendar when available."""
    if calendar_lookup:
        # Prefer the exact year, but if absent fall back to any available calendar;
        # this keeps empirical (non-Gregorian) day counts intact.
        lookup_year = calendar_lookup.get(int(year))
        candidate_years = [lookup_year] if lookup_year is not None else list(calendar_lookup.values())
        for days in candidate_years:
            for idx, (m, d) in enumerate(days):
                if int(m) == int(month) and int(d) == int(day_of_month):
                    return idx + 1
        raise ValueError(
            f"Date {year}-{month}-{day_of_month} not found in CLI calendar lookup "
            f"(available years: {sorted(calendar_lookup.keys())})"
        )

    try:
        return (datetime(year, month, day_of_month) - datetime(year, 1, 1)).days + 1
    except ValueError as exc:
        raise ValueError(
            f"Invalid date {year}-{month}-{day_of_month} with no CLI calendar lookup; "
            f"ensure climate/wepp_cli.parquet exists with year/month/day columns."
        ) from exc


def _compute_sim_day_index(
    year: int,
    julian: int,
    *,
    start_year: int,
    calendar_lookup: Optional[CalendarLookup] = None,
) -> int:
    """Compute simulation day index without assuming Gregorian leap rules."""
    if calendar_lookup:
        offset = 0
        exhaustive = True
        for current_year in range(start_year, year):
            days = calendar_lookup.get(current_year)
            if days is None:
                exhaustive = False
                break
            offset += len(days)
        if exhaustive:
            return offset + julian

    try:
        base = datetime(start_year, 1, 1)
        target = datetime(year, 1, 1) + timedelta(days=julian - 1)
        return (target - base).days + 1
    except ValueError:
        return julian


def _ensure_cli_parquet(
    cli_dir: Path,
    *,
    cli_file_hint: Optional[str] = None,
    log: Optional[logging.Logger] = None,
) -> Optional[Path]:
    """Ensure a CLI parquet exists for calendar lookup.

    Canonical location is ``climate/wepp_cli.parquet``.
    """
    cli_dir = Path(cli_dir)
    wd = cli_dir.parent
    canonical_path = cli_dir / "wepp_cli.parquet"
    retired_root_path = wd / "climate.wepp_cli.parquet"

    if canonical_path.exists():
        return canonical_path
    if retired_root_path.exists():
        raise nodir_migration_required(
            "Retired root resource 'climate.wepp_cli.parquet' detected; "
            "migration to 'climate/wepp_cli.parquet' is required."
        )

    cli_path: Optional[Path] = None
    if cli_file_hint:
        candidate = Path(cli_dir) / cli_file_hint
        if candidate.exists():
            cli_path = candidate

    if cli_path is None:
        cli_candidates = sorted(Path(cli_dir).glob("*.cli"))
        if cli_candidates:
            cli_path = cli_candidates[0]

    if cli_path is None or not cli_path.exists():
        return None

    try:
        from wepppy.climates.cligen.cligen import ClimateFile

        cli_df = ClimateFile(str(cli_path)).as_dataframe(calc_peak_intensities=True)
        export_df = cli_df.copy()
        export_df["year"] = export_df.get("year")
        export_df["month"] = export_df.get("mo")
        export_df["day_of_month"] = export_df.get("da")
        if {"year", "month", "day_of_month"}.issubset(export_df.columns):
            date_df = export_df[["year", "month", "day_of_month"]].copy()
            for col in ("year", "month", "day_of_month"):
                date_df[col] = pd.to_numeric(date_df[col], errors="coerce")
            date_df = date_df.dropna()
            if not date_df.empty:
                date_df["year"] = date_df["year"].astype(int)
                date_df["month"] = date_df["month"].astype(int)
                date_df["day_of_month"] = date_df["day_of_month"].astype(int)
                ordered = date_df.sort_values(["year", "month", "day_of_month"])
                ordered["julian"] = ordered.groupby("year").cumcount() + 1
                year_counts = ordered.groupby("year")["julian"].max().sort_index()
                offsets = year_counts.cumsum().shift(fill_value=0)
                ordered["sim_day_index"] = ordered["julian"] + ordered["year"].map(offsets)
                export_df["julian"] = ordered["julian"].reindex(export_df.index).astype("Int64")
                export_df["sim_day_index"] = ordered["sim_day_index"].reindex(export_df.index).astype("Int64")
        export_df["peak_intensity_10"] = export_df.get("10-min Peak Rainfall Intensity (mm/hour)")
        export_df["peak_intensity_15"] = export_df.get("15-min Peak Rainfall Intensity (mm/hour)")
        export_df["peak_intensity_30"] = export_df.get("30-min Peak Rainfall Intensity (mm/hour)")
        export_df["storm_duration_hours"] = export_df.get("dur")
        export_df["storm_duration"] = export_df.get("dur")

        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        export_df.to_parquet(canonical_path, index=False)
        return canonical_path
    except Exception:
        (log or logger).exception("Failed to materialize CLI parquet", extra={"cli_path": str(cli_path)})
        return None


def _build_cli_calendar_lookup(
    wepp_output_dir: Path,
    *,
    climate_files: Optional[Sequence[str]] = None,
    log: Optional[logging.Logger] = None,
) -> CalendarLookup:
    """Return a per-year calendar lookup derived from the CLI parquet when available."""
    base = Path(wepp_output_dir)
    cli_dir: Optional[Path] = None
    for candidate in (base, *base.parents):
        maybe_cli = candidate / "climate"
        if maybe_cli.exists():
            cli_dir = maybe_cli
            break

    if cli_dir is None:
        return {}

    cli_hint = None
    if climate_files:
        for name in climate_files:
            if name:
                cli_hint = name
                break

    parquet_path = _ensure_cli_parquet(cli_dir, cli_file_hint=cli_hint, log=log)
    if parquet_path is None or not parquet_path.exists():
        return {}

    try:
        import pyarrow.parquet as pq

        table = pq.read_table(parquet_path)
    except Exception:
        (log or logger).debug("Unable to read CLI parquet for calendar lookup", exc_info=True)
        return {}

    available = set(table.schema.names)
    if "year" not in available:
        return {}

    month_column = "month" if "month" in available else "mo" if "mo" in available else None
    day_column = "day_of_month" if "day_of_month" in available else "da" if "da" in available else None
    if month_column is None or day_column is None:
        return {}

    df = table.select(["year", month_column, day_column]).to_pandas()
    df.sort_values(["year", month_column, day_column], inplace=True)

    lookup: CalendarLookup = {}
    for year, group in df.groupby("year"):
        lookup[int(year)] = list(
            zip(group[month_column].astype(int).tolist(), group[day_column].astype(int).tolist())
        )
    return lookup
