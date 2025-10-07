from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

WAT_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)
RAW_HEADER_SUBSTITUTIONS = (
    (" -", ""),
    ("#", "(#)"),
    (" mm", " (mm)"),
    ("Water(mm)", "Water (mm)"),
    ("m^2", "(m^2)"),
)

WAT_COLUMN_NAMES = [
    "OFE (#)",
    "J",
    "Y",
    "P (mm)",
    "RM (mm)",
    "Q (mm)",
    "Ep (mm)",
    "Es (mm)",
    "Er (mm)",
    "Dp (mm)",
    "UpStrmQ (mm)",
    "SubRIn (mm)",
    "latqcc (mm)",
    "Total-Soil Water (mm)",
    "frozwt (mm)",
    "Snow-Water (mm)",
    "QOFE (mm)",
    "Tile (mm)",
    "Irr (mm)",
    "Area (m^2)",
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
        ("OFE (#)", pa.int16()),
        ("J", pa.int16()),
        ("Y", pa.int16()),
        ("P (mm)", pa.float64()),
        ("RM (mm)", pa.float64()),
        ("Q (mm)", pa.float64()),
        ("Ep (mm)", pa.float64()),
        ("Es (mm)", pa.float64()),
        ("Er (mm)", pa.float64()),
        ("Dp (mm)", pa.float64()),
        ("UpStrmQ (mm)", pa.float64()),
        ("SubRIn (mm)", pa.float64()),
        ("latqcc (mm)", pa.float64()),
        ("Total-Soil Water (mm)", pa.float64()),
        ("frozwt (mm)", pa.float64()),
        ("Snow-Water (mm)", pa.float64()),
        ("QOFE (mm)", pa.float64()),
        ("Tile (mm)", pa.float64()),
        ("Irr (mm)", pa.float64()),
        ("Area (m^2)", pa.float64()),
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


def _julian_to_calendar(year: int, julian: int) -> tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _extract_header(lines: List[str]) -> tuple[List[str], int]:
    header_start: Optional[int] = None
    header_end: Optional[int] = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            if header_start is None:
                header_start = idx
            elif header_end is None:
                header_end = idx
                break

    if header_start is None or header_end is None:
        raise ValueError("Unable to locate WAT header delimiters")

    raw_header_rows = [line.split() for line in lines[header_start + 1 : header_end]]
    transposed = zip(*raw_header_rows)
    header: List[str] = []
    for column_parts in transposed:
        merged = " ".join(column_parts)
        for old, new in RAW_HEADER_SUBSTITUTIONS:
            merged = merged.replace(old, new)
        header.append(merged.strip())

    if header != WAT_COLUMN_NAMES:
        raise ValueError(f"Unexpected WAT column layout: {header}")

    return header, header_end + 2


def _parse_wat_file(path: Path) -> pa.Table:
    match = WAT_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized WAT filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    lines = path.read_text().splitlines()
    header, data_start = _extract_header(lines)
    column_positions = {name: idx for idx, name in enumerate(header)}

    out = _init_column_store()

    for raw_line in lines[data_start:]:
        if not raw_line.strip():
            continue
        tokens = raw_line.split()
        if len(tokens) != len(header):
            continue

        julian = int(tokens[column_positions["J"]])
        year = int(tokens[column_positions["Y"]])
        month, day_of_month = _julian_to_calendar(year, julian)
        wy = determine_wateryear(year, julian)
        ofe_id = int(tokens[column_positions["OFE (#)"]])

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "ofe_id": ofe_id,
            "year": year,
            "day": julian,
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": int(wy),
            "OFE (#)": ofe_id,
            "J": julian,
            "Y": year,
        }

        for name in WAT_COLUMN_NAMES[3:]:
            token = tokens[column_positions[name]]
            row[name] = _parse_float(token)

        _append_row(out, row)

    return pa.table(out, schema=SCHEMA)


def run_wepp_hillslope_wat_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    wat_files = sorted(base.glob("H*.wat.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.wat.parquet"

    write_parquet_with_pool(wat_files, _parse_wat_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
