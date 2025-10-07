from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import concurrency as concurrency_module
from wepppy.wepp.interchange import hill_ebe_interchange as ebe_module


def test_ebe_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    sample_rows = [
        "  15   1  2001  12.7   5.6   0.123   0.45   0.78  210.5   0.11   0.22  300.3     0.33  0.95",
        "  16   1  2001   0.0   0.0   0.000   0.00   0.00    0.0   0.00   0.00    0.0     0.00  1.00",
    ]

    header = [
        " EVENT OUTPUT",
        "day mo  year Precp  Runoff  IR-det Av-det Mx-det  Point  Av-dep Max-dep  Point Sed.Del    ER",
        "--- --  ----  (mm)    (mm)  kg/m^2 kg/m^2 kg/m^2    (m)  kg/m^2  kg/m^2    (m)  (kg/m)  ----",
    ]

    h1_path = workdir / "H1.ebe.dat"
    h1_path.write_text("\n".join(header + sample_rows) + "\n")

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(ebe_module, "write_parquet_with_pool", _wrapper)

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".ebe.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == len(sample_rows)

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1}
    assert list(df["Precp (mm)"]) == pytest.approx([12.7, 0.0])
    assert list(df["Point (m)_2"]) == pytest.approx([300.3, 0.0])

    first = df.iloc[0]
    assert first["month"] == 1
    assert first["day_of_month"] == 15
    assert first["julian"] == 15
    assert first["water_year"] == 2001


def test_ebe_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == 0
