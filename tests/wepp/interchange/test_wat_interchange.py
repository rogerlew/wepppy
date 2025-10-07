import importlib.util
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


def _load_wat_module():
    module_path = Path(__file__).resolve().parents[3] / "wepppy/wepp/interchange/wat_interchange.py"
    spec = importlib.util.spec_from_file_location("wat_interchange", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wat_module():
    return _load_wat_module()


def test_wat_interchange_writes_parquet(tmp_path, wat_module):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == wat_module.SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1, 2, 3}
    assert (df["day"] == df["julian"]).all()
    assert (df["ofe_id"] == df["OFE (#)"]).all()

    first_row = df.iloc[0]
    assert first_row["month"] == 1
    assert first_row["day_of_month"] == 1
    assert pytest.approx(first_row["P (mm)"], rel=1e-6) == 12.20


def test_wat_interchange_handles_missing_files(tmp_path, wat_module):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == wat_module.SCHEMA
    assert table.num_rows == 0
