from __future__ import annotations

import math
from datetime import datetime, timedelta
import shutil
from pathlib import Path
from typing import Dict, List

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine.activate import activate_query_engine
from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query
from wepppy.query_engine.payload import QueryRequest

RUN_RIDDLED = Path("/wc1/runs/ri/riddled-headmaster")
RUN_ORCHESTRAL = Path("/wc1/runs/or/orchestral-ringing")


def _require_run(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Run directory {path} not available in test environment")


def _prepare_run_copy(source: Path, tmp_root: Path, patterns: list[str]) -> Path:
    dest = tmp_root / source.name
    for pattern in patterns:
        matches = list(source.glob(pattern))
        if not matches:
            continue
        if pattern.endswith("H*.wat.dat"):
            matches = sorted(matches)[:25]
        for src_path in matches:
            relative = src_path.relative_to(source)
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, target)
    return dest


def _load_run_context(run_dir: Path) -> RunContext:
    activate_query_engine(str(run_dir), run_interchange=False)
    catalog = DatasetCatalog.load(run_dir / "_query_engine" / "catalog.json")
    return RunContext(runid=str(run_dir), base_dir=run_dir, scenario=None, catalog=catalog)


def test_landuse_dict_payload(tmp_path: Path) -> None:
    _require_run(RUN_ORCHESTRAL)
    working_run = _prepare_run_copy(RUN_ORCHESTRAL, tmp_path, ["landuse/landuse.parquet"])
    ctx = _load_run_context(working_run)

    payload = QueryRequest(datasets=["landuse/landuse.parquet"], include_schema=False)
    result = run_query(ctx, payload)

    assert result.row_count > 0
    mapping: Dict[int, Dict[str, object]] = {}
    for row in result.records:
        topaz_id = row.get("TopazID") or row.get("topaz_id")
        assert topaz_id is not None
        mapping[int(topaz_id)] = row

    assert mapping, "Expected non-empty landuse mapping"
    sample_key = next(iter(mapping))
    sample_row = mapping[sample_key]
    assert "key" in sample_row or "desc" in sample_row


def _parse_wat_files(run_dir: Path) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    wat_dir = run_dir / "wepp/output"
    for wat_file in wat_dir.glob("H*.wat.dat"):
        wepp_id = int(wat_file.stem[1:].split(".")[0])
        lines = wat_file.read_text().splitlines()
        sep_indices = [idx for idx, line in enumerate(lines) if line.strip().startswith("-")]
        if len(sep_indices) < 2:
            continue
        start_idx = sep_indices[1] + 1
        for line in lines[start_idx:]:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) != 20:
                continue
            julian = int(parts[1])
            year = int(parts[2])
            date = datetime(year, 1, 1) + timedelta(days=julian - 1)
            rows.append(
                {
                    "wepp_id": wepp_id,
                    "year": year,
                    "month": date.month,
                    "day_of_month": date.day,
                    "julian": julian,
                    "Q": float(parts[5]),
                    "Ep": float(parts[6]),
                    "Es": float(parts[7]),
                    "Er": float(parts[8]),
                    "Dp": float(parts[9]),
                    "latqcc": float(parts[12]),
                }
            )
    if not rows:
        pytest.skip("No H*.wat.dat files found for aggregation test")
    wat_df = pd.DataFrame(rows)
    return wat_df.groupby(["wepp_id", "year", "month", "day_of_month", "julian"], as_index=False).sum()


def test_totalwatsed_aggregate_cache(tmp_path: Path) -> None:
    _require_run(RUN_RIDDLED)
    working_run = _prepare_run_copy(
        RUN_RIDDLED,
        tmp_path,
        [
            "landuse/landuse.parquet",
            "wepp/output/interchange/H.pass.parquet",
            "wepp/output/H*.wat.dat",
        ],
    )
    ctx = _load_run_context(working_run)

    cache_dir = ctx.base_dir / "_query_engine" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / "totalwatsed3.parquet"
    if output_path.exists():
        output_path.unlink()

    wat_daily = _parse_wat_files(working_run)

    pass_path = working_run / "wepp/output/interchange/H.pass.parquet"
    if not pass_path.exists():
        pytest.skip("H.pass.parquet not available for aggregation test")

    con = duckdb.connect()
    pass_daily = con.execute(
        f"""
        SELECT
            wepp_id,
            year,
            month,
            day_of_month,
            julian,
            SUM(runoff)  AS runoff_mm,
            SUM(runvol)  AS runoff_volume,
            SUM(tdet)    AS sed_det,
            SUM(tdep)    AS sed_dep
        FROM read_parquet('{pass_path.as_posix()}')
        WHERE event = 'SUBEVENT'
        GROUP BY 1,2,3,4,5
        """
    ).fetchdf()

    merged = pass_daily.merge(
        wat_daily,
        on=["wepp_id", "year", "month", "day_of_month", "julian"],
        how="outer",
    ).fillna(0.0)

    # Drop hillslope identifier before aggregating to daily totals
    merged_no_id = merged.drop(columns=["wepp_id"])
    daily_totals = merged_no_id.groupby(["year", "month", "day_of_month", "julian"], as_index=False).sum(numeric_only=True)
    daily_totals.sort_values(["year", "month", "day_of_month"], inplace=True)

    table = pa.Table.from_pandas(daily_totals)
    pq.write_table(table, output_path)

    assert output_path.exists()
    written = pq.read_table(output_path)
    assert written.num_rows == len(daily_totals)
    assert "runoff_mm" in written.column_names
    # Basic sanity: totals should be non-negative
    assert written.column("runoff_mm").to_numpy().min() >= 0.0
