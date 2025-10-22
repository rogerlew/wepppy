from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module
load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
element_module = load_module("wepppy.wepp.interchange.hill_element_interchange", "wepppy/wepp/interchange/hill_element_interchange.py")
cleanup_import_state()

def test_element_interchange_writes_parquet(tmp_path, monkeypatch):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    h1_path = workdir / "H1.element.dat"
    lines = h1_path.read_text().splitlines()
    for idx, raw in enumerate(lines):
        if raw.strip().startswith("1  1  1 2000"):
            runoff_idx = element_module.ELEMENT_COLUMN_NAMES.index("Runoff")
            start = sum(element_module.ELEMENT_FIELD_WIDTHS[:runoff_idx])
            width = element_module.ELEMENT_FIELD_WIDTHS[runoff_idx]
            end = start + width
            replacement = f"{'******':>{width}}"
            # Ensure the line is padded to the expected width before substitution
            padded = raw.ljust(sum(element_module.ELEMENT_FIELD_WIDTHS))
            lines[idx] = padded[:start] + replacement + padded[end:]
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
    assert "MM" not in df.columns
    assert "DD" not in df.columns
    assert "YYYY" not in df.columns
    assert "day" not in df.columns

    first_row = df.sort_values(["wepp_id", "julian", "ofe_id"]).iloc[0]
    assert first_row["Runoff"] == pytest.approx(0.0)
    assert first_row["Precip"] == pytest.approx(0.0)


def test_element_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = element_module.run_wepp_hillslope_element_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == element_module.SCHEMA
    assert table.num_rows == 0
