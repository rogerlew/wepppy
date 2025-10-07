from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

ELEMENT_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)

ELEMENT_COLUMN_NAMES = [
    "OFE",
    "DD",
    "MM",
    "YYYY",
    "Precip (mm)",
    "Runoff (mm)",
    "EffInt (mm/h)",
    "PeakRO (mm/h)",
    "EffDur (h)",
    "Enrich (Ratio)",
    "Keff (mm/h)",
    "Sm (mm)",
    "LeafArea (Index)",
    "CanHgt (m)",
    "Cancov (%)",
    "IntCov (%)",
    "RilCov (%)",
    "LivBio (Kg/m^2)",
    "DeadBio (Kg/m^2)",
    "Ki",
    "Kr",
    "Tcrit",
    "RilWid (m)",
    "SedLeave (kg/m)",
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
        ("DD", pa.int16()),
        ("MM", pa.int16()),
        ("YYYY", pa.int16()),
        ("Precip (mm)", pa.float64()),
        ("Runoff (mm)", pa.float64()),
        ("EffInt (mm/h)", pa.float64()),
        ("PeakRO (mm/h)", pa.float64()),
        ("EffDur (h)", pa.float64()),
        ("Enrich (Ratio)", pa.float64()),
        ("Keff (mm/h)", pa.float64()),
        ("Sm (mm)", pa.float64()),
        ("LeafArea (Index)", pa.float64()),
        ("CanHgt (m)", pa.float64()),
        ("Cancov (%)", pa.float64()),
        ("IntCov (%)", pa.float64()),
        ("RilCov (%)", pa.float64()),
        ("LivBio (Kg/m^2)", pa.float64()),
        ("DeadBio (Kg/m^2)", pa.float64()),
        ("Ki", pa.float64()),
        ("Kr", pa.float64()),
        ("Tcrit", pa.float64()),
        ("RilWid (m)", pa.float64()),
        ("SedLeave (kg/m)", pa.float64()),
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


def _is_missing_token(token: str) -> bool:
    stripped = token.strip()
    return bool(stripped) and set(stripped) == {"*"}


def _parse_optional_float(token: str) -> Optional[float]:
    if _is_missing_token(token):
        return None
    return _parse_float(token)


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


def _parse_element_file(path: Path) -> pa.Table:
    match = ELEMENT_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized element filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    raw_lines = path.read_text().splitlines()
    stripped_lines = [line.strip() for line in raw_lines if line.strip()]
    if len(stripped_lines) < 3:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    data_lines = stripped_lines[2:]
    out = _init_column_store()

    previous_values: Dict[str, float] = {}

    for idx, raw_line in enumerate(data_lines):
        tokens = raw_line.split()
        if len(tokens) != len(ELEMENT_COLUMN_NAMES):
            raise ValueError(f"Unexpected token count in {path}: {len(tokens)}")

        ofe = int(tokens[0])
        day_of_month = int(tokens[1])
        month = int(tokens[2])
        year = int(tokens[3])

        julian = (datetime(year, month, day_of_month) - datetime(year, 1, 1)).days + 1
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
            "DD": day_of_month,
            "MM": month,
            "YYYY": year,
        }

        for column_name, token in zip(ELEMENT_COLUMN_NAMES[4:], tokens[4:]):
            value = _parse_optional_float(token)
            if value is None:
                if idx == 0:
                    value = 0.0
                else:
                    value = previous_values[column_name]
            row[column_name] = value

        _append_row(out, row)
        previous_values = {name: row[name] for name in ELEMENT_COLUMN_NAMES[4:]}

    return pa.table(out, schema=SCHEMA)


def run_wepp_hillslope_element_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    element_files = sorted(base.glob("H*.element.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.element.parquet"

    write_parquet_with_pool(element_files, _parse_element_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
