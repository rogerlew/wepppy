from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

PASS_FILENAME = "pass_pw0.txt"
EVENTS_PARQUET = "pass_pw0.events.parquet"
METADATA_PARQUET = "pass_pw0.metadata.parquet"

_EVENT_LINE_RE = re.compile(r"(?P<label>[A-Z ]+?)\s+(?P<year>\d+)\s+(?P<day>\d+)")


def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 0.0
    if stripped[0] == ".":
        stripped = f"0{stripped}"
    return float(stripped)


def _collect_values(lines: List[str], start_idx: int, count: int) -> Tuple[List[float], int]:
    values: List[float] = []
    idx = start_idx
    while len(values) < count:
        if idx >= len(lines):
            raise ValueError("Unexpected end of pass file while collecting numeric values.")
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        values.extend(_parse_float(token) for token in line.split())
    return values[:count], idx


def _julian_to_calendar(year: int, julian: int) -> Tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


def _parse_metadata(header_lines: List[str]) -> Tuple[Dict[str, object], pa.Table, int, List[int], int]:
    version = None
    nhill = None
    max_years = None
    begin_year = None
    metadata_rows: Dict[str, List[object]] = {}
    hillslope_ids: List[int] = []
    particle_diams: List[List[float]] = []
    climate_files: List[str] = []
    areas: List[float] = []
    srp_list: List[float] = []
    slfp_list: List[float] = []
    bfp_list: List[float] = []
    scp_list: List[float] = []

    for line in header_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith("--> VERSION NUMBER"):
            version = _parse_float(stripped.split()[0])
        elif stripped.endswith("NUMBER OF UNIQUE HILLSLOPES IN WATERSHED"):
            nhill = int(stripped.split()[0])
        elif stripped.endswith("WATERSHED MAXIMUM SIMULATION TIME (YEARS)"):
            max_years = int(stripped.split()[0])
        elif stripped.endswith("BEGINNING YEAR OF WATERSHED CLIMATE FILE"):
            begin_year = int(stripped.split()[0])
        elif stripped.startswith("HILLSLOPE"):
            parts = stripped.split()
            # structure: HILLSLOPE <id> <climate> <dia...> <area> <srp> <slfp> <bfp> <scp>
            if len(parts) < 2 or not parts[1].isdigit():
                continue
            if len(parts) < 10:
                raise ValueError(f"Unexpected HILLSLOPE metadata line: {line}")
            wepp_id = int(parts[1])
            climate_file = parts[2]
            # last four numbers are P concentrations
            srp = _parse_float(parts[-4])
            slfp = _parse_float(parts[-3])
            bfp = _parse_float(parts[-2])
            scp = _parse_float(parts[-1])
            area = _parse_float(parts[-5])
            diam_tokens = parts[3:-5]
            dia_values = [_parse_float(tok) for tok in diam_tokens]

            hillslope_ids.append(wepp_id)
            climate_files.append(climate_file)
            particle_diams.append(dia_values)
            areas.append(area)
            srp_list.append(srp)
            slfp_list.append(slfp)
            bfp_list.append(bfp)
            scp_list.append(scp)

    if None in (version, nhill, max_years, begin_year):
        raise ValueError("Missing simulation metadata in pass file header.")
    if len(hillslope_ids) != nhill:
        raise ValueError("Mismatch between declared hillslope count and metadata lines.")

    npart = len(particle_diams[0]) if particle_diams else 0
    dia_columns = {f"dia_{idx + 1}": [row[idx] for row in particle_diams] for idx in range(npart)}

    metadata_columns: Dict[str, Iterable[object]] = {
        "wepp_id": hillslope_ids,
        "climate_file": climate_files,
        "area": areas,
        "srp": srp_list,
        "slfp": slfp_list,
        "bfp": bfp_list,
        "scp": scp_list,
    }
    metadata_columns.update(dia_columns)

    metadata_schema_fields = [
        pa.field("wepp_id", pa.int32()),
        pa.field("climate_file", pa.string()),
        pa.field("area", pa.float64()).with_metadata({b"units": b"m^2"}),
        pa.field("srp", pa.float64()).with_metadata({b"units": b"mg/L"}),
        pa.field("slfp", pa.float64()).with_metadata({b"units": b"mg/L"}),
        pa.field("bfp", pa.float64()).with_metadata({b"units": b"mg/L"}),
        pa.field("scp", pa.float64()).with_metadata({b"units": b"mg/kg"}),
    ] + [pa.field(name, pa.float64()).with_metadata({b"units": b"m"}) for name in dia_columns]

    metadata_schema = pa.schema(metadata_schema_fields).with_metadata(
        {
            b"version": str(version).encode(),
            b"nhill": str(nhill).encode(),
            b"max_years": str(max_years).encode(),
            b"begin_year": str(begin_year).encode(),
            b"npart": str(npart).encode(),
        }
    )
    metadata_table = pa.table(metadata_columns, schema=metadata_schema)

    global_meta = {
        "version": version,
        "nhill": nhill,
        "max_years": max_years,
        "begin_year": begin_year,
        "npart": npart,
    }

    return global_meta, metadata_table, npart, hillslope_ids, nhill


