from __future__ import annotations

import os
import zipfile
from datetime import date, datetime
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

try:  # Optional dependency for DSS exports
    from pydsstools.core import TimeSeriesContainer
    from pydsstools.heclib.dss import HecDss
except ModuleNotFoundError as exc:  # pragma: no cover - executed when pydsstools missing
    TimeSeriesContainer = None  # type: ignore[assignment]
    HecDss = None  # type: ignore[assignment]
    _PYDSSTOOLS_IMPORT_ERROR = exc
else:
    _PYDSSTOOLS_IMPORT_ERROR = None

from wepppy.wepp.interchange.totalwatsed3 import (
    ASH_BLACK_PCT_COLUMN,
    ASH_VOLUME_COLUMN,
    SED_ASH_VOLUME_COLUMN,
    run_totalwatsed3,
)
from wepppy.wepp.interchange.date_filters import apply_date_filters

__all__ = ["totalwatsed_partitioned_dss_export", "archive_dss_export_zip"]


def _channel_wepp_ids(translator, network, channel_top_id: int) -> list[int]:
    try:
        from wepppy.topo.watershed_abstraction import upland_hillslopes
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise ModuleNotFoundError(
            "watershed_totalwatsed_export requires wepppy.topo.watershed_abstraction"
        ) from exc

    hillslopes = upland_hillslopes(channel_top_id, network, translator)
    wepp_ids: list[int] = []
    for topo_id in hillslopes:
        wepp_id = translator.wepp(top=int(topo_id))
        if wepp_id is not None:
            wepp_ids.append(int(wepp_id))
    return sorted(set(wepp_ids))


def _column_units(table: pq.Table) -> dict[str, str]:
    units: dict[str, str] = {}
    schema = table.schema
    for field in schema:
        metadata = field.metadata or {}
        raw = metadata.get(b"units")
        units[field.name] = raw.decode("utf-8") if raw else ""
    return units


def _require_pydsstools() -> tuple[type, type]:
    if TimeSeriesContainer is None or HecDss is None:
        raise ModuleNotFoundError(
            "pydsstools is required for DSS export operations"
        ) from _PYDSSTOOLS_IMPORT_ERROR
    return TimeSeriesContainer, HecDss


