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

    target = element_module.run_wepp_hillslope_element_interchange(workdir, start_year=2000)
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


def test_element_interchange_normalizes_overflow_dates(tmp_path):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    template_path = workdir / "H1.element.dat"
    lines = template_path.read_text().splitlines()
    header = lines[:2]
    template_tokens = element_module._split_fixed_width_line(lines[2])
    template_tokens[1] = "30"  # Day
    template_tokens[2] = "2"   # Month
    template_tokens[3] = "5"   # Relative year
    formatted = "".join(
        f"{token:>{width}}"
        for token, width in zip(template_tokens, element_module.ELEMENT_FIELD_WIDTHS)
    )
    new_path = workdir / "H901.element.dat"
    new_path.write_text("\n".join(header + [formatted]) + "\n")

    target = element_module.run_wepp_hillslope_element_interchange(workdir, start_year=2008)
    table = pq.read_table(target)
    df = table.to_pandas()
    subset = df[df["wepp_id"] == 901]
    assert not subset.empty
    row = subset.iloc[0]
    assert row["year"] == 2012
    assert row["month"] == 2
    assert row["day_of_month"] == 29
    assert row["julian"] == 60
