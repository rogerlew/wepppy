from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from .module_loader import cleanup_import_state, load_module


_all_your_base = load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
_concurrency = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
load_module("wepppy.wepp.interchange.schema_utils", "wepppy/wepp/interchange/schema_utils.py")
load_module("wepppy.wepp.interchange._utils", "wepppy/wepp/interchange/_utils.py")
_hill_pass = load_module("wepppy.wepp.interchange.hill_pass_interchange", "wepppy/wepp/interchange/hill_pass_interchange.py")
cleanup_import_state()

write_parquet_with_pool = _concurrency.write_parquet_with_pool
SCHEMA = _hill_pass.SCHEMA
run_wepp_hillslope_pass_interchange = _hill_pass.run_wepp_hillslope_pass_interchange


def _make_dummy_inputs(tmp_path: Path, count: int, delays: list[float] | None = None) -> list[Path]:
    inputs: list[Path] = []
    for idx in range(count):
        delay = 0.0 if delays is None else delays[idx]
        path = tmp_path / f"{idx}.dat"
        path.write_text(f"{idx},{delay}")
        inputs.append(path)
    return inputs


_CONCURRENT_SCHEMA = pa.schema([("value", pa.int32())])


def _parser_with_delay(path: Path) -> pa.Table:
    raw = path.read_text().strip()
    if "," in raw:
        value_str, delay_str = raw.split(",", 1)
        delay = float(delay_str)
    else:
        value_str = raw
        delay = 0.0
    if delay > 0.0:
        time.sleep(delay)
    value = int(value_str)
    return pa.table({"value": [value]}, schema=_CONCURRENT_SCHEMA)


def test_write_parquet_with_pool_concurrent(tmp_path: Path) -> None:
    inputs = _make_dummy_inputs(tmp_path, 2, delays=[0.2, 0.0])
    target = tmp_path / "pool.parquet"
    try:
        write_parquet_with_pool(inputs, _parser_with_delay, _CONCURRENT_SCHEMA, target, max_workers=2)
    except PermissionError as exc:
        pytest.skip(f"ProcessPoolExecutor unavailable due to OS permission error: {exc}")

    table = pq.read_table(target)
    assert table.column("value").to_pylist() == [0, 1]


def test_write_parquet_with_pool_handles_empty(tmp_path: Path) -> None:
    schema = pa.schema([("value", pa.int32())])
    target = tmp_path / "empty.parquet"

    write_parquet_with_pool([], lambda _: NotImplemented, schema, target, max_workers=1)

    table = pq.read_table(target)
    assert table.num_rows == 0
    assert table.schema == schema


def test_write_parquet_with_pool_falls_back_when_tmp_invalid(tmp_path: Path) -> None:
    inputs = _make_dummy_inputs(tmp_path, 1)

    bad_tmp = tmp_path / "not_a_dir.tmp"
    bad_tmp.write_text("x")
    target = tmp_path / "fallback.parquet"
    try:
        write_parquet_with_pool(inputs, _parser_with_delay, _CONCURRENT_SCHEMA, target, max_workers=1, tmp_dir=bad_tmp)
    except PermissionError as exc:
        pytest.skip(f"ProcessPoolExecutor unavailable due to OS permission error: {exc}")

    table = pq.read_table(target)
    assert table.column("value").to_pylist() == [0]


def test_hill_pass_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    try:
        target = run_wepp_hillslope_pass_interchange(workdir)
    except PermissionError as exc:
        pytest.skip(f"ProcessPoolExecutor unavailable due to OS permission error: {exc}")
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["event"].unique()).issubset({"SUBEVENT", "NO EVENT"})
    assert set(df["wepp_id"].unique()) == {1, 2, 3}

    no_event = df[df["event"] == "NO EVENT"]
    assert (no_event[["runoff", "sbrunf", "sbrunv", "drainq", "drrunv"]].eq(0.0)).all().all()

    first_row = df.iloc[0]
    assert first_row["month"] == 1
    assert first_row["day_of_month"] == 1
    assert first_row["sim_day_index"] == 1
    assert first_row["julian"] == 1


def test_hill_pass_interchange_handles_missing_files(tmp_path: Path) -> None:
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = run_wepp_hillslope_pass_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == SCHEMA
    assert table.num_rows == 0
