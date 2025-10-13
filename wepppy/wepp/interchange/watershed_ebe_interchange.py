from __future__ import annotations

import errno
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear
from ._utils import _wait_for_path, _parse_float
from .schema_utils import pa_field
from .versioning import schema_with_version

EBE_FILENAME = "ebe_pw0.txt"
EBE_PARQUET = "ebe_pw0.parquet"
CHUNK_SIZE = 250_000


MEASUREMENT_COLUMNS: List[str] = [
    "precip",
    "runoff_volume",
    "peak_runoff",
    "sediment_yield",
    "soluble_pollutant",
    "particulate_pollutant",
    "total_pollutant",
]


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("simulation_year", pa.int16(), description="WEPP simulation year reported in output"),
            pa_field("month", pa.int8(), description="Calendar month"),
            pa_field("day_of_month", pa.int8(), description="Calendar day of month"),
            pa_field("julian", pa.int16(), description="Julian day from WEPP output"),
            pa_field("water_year", pa.int16(), description="Water year derived from year/julian"),
            pa_field("precip", pa.float64(), units="mm", description="Watershed precipitation depth for the event"),  # sedout.for:3100
            pa_field("runoff_volume", pa.float64(), units="m^3", description="Watershed runoff volume for the event"),  # sedout.for:3100
            pa_field("peak_runoff", pa.float64(), units="m^3/s", description="Peak watershed discharge"),  # sedout.for:3100
            pa_field("sediment_yield", pa.float64(), units="kg", description="Sediment yield at the watershed outlet"),  # sedout.for:3100
            pa_field("soluble_pollutant", pa.float64(), units="kg", description="Soluble pollutant mass delivered at watershed outlet"),
            pa_field("particulate_pollutant", pa.float64(), units="kg", description="Particulate pollutant mass delivered at watershed outlet"),
            pa_field("total_pollutant", pa.float64(), units="kg", description="Total pollutant mass delivered (soluble + particulate)"),
            pa_field("element_id", pa.int32(), description="Channel element identifier (Elmt_ID)"),
        ]
    )
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


def _write_ebe_parquet(
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

    try:
        with source.open("r") as stream:
            for raw_line in stream:
                stripped = raw_line.strip()
                if (
                    not stripped
                    or stripped.startswith("WATERSHED")
                    or stripped.startswith("(")
                    or stripped.startswith("Day")
                    or stripped.startswith("-")
                    or stripped.startswith("Month")
                    or stripped.startswith("Year")
                ):
                    continue

                tokens = stripped.split()
                if len(tokens) != 11:
                    continue

                day_of_month = int(tokens[0])
                month = int(tokens[1])
                sim_year = int(tokens[2])
                if start_year is not None and sim_year < 1000:
                    year = start_year + sim_year - 1
                else:
                    year = sim_year

                julian = (datetime(year, month, day_of_month) - datetime(year, 1, 1)).days + 1
                store["year"].append(year)
                store["simulation_year"].append(sim_year)
                store["month"].append(month)
                store["day_of_month"].append(day_of_month)
                store["julian"].append(julian)
                store["water_year"].append(int(determine_wateryear(year, julian)))

                store["precip"].append(_parse_float(tokens[3]))
                store["runoff_volume"].append(_parse_float(tokens[4]))
                store["peak_runoff"].append(_parse_float(tokens[5]))
                store["sediment_yield"].append(_parse_float(tokens[6]))
                store["soluble_pollutant"].append(_parse_float(tokens[7]))
                store["particulate_pollutant"].append(_parse_float(tokens[8]))
                store["total_pollutant"].append(_parse_float(tokens[9]))

                store["element_id"].append(int(tokens[10]))

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

def run_wepp_watershed_ebe_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    ebe_path = base / EBE_FILENAME
    _wait_for_path(ebe_path)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / EBE_PARQUET
    _write_ebe_parquet(ebe_path, target, start_year=start_year)
    return target
