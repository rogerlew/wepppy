from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

from .schema_utils import pa_field
from ._utils import _build_cli_calendar_lookup, _julian_to_calendar, _parse_float
from .versioning import schema_with_version

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

LEGACY_HEADER = RAW_HEADER[:-2]

LOGGER = logging.getLogger(__name__)

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

COMPACT_UNITS = [token for token in RAW_UNITS if token]
LEGACY_UNITS = COMPACT_UNITS[: len(LEGACY_HEADER) - 3]

MEASUREMENT_COLUMNS = [
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

LEGACY_MEASUREMENT_COLUMNS = MEASUREMENT_COLUMNS[: len(LEGACY_HEADER) - 3]

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("ofe_id", pa.int16()),
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
        pa_field("julian", pa.int16()),
        pa_field("month", pa.int8()),
        pa_field("day_of_month", pa.int8()),
        pa_field("water_year", pa.int16()),
        pa_field("OFE", pa.int16()),
        pa_field("Poros", pa.float64(), units="%", description="Soil porosity"),
        pa_field("Keff", pa.float64(), units="mm/hr", description="Effective hydraulic conductivity"),
        pa_field("Suct", pa.float64(), units="mm", description="Suction across wetting front"),
        pa_field("FC", pa.float64(), units="mm/mm", description="Field capacity"),
        pa_field("WP", pa.float64(), units="mm/mm", description="Wilting point"),
        pa_field("Rough", pa.float64(), units="mm", description="Surface roughness"),
        pa_field("Ki", pa.float64(), units="adjsmt", description="Interrill erodibility adjustment factor"),
        pa_field("Kr", pa.float64(), units="adjsmt", description="Rill erodibility adjustment factor"),
        pa_field("Tauc", pa.float64(), units="adjsmt", description="Critical shear stress adjustment factor"),
            pa_field("Saturation", pa.float64(), units="frac", description="Saturation as fraction"),
            pa_field("TSW", pa.float64(), units="mm", description="Total soil water"),
        ]
    )
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)


def _extract_layout(lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
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

    if header_tokens == RAW_HEADER:
        expected_units = COMPACT_UNITS
        measurement_columns = MEASUREMENT_COLUMNS
    elif header_tokens == LEGACY_HEADER:
        expected_units = LEGACY_UNITS
        measurement_columns = LEGACY_MEASUREMENT_COLUMNS
    else:
        raise ValueError(f"Unexpected SOIL header layout: {header_tokens}")

    if unit_tokens != expected_units:
        raise ValueError(f"Unexpected SOIL units: {unit_tokens}")

    start_idx = unit_idx + 1
    while start_idx < len(lines) and not lines[start_idx].strip():
        start_idx += 1
    while start_idx < len(lines) and set(lines[start_idx].strip()) == {"-"}:
        start_idx += 1

    return lines[start_idx:], header_tokens, measurement_columns


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _parse_soil_file(path: Path, *, calendar_lookup: dict[int, list[tuple[int, int]]] | None = None) -> pa.Table:
    match = SOIL_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized SOIL filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    lines = path.read_text().splitlines()
    data_lines, header_tokens, measurement_columns = _extract_layout(lines)
    if not data_lines:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    expected_columns = len(header_tokens)
    store = _init_column_store()

    for raw_line in data_lines:
        if not raw_line.strip():
            continue
        tokens = raw_line.split()
        if len(tokens) != expected_columns:
            continue

        ofe = int(tokens[0])
        julian = int(tokens[1])
        year = int(tokens[2])

        month, day_of_month = _julian_to_calendar(year, julian, calendar_lookup=calendar_lookup)
        water_year = int(determine_wateryear(year, julian))

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "ofe_id": ofe,
            "year": year,
            "sim_day_index": int(tokens[1]),
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": water_year,
            "OFE": ofe,
        }

        for column_name, token in zip(measurement_columns, tokens[3:]):
            row[column_name] = _parse_float(token)

        for column_name in MEASUREMENT_COLUMNS:
            row.setdefault(column_name, None)

        _append_row(store, row)

    return pa.table(store, schema=SCHEMA)


def run_wepp_hillslope_soil_interchange(
    wepp_output_dir: Path | str, *, expected_hillslopes: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    soil_files = sorted(base.glob("H*.soil.dat"))
    if expected_hillslopes is not None and len(soil_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope soil files but found {len(soil_files)} in {base}"
        )
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.soil.parquet"

    calendar_lookup = _build_cli_calendar_lookup(base, log=LOGGER)
    parser = partial(_parse_soil_file, calendar_lookup=calendar_lookup)

    write_parquet_with_pool(soil_files, parser, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
