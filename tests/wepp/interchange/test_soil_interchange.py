import importlib.util
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


def _load_soil_module():
    module_path = Path(__file__).resolve().parents[3] / "wepppy/wepp/interchange/soil_interchange.py"
    spec = importlib.util.spec_from_file_location("soil_interchange", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def soil_module():
    return _load_soil_module()


def test_soil_interchange_writes_parquet(tmp_path, soil_module):
    src = Path("tests/wepp/interchange/test_project/output")
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

    target = soil_module.run_wepp_hillslope_soil_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == soil_module.SCHEMA
    assert table.num_rows == len(rows)

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1}
    assert list(df["ofe_id"]) == [1, 2]
    assert (df["day"] == df["Day"]).all()
    assert (df["julian"] == df["day"]).all()

    first = df.iloc[0]
    assert first["month"] == 1
    assert first["day_of_month"] == 15
    assert first["Saturation (frac)"] == pytest.approx(0.46)

    second = df.iloc[1]
    assert second["month"] == 7
    assert second["day_of_month"] == 19
    assert second["TSW (mm)"] == pytest.approx(40.00)


def test_soil_interchange_handles_missing_files(tmp_path, soil_module):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = soil_module.run_wepp_hillslope_soil_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == soil_module.SCHEMA
    assert table.num_rows == 0