def _parse_events(data_lines: List[str], hillslope_ids: List[int], nhill: int, npart: int) -> pa.Table:
    column_store: Dict[str, List[object]] = {}

    def _init_column(name: str):
        column_store[name] = []

    base_columns = [
        "event",
        "year",
        "day",
        "julian",
        "month",
        "day_of_month",
        "water_year",
        "wepp_id",
        "dur",
        "tcs",
        "oalpha",
        "runoff",
        "runvol",
        "sbrunf",
        "sbrunv",
        "drainq",
        "drrunv",
        "peakro",
        "tdet",
        "tdep",
        "gwbfv",
        "gwdsv",
    ]

    sed_columns = [f"sedcon_{idx + 1}" for idx in range(npart)]
    frc_columns = [f"frcflw_{idx + 1}" for idx in range(npart)]
    all_columns = base_columns + sed_columns + frc_columns

    for name in all_columns:
        _init_column(name)

    idx = 0
    while idx < len(data_lines):
        raw_line = data_lines[idx].strip()
        if not raw_line:
            idx += 1
            continue

        match = _EVENT_LINE_RE.match(raw_line)
        if not match:
            raise ValueError(f"Unrecognized event header line: {raw_line}")

        label = match.group("label").strip()
        year = int(match.group("year"))
        julian = int(match.group("day"))
        idx += 1

        month, day_of_month = _julian_to_calendar(year, julian)
        water_year = int(determine_wateryear(year, julian))

        if label == "EVENT":
            dur, idx = _collect_values(data_lines, idx, nhill)
            tcs, idx = _collect_values(data_lines, idx, nhill)
            oalpha, idx = _collect_values(data_lines, idx, nhill)
            runoff, idx = _collect_values(data_lines, idx, nhill)
            runvol, idx = _collect_values(data_lines, idx, nhill)
            sbrunf, idx = _collect_values(data_lines, idx, nhill)
            sbrunv, idx = _collect_values(data_lines, idx, nhill)
            drainq, idx = _collect_values(data_lines, idx, nhill)
            drrunv, idx = _collect_values(data_lines, idx, nhill)
            peakro, idx = _collect_values(data_lines, idx, nhill)
            tdet, idx = _collect_values(data_lines, idx, nhill)
            tdep, idx = _collect_values(data_lines, idx, nhill)
            sedcon_vals, idx = _collect_values(data_lines, idx, npart * nhill)
            frcflw_vals, idx = _collect_values(data_lines, idx, npart * nhill)
            gwbfv, idx = _collect_values(data_lines, idx, nhill)
            gwdsv, idx = _collect_values(data_lines, idx, nhill)

            for pos, wepp_id in enumerate(hillslope_ids):
                row_sed = sedcon_vals[pos * npart : (pos + 1) * npart]
                row_frc = frcflw_vals[pos * npart : (pos + 1) * npart]
                for name, value in [
                    ("event", label),
                    ("year", year),
                    ("day", julian),
                    ("julian", julian),
                    ("month", month),
                    ("day_of_month", day_of_month),
                    ("water_year", water_year),
                    ("wepp_id", wepp_id),
                    ("dur", dur[pos]),
                    ("tcs", tcs[pos]),
                    ("oalpha", oalpha[pos]),
                    ("runoff", runoff[pos]),
                    ("runvol", runvol[pos]),
                    ("sbrunf", sbrunf[pos]),
                    ("sbrunv", sbrunv[pos]),
                    ("drainq", drainq[pos]),
                    ("drrunv", drrunv[pos]),
                    ("peakro", peakro[pos]),
                    ("tdet", tdet[pos]),
                    ("tdep", tdep[pos]),
                    ("gwbfv", gwbfv[pos]),
                    ("gwdsv", gwdsv[pos]),
                ]:
                    column_store[name].append(value)
                for col_name, value in zip(sed_columns, row_sed):
                    column_store[col_name].append(value)
                for col_name, value in zip(frc_columns, row_frc):
                    column_store[col_name].append(value)

        elif label == "SUBEVENT":
            sbrunf, idx = _collect_values(data_lines, idx, nhill)
            sbrunv, idx = _collect_values(data_lines, idx, nhill)
            drainq, idx = _collect_values(data_lines, idx, nhill)
            drrunv, idx = _collect_values(data_lines, idx, nhill)
            gwbfv, idx = _collect_values(data_lines, idx, nhill)
            gwdsv, idx = _collect_values(data_lines, idx, nhill)

            for pos, wepp_id in enumerate(hillslope_ids):
                for name, value in [
                    ("event", label),
                    ("year", year),
                    ("day", julian),
                    ("julian", julian),
                    ("month", month),
                    ("day_of_month", day_of_month),
                    ("water_year", water_year),
                    ("wepp_id", wepp_id),
                    ("dur", 0.0),
                    ("tcs", 0.0),
                    ("oalpha", 0.0),
                    ("runoff", 0.0),
                    ("runvol", 0.0),
                    ("sbrunf", sbrunf[pos]),
                    ("sbrunv", sbrunv[pos]),
                    ("drainq", drainq[pos]),
                    ("drrunv", drrunv[pos]),
                    ("peakro", 0.0),
                    ("tdet", 0.0),
                    ("tdep", 0.0),
                    ("gwbfv", gwbfv[pos]),
                    ("gwdsv", gwdsv[pos]),
                ]:
                    column_store[name].append(value)
                for col_name in sed_columns + frc_columns:
                    column_store[col_name].append(0.0)

        elif label == "NO EVENT":
            gwbfv, idx = _collect_values(data_lines, idx, nhill)
            gwdsv, idx = _collect_values(data_lines, idx, nhill)

            for pos, wepp_id in enumerate(hillslope_ids):
                for name, value in [
                    ("event", label),
                    ("year", year),
                    ("day", julian),
                    ("julian", julian),
                    ("month", month),
                    ("day_of_month", day_of_month),
                    ("water_year", water_year),
                    ("wepp_id", wepp_id),
                    ("dur", 0.0),
                    ("tcs", 0.0),
                    ("oalpha", 0.0),
                    ("runoff", 0.0),
                    ("runvol", 0.0),
                    ("sbrunf", 0.0),
                    ("sbrunv", 0.0),
                    ("drainq", 0.0),
                    ("drrunv", 0.0),
                    ("peakro", 0.0),
                    ("tdet", 0.0),
                    ("tdep", 0.0),
                    ("gwbfv", gwbfv[pos]),
                    ("gwdsv", gwdsv[pos]),
                ]:
                    column_store[name].append(value)
                for col_name in sed_columns + frc_columns:
                    column_store[col_name].append(0.0)

        else:
            raise ValueError(f"Unsupported pass file event label: {label}")

    schema_fields = [
        pa.field("event", pa.string()),
        pa.field("year", pa.int16()),
        pa.field("day", pa.int16()),
        pa.field("julian", pa.int16()),
        pa.field("month", pa.int8()),
        pa.field("day_of_month", pa.int8()),
        pa.field("water_year", pa.int16()),
        pa.field("wepp_id", pa.int32()),
        pa.field("dur", pa.float64()),
        pa.field("tcs", pa.float64()),
        pa.field("oalpha", pa.float64()),
        pa.field("runoff", pa.float64()),
        pa.field("runvol", pa.float64()),
        pa.field("sbrunf", pa.float64()),
        pa.field("sbrunv", pa.float64()),
        pa.field("drainq", pa.float64()),
        pa.field("drrunv", pa.float64()),
        pa.field("peakro", pa.float64()),
        pa.field("tdet", pa.float64()),
        pa.field("tdep", pa.float64()),
        pa.field("gwbfv", pa.float64()),
        pa.field("gwdsv", pa.float64()),
    ] + [pa.field(name, pa.float64()) for name in sed_columns + frc_columns]

    schema = pa.schema(schema_fields).with_metadata(
        {
            b"npart": str(npart).encode(),
            b"nhill": str(nhill).encode(),
        }
    )

    return pa.table(column_store, schema=schema)


