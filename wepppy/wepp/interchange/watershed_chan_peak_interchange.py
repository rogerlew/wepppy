from __future__ import annotations

import errno
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

CHAN_PEAK_FILENAME = "chan.out"
CHAN_PEAK_PARQUET = "chan.out.parquet"
CHUNK_SIZE = 500_000


def _field(name: str, dtype: pa.DataType, *, units: str | None = None, description: str | None = None) -> pa.Field:
    metadata: Dict[bytes, bytes] = {}
    if units is not None:
        metadata[b"units"] = units.encode()
    if description is not None:
        metadata[b"description"] = description.encode()
    if metadata:
        return pa.field(name, dtype).with_metadata(metadata)
    return pa.field(name, dtype)


SCHEMA = pa.schema(
    [
        _field("year", pa.int16(), description="Calendar year"),
        _field("simulation_year", pa.int16(), description="Simulation year from chan.out"),
        _field("julian", pa.int16(), description="Julian day reported by WEPP"),
        _field("month", pa.int8(), description="Calendar month derived from Julian day"),
        _field("day_of_month", pa.int8(), description="Calendar day-of-month derived from Julian day"),
        _field("water_year", pa.int16(), description="Water year computed from Julian day"),
        _field("Elmt_ID", pa.int32(), description="Channel element identifier"),
        _field("Chan_ID", pa.int32(), description="Channel ID reported by WEPP"),
        _field("Time (s)", pa.float64(), units="s", description="Time to peak discharge"),
        _field(
            "Peak_Discharge (m^3/s)",
            pa.float64(),
            units="m^3/s",
            description="Peak discharge within the reporting interval",
        ),
    ]
)


def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 0.0
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

    source = base / CHAN_PEAK_FILENAME
    if not source.exists():
        raise FileNotFoundError(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHAN_PEAK_PARQUET
    _write_chan_peak_parquet(source, target, start_year=start_year)
    return target
