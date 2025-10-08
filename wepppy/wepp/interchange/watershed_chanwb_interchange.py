from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

CHANWB_FILENAME = "chnwb.txt"
CHANWB_PARQUET = "chnwb.parquet"


def _field(name: str, dtype: pa.DataType, *, units: str | None = None, description: str | None = None) -> pa.Field:
    metadata: Dict[bytes, bytes] = {}
    if units is not None:
        metadata[b"units"] = units.encode()
    if description is not None:
        metadata[b"description"] = description.encode()

    if metadata:
        return pa.field(name, dtype).with_metadata(metadata)
    return pa.field(name, dtype)


MEASUREMENT_COLUMNS: List[tuple[str, str | None, str | None]] = [
    ("P (mm)", "mm", "precipitation"),
    ("RM (mm)", "mm", "rainfall + irrigation + snowmelt"),
    ("Q (mm)", "mm", "daily runoff over effective length"),
    ("Ep (mm)", "mm", "plant transpiration"),
    ("Es (mm)", "mm", "soil evaporation"),
    ("Er (mm)", "mm", "residue evaporation"),
    ("Dp (mm)", "mm", "deep percolation"),
    ("UpStrmQ (mm)", "mm", "Runon added to OFE"),
    ("SubRIn (mm)", "mm", "Subsurface runon added to OFE"),
    ("latqcc (mm)", "mm", "lateral subsurface flow"),
    ("Total Soil Water (mm)", "mm", "Unfrozen water in soil profile"),
    ("frozwt (mm)", "mm", "Frozen water in soil profile"),
    ("Snow Water (mm)", "mm", "Water in surface snow"),
    ("QOFE (mm)", "mm", "Daily runoff scaled to single OFE"),
    ("Tile (mm)", "mm", "Tile drainage"),
    ("Irr (mm)", "mm", "Irrigation"),
    ("Surf (mm)", "mm", "Surface storage"),
    ("Base (mm)", "mm", "Portion of runon from external baseflow"),
    ("Area (m^2)", "m^2", "Area that depths apply over"),
]


SCHEMA = pa.schema(
    [
        _field("wepp_id", pa.int32(), description="Channel (OFE) identifier"),
        _field("julian", pa.int16(), description="Julian day"),
        _field("year", pa.int16(), description="Calendar year"),
        _field("simulation_year", pa.int16(), description="Simulation year value from input file"),
        _field("month", pa.int8(), description="Calendar month"),
        _field("day_of_month", pa.int8(), description="Calendar day of month"),
        _field("water_year", pa.int16(), description="Computed water year"),
        _field("OFE", pa.int16(), description="Channel OFE index"),
        _field("J", pa.int16(), description="Julian day as reported"),
        _field("Y", pa.int16(), description="Simulation year as reported"),
    ]
    + [
        _field(name, pa.float64(), units=units, description=description)
        for name, units, description in MEASUREMENT_COLUMNS
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


def _parse_chanwb_file(path: Path, *, start_year: int | None = None) -> pa.Table:
    with path.open("r") as stream:
        lines = stream.readlines()

    header_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("OFE"):
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError("Unable to locate header line in chnwb.txt")

    data_lines = lines[header_idx + 3 :]
    column_store: Dict[str, List] = {name: [] for name in SCHEMA.names}

    for raw_line in data_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("-"):
            continue

        tokens = stripped.split()
        if len(tokens) != 22:
            continue

        ofe = int(tokens[0])
        julian = int(tokens[1])
        sim_year = int(tokens[2])

        if start_year is not None and sim_year < 1000:
            year = start_year + sim_year - 1
        else:
            year = sim_year

        date_obj = datetime(year, 1, 1) + timedelta(days=julian - 1)
        month = date_obj.month
        day_of_month = date_obj.day
        water_year = int(determine_wateryear(year, julian))

        column_store["wepp_id"].append(ofe)
        column_store["julian"].append(julian)
        column_store["year"].append(year)
        column_store["simulation_year"].append(sim_year)
        column_store["month"].append(month)
        column_store["day_of_month"].append(day_of_month)
        column_store["water_year"].append(water_year)
        column_store["OFE"].append(ofe)
        column_store["J"].append(julian)
        column_store["Y"].append(sim_year)

        measurement_values = tokens[3:]
        for (key, _units, _description), token in zip(MEASUREMENT_COLUMNS, measurement_values):
            column_store[key].append(_parse_float(token))

    return pa.table(column_store, schema=SCHEMA)


def run_wepp_watershed_chanwb_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / CHANWB_FILENAME
    if not source.exists():
        raise FileNotFoundError(source)

    table = _parse_chanwb_file(source, start_year=start_year)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHANWB_PARQUET
    pq.write_table(table, target, compression="snappy", use_dictionary=True)
    return target
