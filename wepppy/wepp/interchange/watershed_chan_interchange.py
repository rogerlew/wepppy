from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

CHAN_FILENAME = "chanwb.out"
CHAN_PARQUET = "chanwb.parquet"


def _field(name: str, dtype: pa.DataType, *, units: str | None = None, description: str | None = None) -> pa.Field:
    metadata: Dict[bytes, bytes] = {}
    if units is not None:
        metadata[b"units"] = units.encode()
    if description is not None:
        metadata[b"description"] = description.encode()
    if metadata:
        return pa.field(name, dtype).with_metadata(metadata)
    return pa.field(name, dtype)


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
        _field("year", pa.int16(), description="Calendar year"),
        _field("simulation_year", pa.int16(), description="Simulation year from chanwb.out"),
        _field("julian", pa.int16(), description="Julian day reported by WEPP"),
        _field("month", pa.int8(), description="Calendar month derived from Julian day"),
        _field("day_of_month", pa.int8(), description="Calendar day-of-month derived from Julian day"),
        _field("water_year", pa.int16(), description="Water year computed from Julian day"),
        _field("Elmt_ID", pa.int32(), description="Channel element identifier"),
        _field("Chan_ID", pa.int32(), description="Channel ID reported by WEPP"),
    ]
    + [_field(name, pa.float64(), units=units, description=description) for name, units, description in MEASUREMENT_COLUMNS]
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


def _parse_chan_file(path: Path, *, start_year: int | None = None) -> pa.Table:
    with path.open("r") as stream:
        lines = stream.readlines()

    data_start = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("Year") and "Elmt_ID" in line:
            data_start = idx + 1
            break

    if data_start is None:
        raise ValueError("Unable to locate data table in chanwb.out")

    column_store: Dict[str, List] = {name: [] for name in SCHEMA.names}
    data_lines = lines[data_start:]

    for raw_line in data_lines:
        stripped = raw_line.strip()
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
        month = date_obj.month
        day_of_month = date_obj.day
        water_year = int(determine_wateryear(year, julian))

        column_store["year"].append(year)
        column_store["simulation_year"].append(sim_year)
        column_store["julian"].append(julian)
        column_store["month"].append(month)
        column_store["day_of_month"].append(day_of_month)
        column_store["water_year"].append(water_year)
        column_store["Elmt_ID"].append(elmt_id)
        column_store["Chan_ID"].append(chan_id)

        measurement_values = tokens[4:]
        for (col_name, _units, _desc), token in zip(MEASUREMENT_COLUMNS, measurement_values):
            column_store[col_name].append(_parse_float(token))

    return pa.table(column_store, schema=SCHEMA)


def run_wepp_watershed_chan_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / CHAN_FILENAME
    if not source.exists():
        raise FileNotFoundError(source)

    table = _parse_chan_file(source, start_year=start_year)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHAN_PARQUET
    pq.write_table(table, target, compression="snappy", use_dictionary=True)
    return target
