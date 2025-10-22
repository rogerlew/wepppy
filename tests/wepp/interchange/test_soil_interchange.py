from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module
load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
load_module("wepppy.wepp.interchange.schema_utils", "wepppy/wepp/interchange/schema_utils.py")
load_module("wepppy.wepp.interchange._utils", "wepppy/wepp/interchange/_utils.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
soil_module = load_module("wepppy.wepp.interchange.hill_soil_interchange", "wepppy/wepp/interchange/hill_soil_interchange.py")
cleanup_import_state()


def test_soil_interchange_writes_parquet(tmp_path, monkeypatch):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    for soil_path in workdir.glob("H*.soil.dat"):
        if soil_path.name != "H1.soil.dat":
            soil_path.unlink()

    header = [
        " Soil properties, daily output",
        "------------------------------------------------------------------------------------------------",
        " OFE Day   Y   Poros   Keff  Suct    FC     WP    Rough    Ki     Kr    Tauc    Saturation    TSW",
        "                 %    mm/hr   mm    mm/mm  mm/mm    mm   adjsmt adjsmt adjsmt   frac          mm",
        "------------------------------------------------------------------------------------------------",
        "",
    ]
    rows = [
        "  1   15   2001   66.01  40.00  17.65   0.20   0.05 100.00   0.04   0.13   2.00    0.46   30.56",
        "  2  200   2001   55.50  20.00  25.00   0.18   0.04  80.00   0.03   0.10   1.50    0.60   40.00",
    ]

    h1_path = workdir / "H1.soil.dat"
    h1_path.write_text("\n".join(header + rows) + "\n")

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(soil_module, "write_parquet_with_pool", _wrapper)

    target = soil_module.run_wepp_hillslope_soil_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".soil.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == soil_module.SCHEMA
    assert table.num_rows == len(rows)

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1}
    assert list(df["ofe_id"]) == [1, 2]
    assert (df["julian"] == df["sim_day_index"]).all()

    first = df.iloc[0]
    assert first["month"] == 1
    assert first["day_of_month"] == 15
    assert first["Saturation"] == pytest.approx(0.46)

    second = df.iloc[1]
    assert second["month"] == 7
    assert second["day_of_month"] == 19
    assert second["TSW"] == pytest.approx(40.00)


def test_soil_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = soil_module.run_wepp_hillslope_soil_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == soil_module.SCHEMA
    assert table.num_rows == 0
