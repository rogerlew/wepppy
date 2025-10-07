from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import concurrency as concurrency_module
from wepppy.wepp.interchange import hill_element_interchange as element_module


def test_element_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    h1_path = workdir / "H1.element.dat"
    lines = h1_path.read_text().splitlines()
    for idx, raw in enumerate(lines):
        if raw.strip().startswith("1  1  1 2000"):
            tokens = raw.split()
            tokens[5] = "******"  # Set Runoff to missing for first record
            lines[idx] = " ".join(tokens)
            break
    h1_path.write_text("\n".join(lines) + "\n")

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(element_module, "write_parquet_with_pool", _wrapper)

    target = element_module.run_wepp_hillslope_element_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".element.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == element_module.SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1, 2, 3}
    assert (df["ofe_id"] == df["OFE"]).all()
    assert (df["month"] == df["MM"]).all()
    assert (df["day_of_month"] == df["DD"]).all()
    assert (df["year"] == df["YYYY"]).all()
    assert (df["day"] == df["julian"]).all()

    first_row = df.sort_values(["wepp_id", "julian", "ofe_id"]).iloc[0]
    assert first_row["Runoff (mm)"] == pytest.approx(0.0)
    assert first_row["Precip (mm)"] == pytest.approx(0.0)


def test_element_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = element_module.run_wepp_hillslope_element_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == element_module.SCHEMA
    assert table.num_rows == 0
