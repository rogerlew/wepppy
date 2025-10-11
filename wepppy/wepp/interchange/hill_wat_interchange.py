from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

from ._utils import _parse_float, _julian_to_calendar
from .schema_utils import pa_field

WAT_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)
RAW_HEADER_SUBSTITUTIONS = (
    (" -", ""),
    ("#", "(#)"),
    (" mm", ""),
    ("Water(mm)", "Water"),
    ("m^2", "(m^2)"),
)

WAT_COLUMN_NAMES = [
    "OFE",
    "J",
    "Y",
    "P",
    "RM",
    "Q",
    "Ep",
    "Es",
    "Er",
    "Dp",
    "UpStrmQ",
    "SubRIn",
    "latqcc",
    "Total-Soil Water",
    "frozwt",
    "Snow-Water",
    "QOFE",
    "Tile",
    "Irr",
    "Area",
]

HEADER_ALIASES = {
    "OFE (#)": "OFE",
    "OFE": "OFE",
    "P (mm)": "P",
    "RM (mm)": "RM",
    "Q (mm)": "Q",
    "Ep (mm)": "Ep",
    "Es (mm)": "Es",
    "Er (mm)": "Er",
    "Dp (mm)": "Dp",
    "UpStrmQ (mm)": "UpStrmQ",
    "SubRIn (mm)": "SubRIn",
    "latqcc (mm)": "latqcc",
    "Total-Soil Water (mm)": "Total-Soil Water",
    "frozwt (mm)": "frozwt",
    "Snow-Water (mm)": "Snow-Water",
    "QOFE (mm)": "QOFE",
    "Tile (mm)": "Tile",
    "Irr (mm)": "Irr",
    "Area (m^2)": "Area",
}

SCHEMA = pa.schema(
    [
        pa_field("wepp_id", pa.int32()),
        pa_field("ofe_id", pa.int16()),
        pa_field("year", pa.int16()),
        pa_field("julian", pa.int16()),
        pa_field("month", pa.int8()),
        pa_field("day_of_month", pa.int8()),
        pa_field("water_year", pa.int16()),
        pa_field("OFE", pa.int16()),
        pa_field("P", pa.float64(), units="mm", description="Precipitation"),
        pa_field("RM", pa.float64(), units="mm", description="Rainfall+Irrigation+Snowmelt"),
        pa_field("Q", pa.float64(), units="mm", description="Daily runoff over eff length"),
        pa_field("Ep", pa.float64(), units="mm", description="Plant transpiration"),
        pa_field("Es", pa.float64(), units="mm", description="Soil evaporation"),
        pa_field("Er", pa.float64(), units="mm", description="Residue evaporation"),
        pa_field("Dp", pa.float64(), units="mm", description="Deep percolation"),
        pa_field("UpStrmQ", pa.float64(), units="mm", description="Runon added to OFE"),
        pa_field("SubRIn", pa.float64(), units="mm", description="Subsurface runon added to OFE"),
        pa_field("latqcc", pa.float64(), units="mm", description="Lateral subsurface flow"),
        pa_field("Total-Soil Water", pa.float64(), units="mm", description="Unfrozen water in soil profile"),
        pa_field("frozwt", pa.float64(), units="mm", description="Frozen water in soil profile"),
        pa_field("Snow-Water", pa.float64(), units="mm", description="Water in surface snow"),
        pa_field("QOFE", pa.float64(), units="mm", description="Daily runoff scaled to single OFE"),
        pa_field("Tile", pa.float64(), units="mm", description="Tile drainage"),
        pa_field("Irr", pa.float64(), units="mm", description="Irrigation"),
        pa_field("Area", pa.float64(), units="m^2", description="Area that depths apply over"),
    ]
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)


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
    transposed = list(zip(*raw_header_rows))
    header: List[str] = []
    for column_parts in transposed:
        merged = " ".join(column_parts)
        for old, new in RAW_HEADER_SUBSTITUTIONS:
            merged = merged.replace(old, new)
        header.append(merged.strip())

    canonical_header: List[str] = [HEADER_ALIASES.get(value, value) for value in header]

    if canonical_header != WAT_COLUMN_NAMES:
        raise ValueError(f"Unexpected WAT column layout: {header}")

    return canonical_header, header_end + 2


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
        ofe_id = int(tokens[column_positions["OFE"]])

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "ofe_id": ofe_id,
            "year": year,
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": int(wy),
            "OFE": ofe_id,
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
