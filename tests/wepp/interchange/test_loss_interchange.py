import importlib.util
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


def _load_loss_module():
    module_path = Path(__file__).resolve().parents[3] / "wepppy/wepp/interchange/loss_interchange.py"
    spec = importlib.util.spec_from_file_location("loss_interchange", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def loss_module():
    return _load_loss_module()


def test_loss_interchange_writes_parquet(tmp_path, loss_module):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == loss_module.SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1, 2, 3}
    assert (df.groupby("wepp_id")["Class"].nunique() == 5).all()

    first = df.sort_values(["wepp_id", "Class"]).iloc[0]
    assert first["Diameter (mm)"] == pytest.approx(0.002)
    assert first["Sediment Fraction"] == pytest.approx(0.010)
    assert first["In Flow Exiting"] == pytest.approx(0.0)


def test_loss_interchange_handles_missing_files(tmp_path, loss_module):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == loss_module.SCHEMA
    assert table.num_rows == 0
