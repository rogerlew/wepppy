from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa
import pyarrow.parquet as pq

LOSS_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)

MEASUREMENT_COLUMNS = [
    "Class",
    "Diameter (mm)",
    "Specific Gravity",
    "% Sand",
    "% Silt",
    "% Clay",
    "% O.M.",
    "Sediment Fraction",
    "In Flow Exiting",
]

SCHEMA = pa.schema(
    [
        ("wepp_id", pa.int32()),
        ("class_id", pa.int8()),
        ("Class", pa.int8()),
        ("Diameter (mm)", pa.float64()),
        ("Specific Gravity", pa.float64()),
        ("% Sand", pa.float64()),
        ("% Silt", pa.float64()),
        ("% Clay", pa.float64()),
        ("% O.M.", pa.float64()),
        ("Sediment Fraction", pa.float64()),
        ("In Flow Exiting", pa.float64()),
    ]
)


def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped or set(stripped) <= {"*"}:
        return float("nan")
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


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _locate_class_table(lines: List[str]) -> Optional[int]:
    target_phrase = "sediment particle information leaving profile"
    start_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if target_phrase in line.lower():
            start_idx = idx
    return start_idx


def _parse_loss_file(path: Path) -> pa.Table:
    match = LOSS_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized LOSS filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    lines = path.read_text().splitlines()
    table_anchor = _locate_class_table(lines)
    if table_anchor is None:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    data_start = table_anchor + 6
    store = _init_column_store()

    for raw_line in lines[data_start:]:
        stripped = raw_line.strip()
        if not stripped:
            break
        if set(stripped) == {"-"}:
            break

        tokens = stripped.split()
        if len(tokens) < len(MEASUREMENT_COLUMNS):
            continue

        class_value = int(tokens[0])
        measurements = tokens[1 : 1 + len(MEASUREMENT_COLUMNS) - 1]

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "class_id": class_value,
            "Class": class_value,
        }

        for column_name, token in zip(MEASUREMENT_COLUMNS[1:], measurements):
            row[column_name] = _parse_float(token)

        _append_row(store, row)

    return pa.table(store, schema=SCHEMA)


def run_wepp_hillslope_loss_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    loss_files = sorted(base.glob("H*.loss.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.loss.parquet"

    if not loss_files:
        empty_table = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)
        pq.write_table(empty_table, target_path)
        return target_path

    tmp_path = target_path.with_suffix(".tmp")
    writer: Optional[pq.ParquetWriter] = None
    try:
        for loss_file in loss_files:
            table = _parse_loss_file(loss_file)
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
