import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module

load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
ebe_module = load_module("wepppy.wepp.interchange.hill_ebe_interchange", "wepppy/wepp/interchange/hill_ebe_interchange.py")
cleanup_import_state()


@pytest.mark.parametrize(
    ("layout_name", "extra_measurements"),
    [
        ("standard", [[], []]),
        ("reveg", [["65.0", "80.0"], ["61.0", "79.0"]]),
    ],
)
def test_ebe_interchange_writes_parquet(layout_name, extra_measurements, tmp_path, monkeypatch):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    for ebe_path in workdir.glob("H*.ebe.dat"):
        if ebe_path.name != "H1.ebe.dat":
            ebe_path.unlink()

    base_rows = [
        ["29", "2", "5", "10.6", "4.1", "0.000", "0.00", "0.00", "0.0", "0.00", "0.00", "0.0", "0.0", "1.00"],
        ["1", "3", "5", "0.0", "0.0", "0.000", "0.00", "0.00", "0.0", "0.00", "0.00", "0.0", "0.0", "1.00"],
    ]
    sample_rows = [" ".join(row + extra) for row, extra in zip(base_rows, extra_measurements)]

    header_tokens, unit_tokens = {
        "standard": (ebe_module.RAW_HEADER_STANDARD, ebe_module.RAW_UNITS_STANDARD),
        "reveg": (ebe_module.RAW_HEADER_REVEG, ebe_module.RAW_UNITS_REVEG),
    }[layout_name]

    header = [
        " EVENT OUTPUT",
        " ".join(header_tokens),
        " ".join(unit_tokens),
    ]

    h1_path = workdir / "H1.ebe.dat"
    h1_path.write_text("\n".join(header + sample_rows) + "\n")

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(ebe_module, "write_parquet_with_pool", _wrapper)

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir, start_year=2008)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".ebe.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == len(sample_rows)

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1}
    assert set(df["year"].unique()) == {2012}
    assert list(df["Precip"]) == pytest.approx([10.6, 0.0])
    assert list(df["Dep-point"]) == pytest.approx([0.0, 0.0])

    first = df.iloc[0]
    assert first["month"] == 2
    assert first["day_of_month"] == 29
    assert first["julian"] == 60
    assert first["water_year"] == 2012

    if layout_name == "standard":
        assert df["Det-Len"].isna().all()
        assert df["Dep-Len"].isna().all()
    else:
        assert df["Det-Len"].tolist() == pytest.approx([65.0, 61.0])
        assert df["Dep-Len"].tolist() == pytest.approx([80.0, 79.0])


def test_ebe_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == 0
