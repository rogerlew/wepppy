from __future__ import annotations

import os
import zipfile
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pydsstools.core import TimeSeriesContainer
from pydsstools.heclib.dss import HecDss

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.topo.watershed_abstraction import upland_hillslopes
from wepppy.wepp.interchange.totalwatsed3 import run_totalwatsed3

__all__ = ["totalwatsed_partitioned_dss_export", "archive_dss_export_zip"]


def _channel_wepp_ids(translator, network, channel_top_id: int) -> list[int]:
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


def totalwatsed_partitioned_dss_export(
    wd: str | Path,
    export_channel_ids: list[int] | None = None,
    status_channel: str | None = None,
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

    if status_channel is not None:
        StatusMessenger.publish(status_channel, "totalwatsed_partitioned_dss_export()...\n")

    if dss_export_dir.exists():
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "cleaning export/dss/totalwatsed3_chan_*.dss\n")
        for fn in glob(str(dss_export_dir / "totalwatsed3_chan_*.dss")):
            os.remove(fn)

    dss_export_dir.mkdir(parents=True, exist_ok=True)

    for chn_id_str in translator.iter_chn_ids():
        channel_top_id = int(chn_id_str.split("_")[1])

        if export_channel_ids is not None and channel_top_id not in export_channel_ids:
            continue

        if status_channel is not None:
            StatusMessenger.publish(status_channel, f"processing channel {channel_top_id}...\n")

        wepp_ids = _channel_wepp_ids(translator, network, channel_top_id)
        if not wepp_ids:
            continue

        parquet_path = run_totalwatsed3(interchange_dir, baseflow_opts, wepp_ids=wepp_ids)
        table = pq.read_table(parquet_path)
        if table.num_rows == 0:
            continue

        df = table.to_pandas()
        df.sort_values(["year", "julian"], kind="mergesort", inplace=True)
        df.reset_index(drop=True, inplace=True)

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
            "day",
            "julian",
            "month",
            "day_of_month",
            "water_year",
            "Area",
        }

        date_index = pd.to_datetime(
            dict(
                year=df["year"].astype(int, copy=False),
                month=df["month"].astype(int, copy=False),
                day=df["day_of_month"].astype(int, copy=False),
            )
        )
        start_date = date_index.iloc[0]

        dss_file = dss_export_dir / f"totalwatsed3_chan_{channel_top_id}.dss"
        with HecDss.Open(str(dss_file)) as fid:
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

                pathname = f"/WEPP/TOTALWATSED3/{label.upper()}//1DAY/{channel_top_id}/"
                tsc = TimeSeriesContainer()
                tsc.pathname = pathname
                tsc.startDateTime = start_date.strftime("%d%b%Y %H:%M:%S").upper()
                tsc.interval = 1440
                tsc.numberValues = len(series)
                tsc.units = units.get(column, "")
                tsc.type = "INST"
                tsc.values = series

                fid.deletePathname(tsc.pathname)
                fid.put_ts(tsc)


def archive_dss_export_zip(wd: str | Path, status_channel: str | None = None) -> None:
    if status_channel is not None:
        StatusMessenger.publish(status_channel, "zipping export/dss\n")

    wd_path = Path(wd)
    dss_export_dir = wd_path / "export" / "dss"

    zip_file = wd_path / "export" / "dss.zip"
    with zipfile.ZipFile(zip_file, "w") as zipf:
        for root, dirs, files in os.walk(dss_export_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, dss_export_dir))
