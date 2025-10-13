from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import re

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

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
        pa_field("day", pa.int16()),
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

CANONICAL_COLUMN_ALIASES = {
    "wepp_id": ("wepp_id",),
    "year": ("year", "Y"),
    "julian": ("julian", "J"),
    "month": ("month", "M"),
    "day_of_month": ("day_of_month", "day", "D"),
    "water_year": ("water_year", "Water Year"),
    "Area": ("Area", "Area (m^2)"),
    "OFE": ("OFE", "OFE (#)"),
    "P": ("P", "P (mm)"),
    "RM": ("RM", "RM (mm)"),
    "Q": ("Q", "Q (mm)"),
    "Ep": ("Ep", "Ep (mm)"),
    "Es": ("Es", "Es (mm)"),
    "Er": ("Er", "Er (mm)"),
    "Dp": ("Dp", "Dp (mm)"),
    "UpStrmQ": ("UpStrmQ", "UpStrmQ (mm)"),
    "SubRIn": ("SubRIn", "SubRIn (mm)"),
    "latqcc": ("latqcc", "latqcc (mm)"),
    "Total-Soil Water": ("Total-Soil Water", "Total-Soil Water (mm)"),
    "frozwt": ("frozwt", "frozwt (mm)"),
    "Snow-Water": ("Snow-Water", "Snow-Water (mm)"),
    "QOFE": ("QOFE", "QOFE (mm)"),
    "Tile": ("Tile", "Tile (mm)"),
    "Irr": ("Irr", "Irr (mm)"),
}

PANDAS_TYPE_MAP: Dict[str, np.dtype] = {
    field.name: field.type.to_pandas_dtype()  # type: ignore[attr-defined]
    for field in SCHEMA
}

DAILY_MM_COLUMNS: Tuple[str, ...] = (
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
)


def _empty_wat_dataframe() -> pd.DataFrame:
    data: Dict[str, pd.Series] = {
        name: pd.Series(dtype=dtype) for name, dtype in PANDAS_TYPE_MAP.items()
    }
    return pd.DataFrame(data)[SCHEMA.names]


def _resolve_column_aliases(path: Path) -> Dict[str, str]:
    schema = pq.read_schema(path)
    available = set(schema.names)
    resolved: Dict[str, str] = {}
    for canonical in SCHEMA.names:
        candidates = CANONICAL_COLUMN_ALIASES.get(canonical, (canonical,))
        for candidate in candidates:
            if candidate in available:
                resolved[canonical] = candidate
                break
        else:
            if canonical in available:
                resolved[canonical] = canonical
            else:
                raise KeyError(f"Column '{canonical}' not found in {path}")
    return resolved


