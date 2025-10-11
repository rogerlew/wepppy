from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from functools import partial

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

from ._utils import _parse_float
from .schema_utils import pa_field

EBE_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)
UNIT_SKIP_TOKENS = {"---", "--", "----"}
RAW_HEADER = [
    "day",
    "mo",
    "year",
    "Precp",
    "Runoff",
    "IR-det",
    "Av-det",
    "Mx-det",
    "Point",
    "Av-dep",
    "Max-dep",
    "Point",
    "Sed.Del",
    "ER",
]
RAW_UNITS = [
    "---",
    "--",
    "----",
    "(mm)",
    "(mm)",
    "kg/m^2",
    "kg/m^2",
    "kg/m^2",
    "(m)",
    "kg/m^2",
    "kg/m^2",
    "(m)",
    "(kg/m)",
    "----",
]
MEASUREMENT_COLUMNS = [
    "Precp (mm)",
    "Runoff (mm)",
    "IR-det (kg/m^2)",
    "Av-det (kg/m^2)",
    "Mx-det (kg/m^2)",
    "Point (m)",
    "Av-dep (kg/m^2)",
    "Max-dep (kg/m^2)",
    "Point (m)_2",
    "Sed.Del (kg/m)",
    "ER",
]

COLUMN_ALIASES = {
    "Precp (mm)": "Precip",
    "Runoff (mm)": "Runoff",
    "IR-det (kg/m^2)": "IR-det",
    "Av-det (kg/m^2)": "Av-det",
    "Mx-det (kg/m^2)": "Mx-det",
    "Point (m)": "Det-point",
    "Point (m)_2": "Dep-point",
    "Sed.Del (kg/m)": "Sed.Del",
    "Av-dep (kg/m^2)": "Av-dep",
    "Max-dep (kg/m^2)": "Max-dep",
}

SCHEMA = pa.schema(
    [
        pa_field("wepp_id", pa.int32()),
        pa_field("year", pa.int16()),
        pa_field("month", pa.int8()),
        pa_field("day_of_month", pa.int8()),
        pa_field("julian", pa.int16()),
        pa_field("water_year", pa.int16()),
        pa_field("Precip", pa.float64(), units="mm", description="Storm precipitation depth"),  # sedout.for:439
        pa_field("Runoff", pa.float64(), units="mm", description="Runoff depth scaled by effective flow length"),  # sedout.for:433-438
        pa_field("IR-det", pa.float64(), units="kg/m^2", description="Weighted interrill detachment over the hillslope"),  # sedout.for:420-429
        pa_field("Av-det", pa.float64(), units="kg/m^2", description="Average soil detachment across detachment regions"),  # cseddet.inc
        pa_field("Mx-det", pa.float64(), units="kg/m^2", description="Maximum soil detachment across detachment regions"),  # cseddet.inc
        pa_field("Det-point", pa.float64(), units="m", description="Location of maximum soil detachment along hillslope"),  # cseddet.inc
        pa_field("Av-dep", pa.float64(), units="kg/m^2", description="Average sediment deposition across deposition regions"),  # cseddet.inc
        pa_field("Max-dep", pa.float64(), units="kg/m^2", description="Maximum sediment deposition across deposition regions"),  # cseddet.inc
        pa_field("Dep-point", pa.float64(), units="m", description="Location of maximum sediment deposition along hillslope"),  # cseddet.inc
        pa_field("Sed.Del", pa.float64(), units="kg/m", description="Storm sediment load per unit width at hillslope outlet"),  # cavloss.inc / sedout.for:439
        pa_field("ER", pa.float64(), description="Specific surface enrichment ratio for event sediment"),  # cenrpa2.inc / sedout.for:439
    ]
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)


def _normalize_column_names(headers: List[str], units: List[str]) -> List[str]:
    if headers != RAW_HEADER or units != RAW_UNITS:
        raise ValueError(f"Unexpected EBE header layout: {headers} / {units}")

    out: List[str] = []
    for name, unit in zip(headers, units):
        cleaned = unit.strip()
        if cleaned and cleaned not in UNIT_SKIP_TOKENS:
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = cleaned[1:-1]
            column = f"{name} ({cleaned})"
        else:
            column = name
        out.append(column)

    seen: Dict[str, int] = defaultdict(int)
    deduped: List[str] = []
    for column in out:
        seen[column] += 1
        if seen[column] > 1:
            deduped.append(f"{column}_{seen[column]}")
        else:
            deduped.append(column)
    return deduped


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _extract_tokens(lines: List[str]) -> tuple[List[str], List[str], List[str]]:
    stripped = [line.strip() for line in lines if line.strip()]
    if len(stripped) < 3:
        return [], [], []
    header_tokens = stripped[1].split()
    unit_tokens = stripped[2].split()
    data_lines = stripped[3:]
    return header_tokens, unit_tokens, data_lines


def _parse_ebe_file(path: Path, *, start_year: int | None = None) -> pa.Table:
    match = EBE_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized EBE filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    lines = path.read_text().splitlines()
    header_tokens, unit_tokens, data_lines = _extract_tokens(lines)
    if not data_lines:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    column_names = _normalize_column_names(header_tokens, unit_tokens)
    measurement_columns = column_names[3:]
    if measurement_columns != MEASUREMENT_COLUMNS:
        raise ValueError(f"Unexpected EBE measurement columns: {measurement_columns}")
    store = _init_column_store()

    for raw_line in data_lines:
        tokens = raw_line.split()
        if len(tokens) != len(column_names):
            continue

        day_of_month = int(tokens[0])
        month = int(tokens[1])
        raw_year = int(tokens[2])
        if start_year is not None and raw_year < 1000:
            year = start_year + raw_year - 1
        else:
            year = raw_year
            
        julian = (datetime(year, month, day_of_month) - datetime(year, 1, 1)).days + 1
        water_year = int(determine_wateryear(year, julian))

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "year": year,
            "month": month,
            "day_of_month": day_of_month,
            "julian": julian,
            "water_year": water_year,
        }

        for column_name, token in zip(measurement_columns, tokens[3:]):
            target_name = COLUMN_ALIASES.get(column_name, column_name)
            row[target_name] = _parse_float(token)

        _append_row(store, row)

    table = pa.table(store, schema=SCHEMA)
    return table


def run_wepp_hillslope_ebe_interchange(wepp_output_dir: Path | str, *, start_year: int | None = None) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    ebe_files = sorted(base.glob("H*.ebe.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.ebe.parquet"

    if start_year is None:
        parser = _parse_ebe_file
    else:
        parser = partial(_parse_ebe_file, start_year=start_year)

    write_parquet_with_pool(ebe_files, parser, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
