from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import concurrency as concurrency_module
from wepppy.wepp.interchange import hil_loss_interchange as loss_module


def test_loss_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(loss_module, "write_parquet_with_pool", _wrapper)

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".loss.dat") for p in calls[0]["files"])

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


def test_loss_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == loss_module.SCHEMA
    assert table.num_rows == 0
