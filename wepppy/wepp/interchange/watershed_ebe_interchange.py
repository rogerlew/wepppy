from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

EBE_FILENAME = "ebe_pw0.txt"
EBE_PARQUET = "ebe_pw0.parquet"


MEASUREMENT_COLUMNS: List[tuple[str, str]] = [
    ("Precip Depth (mm)", "mm"),
    ("Runoff Volume (m^3)", "m^3"),
    ("Peak Runoff (m^3/s)", "m^3/s"),
    ("Sediment Yield (kg)", "kg"),
    ("Solub. React. Phosphorus (kg)", "kg"),
    ("Particulate Phosphorus (kg)", "kg"),
    ("Total Phosphorus (kg)", "kg"),
]


def _field(name: str, dtype: pa.DataType, units: str | None = None) -> pa.Field:
    if units is None:
        return pa.field(name, dtype)
    return pa.field(name, dtype).with_metadata({b"units": units.encode()})


SCHEMA = pa.schema(
    [
        _field("year", pa.int16()),
        _field("simulation_year", pa.int16()),
        _field("month", pa.int8()),
        _field("day_of_month", pa.int8()),
        _field("julian", pa.int16()),
        _field("water_year", pa.int16()),
    ]
    + [_field(name, pa.float64(), units) for name, units in MEASUREMENT_COLUMNS]
    + [_field("Elmt ID", pa.int32())]
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


def _parse_ebe_file(path: Path, *, start_year: int | None = None) -> pa.Table:
    with path.open("r") as stream:
        lines = stream.readlines()

    store: Dict[str, List] = {name: [] for name in SCHEMA.names}

    for raw_line in lines:
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

        # datetime supports year >= 1; simulation years should satisfy this.
        julian = (datetime(year, month, day_of_month) - datetime(year, 1, 1)).days + 1
        water_year = int(determine_wateryear(year, julian))

        store["year"].append(year)
        store["simulation_year"].append(sim_year)
        store["month"].append(month)
        store["day_of_month"].append(day_of_month)
        store["julian"].append(julian)
        store["water_year"].append(water_year)

        for (column_name, _units), token in zip(MEASUREMENT_COLUMNS, tokens[3:10]):
            store[column_name].append(_parse_float(token))

        store["Elmt ID"].append(int(tokens[10]))

    return pa.table(store, schema=SCHEMA)


def run_wepp_watershed_ebe_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    ebe_path = base / EBE_FILENAME
    if not ebe_path.exists():
        raise FileNotFoundError(ebe_path)

    table = _parse_ebe_file(ebe_path, start_year=start_year)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / EBE_PARQUET
    pq.write_table(table, target, compression="snappy", use_dictionary=True)
    return target