def _parse_pass_file(path: Path) -> Tuple[pa.Table, pa.Table]:
    with path.open("r") as stream:
        lines = stream.readlines()

    stripped_lines = [line.rstrip("\n") for line in lines]

    try:
        begin_idx = next(
            idx for idx, line in enumerate(stripped_lines) if line.strip() == "BEGIN HILLSLOPE HYDROLOGY AND SEDIMENT INFORMATION"
        )
    except StopIteration:
        raise ValueError("Unable to locate beginning of hydrology section in pass file.")

    header_lines = stripped_lines[:begin_idx]
    data_lines = stripped_lines[begin_idx + 1 :]

    global_meta, metadata_table, npart, hillslope_ids, nhill = _parse_metadata(header_lines)
    events_table = _parse_events(data_lines, hillslope_ids, nhill, npart)

    # Attach simulation metadata to events table as schema metadata
    events_table = events_table.replace_schema_metadata(
        {
            b"version": str(global_meta["version"]).encode(),
            b"nhill": str(global_meta["nhill"]).encode(),
            b"max_years": str(global_meta["max_years"]).encode(),
            b"begin_year": str(global_meta["begin_year"]).encode(),
            b"npart": str(global_meta["npart"]).encode(),
        }
    )

    return events_table, metadata_table


def run_wepp_watershed_pass_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    pass_path = base / PASS_FILENAME
    if not pass_path.exists():
        raise FileNotFoundError(pass_path)

    events_table, metadata_table = _parse_pass_file(pass_path)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    events_path = interchange_dir / EVENTS_PARQUET
    metadata_path = interchange_dir / METADATA_PARQUET

    pq.write_table(events_table, events_path, compression="snappy", use_dictionary=True)
    pq.write_table(metadata_table, metadata_path, compression="snappy", use_dictionary=True)

    return {"events": events_path, "metadata": metadata_path}
