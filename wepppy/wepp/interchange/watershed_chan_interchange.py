from __future__ import annotations

import errno
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

from .schema_utils import pa_field
from ._utils import _wait_for_path, _parse_float

CHAN_FILENAME = "chanwb.out"
CHAN_PARQUET = "chanwb.parquet"


MEASUREMENT_COLUMNS: List[tuple[str, str, str]] = [
    ("Inflow (m^3)", "m^3", "Total inflow above channel outlet, includes baseflow, all sources"),
    ("Outflow (m^3)", "m^3", "Water flow out of channel outlet"),
    ("Storage (m^3)", "m^3", "Water surface storage at the end of the day"),
    ("Baseflow (m^3)", "m^3", "Portion of inflow from baseflow"),
    ("Loss (m^3)", "m^3", "Transmission loss in channel, infiltration"),
    ("Balance (m^3)", "m^3", "Water balance error at end of day (inflow - outflow - loss - Δstorage)"),
]


SCHEMA = pa.schema(
    [
        pa_field("year", pa.int16(), description="Calendar year"),
        pa_field("simulation_year", pa.int16(), description="Simulation year from chanwb.out"),
        pa_field("julian", pa.int16(), description="Julian day reported by WEPP"),
        pa_field("month", pa.int8(), description="Calendar month derived from Julian day"),
        pa_field("day_of_month", pa.int8(), description="Calendar day-of-month derived from Julian day"),
        pa_field("water_year", pa.int16(), description="Water year computed from Julian day"),
        pa_field("Elmt_ID", pa.int32(), description="Channel element identifier"),
        pa_field("Chan_ID", pa.int32(), description="Channel ID reported by WEPP"),
    ]
    + [pa_field(name, pa.float64(), units=units, description=description) for name, units, description in MEASUREMENT_COLUMNS]
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


def _write_chan_parquet(
    source: Path,
    target: Path,
    *,
    start_year: int | None = None,
    chunk_size: int = 500_000,
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
                if len(tokens) != 10:
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

                measurement_values = tokens[4:]
                for (col_name, _units, _desc), token in zip(MEASUREMENT_COLUMNS, measurement_values):
                    store[col_name].append(_parse_float(token))

                row_counter += 1
                if row_counter % chunk_size == 0:
                    _flush_chunk(store, writer)

        if store["year"]:
            _flush_chunk(store, writer)
        elif row_counter == 0:
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


def run_wepp_watershed_chan_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / CHAN_FILENAME
    _wait_for_path(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHAN_PARQUET
    _write_chan_parquet(source, target, start_year=start_year)
    return target
