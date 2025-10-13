from __future__ import annotations

import errno
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from wepppy.all_your_base.hydro import determine_wateryear

from ._utils import _wait_for_path, _parse_float
from .schema_utils import pa_field

CHAN_PEAK_FILENAME = "chan.out"
CHAN_PEAK_PARQUET = "chan.out.parquet"
CHUNK_SIZE = 500_000



SCHEMA = pa.schema(
    [
        pa_field("year", pa.int16(), description="Calendar year"),
        pa_field("simulation_year", pa.int16(), description="Simulation year from chan.out"),
        pa_field("julian", pa.int16(), description="Julian day reported by WEPP"),
        pa_field("month", pa.int8(), description="Calendar month derived from Julian day"),
        pa_field("day_of_month", pa.int8(), description="Calendar day-of-month derived from Julian day"),
        pa_field("water_year", pa.int16(), description="Water year computed from Julian day"),
        pa_field("Elmt_ID", pa.int32(), description="Channel element identifier"),
        pa_field("Chan_ID", pa.int32(), description="Channel ID reported by WEPP"),
        pa_field("Time (s)", pa.float64(), units="s", description="Time to peak discharge"),
        pa_field(
            "Peak_Discharge (m^3/s)",
            pa.float64(),
            units="m^3/s",
            description="Peak discharge within the reporting interval",
        ),
    ]
)


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _flush_chunk(store: Dict[str, List], writer: pq.ParquetWriter) -> None:
    if not store["year"]:
        return
    table = pa.table(store, schema=SCHEMA)
    writer.write_table(table)
    store.clear()
    store.update(_init_column_store())


def _write_chan_peak_parquet(
    source: Path,
    target: Path,
    *,
    start_year: int | None = None,
    chunk_size: int = CHUNK_SIZE,
) -> None:
    tmp_target = target.with_suffix(f"{target.suffix}.tmp")
    if tmp_target.exists():
        tmp_target.unlink()

    writer = pq.ParquetWriter(
        tmp_target,
        SCHEMA,
        compression="snappy",
        use_dictionary=True,
    )

    store = _init_column_store()
    row_counter = 0
    data_section = False

    try:
        with source.open("r") as stream:
            for raw_line in stream:
                stripped = raw_line.strip()
                if not data_section:
                    if stripped.startswith("Year") and "Elmt_ID" in stripped:
                        data_section = True
                    continue

                if not stripped:
                    continue

                tokens = stripped.split()
                if len(tokens) != 6:
                    continue

                sim_year = int(tokens[0])
                julian = int(tokens[1])
                elmt_id = int(tokens[2])
                chan_id = int(tokens[3])

                if start_year is not None and sim_year < 1000:
                    year = start_year + sim_year - 1
                else:
                    year = sim_year

                date_obj = datetime(year, 1, 1) + timedelta(days=julian - 1)
                store["year"].append(year)
                store["simulation_year"].append(sim_year)
                store["julian"].append(julian)
                store["month"].append(date_obj.month)
                store["day_of_month"].append(date_obj.day)
                store["water_year"].append(int(determine_wateryear(year, julian)))
                store["Elmt_ID"].append(elmt_id)
                store["Chan_ID"].append(chan_id)
                store["Time (s)"].append(_parse_float(tokens[4]))
                store["Peak_Discharge (m^3/s)"].append(_parse_float(tokens[5]))

                row_counter += 1
                if row_counter % chunk_size == 0:
                    _flush_chunk(store, writer)

        if store["year"]:
            _flush_chunk(store, writer)
        else:
            writer.write_table(pa.table(_init_column_store(), schema=SCHEMA))
    except Exception:
        writer.close()
        if tmp_target.exists():
            tmp_target.unlink()
        raise
    else:
        writer.close()
        try:
            tmp_target.replace(target)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                shutil.move(str(tmp_target), str(target))
            else:
                raise


def run_wepp_watershed_chan_peak_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    source = base / CHAN_PEAK_FILENAME
    _wait_for_path(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHAN_PEAK_PARQUET
    _write_chan_peak_parquet(source, target, start_year=start_year)
    return target


def chanout_dss_export(wd: Path | str, status_channel: str | None = None) -> None:
    """
    Export channel-peak flow data to a DSS time-series file.
    """
    from pydsstools.heclib.dss import HecDss
    from pydsstools.core import TimeSeriesContainer
    from wepppy.nodb.status_messenger import StatusMessenger
    from wepppy.nodb.core import Watershed

    wd_path = Path(wd)
    watershed = Watershed.getInstance(wd_path)
    translator = watershed.translator_factory()

    dss_dir = wd_path / "export" / "dss"
    dss_dir.mkdir(parents=True, exist_ok=True)
    chan_dss = dss_dir / "chan.dss"

    if chan_dss.exists():
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "cleaning export/dss/chan.dss\n")
        chan_dss.unlink()

    if status_channel is not None:
        StatusMessenger.publish(status_channel, "chanout_dss_export()...\n")

    parquet_path = run_wepp_watershed_chan_peak_interchange(wd_path / "wepp" / "output")
    df = pd.read_parquet(parquet_path)

    id_column = "Chan_ID"
    if translator is not None and hasattr(translator, "top"):
        try:
            df["TopazID"] = df["Elmt_ID"].apply(lambda wepp_id: translator.top(wepp=int(wepp_id)))
            id_column = "TopazID"
        except Exception:
            if "TopazID" in df.columns:
                df.drop(columns=["TopazID"], inplace=True)

    df["year"] = df["year"].astype(int)
    df["julian"] = df["julian"].astype(int)
    df["Time (s)"] = df["Time (s)"].fillna(0.0).astype(float)

    base_dates = pd.to_datetime(df["year"].astype(str), format="%Y")
    base_dates = base_dates + pd.to_timedelta(df["julian"] - 1, unit="D")
    df["datetime"] = base_dates + pd.to_timedelta(df["Time (s)"], unit="s")

    with HecDss.Open(str(chan_dss)) as fid:
        for channel_id, group in df.groupby(id_column):
            values = group["Peak_Discharge (m^3/s)"].astype(float).to_list()
            times = group["datetime"].to_list()

            # DSS Pathname Parts: /A/B/C/D/E/F/
            # A: Project -> WEPP
            # B: Version -> CHAN-OUT
            # C: Parameter -> PEAK-FLOW
            # D: Time Window -> IR-YEAR (Irregular Yearly)
            # E: Interval -> Blank for irregular data
            # F: Location -> Channel ID
            tsc = TimeSeriesContainer()
            tsc.pathname = f"/WEPP/CHAN-OUT/PEAK-FLOW//IR-YEAR/{channel_id}/"
            tsc.times = times
            tsc.values = values
            tsc.numberValues = len(values)
            tsc.units = "M3/S"
            tsc.type = "INST"
            tsc.interval = -1

            fid.put_ts(tsc)
