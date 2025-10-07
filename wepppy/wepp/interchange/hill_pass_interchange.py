from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import re

import pyarrow as pa

from wepppy.all_your_base.hydro import determine_wateryear
from .concurrency import write_parquet_with_pool

EVENT_LABELS = {"EVENT", "SUBEVENT", "NO EVENT"}
SEDCLASS_COUNT = 5
EVENT_FLOAT_COUNT = 12 + (2 * SEDCLASS_COUNT) + 2  # dur..tdep + sedcon + frcflw + gwbfv/gwdsv
SUBEVENT_FLOAT_COUNT = 6  # sbrunf, sbrunv, drainq, drrunv, gwbfv, gwdsv
NOEVENT_FLOAT_COUNT = 2  # gwbfv, gwdsv


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


def _julian_to_calendar(year: int, julian: int) -> tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


SCHEMA = pa.schema(
    [
        ("wepp_id", pa.int32()),
        ("event", pa.string()),
        ("year", pa.int16()),
        ("day", pa.int16()),
        ("julian", pa.int16()),
        ("month", pa.int8()),
        ("day_of_month", pa.int8()),
        ("water_year", pa.int16()),
        ("dur", pa.float64()),
        ("tcs", pa.float64()),
        ("oalpha", pa.float64()),
        ("runoff", pa.float64()),
        ("runvol", pa.float64()),
        ("sbrunf", pa.float64()),
        ("sbrunv", pa.float64()),
        ("drainq", pa.float64()),
        ("drrunv", pa.float64()),
        ("peakro", pa.float64()),
        ("tdet", pa.float64()),
        ("tdep", pa.float64()),
        ("sedcon_1", pa.float64()),
        ("sedcon_2", pa.float64()),
        ("sedcon_3", pa.float64()),
        ("sedcon_4", pa.float64()),
        ("sedcon_5", pa.float64()),
        ("frcflw_1", pa.float64()),
        ("frcflw_2", pa.float64()),
        ("frcflw_3", pa.float64()),
        ("frcflw_4", pa.float64()),
        ("frcflw_5", pa.float64()),
        ("gwbfv", pa.float64()),
        ("gwdsv", pa.float64()),
    ]
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)

def _event_tokens(lines: List[str], start_idx: int) -> tuple[List[str], int]:
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
    return line[8:].split()


def _noevent_tokens(line: str) -> List[str]:
    return line[8:].split()


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _append_row(store: Dict[str, List], row: Dict[str, object]) -> None:
    for name in SCHEMA.names:
        store[name].append(row[name])


PASS_FILE_RE = re.compile(r"H(?P<wepp_id>\d+)", re.IGNORECASE)


def _parse_pass_file(path: Path) -> pa.Table:
    match = PASS_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized PASS filename pattern: {path}")
    wepp_id = int(match.group("wepp_id"))

    with path.open("r") as stream:
        lines = stream.readlines()

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

        row = {
            "wepp_id": wepp_id,
            "event": label_upper,
            "year": year,
            "day": julian,
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
            "frcflw_1": 0.0,
            "frcflw_2": 0.0,
            "frcflw_3": 0.0,
            "frcflw_4": 0.0,
            "frcflw_5": 0.0,
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
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    pass_files = sorted(base.glob("H*.pass.dat"))
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.pass.parquet"

    write_parquet_with_pool(pass_files, _parse_pass_file, SCHEMA, target_path, empty_table=EMPTY_TABLE)
    return target_path
