import importlib.util
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


def _load_pass_module():
    module_path = Path(__file__).resolve().parents[3] / "wepppy/wepp/interchange/pass_interchange.py"
    spec = importlib.util.spec_from_file_location("pass_interchange", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pass_module():
    return _load_pass_module()


def test_pass_interchange_writes_parquet(tmp_path, pass_module):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = pass_module.run_wepp_hillslope_pass_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == pass_module.SCHEMA
    assert table.num_rows > 0

    interchange_dir = workdir / "interchange"
    for name in ["H.ebe.parquet", "H.element.parquet", "H.loss.parquet", "H.soil.parquet", "H.wat.parquet"]:
        assert (interchange_dir / name).exists()

    df = table.to_pandas()
    assert set(df["event"].unique()).issubset({"SUBEVENT", "NO EVENT"})
    assert set(df["wepp_id"].unique()) == {1, 2, 3}

    no_event = df[df["event"] == "NO EVENT"]
    assert (no_event[["runoff", "sbrunf", "sbrunv", "drainq", "drrunv"]].eq(0.0)).all().all()

    first_row = df.iloc[0]
    assert first_row["month"] == 1
    assert first_row["day_of_month"] == 1
    assert first_row["julian"] == first_row["day"]


def test_pass_interchange_handles_missing_files(tmp_path, pass_module):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = pass_module.run_wepp_hillslope_pass_interchange(workdir)
    table = pq.read_table(target)
    assert table.schema == pass_module.SCHEMA
    assert table.num_rows == 0

    interchange_dir = workdir / "interchange"
    for name in ["H.ebe.parquet", "H.element.parquet", "H.loss.parquet", "H.soil.parquet", "H.wat.parquet"]:
        assert (interchange_dir / name).exists()
