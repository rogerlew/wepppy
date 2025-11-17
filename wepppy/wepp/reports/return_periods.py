"""Return-period staging utilities for WEPP event datasets and derived reports."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.stats import weibull_series
from wepppy.climates.cligen import ClimateFile
from wepppy.query_engine import activate_query_engine, resolve_run_context, update_catalog_entry
LOGGER = logging.getLogger(__name__)

EVENTS_REL_PATH = Path("wepp/output/interchange/return_period_events.parquet")
RANKS_REL_PATH = Path("wepp/output/interchange/return_period_event_ranks.parquet")
EBE_DATASET = "wepp/output/interchange/ebe_pw0.parquet"
TOTALWATSED3_DATASET = "wepp/output/interchange/totalwatsed3.parquet"

CLIMATE_REQUIRED = {
    "year": ("year", "Year"),
    "month": ("month", "Month"),
    "day": ("day_of_month", "Day", "day"),
    "intensity_10": ("10-min Peak Rainfall Intensity (mm/hour)", "peak_intensity_10", "i10"),
    "intensity_15": ("15-min Peak Rainfall Intensity (mm/hour)", "peak_intensity_15", "i15"),
    "intensity_30": ("30-min Peak Rainfall Intensity (mm/hour)", "peak_intensity_30", "i30"),
    "duration": ("dur", "storm_duration_hours", "storm_duration"),
}


@dataclass(frozen=True)
class MeasureSpec:
    measure_id: str
    label: str
    value_column: str
    units: str
    optional: bool = False


MEASURE_SPECS: Tuple[MeasureSpec, ...] = (
    MeasureSpec("precip_depth", "Precipitation Depth", "precip_mm", "mm"),
    MeasureSpec("runoff_depth", "Runoff", "runoff_depth_mm", "mm"),
    MeasureSpec("peak_discharge", "Peak Discharge", "peak_discharge_m3s", "m^3/s"),
    MeasureSpec("sediment_yield", "Sediment Yield", "sediment_yield_tonnes", "tonne"),
    MeasureSpec("soluble_reactive_p", "Soluble Reactive P", "soluble_reactive_p_kg", "kg", optional=True),
    MeasureSpec("particulate_p", "Particulate P", "particulate_p_kg", "kg", optional=True),
    MeasureSpec("total_p", "Total P", "total_p_kg", "kg", optional=True),
    MeasureSpec("intensity_10min", "10-min Peak Rainfall Intensity", "intensity_10min", "mm/hour", optional=True),
    MeasureSpec("intensity_15min", "15-min Peak Rainfall Intensity", "intensity_15min", "mm/hour", optional=True),
    MeasureSpec("intensity_30min", "30-min Peak Rainfall Intensity", "intensity_30min", "mm/hour", optional=True),
    MeasureSpec("storm_duration", "Storm Duration", "storm_duration_hours", "hours", optional=True),
    MeasureSpec("hill_sediment", "Hill Sed Del", "hill_sediment_tonnes", "tonne", optional=True),
    MeasureSpec("hill_streamflow", "Hill Streamflow", "hill_streamflow_mm", "mm", optional=True),
)

MEASURE_LOOKUP: Dict[str, MeasureSpec] = {spec.measure_id: spec for spec in MEASURE_SPECS}


def _ensure_path(value: str | Path) -> Path:
    """Expand and validate that a run directory exists."""
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _quote_identifier(identifier: str) -> str:
    """Escape a DuckDB identifier so it can be referenced safely in SQL."""
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _generate_cli_parquet(base: Path) -> tuple[Path | None, Dict[str, str]]:
    """Materialize a climate parquet from an existing CLI when none are present."""
    cli_dir = base / "wepp" / "runs"
    if not cli_dir.exists():
        return None, {}

    for cli_candidate in sorted(cli_dir.glob("*.cli")):
        try:
            cli_df = ClimateFile(str(cli_candidate)).as_dataframe(calc_peak_intensities=True)
        except Exception:  # pragma: no cover - defensive
            continue

        export_df = cli_df.copy()
        export_df["year"] = export_df.get("year")
        export_df["month"] = export_df.get("mo")
        export_df["day_of_month"] = export_df.get("da")

        export_df["peak_intensity_10"] = export_df.get("10-min Peak Rainfall Intensity (mm/hour)")
        export_df["peak_intensity_15"] = export_df.get("15-min Peak Rainfall Intensity (mm/hour)")
        export_df["peak_intensity_30"] = export_df.get("30-min Peak Rainfall Intensity (mm/hour)")
        export_df["storm_duration_hours"] = export_df.get("dur")
        export_df["storm_duration"] = export_df.get("dur")

        climate_dir = base / "climate"
        climate_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = climate_dir / "wepp_cli.parquet"
        export_df.to_parquet(parquet_path, index=False)

        LOGGER.info(
            "Generated climate parquet from CLI for return-period staging",
            extra={"cli": str(cli_candidate), "parquet": str(parquet_path)},
        )

        return parquet_path, {
            "year": "year",
            "month": "month",
            "day": "day_of_month",
            "intensity_10": "peak_intensity_10",
            "intensity_15": "peak_intensity_15",
            "intensity_30": "peak_intensity_30",
            "duration": "storm_duration_hours",
        }

    return None, {}


def _discover_climate_asset(base: Path) -> tuple[Path, Dict[str, str]] | tuple[None, Dict[str, str]]:
    """Return a parquet climate asset plus column mapping if one exists."""
    climate_dir = base / "climate"
    if not climate_dir.exists():
        generated_path, generated_mapping = _generate_cli_parquet(base)
        if generated_path:
            return generated_path, generated_mapping
        return None, {}

    for candidate in sorted(climate_dir.rglob("*.parquet")):
        try:
            schema = pq.read_schema(candidate)
        except Exception:  # pragma: no cover - defensive
            continue
        columns = {field.name for field in schema}

        mapping: Dict[str, str] = {}
        for key, options in CLIMATE_REQUIRED.items():
            selected = next((name for name in options if name in columns), None)
            if selected:
                mapping[key] = selected

        if {"year", "month", "day"}.issubset(mapping):
            return candidate, mapping

    generated_path, generated_mapping = _generate_cli_parquet(base)
    if generated_path:
        return generated_path, generated_mapping

    return None, {}


def _build_topaz_filter(topaz_ids: Optional[Sequence[int]]) -> str:
    """Generate a SQL WHERE clause limiting events to the given Topaz IDs."""
    if not topaz_ids:
        return ""
    values = sorted({int(v) for v in topaz_ids})
    return f"WHERE e.element_id IN ({', '.join(str(v) for v in values)})"


def _build_raw_event_query(
    ebe_path: Path,
    tot_path: Path,
    climate_info: tuple[Path | None, Dict[str, str]],
    topaz_filter: str,
) -> str:
    """Compose the DuckDB SQL used to stage event metrics prior to ranking."""
    climate_path, columns = climate_info

    if climate_path is None or not columns:
        climate_join = ""
        intensity_10_expr = "CAST(NULL AS DOUBLE)"
        intensity_15_expr = "CAST(NULL AS DOUBLE)"
        intensity_30_expr = "CAST(NULL AS DOUBLE)"
        duration_expr = "CAST(NULL AS DOUBLE)"
    else:
        climate_alias = "climate"
        year_col = _quote_identifier(columns["year"])
        month_col = _quote_identifier(columns["month"])
        day_col = _quote_identifier(columns["day"])

        def _expr(key: str) -> str:
            column = columns.get(key)
            if column is None:
                return "CAST(NULL AS DOUBLE)"
            return f"{climate_alias}.{_quote_identifier(column)}"

        climate_join = f"""
        LEFT JOIN read_parquet('{climate_path.as_posix()}') AS {climate_alias}
          ON {climate_alias}.{year_col} = e.year
         AND {climate_alias}.{month_col} = e.month
         AND {climate_alias}.{day_col} = e.day_of_month
        """
        intensity_10_expr = _expr("intensity_10")
        intensity_15_expr = _expr("intensity_15")
        intensity_30_expr = _expr("intensity_30")
        duration_expr = _expr("duration")

    return f"""
        SELECT
            ROW_NUMBER() OVER () AS event_id,
            e.element_id AS topaz_id,
            e.simulation_year AS year,
            e.year AS calendar_year,
            e.month AS mo,
            e.day_of_month AS da,
            e.julian,
            e.water_year,
            e.precip AS precip_mm,
            e.runoff_volume AS runoff_volume_m3,
            CASE
                WHEN tot.Area IS NOT NULL AND tot.Area > 0
                    THEN (e.runoff_volume / tot.Area) * 1000.0
                ELSE NULL
            END AS runoff_depth_mm,
            e.peak_runoff AS peak_discharge_m3s,
            e.sediment_yield AS sediment_yield_kg,
            CASE WHEN e.sediment_yield IS NOT NULL THEN e.sediment_yield / 1000.0 ELSE NULL END AS sediment_yield_tonnes,
            e.soluble_pollutant AS soluble_reactive_p_kg,
            e.particulate_pollutant AS particulate_p_kg,
            e.total_pollutant AS total_p_kg,
            tot.Area AS contributing_area_m2,
            tot.tdet AS hill_sediment_kg,
            CASE WHEN tot.tdet IS NOT NULL THEN tot.tdet / 1000.0 ELSE NULL END AS hill_sediment_tonnes,
            tot."Streamflow" AS hill_streamflow_mm,
            {intensity_10_expr} AS intensity_10min,
            {intensity_15_expr} AS intensity_15min,
            {intensity_30_expr} AS intensity_30min,
            {duration_expr} AS storm_duration_hours
        FROM read_parquet('{ebe_path.as_posix()}') AS e
        LEFT JOIN read_parquet('{tot_path.as_posix()}') AS tot
          ON tot.year = e.year
         AND tot.month = e.month
         AND tot.day_of_month = e.day_of_month
        {climate_join}
        {topaz_filter}
    """


def _compute_event_counts(
    connection: duckdb.DuckDBPyConnection,
    ebe_path: Path,
    topaz_filter: str,
) -> pd.DataFrame:
    """Return per-topaz per-month event counts for downstream interpolation."""
    query = f"""
        SELECT
            e.element_id AS topaz_id,
            e.simulation_year AS year,
            e.month AS month,
            COUNT(*) AS event_count
        FROM read_parquet('{ebe_path.as_posix()}') AS e
        {topaz_filter}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """
    return connection.execute(query).df()


def _build_measure_union(select_alias: str = "event_data") -> str:
    """Return the SQL fragment that unpivots all measure columns for ranking."""
    statements: list[str] = []
    for spec in MEASURE_SPECS:
        statements.append(
            f"""
            SELECT
                '{spec.measure_id}' AS measure_id,
                topaz_id,
                event_id,
                {spec.value_column} AS measure_value
            FROM {select_alias}
            """
        )
    return "\nUNION ALL\n".join(statements)


def _serialize_metadata(mapping: Mapping[str, Any]) -> Dict[bytes, bytes]:
    """Encode a JSON-serializable mapping into Arrow schema metadata format."""
    payload: Dict[bytes, bytes] = {}
    for key, value in mapping.items():
        payload[key.encode("utf-8")] = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return payload


def refresh_return_period_events(
    wd: str | Path,
    *,
    topaz_ids: Optional[Sequence[int]] = None,
    max_rank: int = 128,
    buffer: int = 10,
) -> tuple[Path, Path]:
    """Regenerate the staged parquet assets that power return-period reports.

    Args:
        wd: Run directory that owns the interchange parquet files.
        topaz_ids: Optional subset of channel identifiers to rank.
        max_rank: Maximum rank that should be guaranteed in the staged table.
        buffer: Additional rows per measure retained beyond ``max_rank``.

    Returns:
        Tuple containing the paths to the staged ``events`` and ``ranks`` parquet files.
    """

    base = _ensure_path(wd)
    activate_query_engine(base, run_interchange=False)
    context = resolve_run_context(str(base), auto_activate=False)
    root_dir = context.base_dir

    ebe_path = root_dir / EBE_DATASET
    if not ebe_path.exists():
        alt_ebe = root_dir / "wepp" / "output" / "ebe_pw0.parquet"
        if alt_ebe.exists():
            ebe_path = alt_ebe
        else:
            raise FileNotFoundError(ebe_path)

    tot_path = root_dir / TOTALWATSED3_DATASET
    if not tot_path.exists():
        raise FileNotFoundError(tot_path)

    climate_info = _discover_climate_asset(root_dir)
    topaz_filter = _build_topaz_filter(topaz_ids)

    events_path = root_dir / EVENTS_REL_PATH
    ranks_path = root_dir / RANKS_REL_PATH
    events_path.parent.mkdir(parents=True, exist_ok=True)

    rank_limit = max(max_rank + buffer, max_rank)

    with duckdb.connect() as con:
        con.execute("PRAGMA threads=4")

        raw_event_query = _build_raw_event_query(ebe_path, tot_path, climate_info, topaz_filter)
        con.execute(f"CREATE OR REPLACE TEMP TABLE raw_events AS {raw_event_query}")

        counts_df = _compute_event_counts(con, ebe_path, topaz_filter)

        measure_union = _build_measure_union("raw_events")
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE ranked_events AS
            SELECT
                measure_id,
                topaz_id,
                event_id,
                measure_value,
                DENSE_RANK() OVER (
                    PARTITION BY measure_id, topaz_id
                    ORDER BY measure_value DESC NULLS LAST
                ) AS rank
            FROM (
                {measure_union}
            )
            WHERE measure_value IS NOT NULL
            """
        )

        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE return_period_events AS
            SELECT *
            FROM raw_events
            WHERE event_id IN (
                SELECT DISTINCT event_id
                FROM ranked_events
                WHERE rank <= {rank_limit}
            )
            """
        )

        event_table_reader = con.execute(
            """
            SELECT
                event_id,
                topaz_id,
                year,
                calendar_year,
                mo,
                da,
                julian,
                water_year,
                precip_mm,
                runoff_volume_m3,
                runoff_depth_mm,
                peak_discharge_m3s,
                sediment_yield_kg,
                sediment_yield_tonnes,
                soluble_reactive_p_kg,
                particulate_p_kg,
                total_p_kg,
                contributing_area_m2,
                hill_sediment_kg,
                hill_sediment_tonnes,
                hill_streamflow_mm,
                intensity_10min,
                intensity_15min,
                intensity_30min,
                storm_duration_hours
            FROM return_period_events
            ORDER BY topaz_id, event_id
            """
        ).arrow()
        event_table = (
            event_table_reader.read_all()
            if hasattr(event_table_reader, "read_all")
            else event_table_reader
        )

        ranks_table_reader = con.execute(
            f"""
            SELECT
                measure_id,
                topaz_id,
                event_id,
                rank,
                measure_value
            FROM ranked_events
            WHERE rank <= {rank_limit}
            ORDER BY measure_id, topaz_id, rank
            """
        ).arrow()
        ranks_table = (
            ranks_table_reader.read_all()
            if hasattr(ranks_table_reader, "read_all")
            else ranks_table_reader
        )

        wsarea_lookup = {}
        if event_table.num_rows > 0:
            tmp_df = event_table.select(["topaz_id", "contributing_area_m2"]).to_pandas()
            tmp_df = tmp_df.dropna(subset=["contributing_area_m2"])
            for topaz_id, group in tmp_df.groupby("topaz_id"):
                wsarea_lookup[str(int(topaz_id))] = float(group["contributing_area_m2"].max() / 10000.0)

        counts_payload = counts_df.to_dict(orient="records")
        measure_metadata = [
            {
                "measure_id": spec.measure_id,
                "label": spec.label,
                "units": spec.units,
                "optional": spec.optional,
                "value_column": spec.value_column,
            }
            for spec in MEASURE_SPECS
        ]

        events_metadata = _serialize_metadata(
            {
                "watershed_area_ha": wsarea_lookup,
                "event_schema_version": 1,
            }
        )
        ranks_metadata = _serialize_metadata(
            {
                "measure_metadata": measure_metadata,
                "event_counts": counts_payload,
                "rank_limit": rank_limit,
            }
        )

        event_table = event_table.combine_chunks().replace_schema_metadata(events_metadata)
        ranks_table = ranks_table.combine_chunks().replace_schema_metadata(ranks_metadata)

        pq.write_table(event_table, events_path, compression="snappy")
        pq.write_table(ranks_table, ranks_path, compression="snappy")

    try:
        update_catalog_entry(root_dir, str(EVENTS_REL_PATH))
    except FileNotFoundError:  # pragma: no cover - catalog may not exist yet
        activate_query_engine(root_dir, run_interchange=False)

    try:
        update_catalog_entry(root_dir, str(RANKS_REL_PATH))
    except FileNotFoundError:  # pragma: no cover
        activate_query_engine(root_dir, run_interchange=False)

    return events_path, ranks_path


class ReturnPeriodDataset:
    """Loader and façade for the staged return-period parquet datasets."""
    def __init__(
        self,
        wd: str | Path,
        *,
        auto_refresh: bool = True,
        max_rank: int = 128,
        buffer: int = 10,
    ) -> None:
        """Load the staged parquet files and optionally regenerate them first.

        Args:
            wd: Run directory containing the staged parquet files.
            auto_refresh: When ``True`` the staging pipeline is executed if either file is absent.
            max_rank: Maximum desired rank for ``auto_refresh`` operations.
            buffer: Additional rows retained beyond ``max_rank`` when auto-refreshing.
        """
        base = _ensure_path(wd)
        context = resolve_run_context(str(base), auto_activate=False)
        self._root = context.base_dir

        self._events_path = self._root / EVENTS_REL_PATH
        self._ranks_path = self._root / RANKS_REL_PATH

        if auto_refresh and (not self._events_path.exists() or not self._ranks_path.exists()):
            refresh_return_period_events(base, max_rank=max_rank, buffer=buffer)

        self._events_table = pq.read_table(self._events_path)
        self._ranks_table = pq.read_table(self._ranks_path)

        self._events = self._events_table.to_pandas()
        self._ranks = self._ranks_table.to_pandas()

        metadata_events = self._events_table.schema.metadata or {}
        metadata_ranks = self._ranks_table.schema.metadata or {}

        if b"watershed_area_ha" in metadata_events:
            wsarea_payload = json.loads(metadata_events[b"watershed_area_ha"].decode("utf-8"))
            self._watershed_area = {str(key): float(value) for key, value in wsarea_payload.items()}
        else:
            self._watershed_area = {}

        self._event_counts = pd.DataFrame(
            json.loads(metadata_ranks.get(b"event_counts", b"[]").decode("utf-8"))
        ) if b"event_counts" in metadata_ranks else pd.DataFrame(columns=["topaz_id", "year", "month", "event_count"])

        measure_payload = json.loads(metadata_ranks.get(b"measure_metadata", b"[]").decode("utf-8")) if b"measure_metadata" in metadata_ranks else []
        self._measure_specs: Dict[str, MeasureSpec] = {}
        for entry in measure_payload:
            spec = MeasureSpec(
                entry["measure_id"],
                entry["label"],
                entry["value_column"],
                entry["units"],
                entry.get("optional", False),
            )
            self._measure_specs[spec.measure_id] = spec

        if not self._measure_specs:
            self._measure_specs = MEASURE_LOOKUP.copy()

        self._has_phosphorus = any(
            col in self._events.columns and not self._events[col].isna().all()
            for col in ("soluble_reactive_p_kg", "particulate_p_kg", "total_p_kg")
        )

    @property
    def topaz_ids(self) -> list[int]:
        """Return the sorted list of channel identifiers present in the staged events."""
        if "topaz_id" not in self._events.columns:
            return []
        ids = sorted(set(int(v) for v in self._events["topaz_id"].unique()))
        return ids

    def _events_for_topaz(self, topaz_id: int) -> pd.DataFrame:
        """Return the subset of events scoped to ``topaz_id``."""
        return self._events[self._events["topaz_id"] == topaz_id].copy()

    def _ranks_for_topaz(self, topaz_id: int) -> pd.DataFrame:
        """Return the subset of ranked measures scoped to ``topaz_id``."""
        return self._ranks[self._ranks["topaz_id"] == topaz_id].copy()

    def _counts_for_topaz(self, topaz_id: int) -> pd.DataFrame:
        """Return the seasonal event-count dataframe for ``topaz_id``."""
        if self._event_counts.empty:
            return pd.DataFrame(columns=["year", "month", "event_count"])
        return self._event_counts[self._event_counts["topaz_id"] == topaz_id].copy()

    def create_report(
        self,
        recurrence: Sequence[int],
        *,
        exclude_yr_indxs: Optional[Sequence[int]] = None,
        exclude_months: Optional[Sequence[int]] = None,
        method: str = "cta",
        gringorten_correction: bool = False,
        topaz_id: Optional[int] = None,
    ) -> "ReturnPeriods":
        """Generate a :class:`ReturnPeriods` instance for the requested parameters.

        Args:
            recurrence: Target recurrence intervals (years) to include in the report.
            exclude_yr_indxs: Optional zero-based indexes of simulation years to remove.
            exclude_months: Optional calendar months (1-12) to remove.
            method: Either ``cta`` (default) or ``annual_maximum`` for the ranking strategy.
            gringorten_correction: Whether to apply the Gringorten correction to the Weibull formula.
            topaz_id: Optional channel identifier to target; defaults to the first available.

        Returns:
            Materialized :class:`ReturnPeriods` object carrying display-ready rows.
        """
        if not recurrence:
            raise ValueError("recurrence intervals must be provided")

        available = self.topaz_ids
        if not available:
            raise ValueError("No channel events are available in the staged dataset")
        target_topaz = topaz_id if topaz_id is not None else available[0]
        if target_topaz not in available:
            raise ValueError(f"Topaz ID {target_topaz} not present in staged events")

        events = self._events_for_topaz(target_topaz)
        ranks = self._ranks_for_topaz(target_topaz)
        counts = self._counts_for_topaz(target_topaz)

        if events.empty:
            raise ValueError(f"No ranked events available after staging for Topaz {target_topaz}")

        exclude_months = tuple(sorted(set(int(m) for m in exclude_months))) if exclude_months else ()

        if exclude_months:
            events = events[~events["mo"].isin(exclude_months)]
            ranks = ranks[ranks["event_id"].isin(events["event_id"])]

        year_values = sorted(int(y) for y in events["year"].dropna().unique())
        if not year_values:
            raise ValueError("Unable to determine simulation years for events")

        exclude_yr_indxs = tuple(sorted(set(int(i) for i in exclude_yr_indxs))) if exclude_yr_indxs else ()
        excluded_years = {year_values[idx] for idx in exclude_yr_indxs if 0 <= idx < len(year_values)}
        if excluded_years:
            events = events[~events["year"].isin(excluded_years)]
            ranks = ranks[ranks["event_id"].isin(events["event_id"])]

        counts_filtered = counts.copy()
        if not counts_filtered.empty:
            if exclude_months:
                counts_filtered = counts_filtered[~counts_filtered["month"].isin(exclude_months)]
            if excluded_years:
                counts_filtered = counts_filtered[~counts_filtered["year"].isin(excluded_years)]

        if counts_filtered.empty:
            total_events = len(events)
            years_count = len(set(events["year"]))
        else:
            total_events = int(counts_filtered["event_count"].sum())
            years_count = len(set(counts_filtered["year"]))

        years_count = max(years_count, 1)
        days_in_year = total_events / years_count if years_count > 0 else 0.0

        rec_map = weibull_series(recurrence, years_count, method=method, gringorten_correction=gringorten_correction)

        measure_results: Dict[str, Dict[int, Dict[str, float]]] = {}

        seen_specs: set[str] = set()
        ordered_specs: list[MeasureSpec] = []
        for template_spec in MEASURE_SPECS:
            resolved = self._measure_specs.get(template_spec.measure_id, template_spec)
            ordered_specs.append(resolved)
            seen_specs.add(resolved.measure_id)
        for measure_id, spec in self._measure_specs.items():
            if measure_id not in seen_specs:
                ordered_specs.append(spec)
                seen_specs.add(measure_id)

        for spec in ordered_specs:
            if spec.measure_id not in ranks["measure_id"].values:
                continue

            subset = ranks[ranks["measure_id"] == spec.measure_id]
            if subset.empty:
                continue

            merged = subset.merge(events, on="event_id", how="inner", suffixes=("", "_event"))
            if merged.empty:
                continue

            merged = merged.sort_values(["measure_value", "event_id"], ascending=[False, True]).reset_index(drop=True)

            if method.lower() != "cta":
                merged = (
                    merged.sort_values(["year", "measure_value"], ascending=[True, False])
                    .groupby("year", as_index=False, sort=False)
                    .head(1)
                )
                merged = merged.sort_values(["measure_value", "event_id"], ascending=[False, True]).reset_index(drop=True)

            merged["weibull_rank"] = merged.index + 1
            if days_in_year > 0:
                merged["weibull_T"] = ((total_events + 1) / merged["weibull_rank"]) / days_in_year
            else:
                merged["weibull_T"] = np.nan

            display_label = spec.label
            rows_for_measure: Dict[int, Dict[str, float]] = {}

            for ret, idx in rec_map.items():
                if idx >= len(merged):
                    continue
                row = merged.iloc[idx]
                formatted = _format_event_row(row, spec)
                rows_for_measure[int(ret)] = formatted

            if rows_for_measure:
                measure_results[display_label] = rows_for_measure

        wsarea = self._watershed_area.get(str(target_topaz))
        wsarea_val = float(wsarea) if wsarea is not None else np.nan

        report = ReturnPeriods.__new__(ReturnPeriods)  # bypass __init__
        report.has_phosphorus = self._has_phosphorus
        report.header = [
            "Precipitation Depth (mm)",
            "Runoff Volume (m^3)",
            "Peak Runoff (m^3/s)",
            "Sediment Yield (kg)",
            "Soluble Reactive P (kg)",
            "Particulate P (kg)",
            "Total P (kg)",
            "TopazID",
            "Hill Sed Del (kg)",
            "10-min Peak Rainfall Intensity (mm/hour)",
            "15-min Peak Rainfall Intensity (mm/hour)",
            "30-min Peak Rainfall Intensity (mm/hour)",
            "Storm Duration (hours)",
            "Hill Streamflow (mm)",
        ]
        report.method = method
        report.gringorten_correction = gringorten_correction
        report.y0 = year_values[0] if year_values else 0
        report.years = years_count
        report.wsarea = wsarea_val
        report.recurrence = sorted(int(r) for r in recurrence)
        report.return_periods = measure_results
        report.num_events = total_events
        report.intervals = sorted(measure_results[next(iter(measure_results))].keys()) if measure_results else []
        report.units_d = {
            "Precipitation Depth": "mm",
            "Runoff": "mm",
            "Peak Discharge": "m^3/s",
            "Sediment Yield": "tonne",
            "Soluble Reactive P": "kg",
            "Particulate P": "kg",
            "Total P": "kg",
            "10-min Peak Rainfall Intensity": "mm/hour",
            "15-min Peak Rainfall Intensity": "mm/hour",
            "30-min Peak Rainfall Intensity": "mm/hour",
            "Storm Duration": "hours",
            "Hill Sed Del": "tonne",
            "Hill Streamflow": "mm",
        }
        report.exclude_yr_indxs = list(exclude_yr_indxs) if exclude_yr_indxs else None
        report.exclude_months = list(exclude_months) if exclude_months else None
        return report


def _format_event_row(row: pd.Series, spec: MeasureSpec) -> Dict[str, Any]:
    """Convert a ranked event row into the structure the templates consume."""
    result: Dict[str, Any] = {
        "mo": int(row["mo"]),
        "da": int(row["da"]),
        "year": int(row["year"]),
        "TopazID": int(row["topaz_id"]),
        "Precipitation Depth": float(row.get("precip_mm", np.nan)),
        "Runoff": float(row.get("runoff_depth_mm", np.nan)) if not pd.isna(row.get("runoff_depth_mm")) else 0.0,
        "Peak Discharge": float(row.get("peak_discharge_m3s", np.nan)),
        "Sediment Yield": float(row.get("sediment_yield_tonnes", np.nan)),
        "Soluble Reactive P": float(row.get("soluble_reactive_p_kg", np.nan))
        if "soluble_reactive_p_kg" in row else np.nan,
        "Particulate P": float(row.get("particulate_p_kg", np.nan)) if "particulate_p_kg" in row else np.nan,
        "Total P": float(row.get("total_p_kg", np.nan)) if "total_p_kg" in row else np.nan,
        "Hill Sed Del": float(row.get("hill_sediment_tonnes", np.nan)),
        "Hill Streamflow": float(row.get("hill_streamflow_mm", np.nan)),
        "10-min Peak Rainfall Intensity": float(row.get("intensity_10min", np.nan)),
        "15-min Peak Rainfall Intensity": float(row.get("intensity_15min", np.nan)),
        "30-min Peak Rainfall Intensity": float(row.get("intensity_30min", np.nan)),
        "Storm Duration": float(row.get("storm_duration_hours", np.nan)),
        "weibull_rank": int(row["weibull_rank"]),
        "weibull_T": float(row.get("weibull_T", np.nan)),
    }

    target_value = row.get(spec.value_column)
    if target_value is not None and not pd.isna(target_value):
        result[spec.label] = float(target_value)

    return result


class ReturnPeriods:
    """Immutable-ish container for the final return-period table structures."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "ReturnPeriods must be constructed using ReturnPeriodDataset.create_report; "
            "direct construction is no longer supported."
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the report for persistence or transfer."""
        return {
            "has_phosphorus": self.has_phosphorus,
            "header": self.header,
            "method": self.method,
            "gringorten_correction": self.gringorten_correction,
            "y0": self.y0,
            "years": self.years,
            "wsarea": self.wsarea,
            "recurrence": self.recurrence,
            "return_periods": self.return_periods,
            "num_events": self.num_events,
            "intervals": self.intervals,
            "units_d": self.units_d,
            "exclude_yr_indxs": self.exclude_yr_indxs,
            "exclude_months": self.exclude_months,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReturnPeriods":
        """Rehydrate an instance from :meth:`to_dict` output."""
        instance = cls.__new__(cls)
        instance.has_phosphorus = data.get("has_phosphorus", False)
        instance.header = list(data.get("header", []))
        instance.method = data.get("method", "cta")
        instance.gringorten_correction = data.get("gringorten_correction", False)
        instance.y0 = data.get("y0", 0)
        instance.years = data.get("years", 0)
        instance.wsarea = data.get("wsarea")
        instance.recurrence = list(data.get("recurrence", []))
        instance.return_periods = {}
        ret_periods = data.get("return_periods", {})
        for measure, mapping in ret_periods.items():
            instance.return_periods[measure] = {}
            for key, value in mapping.items():
                instance.return_periods[measure][int(key)] = value
        instance.num_events = data.get("num_events", 0)
        instance.intervals = list(data.get("intervals", []))
        instance.units_d = dict(data.get("units_d", {}))
        instance.exclude_yr_indxs = data.get("exclude_yr_indxs")
        instance.exclude_months = data.get("exclude_months")
        return instance

    def export_tsv_summary(self, summary_path: str | Path, extraneous: bool = False) -> None:
        """Write a TSV summary to ``summary_path`` using the desired column set."""
        summary_path = Path(summary_path)
        if extraneous:
            self._export_tsv_summary_extraneous(summary_path)
        else:
            self._export_tsv_summary_simple(summary_path)

    def _export_tsv_summary_simple(self, summary_path: Path) -> None:
        """Write the condensed TSV layout consumed by most clients."""
        measures = [
            "Precipitation Depth",
            "Runoff",
            "Peak Discharge",
            "10-min Peak Rainfall Intensity",
            "15-min Peak Rainfall Intensity",
            "30-min Peak Rainfall Intensity",
            "Sediment Yield",
        ]
        if self.has_phosphorus:
            measures.extend(["Soluble Reactive P", "Particulate P", "Total P"])

        with summary_path.open("w", encoding="utf-8") as stream:
            stream.write("WEPPcloud Return Period Analysis\n")
            stream.write(f"Years in Simulation\t{self.years}\n")
            stream.write(f"Events in Simulation\t{self.num_events}\n")
            if self.exclude_yr_indxs:
                stream.write(f"Excluded Year Indexes\t{', '.join(map(str, self.exclude_yr_indxs))}\n")
            if self.gringorten_correction:
                stream.write("Using Gringorten Correction for Weibull formula\n")
            stream.write("\n")

            for key in measures:
                if key not in self.return_periods:
                    continue
                stream.write(f"{key}\n")
                unit = self.units_d.get(key, "")
                stream.write("Recurrence Interval (years)\tDate (mm/dd/yyyy)\t")
                stream.write(f"{key} ({unit})\n")
                for rec_interval in sorted(self.return_periods[key], reverse=True):
                    row = self.return_periods[key][rec_interval]
                    date = f"{int(row['mo']):02d}/{int(row['da']):02d}/{int(row['year'] + self.y0 - 1):04d}"
                    value = row.get(key, 0.0)
                    stream.write(f"{rec_interval}\t{date}\t{value:.2f}\n")
                stream.write("\n")

    def _export_tsv_summary_extraneous(self, summary_path: Path) -> None:
        """Write the verbose TSV layout that includes intermediate columns."""
        measures = [
            "Precipitation Depth",
            "Runoff",
            "Peak Discharge",
            "10-min Peak Rainfall Intensity",
            "15-min Peak Rainfall Intensity",
            "30-min Peak Rainfall Intensity",
            "Sediment Yield",
        ]
        if self.has_phosphorus:
            measures.extend(["Soluble Reactive P", "Particulate P", "Total P"])

        with summary_path.open("w", encoding="utf-8") as stream:
            stream.write("WEPPcloud Return Period Analysis\n")
            stream.write(f"Years in Simulation\t{self.years}\n")
            stream.write(f"Events in Simulation\t{self.num_events}\n")
            if self.exclude_yr_indxs:
                stream.write(f"Excluded Year Indexes\t{', '.join(map(str, self.exclude_yr_indxs))}\n")
            else:
                stream.write("Excluded Year Indexes\tNone\n")
            stream.write("\n")

            for key in measures:
                if key not in self.return_periods:
                    continue

                headers = [
                    "Recurrence Interval (years)",
                    "Date (mm/dd/yyyy)",
                    f"Precipitation Depth ({self.units_d.get('Precipitation Depth', 'mm')})",
                    f"Runoff ({self.units_d.get('Runoff', 'mm')})",
                    f"Peak Discharge ({self.units_d.get('Peak Discharge', 'm^3/s')})",
                ]
                if "10-min Peak Rainfall Intensity" in self.return_periods:
                    headers.append(f"10-min Peak Rainfall Intensity ({self.units_d.get('10-min Peak Rainfall Intensity', 'mm/hour')})")
                if "15-min Peak Rainfall Intensity" in self.return_periods:
                    headers.append(f"15-min Peak Rainfall Intensity ({self.units_d.get('15-min Peak Rainfall Intensity', 'mm/hour')})")
                if "30-min Peak Rainfall Intensity" in self.return_periods:
                    headers.append(f"30-min Peak Rainfall Intensity ({self.units_d.get('30-min Peak Rainfall Intensity', 'mm/hour')})")
                if "Storm Duration" in self.return_periods:
                    headers.append(f"Storm Duration ({self.units_d.get('Storm Duration', 'hours')})")
                headers.append(f"Sediment Yield ({self.units_d.get('Sediment Yield', 'tonne')})")
                if self.has_phosphorus:
                    headers.extend(
                        [
                            f"Soluble Reactive P ({self.units_d.get('Soluble Reactive P', 'kg')})",
                            f"Particulate P ({self.units_d.get('Particulate P', 'kg')})",
                            f"Total P ({self.units_d.get('Total P', 'kg')})",
                        ]
                    )
                headers.extend(["Rank", "Weibull T"])
                stream.write(f"{key}\n")
                stream.write("\t".join(headers) + "\n")

                for rec_interval in sorted(self.return_periods[key], reverse=True):
                    row = self.return_periods[key][rec_interval]
                    date = f"{int(row['mo']):02d}/{int(row['da']):02d}/{int(row['year'] + self.y0 - 1):04d}"
                    values = [
                        str(rec_interval),
                        date,
                        f"{row.get('Precipitation Depth', 0):.2f}",
                        f"{row.get('Runoff', 0):.2f}",
                        f"{row.get('Peak Discharge', 0):.2f}",
                    ]
                    if "10-min Peak Rainfall Intensity" in self.return_periods:
                        values.append(f"{row.get('10-min Peak Rainfall Intensity', 0):.2f}")
                    if "15-min Peak Rainfall Intensity" in self.return_periods:
                        values.append(f"{row.get('15-min Peak Rainfall Intensity', 0):.2f}")
                    if "30-min Peak Rainfall Intensity" in self.return_periods:
                        values.append(f"{row.get('30-min Peak Rainfall Intensity', 0):.2f}")
                    if "Storm Duration" in self.return_periods:
                        values.append(f"{row.get('Storm Duration', 0):.2f}")
                    values.append(f"{row.get('Sediment Yield', 0):.2f}")
                    if self.has_phosphorus:
                        values.extend(
                            [
                                f"{row.get('Soluble Reactive P', 0):.2f}",
                                f"{row.get('Particulate P', 0):.2f}",
                                f"{row.get('Total P', 0):.2f}",
                            ]
                        )
                    values.extend(
                        [
                            str(row.get("weibull_rank", "")),
                            f"{row.get('weibull_T', 0):.2f}",
                        ]
                    )
                    stream.write("\t".join(values) + "\n")
                stream.write("\n")


__all__ = [
    "ReturnPeriodDataset",
    "ReturnPeriods",
    "refresh_return_period_events",
]
