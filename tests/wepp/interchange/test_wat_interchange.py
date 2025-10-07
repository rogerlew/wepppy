from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import concurrency as concurrency_module
from wepppy.wepp.interchange import hill_wat_interchange as wat_module


def test_wat_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(wat_module, "write_parquet_with_pool", _wrapper)

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".wat.dat") for p in calls[0]["files"])

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


def test_wat_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == wat_module.SCHEMA
    assert table.num_rows == 0
