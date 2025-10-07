from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
import shutil
import threading
import time

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(full_name: str, relative_path: str):
    parts = full_name.split(".")
    for idx in range(1, len(parts)):
        pkg = ".".join(parts[:idx])
        if pkg not in sys.modules:
            module = types.ModuleType(pkg)
            module.__path__ = []
            sys.modules[pkg] = module

    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_all_your_base = _load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
_load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
_concurrency = _load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
_hill_pass = _load_module("wepppy.wepp.interchange.hill_pass_interchange", "wepppy/wepp/interchange/hill_pass_interchange.py")

write_parquet_with_pool = _concurrency.write_parquet_with_pool
SCHEMA = _hill_pass.SCHEMA
run_wepp_hillslope_pass_interchange = _hill_pass.run_wepp_hillslope_pass_interchange


def _make_dummy_inputs(tmp_path: Path, count: int) -> list[Path]:
    inputs: list[Path] = []
    for idx in range(count):
        path = tmp_path / f"{idx}.dat"
        path.write_text(str(idx))
        inputs.append(path)
    return inputs


def test_write_parquet_with_pool_concurrent(tmp_path: Path) -> None:
    schema = pa.schema([("value", pa.int32())])
    inputs = _make_dummy_inputs(tmp_path, 2)
    barrier = threading.Barrier(len(inputs))

    def parser(path: Path) -> pa.Table:
        barrier.wait(timeout=5)
        if path.stem == "0":
            time.sleep(0.1)
        return pa.table({"value": [int(path.stem)]}, schema=schema)

    target = tmp_path / "pool.parquet"
    write_parquet_with_pool(inputs, parser, schema, target, max_workers=2)

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
    schema = pa.schema([("value", pa.int32())])
    inputs = _make_dummy_inputs(tmp_path, 1)

    def parser(path: Path) -> pa.Table:
        return pa.table({"value": [int(path.stem)]}, schema=schema)

    bad_tmp = tmp_path / "not_a_dir.tmp"
    bad_tmp.write_text("x")
    target = tmp_path / "fallback.parquet"
    write_parquet_with_pool(inputs, parser, schema, target, max_workers=1, tmp_dir=bad_tmp)

    table = pq.read_table(target)
    assert table.column("value").to_pylist() == [0]


def test_hill_pass_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = run_wepp_hillslope_pass_interchange(workdir)
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
    assert first_row["julian"] == first_row["day"]


def test_hill_pass_interchange_handles_missing_files(tmp_path: Path) -> None:
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = run_wepp_hillslope_pass_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == SCHEMA
    assert table.num_rows == 0
