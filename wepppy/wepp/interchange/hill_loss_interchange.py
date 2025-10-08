from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from .concurrency import write_parquet_with_pool

try:
    from .schema_utils import pa_field
except ModuleNotFoundError:
    import importlib.machinery
    import importlib.util
    import sys
    from pathlib import Path

    schema_utils_path = Path(__file__).with_name("schema_utils.py")
    loader = importlib.machinery.SourceFileLoader("schema_utils_local", str(schema_utils_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    pa_field = module.pa_field

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

COLUMN_ALIASES = {
    "Diameter (mm)": "Diameter",
}

SCHEMA = pa.schema(
    [
        pa_field("wepp_id", pa.int32()),
        pa_field("class_id", pa.int8()),
        pa_field("Class", pa.int8(), description="Sediment particle size class"),
        pa_field("Diameter", pa.float64(), units="mm"),
        pa_field("Specific Gravity", pa.float64()),
        pa_field("% Sand", pa.float64(), units="%"),
        pa_field("% Silt", pa.float64(), units="%"),
        pa_field("% Clay", pa.float64(), units="%"),
        pa_field("% O.M.", pa.float64(), units="%"),
        pa_field("Sediment Fraction", pa.float64()),
        pa_field("In Flow Exiting", pa.float64()),
    ]
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)


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
            target_name = COLUMN_ALIASES.get(column_name, column_name)
            row[target_name] = _parse_float(token)

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

    write_parquet_with_pool(loss_files, _parse_loss_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
