from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

SOIL_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)

RAW_HEADER = [
    "OFE",
    "Day",
    "Y",
    "Poros",
    "Keff",
    "Suct",
    "FC",
    "WP",
    "Rough",
    "Ki",
    "Kr",
    "Tauc",
    "Saturation",
    "TSW",
]

RAW_UNITS = [
    "",
    "",
    "",
    "%",
    "mm/hr",
    "mm",
    "mm/mm",
    "mm/mm",
    "mm",
    "adjsmt",
    "adjsmt",
    "adjsmt",
    "frac",
    "mm",
]

MEASUREMENT_COLUMNS = [
    "Poros (%)",
    "Keff (mm/hr)",
    "Suct (mm)",
    "FC (mm/mm)",
    "WP (mm/mm)",
    "Rough (mm)",
    "Ki (adjsmt)",
    "Kr (adjsmt)",
    "Tauc (adjsmt)",
    "Saturation (frac)",
    "TSW (mm)",
]

SCHEMA = pa.schema(
    [
        ("wepp_id", pa.int32()),
        ("ofe_id", pa.int16()),
        ("year", pa.int16()),
        ("day", pa.int16()),
        ("julian", pa.int16()),
        ("month", pa.int8()),
        ("day_of_month", pa.int8()),
        ("water_year", pa.int16()),
        ("OFE", pa.int16()),
        ("Day", pa.int16()),
        ("Y", pa.int16()),
        ("Poros (%)", pa.float64()),
        ("Keff (mm/hr)", pa.float64()),
        ("Suct (mm)", pa.float64()),
        ("FC (mm/mm)", pa.float64()),
        ("WP (mm/mm)", pa.float64()),
        ("Rough (mm)", pa.float64()),
        ("Ki (adjsmt)", pa.float64()),
        ("Kr (adjsmt)", pa.float64()),
        ("Tauc (adjsmt)", pa.float64()),
        ("Saturation (frac)", pa.float64()),
        ("TSW (mm)", pa.float64()),
    ]
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)


def _parse_float(token: str) -> float:
    try:
        return float(token)
    except ValueError:
        if "E" not in token.upper():
            if "-" in token[1:]:
                return float(token.replace("-", "E-", 1))
            if "+" in token[1:]:
                return float(token.replace("+", "E+", 1))
        raise


def _extract_layout(lines: List[str]) -> List[str]:
    header_idx: Optional[int] = None
    unit_idx: Optional[int] = None
    header_tokens: Optional[List[str]] = None
    unit_tokens: Optional[List[str]] = None

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        if header_idx is None and tokens[:3] == ["OFE", "Day", "Y"]:
            header_idx = idx
            header_tokens = tokens
            continue
        if header_idx is not None and unit_idx is None and {"mm/hr", "frac", "adjsmt"}.intersection(tokens):
            unit_idx = idx
            unit_tokens = tokens
            break

    if header_idx is None or unit_idx is None or header_tokens is None or unit_tokens is None:
        raise ValueError("Unable to locate SOIL header layout")

    if header_tokens != RAW_HEADER:
        raise ValueError(f"Unexpected SOIL header layout: {header_tokens}")

    expected_units = [token for token in RAW_UNITS if token]
    if unit_tokens != expected_units:
        raise ValueError(f"Unexpected SOIL units: {unit_tokens}")

    start_idx = unit_idx + 1
    while start_idx < len(lines) and not lines[start_idx].strip():
        start_idx += 1
    while start_idx < len(lines) and set(lines[start_idx].strip()) == {"-"}:
        start_idx += 1

    return lines[start_idx:]


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _parse_soil_file(path: Path) -> pa.Table:
    match = SOIL_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized SOIL filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    lines = path.read_text().splitlines()
    data_lines = _extract_layout(lines)
    if not data_lines:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    store = _init_column_store()

    for raw_line in data_lines:
        if not raw_line.strip():
            continue
        tokens = raw_line.split()
        if len(tokens) != len(RAW_HEADER):
            continue

        ofe = int(tokens[0])
        julian = int(tokens[1])
        year = int(tokens[2])

        date = datetime(year, 1, 1) + timedelta(days=julian - 1)
        month = date.month
        day_of_month = date.day
        water_year = int(determine_wateryear(year, julian))

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "ofe_id": ofe,
            "year": year,
            "day": julian,
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": water_year,
            "OFE": ofe,
            "Day": julian,
            "Y": year,
        }

        for column_name, token in zip(MEASUREMENT_COLUMNS, tokens[3:]):
            row[column_name] = _parse_float(token)

        _append_row(store, row)

    return pa.table(store, schema=SCHEMA)


def run_wepp_hillslope_soil_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    soil_files = sorted(base.glob("H*.soil.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.soil.parquet"

    write_parquet_with_pool(soil_files, _parse_soil_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
