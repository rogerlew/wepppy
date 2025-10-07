import importlib.util
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


def _load_ebe_module():
    module_path = Path(__file__).resolve().parents[3] / "wepppy/wepp/interchange/ebe_interchange.py"
    spec = importlib.util.spec_from_file_location("ebe_interchange", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ebe_module():
    return _load_ebe_module()


def test_ebe_interchange_writes_parquet(tmp_path, ebe_module):
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

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()

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


def test_ebe_interchange_handles_missing_files(tmp_path, ebe_module):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == 0
