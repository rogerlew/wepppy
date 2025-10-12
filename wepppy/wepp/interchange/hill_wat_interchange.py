from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import re

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

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


def _collapse_scanner_rows(
    scanner: ds.Scanner,
    *,
    group_keys: Sequence[str],
    first_value_columns: Sequence[str] | None = None,
    sum_columns: Sequence[str] | None = None,
    weighted_avg_columns: Sequence[str] | None = None,
    weight_column: str | None = None,
    sort_keys: Sequence[str] | None = None,
) -> pd.DataFrame:
    """
    Collapse scanner batches into grouped aggregates with optional weighted averages.
    """

    aggregated: Dict[Tuple[object, ...], Dict[str, object]] = {}
    has_rows = False

    for batch in scanner.to_batches():
        if batch.num_rows == 0:
            continue

        has_rows = True
        frame = batch.to_pandas(split_blocks=True)
        grouped = frame.groupby(list(group_keys), sort=False)

        for raw_key, slice_df in grouped:
            if not isinstance(raw_key, tuple):
                raw_key = (raw_key,)

            entry = aggregated.get(raw_key)
            if entry is None:
                entry = {
                    "count": 0,
                    "sum": {col: 0.0 for col in sum_columns or []},
                    "weighted": {col: 0.0 for col in weighted_avg_columns or []},
                    "weight_total": 0.0 if weight_column else None,
                    "first": {},
                }
                aggregated[raw_key] = entry

            entry["count"] += len(slice_df)

            if sum_columns:
                for col in sum_columns:
                    entry["sum"][col] += slice_df[col].sum()

            if weighted_avg_columns:
                if weight_column:
                    weights = slice_df[weight_column]
                    weight_sum = weights.sum()
                    entry["weight_total"] += weight_sum
                    weighted_values = slice_df[weighted_avg_columns].multiply(
                        weights, axis=0
                    )
                    for col in weighted_avg_columns:
                        entry["weighted"][col] += weighted_values[col].sum()
                else:
                    for col in weighted_avg_columns:
                        entry["weighted"][col] += slice_df[col].sum()

            if first_value_columns:
                for col in first_value_columns:
                    if col not in entry["first"]:
                        entry["first"][col] = slice_df[col].iloc[0]

    if not has_rows or not aggregated:
        raise ValueError("Expected hillslope records but none were found")

    records: List[Dict[str, object]] = []
    for key_tuple, entry in aggregated.items():
        record: Dict[str, object] = {}
        for col_name, value in zip(group_keys, key_tuple):
            record[col_name] = value

        if first_value_columns:
            record.update(entry["first"])

        if sum_columns:
            for col in sum_columns:
                record[col] = entry["sum"][col]

        if weighted_avg_columns:
            for col in weighted_avg_columns:
                if weight_column:
                    weight_sum = entry["weight_total"]
                    record[col] = (
                        entry["weighted"][col] / weight_sum if weight_sum else 0.0
                    )
                else:
                    count = entry["count"]
                    record[col] = entry["weighted"][col] / count if count else 0.0

        if weight_column and (
            not sum_columns or weight_column not in sum_columns
        ):
            record[weight_column] = entry["weight_total"]

        records.append(record)

    collapsed = pd.DataFrame.from_records(records)
    if sort_keys:
        collapsed.sort_values(list(sort_keys), inplace=True, ignore_index=True)
    else:
        collapsed.sort_values(list(group_keys), inplace=True, ignore_index=True)

    return collapsed


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
         using ``Area`` (m^2) as weights.  ``None`` returns the raw OFE-level records using
         the original schema emitted by the interchange writer.
    """

    base = Path(wepp_output_dir)
    target_path = base / "interchange" / "H.wat.parquet"
    if not target_path.exists():
        run_wepp_hillslope_wat_interchange(base)

    dataset = ds.dataset(target_path, format="parquet")
    filter_expr = ds.field("wepp_id") == int(wepp_id)
    schema_names = set(dataset.schema.names)
    column_map: Dict[str, str] = {}
    for canonical, aliases in CANONICAL_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in schema_names:
                column_map[canonical] = alias
                break

    if collapse is None:
        scanner = dataset.scanner(filter=filter_expr, use_threads=True)
        table = scanner.to_table(use_threads=True)
        df = table.to_pandas(split_blocks=True, use_threads=True)
        if df.empty:
            raise ValueError(
                f"No hillslope WAT records found for wepp_id={wepp_id} in {target_path}"
            )
        metadata_cols = [name for name in df.columns if name.startswith("__")]
        if metadata_cols:
            df = df.drop(columns=metadata_cols)
        rename_map = {source: canonical for canonical, source in column_map.items()}
        if rename_map:
            df = df.rename(columns=rename_map)
        df.attrs["wepp_id"] = int(wepp_id)
        df.attrs["source_path"] = str(target_path)
        return df

    collapse_mode = collapse.lower()
    if collapse_mode != "daily":
        raise ValueError(f"Unsupported collapse mode '{collapse}'. Expected 'daily' or None.")

    canonical_value_columns = WAT_COLUMN_NAMES[3:-1]

    required = ["Area", "OFE", *canonical_value_columns]
    missing = [name for name in required if name not in column_map]
    if missing:
        raise KeyError(
            f"Missing expected WAT columns {missing} in {target_path} schema"
        )

    area_column = column_map["Area"]
    value_columns = [column_map[name] for name in canonical_value_columns]

    requested_columns: List[str] = [
        "wepp_id",
        "year",
        "julian",
        "month",
        "day_of_month",
        "water_year",
        area_column,
        *value_columns,
    ]

    scanner = dataset.scanner(
        columns=requested_columns,
        filter=filter_expr,
        use_threads=True,
    )

    collapsed = _collapse_scanner_rows(
        scanner,
        group_keys=("wepp_id", "year", "julian"),
        first_value_columns=("month", "day_of_month", "water_year"),
        sum_columns=(area_column,),
        weighted_avg_columns=tuple(value_columns),
        weight_column=area_column,
        sort_keys=("year", "julian"),
    )

    if collapsed.empty:
        raise ValueError(
            f"No hillslope WAT records found for wepp_id={wepp_id} in {target_path}"
        )

    rename_map = {column_map[name]: name for name in ("Area", *canonical_value_columns)}
    collapsed = collapsed.rename(columns=rename_map)

    collapsed["day"] = np.arange(1, len(collapsed) + 1, dtype=np.int16)
    collapsed["ofe_id"] = np.full(len(collapsed), -1, dtype=np.int16)
    collapsed["OFE"] = np.full(len(collapsed), -1, dtype=np.int16)

    collapsed = collapsed[
        [
            "wepp_id",
            "ofe_id",
            "year",
            "day",
            "julian",
            "month",
            "day_of_month",
            "water_year",
            "OFE",
            *canonical_value_columns,
            "Area",
        ]
    ]

    collapsed["wepp_id"] = collapsed["wepp_id"].astype(np.int32)
    collapsed["year"] = collapsed["year"].astype(np.int16)
    collapsed["month"] = collapsed["month"].astype(np.int8)
    collapsed["day_of_month"] = collapsed["day_of_month"].astype(np.int8)
    collapsed["julian"] = collapsed["julian"].astype(np.int16)
    collapsed["water_year"] = collapsed["water_year"].astype(np.int16)
    collapsed["ofe_id"] = collapsed["ofe_id"].astype(np.int16)
    collapsed["OFE"] = collapsed["OFE"].astype(np.int16)
    collapsed["Area"] = collapsed["Area"].astype(np.float64)

    collapsed.attrs["wepp_id"] = int(wepp_id)
    collapsed.attrs["source_path"] = str(target_path)
    collapsed.attrs["collapse"] = collapse_mode
    return collapsed
