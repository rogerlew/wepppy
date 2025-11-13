from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

from .schema_utils import pa_field
from ._utils import _parse_float, _julian_to_calendar
from .versioning import schema_with_version


EVENT_LABELS = {"EVENT", "SUBEVENT", "NO EVENT"}
SEDCLASS_COUNT = 5
EVENT_FLOAT_COUNT = 12 + (2 * SEDCLASS_COUNT) + 2  # dur..tdep + sedcon + frcflw + gwbfv/gwdsv
SUBEVENT_FLOAT_COUNT = 6  # sbrunf, sbrunv, drainq, drrunv, gwbfv, gwdsv
NOEVENT_FLOAT_COUNT = 2  # gwbfv, gwdsv


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("event", pa.string(), description="Record type: EVENT, SUBEVENT, NO EVENT"),
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day since start year"),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("dur", pa.float64(), units="s", description="Storm duration"),
            pa_field("tcs", pa.float64(), units="h", description="Overland flow time of concentration"),
            pa_field("oalpha", pa.float64(), units="unitless", description="Overland flow alpha parameter"),
            pa_field("runoff", pa.float64(), units="m", description="Runoff depth"),
            pa_field("runvol", pa.float64(), units="m^3", description="Runoff volume"),
            pa_field("sbrunf", pa.float64(), units="m", description="Subsurface runoff depth"),
            pa_field("sbrunv", pa.float64(), units="m^3", description="Subsurface runoff volume"),
            pa_field("drainq", pa.float64(), units="m/day", description="Drainage flux"),
            pa_field("drrunv", pa.float64(), units="m^3", description="Tile Drainage volume"),
            pa_field("peakro", pa.float64(), units="m^3/s", description="Peak runoff rate"),
            pa_field("tdet", pa.float64(), units="kg", description="Total detachment"),
            pa_field("tdep", pa.float64(), units="kg", description="Total deposition"),
            pa_field("sedcon_1", pa.float64(), units="kg/m^3", description="Sediment concentration 1"),
            pa_field("sedcon_2", pa.float64(), units="kg/m^3", description="Sediment concentration 2"),
            pa_field("sedcon_3", pa.float64(), units="kg/m^3", description="Sediment concentration 3"),
            pa_field("sedcon_4", pa.float64(), units="kg/m^3", description="Sediment concentration 4"),
            pa_field("sedcon_5", pa.float64(), units="kg/m^3", description="Sediment concentration 5"),
            pa_field("clot", pa.float64(), units="m^3/s", description="Friction flow 1"),
            pa_field("slot", pa.float64(), units="%", description="% of exiting sediment in the silt size class"),
            pa_field("saot", pa.float64(), units="%", description="% of exiting sediment in the small aggregate size class"),
            pa_field("laot", pa.float64(), units="%", description="% of exiting sediment in the large aggregate size class"),
            pa_field("sdot", pa.float64(), units="%", description="% of exiting sediment in the sand size class"),
            pa_field("gwbfv", pa.float64(), description="Groundwater baseflow"),
            pa_field("gwdsv", pa.float64(), description="Groundwater deep seepage"),
        ]
    )
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

def _event_tokens(lines: List[str], start_idx: int) -> tuple[List[str], int]:
    """Collect numeric values for a multi-line EVENT record."""
    primary = lines[start_idx]
    numeric_tokens = primary[8:].split()

    expected = 2 + EVENT_FLOAT_COUNT
    idx = start_idx + 1
    while len(numeric_tokens) < expected and idx < len(lines):
        candidate = lines[idx]
        label = candidate[:8].strip()
        if label in EVENT_LABELS and label:
            break
        numeric_tokens.extend(candidate.split())
        idx += 1
    return numeric_tokens, idx


def _subevent_tokens(line: str) -> List[str]:
    """Return numeric tokens for a SUBEVENT line."""
    return line[8:].split()


def _noevent_tokens(line: str) -> List[str]:
    """Return numeric tokens for a NO EVENT line."""
    return line[8:].split()


def _init_column_store() -> Dict[str, List]:
    """Create an empty columnar store keyed by schema field."""
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    """Append a dictionary row to the in-memory columnar store."""
    for name in SCHEMA.names:
        store[name].append(row[name])


PASS_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)