def _coerce_wat_dtypes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    for name, dtype in PANDAS_TYPE_MAP.items():
        if name in frame.columns:
            frame[name] = frame[name].astype(dtype, copy=False)
    return frame


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

    for i, raw_line in enumerate(lines[data_start:]):
        if not raw_line.strip():
            continue
        tokens = raw_line.split()
        if len(tokens) != len(header):
            continue

        julian = int(tokens[column_positions["J"]])
        year = int(tokens[column_positions["Y"]])
        month, day_of_month = _julian_to_calendar(year, julian)
        day = i + 1
        wy = determine_wateryear(year, julian)
        ofe_id = int(tokens[column_positions["OFE"]])

        row: Dict[str, object] = {
            "wepp_id": wepp_id,
            "ofe_id": ofe_id,
            "year": year,
            "day": day,
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

    write_parquet_with_pool(
        wat_files, _parse_wat_file, SCHEMA, target_path, empty_table=EMPTY_TABLE
    )
    return target_path


def load_hill_wat_dataframe(
    wepp_output_dir: Path | str,
    wepp_id: int,
    *,
    collapse: str | None = "daily",
) -> pd.DataFrame:
    """
    Load a hillslope WAT time series for the provided WEPP output directory and hillslope id.

    Parameters
    ----------
    wepp_output_dir
        Path to the WEPP output directory (``.../wepp/output``).
    wepp_id
        Integer hillslope identifier (WEPP id).
    collapse
         ``"daily"`` (default) returns one record per simulation day aggregated across OFEs
         using ``Area`` (m^2) as weights by converting mm measures to m^3, aggregating, and converting back to mm. 
        ``None`` returns the raw OFE-level records using
         the original schema emitted by the interchange writer.
    """
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    wat_path = base / "interchange" / "H.wat.parquet"
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)

    if collapse is None:
        normalized_collapse: str | None = None
    elif isinstance(collapse, str):
        normalized_collapse = collapse.lower()
    else:
        raise TypeError("collapse must be a string or None")

    if normalized_collapse not in (None, "daily"):
        raise ValueError(f"Unsupported collapse value: {collapse!r}")

    wepp_id_int = int(wepp_id)
    alias_map = _resolve_column_aliases(wat_path)

    con = duckdb.connect(database=":memory:")
    try:
        if normalized_collapse is None:
            select_list = [
                f'"{alias_map[name]}" AS "{name}"'
                for name in SCHEMA.names
            ]
            query = f"""
                SELECT {', '.join(select_list)}
                FROM read_parquet('{wat_path.as_posix()}')
                WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                ORDER BY "{alias_map['year']}", "{alias_map['julian']}", "{alias_map['day']}", "{alias_map['ofe_id']}"
            """
            frame = con.execute(query).df()
            if frame.empty:
                frame = _empty_wat_dataframe()
            else:
                frame = frame[SCHEMA.names]
                frame = _coerce_wat_dtypes(frame)
        else:
            area_column = alias_map["Area"]
            mm_volume_expr = ",\n                    ".join(
                f'SUM("{alias_map[column]}" * 0.001 * "{area_column}") AS "{column}_volume"'
                for column in DAILY_MM_COLUMNS
            )
            query = f"""
                SELECT
                    "{alias_map['wepp_id']}" AS wepp_id,
                    "{alias_map['year']}" AS year,
                    "{alias_map['day']}" AS day,
                    "{alias_map['julian']}" AS julian,
                    "{alias_map['month']}" AS month,
                    "{alias_map['day_of_month']}" AS day_of_month,
                    "{alias_map['water_year']}" AS water_year,
                    SUM("{area_column}") AS Area,
                    {mm_volume_expr}
                FROM read_parquet('{wat_path.as_posix()}')
                WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                GROUP BY
                    "{alias_map['wepp_id']}",
                    "{alias_map['year']}",
                    "{alias_map['day']}",
                    "{alias_map['julian']}",
                    "{alias_map['month']}",
                    "{alias_map['day_of_month']}",
                    "{alias_map['water_year']}"
                ORDER BY
                    "{alias_map['year']}",
                    "{alias_map['julian']}",
                    "{alias_map['day']}"
            """
            frame = con.execute(query).df()
            if frame.empty:
                frame = _empty_wat_dataframe()
            else:
                area = frame["Area"].to_numpy(dtype=np.float64, copy=False)
                for column in DAILY_MM_COLUMNS:
                    volume_col = f"{column}_volume"
                    volumes = frame.pop(volume_col).to_numpy(dtype=np.float64, copy=False)
                    depths = np.zeros_like(volumes, dtype=np.float64)
                    np.divide(volumes, area, out=depths, where=area > 0.0)
                    depths *= 1000.0
                    frame[column] = depths

                length = len(frame)
                frame["ofe_id"] = np.zeros(length, dtype=np.int16)
                frame["OFE"] = np.zeros(length, dtype=np.int16)
                frame = frame[SCHEMA.names]
                frame = _coerce_wat_dtypes(frame)
    finally:
        con.close()

    frame.attrs["source_path"] = str(wat_path)
    frame.attrs["wepp_id"] = wepp_id_int
    frame.attrs["collapse"] = "daily" if normalized_collapse == "daily" else "raw"
    return frame