def totalwatsed_partitioned_dss_export(
    wd: str | Path,
    export_channel_ids: list[int] | None = None,
    status_channel: str | None = None,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """
    Export per-channel `totalwatsed3` summaries to individual DSS files.
    """
    from wepppy.nodb.core import Watershed, Wepp
    from wepppy.nodb.core.wepp import BaseflowOpts

    wd_path = Path(wd)
    watershed = Watershed.getInstance(wd_path)
    translator = watershed.translator_factory()
    network = watershed.network

    wepp_instance = Wepp.getInstance(wd_path)
    baseflow_opts = wepp_instance.baseflow_opts or BaseflowOpts()

    interchange_dir = wd_path / "wepp" / "output" / "interchange"
    dss_export_dir = wd_path / "export" / "dss"

    status_publisher = None
    if status_channel is not None:
        try:
            from wepppy.nodb.status_messenger import StatusMessenger
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise ModuleNotFoundError(
                "StatusMessenger is unavailable; ensure NoDb components are installed"
            ) from exc
        status_publisher = StatusMessenger.publish
        status_publisher(status_channel, "totalwatsed_partitioned_dss_export()...\n")

    if dss_export_dir.exists():
        if status_publisher is not None and status_channel is not None:
            status_publisher(status_channel, "cleaning export/dss/totalwatsed3_chan_*.dss\n")
        for fn in glob(str(dss_export_dir / "totalwatsed3_chan_*.dss")):
            os.remove(fn)

    dss_export_dir.mkdir(parents=True, exist_ok=True)
    TimeSeriesContainer_cls, HecDss_cls = _require_pydsstools()

    sed_records: list[pd.DataFrame] = []

    start_bound = start_date
    end_bound = end_date

    for chn_id_str in translator.iter_chn_ids():
        channel_top_id = int(chn_id_str.split("_")[1])

        if export_channel_ids is not None and channel_top_id not in export_channel_ids:
            continue

        if status_publisher is not None and status_channel is not None:
            status_publisher(status_channel, f"processing channel {channel_top_id}...\n")

        wepp_ids = _channel_wepp_ids(translator, network, channel_top_id)
        if not wepp_ids:
            continue

        parquet_path = run_totalwatsed3(interchange_dir, baseflow_opts, wepp_ids=wepp_ids)
        table = pq.read_table(parquet_path)
        if table.num_rows == 0:
            continue

        df = table.to_pandas()
        df.sort_values(["year", "julian", "sim_day_index"], kind="mergesort", inplace=True)
        df.reset_index(drop=True, inplace=True)

        if start_bound is not None or end_bound is not None:
            df = apply_date_filters(df, start=start_bound, end=end_bound)
            if df.empty:
                continue

        sed_metric_columns = ["sed_vol_conc", ASH_VOLUME_COLUMN, SED_ASH_VOLUME_COLUMN, ASH_BLACK_PCT_COLUMN]
        available_sed_cols = [col for col in sed_metric_columns if col in df.columns]
        if available_sed_cols:
            sed_subset = df[["year", "month", "day_of_month", *available_sed_cols]].copy()
            sed_subset["channel_top_id"] = channel_top_id
            ordered_cols = ["year", "month", "day_of_month", "channel_top_id", *available_sed_cols]
            sed_records.append(sed_subset[ordered_cols])

        # Derive discharge in m^3/s for compatibility with legacy export.
        area_series = df["Area"].astype(float, copy=False)
        watershed_area_m2 = float(area_series.iloc[0]) if not area_series.empty else 0.0
        if watershed_area_m2 > 0.0 and "Streamflow" in df.columns:
            df["Q (m^3/s)"] = (
                df["Streamflow"].astype(float, copy=False) * watershed_area_m2
            ) / (1000.0 * 86400.0)
        else:
            df["Q (m^3/s)"] = 0.0

        units = _column_units(table)
        units["Q (m^3/s)"] = "m^3/s"

        identifier_columns = {
            "year",
            "sim_day_index",
            "julian",
            "month",
            "day_of_month",
            "water_year",
            "Area",
        }

        start_year = int(df["year"].iloc[0])
        start_month = int(df["month"].iloc[0])
        start_day = int(df["day_of_month"].iloc[0])
        try:
            series_start = datetime(start_year, start_month, start_day)
        except ValueError as exc:
            raise ValueError(
                f"Invalid start date components for DSS export: "
                f"{start_year:04d}-{start_month:02d}-{start_day:02d}"
            ) from exc
        d_part = f"{series_start.strftime('%d%b')}{series_start.year:04d}".upper()
        start_datetime_str = f"{d_part} {series_start.strftime('%H:%M:%S')}".upper()

        dss_file = dss_export_dir / f"totalwatsed3_chan_{channel_top_id}.dss"
        with HecDss_cls.Open(str(dss_file)) as fid:
            for column in df.columns:
                if column in identifier_columns:
                    continue
                series = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
                if np.isnan(series).all():
                    continue

                label = (
                    column.replace("(", "")
                    .replace(")", "")
                    .replace(" ", "-")
                    .replace("_", "-")
                )

                pathname = f"/WEPP/TOTALWATSED3/{label.upper()}/{d_part}/1DAY/{channel_top_id}/"
                tsc = TimeSeriesContainer_cls()
                tsc.pathname = pathname
                tsc.startDateTime = start_datetime_str
                tsc.interval = 1440
                tsc.numberValues = len(series)
                tsc.units = units.get(column, "")
                tsc.type = "INST"
                tsc.values = series

                delete_pattern = f"/WEPP/TOTALWATSED3/{label.upper()}//1DAY/{channel_top_id}/"
                fid.deletePathname(delete_pattern)
                fid.put_ts(tsc)

        assert dss_file.exists(), f"Failed to create DSS file: {dss_file}"

    if sed_records:
        sed_df = pd.concat(sed_records, ignore_index=True)
        column_order = ["year", "month", "day_of_month", "channel_top_id"]
        for col in ["sed_vol_conc", ASH_VOLUME_COLUMN, SED_ASH_VOLUME_COLUMN, ASH_BLACK_PCT_COLUMN]:
            if col in sed_df.columns:
                column_order.append(col)
        sed_df = sed_df[column_order]
        sed_csv_path = dss_export_dir / "sed_vol_conc_by_event_and_chn_id.csv"
        sed_df.to_csv(sed_csv_path, index=False)


def archive_dss_export_zip(wd: str | Path, status_channel: str | None = None) -> None:
    if status_channel is not None:
        try:
            from wepppy.nodb.status_messenger import StatusMessenger
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise ModuleNotFoundError(
                "StatusMessenger is unavailable; ensure NoDb components are installed"
            ) from exc
        StatusMessenger.publish(status_channel, "zipping export/dss\n")

    wd_path = Path(wd)
    dss_export_dir = wd_path / "export" / "dss"

    zip_file = wd_path / "export" / "dss.zip"
    with zipfile.ZipFile(zip_file, "w") as zipf:
        for root, dirs, files in os.walk(dss_export_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, dss_export_dir))