def _parse_pass_file(path: Path) -> pa.Table:
    """Parse a single PASS file into a PyArrow table."""
    match = PASS_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized PASS filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    with path.open("r") as stream:
        lines = stream.readlines()

    if len(lines) < 2:
        raise ValueError(f"PASS file missing simulation metadata header: {path}")

    header_tokens = lines[1].split()
    if not header_tokens:
        raise ValueError(f"Unable to determine simulation start year from PASS header in {path}")
    try:
        begin_year = int(header_tokens[-1])
    except ValueError as exc:
        raise ValueError(f"PASS header does not contain a valid start year in {path}") from exc

    sim_start_date = datetime(begin_year, 1, 1)

    # skip header lines (climate setup, particle definitions)
    data_lines = lines[5:]
    out = _init_column_store()

    idx = 0
    while idx < len(data_lines):
        raw_line = data_lines[idx]
        label = raw_line[:8].strip()
        if not label:
            idx += 1
            continue
        label_upper = label.upper()
        if label_upper not in EVENT_LABELS:
            idx += 1
            continue

        if label_upper == "EVENT":
            tokens, idx = _event_tokens(data_lines, idx)
        elif label_upper == "SUBEVENT":
            tokens = _subevent_tokens(raw_line)
            idx += 1
        else:
            tokens = _noevent_tokens(raw_line)
            idx += 1

        if len(tokens) < 2:
            continue

        year = int(tokens[0])
        julian = int(tokens[1])
        month, day_of_month = _julian_to_calendar(year, julian)
        wy = determine_wateryear(year, julian)
        sim_day_index = (datetime(year, month, day_of_month) - sim_start_date).days + 1
        if sim_day_index < 1:
            raise ValueError(
                f"Computed negative simulation day index ({sim_day_index}) for {path} at year={year}, julian={julian}"
            )

        row = {
            "wepp_id": wepp_id,
            "event": label_upper,
            "year": year,
            "sim_day_index": sim_day_index,
            "julian": julian,
            "month": month,
            "day_of_month": day_of_month,
            "water_year": int(wy),
            "dur": 0.0,
            "tcs": 0.0,
            "oalpha": 0.0,
            "runoff": 0.0,
            "runvol": 0.0,
            "sbrunf": 0.0,
            "sbrunv": 0.0,
            "drainq": 0.0,
            "drrunv": 0.0,
            "peakro": 0.0,
            "tdet": 0.0,
            "tdep": 0.0,
            "sedcon_1": 0.0,
            "sedcon_2": 0.0,
            "sedcon_3": 0.0,
            "sedcon_4": 0.0,
            "sedcon_5": 0.0,
            "clot": 0.0,
            "slot": 0.0,
            "saot": 0.0,
            "laot": 0.0,
            "sdot": 0.0,
            "gwbfv": 0.0,
            "gwdsv": 0.0,
        }

        if label_upper == "EVENT":
            values = tokens[2:]
            if len(values) != EVENT_FLOAT_COUNT:
                raise ValueError(f"Unexpected EVENT token count in {path}: {len(values)}")
            row.update(
                {
                    "dur": _parse_float(values[0]),
                    "tcs": _parse_float(values[1]),
                    "oalpha": _parse_float(values[2]),
                    "runoff": _parse_float(values[3]),
                    "runvol": _parse_float(values[4]),
                    "sbrunf": _parse_float(values[5]),
                    "sbrunv": _parse_float(values[6]),
                    "drainq": _parse_float(values[7]),
                    "drrunv": _parse_float(values[8]),
                    "peakro": _parse_float(values[9]),
                    "tdet": _parse_float(values[10]),
                    "tdep": _parse_float(values[11]),
                    "sedcon_1": _parse_float(values[12]),
                    "sedcon_2": _parse_float(values[13]),
                    "sedcon_3": _parse_float(values[14]),
                    "sedcon_4": _parse_float(values[15]),
                    "sedcon_5": _parse_float(values[16]),
                    "frcflw_1": _parse_float(values[17]),
                    "frcflw_2": _parse_float(values[18]),
                    "frcflw_3": _parse_float(values[19]),
                    "frcflw_4": _parse_float(values[20]),
                    "frcflw_5": _parse_float(values[21]),
                    "gwbfv": _parse_float(values[22]),
                    "gwdsv": _parse_float(values[23]),
                }
            )
        elif label_upper == "SUBEVENT":
            values = tokens[2:]
            if len(values) != SUBEVENT_FLOAT_COUNT:
                raise ValueError(f"Unexpected SUBEVENT token count in {path}: {len(values)}")
            row.update(
                {
                    "sbrunf": _parse_float(values[0]),
                    "sbrunv": _parse_float(values[1]),
                    "drainq": _parse_float(values[2]),
                    "drrunv": _parse_float(values[3]),
                    "gwbfv": _parse_float(values[4]),
                    "gwdsv": _parse_float(values[5]),
                }
            )
        else:  # NO EVENT
            values = tokens[2:]
            if len(values) != NOEVENT_FLOAT_COUNT:
                raise ValueError(f"Unexpected NO EVENT token count in {path}: {len(values)}")
            row.update(
                {
                    "gwbfv": _parse_float(values[0]),
                    "gwdsv": _parse_float(values[1]),
                }
            )

        _append_row(out, row)

    return pa.table(out, schema=SCHEMA)


def run_wepp_hillslope_pass_interchange(wepp_output_dir: Path | str) -> Path:
    """Convert all `H*.pass.dat` files into a consolidated parquet dataset."""
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    pass_files = sorted(base.glob("H*.pass.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.pass.parquet"

    write_parquet_with_pool(pass_files, _parse_pass_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
