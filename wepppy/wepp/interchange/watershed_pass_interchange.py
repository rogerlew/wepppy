from __future__ import annotations

import gzip
import logging
import re
import errno
import shutil
from functools import partial
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple

try:
    from .schema_utils import pa_field
except ModuleNotFoundError:
    import importlib.machinery
    import importlib.util
    import sys

    schema_utils_path = Path(__file__).with_name("schema_utils.py")
    loader = importlib.machinery.SourceFileLoader("schema_utils_local", str(schema_utils_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    pa_field = module.pa_field
from .versioning import schema_with_version

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear
from ._utils import _build_cli_calendar_lookup, _compute_sim_day_index, _julian_to_calendar


PASS_FILENAME = "pass_pw0.txt"
EVENTS_PARQUET = "pass_pw0.events.parquet"
METADATA_PARQUET = "pass_pw0.metadata.parquet"
EVENT_CHUNK_SIZE = 250_000

LOGGER = logging.getLogger(__name__)

_EVENT_LINE_RE = re.compile(r"(?P<label>[A-Z ]+?)\s+(?P<year>\d+)\s+(?P<day>\d+)")
_FLOAT_TOKEN_RE = re.compile(r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?")


def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 0.0
    if stripped[0] == ".":
        stripped = f"0{stripped}"
    return float(stripped)


def _tokenize_numeric_line(line: str) -> List[float]:
    tokens = _FLOAT_TOKEN_RE.findall(line)
    if not tokens:
        return []
    return [_parse_float(tok) for tok in tokens]


def _parse_metadata(
    header_lines: List[str],
) -> Tuple[Dict[str, object], pa.Table, int, List[int], int, List[str]]:
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

    metadata_schema = schema_with_version(
        pa.schema(metadata_schema_fields).with_metadata(
            {
                b"version": str(version).encode(),
                b"nhill": str(nhill).encode(),
                b"max_years": str(max_years).encode(),
                b"begin_year": str(begin_year).encode(),
                b"npart": str(npart).encode(),
            }
        )
    )
    metadata_table = pa.table(metadata_columns, schema=metadata_schema)

    global_meta = {
        "version": version,
        "nhill": nhill,
        "max_years": max_years,
        "begin_year": begin_year,
        "npart": npart,
    }

    return global_meta, metadata_table, npart, hillslope_ids, nhill, climate_files


class _ValueCollector:
    def __init__(self, line_iter: Iterator[str]) -> None:
        self._iter = line_iter
        self._buffer: List[float] = []

    def read(self, count: int) -> List[float]:
        values: List[float] = []
        while len(values) < count:
            if self._buffer:
                take = min(count - len(values), len(self._buffer))
                values.extend(self._buffer[:take])
                self._buffer = self._buffer[take:]
                continue

            try:
                line = next(self._iter)
            except StopIteration as exc:
                raise ValueError("Unexpected end of pass file while collecting numeric values.") from exc

            stripped = line.strip()
            if not stripped:
                continue
            # pass files occasionally contain concatenated numbers without whitespace
            # (e.g., "0.97059-100"); use regex tokenization to split them safely.
            self._buffer.extend(_tokenize_numeric_line(stripped))

        return values


def _build_event_columns(npart: int) -> Tuple[List[str], List[str], List[str]]:
    base_columns = [
        "event",
        "year",
        "sim_day_index",
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
    return base_columns, sed_columns, frc_columns


def _build_event_schema(npart: int, meta: Dict[str, object], nhill: int) -> pa.Schema:
    base_columns, sed_columns, frc_columns = _build_event_columns(npart)
    schema_fields = [
        pa.field("event", pa.string()),
        pa.field("year", pa.int16()),
        pa.field("sim_day_index", pa.int32()),
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

    schema = schema_with_version(
        pa.schema(schema_fields).with_metadata(
            {
                b"version": str(meta["version"]).encode(),
                b"nhill": str(meta["nhill"]).encode(),
                b"max_years": str(meta["max_years"]).encode(),
                b"begin_year": str(meta["begin_year"]).encode(),
                b"npart": str(meta["npart"]).encode(),
            }
        )
    )
    return schema


def _init_event_store(column_names: Iterable[str]) -> Dict[str, List[object]]:
    return {name: [] for name in column_names}


def _flush_event_store(store: Dict[str, List[object]], writer: pq.ParquetWriter) -> None:
    if not store["event"]:
        return
    table = pa.table(store, schema=writer.schema)
    writer.write_table(table)
    for key in store:
        store[key] = []


def _write_events_parquet(
    line_iter: Iterator[str],
    hillslope_ids: List[int],
    nhill: int,
    npart: int,
    global_meta: Dict[str, object],
    target: Path,
    *,
    calendar_lookup: dict[int, list[tuple[int, int]]] | None = None,
    chunk_size: int = EVENT_CHUNK_SIZE,
) -> None:
    base_columns, sed_columns, frc_columns = _build_event_columns(npart)
    column_order = base_columns + sed_columns + frc_columns
    schema = _build_event_schema(npart, global_meta, nhill)

    tmp_target = target.with_suffix(f"{target.suffix}.tmp")
    if tmp_target.exists():
        tmp_target.unlink()

    start_year = int(global_meta["begin_year"])

    writer = pq.ParquetWriter(
        tmp_target,
        schema,
        compression="snappy",
        use_dictionary=True,
    )

    store = _init_event_store(column_order)
    value_reader = _ValueCollector(line_iter)
    row_counter = 0

    try:
        for raw_line in line_iter:
            stripped = raw_line.strip()
            if not stripped:
                continue

            match = _EVENT_LINE_RE.match(stripped)
            if not match:
                numeric_tokens = _tokenize_numeric_line(stripped)
                if numeric_tokens:
                    # Some WEPP builds emit stray numeric lines between events; stash them
                    # so the next read() can consume them instead of failing the parse.
                    value_reader._buffer.extend(numeric_tokens)
                    continue
                raise ValueError(f"Unrecognized event header line: {raw_line}")

            label = match.group("label").strip()
            year = int(match.group("year"))
            julian = int(match.group("day"))
            month, day_of_month = _julian_to_calendar(year, julian, calendar_lookup=calendar_lookup)
            water_year = int(determine_wateryear(year, julian))
            sim_day_index = _compute_sim_day_index(
                year,
                julian,
                start_year=start_year,
                calendar_lookup=calendar_lookup,
            )
            if sim_day_index < 1:
                raise ValueError(
                    f"Computed simulation day index {sim_day_index} before simulation start for {year=}, {julian=}."
                )

            if label == "EVENT":
                dur = value_reader.read(nhill)
                tcs = value_reader.read(nhill)
                oalpha = value_reader.read(nhill)
                runoff = value_reader.read(nhill)
                runvol = value_reader.read(nhill)
                sbrunf = value_reader.read(nhill)
                sbrunv = value_reader.read(nhill)
                drainq = value_reader.read(nhill)
                drrunv = value_reader.read(nhill)
                peakro = value_reader.read(nhill)
                tdet = value_reader.read(nhill)
                tdep = value_reader.read(nhill)
                sedcon_vals = value_reader.read(npart * nhill) if npart else []
                frcflw_vals = value_reader.read(npart * nhill) if npart else []
                gwbfv = value_reader.read(nhill)
                gwdsv = value_reader.read(nhill)

                for pos, wepp_id in enumerate(hillslope_ids):
                    store["event"].append(label)
                    store["year"].append(year)
                    store["sim_day_index"].append(sim_day_index)
                    store["julian"].append(julian)
                    store["month"].append(month)
                    store["day_of_month"].append(day_of_month)
                    store["water_year"].append(water_year)
                    store["wepp_id"].append(wepp_id)
                    store["dur"].append(dur[pos])
                    store["tcs"].append(tcs[pos])
                    store["oalpha"].append(oalpha[pos])
                    store["runoff"].append(runoff[pos])
                    store["runvol"].append(runvol[pos])
                    store["sbrunf"].append(sbrunf[pos])
                    store["sbrunv"].append(sbrunv[pos])
                    store["drainq"].append(drainq[pos])
                    store["drrunv"].append(drrunv[pos])
                    store["peakro"].append(peakro[pos])
                    store["tdet"].append(tdet[pos])
                    store["tdep"].append(tdep[pos])
                    store["gwbfv"].append(gwbfv[pos])
                    store["gwdsv"].append(gwdsv[pos])

                    if npart:
                        row_sed = sedcon_vals[pos * npart : (pos + 1) * npart]
                        row_frc = frcflw_vals[pos * npart : (pos + 1) * npart]
                        for col_name, value in zip(sed_columns, row_sed):
                            store[col_name].append(value)
                        for col_name, value in zip(frc_columns, row_frc):
                            store[col_name].append(value)
                    else:
                        for col_name in sed_columns + frc_columns:
                            store[col_name].append(0.0)

                    row_counter += 1
                    if row_counter % chunk_size == 0:
                        _flush_event_store(store, writer)

            elif label == "SUBEVENT":
                sbrunf = value_reader.read(nhill)
                sbrunv = value_reader.read(nhill)
                drainq = value_reader.read(nhill)
                drrunv = value_reader.read(nhill)
                gwbfv = value_reader.read(nhill)
                gwdsv = value_reader.read(nhill)

                for pos, wepp_id in enumerate(hillslope_ids):
                    store["event"].append(label)
                    store["year"].append(year)
                    store["sim_day_index"].append(sim_day_index)
                    store["julian"].append(julian)
                    store["month"].append(month)
                    store["day_of_month"].append(day_of_month)
                    store["water_year"].append(water_year)
                    store["wepp_id"].append(wepp_id)
                    store["dur"].append(0.0)
                    store["tcs"].append(0.0)
                    store["oalpha"].append(0.0)
                    store["runoff"].append(0.0)
                    store["runvol"].append(0.0)
                    store["sbrunf"].append(sbrunf[pos])
                    store["sbrunv"].append(sbrunv[pos])
                    store["drainq"].append(drainq[pos])
                    store["drrunv"].append(drrunv[pos])
                    store["peakro"].append(0.0)
                    store["tdet"].append(0.0)
                    store["tdep"].append(0.0)
                    store["gwbfv"].append(gwbfv[pos])
                    store["gwdsv"].append(gwdsv[pos])

                    for col_name in sed_columns + frc_columns:
                        store[col_name].append(0.0)

                    row_counter += 1
                    if row_counter % chunk_size == 0:
                        _flush_event_store(store, writer)

            elif label == "NO EVENT":
                gwbfv = value_reader.read(nhill)
                gwdsv = value_reader.read(nhill)

                for pos, wepp_id in enumerate(hillslope_ids):
                    store["event"].append(label)
                    store["year"].append(year)
                    store["sim_day_index"].append(sim_day_index)
                    store["julian"].append(julian)
                    store["month"].append(month)
                    store["day_of_month"].append(day_of_month)
                    store["water_year"].append(water_year)
                    store["wepp_id"].append(wepp_id)
                    store["dur"].append(0.0)
                    store["tcs"].append(0.0)
                    store["oalpha"].append(0.0)
                    store["runoff"].append(0.0)
                    store["runvol"].append(0.0)
                    store["sbrunf"].append(0.0)
                    store["sbrunv"].append(0.0)
                    store["drainq"].append(0.0)
                    store["drrunv"].append(0.0)
                    store["peakro"].append(0.0)
                    store["tdet"].append(0.0)
                    store["tdep"].append(0.0)
                    store["gwbfv"].append(gwbfv[pos])
                    store["gwdsv"].append(gwdsv[pos])

                    for col_name in sed_columns + frc_columns:
                        store[col_name].append(0.0)

                    row_counter += 1
                    if row_counter % chunk_size == 0:
                        _flush_event_store(store, writer)

            else:
                raise ValueError(f"Unsupported pass file event label: {label}")

        if store["event"]:
            _flush_event_store(store, writer)
        elif row_counter == 0:
            empty_store = _init_event_store(column_order)
            writer.write_table(pa.table(empty_store, schema=schema))
    except Exception:
        writer.close()
        if tmp_target.exists():
            tmp_target.unlink()
        raise
    else:
        writer.close()
        try:
            tmp_target.replace(target)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                shutil.move(str(tmp_target), str(target))
            else:
                raise


def _parse_pass_file(stream) -> Tuple[Dict[str, object], pa.Table, int, List[int], int, List[str], Iterator[str]]:
    stripped_lines = (line.rstrip("\n") for line in stream)
    header_lines: List[str] = []
    for line in stripped_lines:
        if line.strip() == "BEGIN HILLSLOPE HYDROLOGY AND SEDIMENT INFORMATION":
            break
        header_lines.append(line)
    else:
        raise ValueError("Unable to locate beginning of hydrology section in pass file.")

    global_meta, metadata_table, npart, hillslope_ids, nhill, climate_files = _parse_metadata(header_lines)
    return global_meta, metadata_table, npart, hillslope_ids, nhill, climate_files, stripped_lines


def run_wepp_watershed_pass_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    pass_path = base / PASS_FILENAME
    source_stream = None
    is_gzip = False
    if not pass_path.exists():
        gz_path = pass_path.with_suffix(pass_path.suffix + ".gz")
        if gz_path.exists():
            pass_path = gz_path
            is_gzip = True
        else:
            raise FileNotFoundError(base / PASS_FILENAME)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    events_path = interchange_dir / EVENTS_PARQUET
    metadata_path = interchange_dir / METADATA_PARQUET

    if is_gzip:
        stream = gzip.open(pass_path, "rt")
    else:
        stream = pass_path.open("r")

    with stream:
        global_meta, metadata_table, npart, hillslope_ids, nhill, climate_files, data_iter = _parse_pass_file(stream)
        calendar_lookup = _build_cli_calendar_lookup(base, climate_files=climate_files, log=LOGGER)
        _write_events_parquet(
            data_iter,
            hillslope_ids,
            nhill,
            npart,
            global_meta,
            events_path,
            calendar_lookup=calendar_lookup,
        )

    pq.write_table(metadata_table, metadata_path, compression="snappy", use_dictionary=True)

    return {"events": events_path, "metadata": metadata_path}
