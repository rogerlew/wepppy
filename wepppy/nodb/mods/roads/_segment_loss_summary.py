"""Source-profile diagnostics; see roads-segment-loss-summary-contract.md."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import uuid
from typing import Callable

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange
from wepppy.wepp.interchange.roads_accounting import validate_destinations

__all__ = ["build_segment_loss_summary"]

POLICY = "roads_segment_pass_v1"
OUTPUT = Path("wepp/roads/output/interchange")
MANIFEST = Path("wepp/roads/segments/roads.segment.pass.manifest.json")
METRICS = ("runvol", "sbrunv", "gwbfv", "tdet", "tdep", *(f"sedcon_{i}" for i in range(1, 6)))
DATES = ("year", "sim_day_index", "julian", "month", "day_of_month", "water_year")
STRINGS = ("segment_id", "design", "surface", "traffic", "soil_texture")
INTEGERS = ("segment_run_id", "target_hillslope_wepp_id", "topaz_id_hill_lowpoint", "topaz_id_chn_lowpoint")
DIMENSIONS = ("rfg_pct", "road_width_m", "segment_length_m", "slope_pct_clamped")
VALUES = ("runoff_volume_m3", "subrunoff_volume_m3", "baseflow_volume_m3", "soil_loss_kg",
          "sediment_deposition_kg", "sediment_yield_kg", "hillslope_area_ha", "runoff_depth_mm",
          "soil_loss_density_kg_m2", "sediment_yield_density_kg_m2", "sediment_delivery_ratio",
          "road_prism_erosion_kg", "sediment_leaving_buffer_kg")
# Preserve the existing download column order and types; append provenance only.
SCHEMA = pa.schema([
    pa.field("segment_id", pa.string()),
    *(pa.field(name, pa.int64()) for name in INTEGERS),
    *(pa.field(name, pa.string()) for name in STRINGS[1:]),
    *(pa.field(name, pa.float64()) for name in DIMENSIONS),
    pa.field("loss_match_key", pa.string()),
    *(pa.field(name, pa.float64()) for name in VALUES),
    pa.field("loss_row_missing", pa.bool_()),
    pa.field("summary_policy", pa.string()), pa.field("simulation_years", pa.int64()),
    pa.field("modeled_area_m2", pa.float64()), pa.field("profile_scope", pa.string()),
    pa.field("source_pass_relpath", pa.string()), pa.field("source_wat_relpath", pa.string()),
])


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _integer(value, name: str, *, required: bool = False) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"Invalid Roads {name}: {value!r}")
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid Roads {name}: {value!r}") from exc
    if result <= 0:
        raise ValueError(f"Invalid Roads {name}: {value!r}")
    return result


def _records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError("Roads segment manifest must be a JSON list")
    records, ids, targets = [], set(), set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Invalid Roads segment manifest record")
        status = str(row.get("status", "completed")).strip().lower()
        if status in ("skipped", "failed"):
            continue
        if status != "completed":
            raise ValueError(f"Unknown Roads segment status: {status}")
        record = {name: _integer(row.get(name), name, required=name == "segment_run_id") for name in INTEGERS}
        source_id = record["segment_run_id"]
        if source_id in ids:
            raise ValueError(f"Duplicate Roads segment ID: {source_id}")
        ids.add(source_id)
        if record["target_hillslope_wepp_id"] is not None:
            targets.add(record["target_hillslope_wepp_id"])
        record.update({name: str(row.get(name) or "") for name in STRINGS})
        record["segment_id"] = record["segment_id"] or str(source_id)
        for name in DIMENSIONS:
            value = row.get(name)
            record[name] = None if value is None else float(value)
            if record[name] is not None and not math.isfinite(record[name]):
                raise ValueError(f"Invalid Roads {name}")
        records.append(record)
    if ids & targets:
        raise ValueError("Roads segment ID collides with a target hillslope ID")
    return records


def _validate_pass(con, ids: list[int], expected_years: int, start_year: int | None) -> None:
    missing = set(ids) - {row[0] for row in con.execute("SELECT DISTINCT wepp_id FROM selected_pass").fetchall()}
    if missing:
        raise ValueError(f"Missing Roads PASS sources: {sorted(missing)}")
    invalid = " OR ".join(f'"{name}" IS NULL OR NOT isfinite("{name}")' for name in METRICS)
    if con.execute(f"SELECT count(*) FROM selected_pass WHERE {invalid}").fetchone()[0]:
        raise ValueError("NULL or nonfinite Roads PASS metric")
    calendars = con.execute('''SELECT wepp_id, year, count(*), count(DISTINCT julian),
        min(julian), max(julian), min(sim_day_index), max(sim_day_index),
        count(DISTINCT sim_day_index) FROM selected_pass GROUP BY wepp_id, year ORDER BY wepp_id, year''').fetchall()
    common = None
    for source_id in ids:
        years = [row[1:] for row in calendars if row[0] == source_id]
        first = years[0][0] if start_year is None else start_year
        if [row[0] for row in years] != list(range(first, first + expected_years)):
            raise ValueError(f"Incomplete Roads simulation years: {source_id}")
        next_day = 1
        for _, count, unique, low, high, sim_low, sim_high, sim_unique in years:
            if count not in (365, 366) or (unique, low, high) != (count, 1, count) or (
                sim_low, sim_high, sim_unique) != (next_day, next_day + count - 1, count):
                raise ValueError(f"Incomplete or duplicate Roads daily calendar: {source_id}")
            next_day += count
        date_rows = con.execute(f'SELECT {", ".join(DATES)} FROM selected_pass WHERE wepp_id=? ORDER BY sim_day_index', [source_id]).fetchall()
        if common is None:
            common = date_rows
        elif common != date_rows:
            raise ValueError("Roads profiles have unequal PASS calendars")
    # EXCEPT compares every selected source's full date identity, independent of OFE count.
    cols = ", ".join(("wepp_id", *DATES))
    if con.execute(f'''SELECT count(*) FROM (
        (SELECT {cols} FROM selected_pass EXCEPT SELECT DISTINCT {cols} FROM selected_wat)
        UNION ALL
        (SELECT DISTINCT {cols} FROM selected_wat EXCEPT SELECT {cols} FROM selected_pass)
        )''').fetchone()[0]:
        raise ValueError("Roads PASS/WAT calendars differ")


def _summarize(root: Path, records: list[dict], expected_years: int, start_year: int | None) -> list[dict]:
    folder = root / OUTPUT
    ids = [r["segment_run_id"] for r in records]
    native = require_wepppyo3_interchange("Roads segment summary", "roads_wat_geometry")
    geometry = dict(native.roads_wat_geometry(str(folder / "H.wat.parquet"), ids))
    schema = pq.read_schema(folder / "H.pass.parquet")
    for name in ("wepp_id", *DATES):
        if not pa.types.is_integer(schema.field(name).type):
            raise ValueError(f"Invalid Roads PASS integer column: {name}")
    with duckdb.connect() as con:
        con.register("wanted", pa.table({"wepp_id": ids}))
        for name in ("pass", "wat"):
            con.read_parquet(str(folder / f"H.{name}.parquet")).create_view(f"source_{name}")
            con.execute(f"CREATE TEMP VIEW selected_{name} AS SELECT p.* FROM source_{name} p JOIN wanted w USING (wepp_id)")
        _validate_pass(con, ids, expected_years, start_year)
        aggregates = con.execute('''SELECT wepp_id, sum(runvol), sum(sbrunv), sum(gwbfv),
            sum(tdet), sum(tdep), sum(runvol * (sedcon_1 + sedcon_2 + sedcon_3 + sedcon_4 + sedcon_5))
            FROM selected_pass GROUP BY wepp_id''').fetchall()
    totals = {row[0]: [v / expected_years for v in row[1:]] for row in aggregates}
    for record in records:
        source_id = record["segment_run_id"]
        ofes = geometry[source_id]
        area = math.fsum(value for _, value in ofes)
        if not math.isfinite(area) or area <= 0:
            raise ValueError(f"Invalid Roads profile area: {source_id}")
        scope = ("replacement_remainder" if record["design"] == "outslope_unrutted_remainder" else
                 "mixed_profile" if len(ofes) > 1 else
                 "road" if record["design"] in ("inslope_bd", "inslope_rd") else "unclassified_profile")
        runoff, subsurface, baseflow, detachment, deposition, sediment = totals[source_id]
        record.update(zip(VALUES[:6], totals[source_id]))
        record.update(hillslope_area_ha=area / 10000., runoff_depth_mm=runoff / area * 1000.,
            soil_loss_density_kg_m2=detachment / area, sediment_yield_density_kg_m2=sediment / area,
            sediment_delivery_ratio=sediment / detachment if detachment > 0 else None,
            road_prism_erosion_kg=detachment if scope == "road" else None,
            sediment_leaving_buffer_kg=None, loss_match_key="segment_run_id", loss_row_missing=False,
            summary_policy=POLICY, simulation_years=expected_years, modeled_area_m2=area, profile_scope=scope,
            source_pass_relpath=str(OUTPUT / "H.pass.parquet"), source_wat_relpath=str(OUTPUT / "H.wat.parquet"))
        if any(record[name] is not None and not math.isfinite(record[name]) for name in VALUES):
            raise ValueError(f"Nonfinite Roads summary result: {source_id}")
    return sorted(records, key=lambda row: (-row["sediment_yield_kg"], row["segment_run_id"]))


def build_segment_loss_summary(root: Path, interchange_dir: Path, *, expected_years: int | None = None,
                               start_year: int | None = None,
                               execution_calendar: Callable[[], tuple[int, int | None]] | None = None) -> str:
    root = Path(root)
    validate_destinations(root)
    folder = root / OUTPUT
    if Path(interchange_dir).resolve() != folder.resolve():
        raise ValueError("Roads summary destination must be the Roads interchange directory")
    manifest = root / MANIFEST
    if manifest.resolve() != root.resolve() / MANIFEST:
        raise ValueError("Roads segment manifest alias")
    sources = {manifest: _hash(manifest)}
    records = _records(manifest)
    if records:
        if execution_calendar is not None:
            expected_years, start_year = execution_calendar()
        expected_years = _integer(expected_years, "simulation years", required=True)
        if start_year is not None:
            start_year = _integer(start_year, "simulation start year", required=True)
        sources.update({folder / name: _hash(folder / name) for name in ("H.pass.parquet", "H.wat.parquet")})
        records = _summarize(root, records, expected_years, start_year)

    def verify_sources():
        validate_destinations(root)
        for path, digest in sources.items():
            if _hash(path) != digest:
                raise ValueError(f"Roads summary source changed: {path.relative_to(root)}")

    verify_sources()
    metadata = {b"roads_segment_summary_policy": POLICY.encode(),
                b"source_sha256": json.dumps({str(p.relative_to(root)): h for p, h in sources.items()}, sort_keys=True).encode(),
                b"annual_basis": b"Mean annual original profile PASS exports over persisted climate input_years; WAT full-profile area",
                b"unavailable_aliases": b"Buffer delivery unavailable; prism detachment only for proven single-OFE inslope road"}
    table = pa.Table.from_pylist(records, schema=SCHEMA).replace_schema_metadata(metadata)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "roads_segment_loss_summary.parquet"
    candidate = folder / f"roads_segment_loss_summary.pending-{uuid.uuid4().hex}.parquet"
    descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if target.exists():
                os.fchmod(stream.fileno(), stat.S_IMODE(target.stat().st_mode))
            pq.write_table(table, stream, compression="zstd")
            stream.flush()
            os.fsync(stream.fileno())
        verify_sources()
        os.replace(candidate, target)
    except (OSError, ValueError, pa.ArrowException) as exc:
        # Publication boundary: preserve the old output and visible failed candidate.
        raise RuntimeError(f"Roads summary publication failed; inspect candidate {candidate}: {exc}") from exc
    return str(target.relative_to(root))
