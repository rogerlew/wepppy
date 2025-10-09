from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
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

ELEMENT_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)

ELEMENT_COLUMN_NAMES = [
    "OFE",
    "DD",
    "MM",
    "YYYY",
    "Precip",
    "Runoff",
    "EffInt",
    "PeakRO",
    "EffDur",
    "Enrich",
    "Keff",
    "Sm",
    "LeafArea",
    "CanHgt",
    "Cancov",
    "IntCov",
    "RilCov",
    "LivBio",
    "DeadBio",
    "Ki",
    "Kr",
    "Tcrit",
    "RilWid",
    "SedLeave",
]

ELEMENT_FIELD_WIDTHS = [
    3,  # OFE
    3,  # DD
    3,  # MM
    5,  # YYYY
    9,  # Precip
    9,  # Runoff
    8,  # EffInt
    8,  # PeakRO
    8,  # EffDur
    6,  # Enrich
    8,  # Keff
    8,  # Sm
    8,  # LeafArea
    7,  # CanHgt
    9,  # Cancov
    9,  # IntCov
    9,  # RilCov
    9,  # LivBio
    7,  # DeadBio
    7,  # Ki
    7,  # Kr
    7,  # Tcrit
    7,  # RilWid
    9,  # SedLeave
]

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
        pa_field("Precip", pa.float64(), units="mm"),
        pa_field("Runoff", pa.float64(), units="mm"),
        pa_field("EffInt", pa.float64(), units="mm/h", description="Effective rainfall intensity"),
        pa_field("PeakRO", pa.float64(), units="mm/h", description="Peak runoff rate"),
        pa_field("EffDur", pa.float64(), units="h"),
        pa_field("Enrich", pa.float64(), description="Sediment enrichment ratio"),
        pa_field("Keff", pa.float64(), units="mm/h", description="Effective hydraulic conductivity"),
        pa_field("Sm", pa.float64(), units="mm"),
        pa_field("LeafArea", pa.float64(), description="Leaf area index"),
        pa_field("CanHgt", pa.float64(), units="m", description="Canopy height"),
        pa_field("Cancov", pa.float64(), units="%", description="Canopy cover"),
        pa_field("IntCov", pa.float64(), units="%", description="Interrill cover"),
        pa_field("RilCov", pa.float64(), units="%", description="Rill cover"),
        pa_field("LivBio", pa.float64(), units="kg/m^2"),
        pa_field("DeadBio", pa.float64(), units="kg/m^2"),
        pa_field("Ki", pa.float64(), units="kg s/m^4", description="Interrill erodibility"),
        pa_field("Kr", pa.float64(), units="s/m", description="Rill erodibility"),
        pa_field("Tcrit", pa.float64()),
        pa_field("RilWid", pa.float64(), units="m"),
        pa_field("SedLeave", pa.float64(), units="kg/m"),
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


_LINE_WIDTH = sum(ELEMENT_FIELD_WIDTHS)


def _split_fixed_width_line(raw_line: str) -> List[str]:
    if len(raw_line) < _LINE_WIDTH:
        raw_line = raw_line.ljust(_LINE_WIDTH)
    tokens: List[str] = []
    idx = 0
    for width in ELEMENT_FIELD_WIDTHS:
        segment = raw_line[idx : idx + width]
        tokens.append(segment.strip())
        idx += width
    remainder = raw_line[idx:]
    if remainder.strip():
        raise ValueError(f"Unexpected trailing characters past fixed width payload: {remainder!r}")
    return tokens


def _parse_element_file(path: Path) -> pa.Table:
    match = ELEMENT_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized element filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    raw_lines = path.read_text().splitlines()
    trimmed_lines = [line.rstrip("\n") for line in raw_lines if line.strip()]
    if len(trimmed_lines) < 3:
        return pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

    data_lines = trimmed_lines[2:]
    out = _init_column_store()

    previous_values: Dict[str, float] = {}

    for idx, raw_line in enumerate(data_lines):
        tokens = _split_fixed_width_line(raw_line)

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
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": water_year,
            "OFE": ofe,
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
