from __future__ import annotations

from functools import partial
from pathlib import Path
import logging
from typing import Dict, List, Optional

import re

import pyarrow as pa

from .concurrency import write_parquet_with_pool

from ._utils import _parse_float
from .schema_utils import pa_field
from .versioning import schema_with_version
from ._rust_interchange import load_rust_interchange, version_args

LOSS_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)
LOGGER = logging.getLogger(__name__)

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

SCHEMA = schema_with_version(
    pa.schema(
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
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

def _init_column_store() -> Dict[str, List]:
    """Create an empty columnar store keyed by schema column name."""
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    """Append a parsed record to the in-memory column store."""
    for name in SCHEMA.names:
        store[name].append(row[name])


def _locate_class_table(lines: List[str]) -> Optional[int]:
    """Return the index of the table header for sediment particle classes."""
    target_phrase = "sediment particle information leaving profile"
    start_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if target_phrase in line.lower():
            start_idx = idx
    return start_idx


def _parse_loss_file(path: Path) -> pa.Table:
    """Parse a single `H*.loss.dat` file into a PyArrow table."""
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


def _parse_loss_file_rust(path: Path, *, version: tuple[int, int]) -> pa.Table:
    rust_mod, rust_err = load_rust_interchange()
    if rust_mod is None:
        LOGGER.warning(
            "wepp interchange: Rust module unavailable for hillslope LOSS; falling back to Python (%s)",
            rust_err,
        )
        return _parse_loss_file(path)

    major, minor = version
    try:
        columns = rust_mod.hillslope_loss_to_columns(str(path), major, minor)
        return pa.table(columns, schema=SCHEMA)
    except Exception as exc:
        LOGGER.warning(
            "wepp interchange: Rust hillslope LOSS failed; falling back to Python (%s)",
            exc,
            exc_info=True,
        )
        return _parse_loss_file(path)


def run_wepp_hillslope_loss_interchange(
    wepp_output_dir: Path | str, *, expected_hillslopes: int | None = None
) -> Path:
    """Generate `H.loss.parquet` by parsing all hillslope loss outputs."""
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    loss_files = sorted(base.glob("H*.loss.dat"))
    if expected_hillslopes is not None and len(loss_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope loss files but found {len(loss_files)} in {base}"
        )
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.loss.parquet"

    rust_mod, rust_err = load_rust_interchange()
    if rust_mod is not None:
        major, minor = version_args()
        parser = partial(_parse_loss_file_rust, version=(major, minor))
        LOGGER.info("wepp interchange: hillslope LOSS via Rust")
    else:
        LOGGER.warning(
            "wepp interchange: Rust module unavailable for hillslope LOSS; falling back to Python (%s)",
            rust_err,
        )
        parser = _parse_loss_file

    write_parquet_with_pool(loss_files, parser, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
