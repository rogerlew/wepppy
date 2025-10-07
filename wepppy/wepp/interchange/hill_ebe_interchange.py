from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

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
SCHEMA = pa.schema(
    [
        ("wepp_id", pa.int32()),
        ("year", pa.int16()),
        ("month", pa.int8()),
        ("day_of_month", pa.int8()),
        ("julian", pa.int16()),
        ("water_year", pa.int16()),
        ("Precp (mm)", pa.float64()),
        ("Runoff (mm)", pa.float64()),
        ("IR-det (kg/m^2)", pa.float64()),
        ("Av-det (kg/m^2)", pa.float64()),
        ("Mx-det (kg/m^2)", pa.float64()),
        ("Point (m)", pa.float64()),
        ("Av-dep (kg/m^2)", pa.float64()),
        ("Max-dep (kg/m^2)", pa.float64()),
        ("Point (m)_2", pa.float64()),
        ("Sed.Del (kg/m)", pa.float64()),
        ("ER", pa.float64()),
    ]
)


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


def _parse_ebe_file(path: Path) -> pa.Table:
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
        year = int(tokens[2])
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
            row[column_name] = _parse_float(token)

        _append_row(store, row)

    table = pa.table(store, schema=SCHEMA)
    return table


def run_wepp_hillslope_ebe_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    ebe_files = sorted(base.glob("H*.ebe.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.ebe.parquet"

    if not ebe_files:
        table = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)
        pq.write_table(table, target_path)
        return target_path

    tmp_path = target_path.with_suffix(".tmp")
    writer: Optional[pq.ParquetWriter] = None
    try:
        for ebe_file in ebe_files:
            table = _parse_ebe_file(ebe_file)
            if table.num_rows == 0:
                continue
            if writer is None:
                writer = pq.ParquetWriter(tmp_path, SCHEMA, compression="snappy", use_dictionary=True)
            writer.write_table(table)

        if writer is None:
            empty_table = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)
            pq.write_table(empty_table, tmp_path)
        else:
            writer.close()
            writer = None
        tmp_path.replace(target_path)
    finally:
        if writer is not None:
            writer.close()
        if tmp_path.exists() and not target_path.exists():
            tmp_path.unlink()

    return target_path
