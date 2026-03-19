from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module

pytestmark = pytest.mark.unit

load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
element_module = load_module("wepppy.wepp.interchange.hill_element_interchange", "wepppy/wepp/interchange/hill_element_interchange.py")
cleanup_import_state()


def _append_qrain_qsnow_columns(path: Path, *, qrain: float, qsnow: float) -> None:
    lines = path.read_text().splitlines()
    lines[0] = f"{lines[0]}   QRain   QSnow"
    lines[1] = f"{lines[1]}      mm      mm"

    for idx in range(2, len(lines)):
        if not lines[idx].strip():
            continue
        lines[idx] = f"{lines[idx]}{qrain:9.3f}{qsnow:9.3f}"
        path.write_text("\n".join(lines) + "\n")
        return

    raise AssertionError(f"No element data rows found in {path}")


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
    assert "QRain" in df.columns
    assert "QSnow" in df.columns
    assert df["QRain"].isna().all()
    assert df["QSnow"].isna().all()

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


def test_element_interchange_parses_qrain_qsnow_columns(tmp_path):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    _append_qrain_qsnow_columns(workdir / "H1.element.dat", qrain=1.234, qsnow=2.345)

    target = element_module.run_wepp_hillslope_element_interchange(workdir)
    table = pq.read_table(target)
    df = table.to_pandas()

    row = (
        df[
            (df["wepp_id"] == 1)
            & df["QRain"].notna()
            & df["QSnow"].notna()
        ]
        .sort_values(["julian", "ofe_id"])
        .iloc[0]
    )
    assert row["QRain"] == pytest.approx(1.234)
    assert row["QSnow"] == pytest.approx(2.345)


def test_element_interchange_mixed_legacy_and_qrain_files(tmp_path):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    _append_qrain_qsnow_columns(workdir / "H1.element.dat", qrain=3.210, qsnow=0.450)

    target = element_module.run_wepp_hillslope_element_interchange(workdir)
    table = pq.read_table(target)
    df = table.to_pandas()

    h1_partition_rows = (
        df[(df["wepp_id"] == 1) & df["QRain"].notna() & df["QSnow"].notna()]
        .sort_values(["julian", "ofe_id"])
    )
    assert not h1_partition_rows.empty
    assert h1_partition_rows.iloc[0]["QRain"] == pytest.approx(3.210)
    assert h1_partition_rows.iloc[0]["QSnow"] == pytest.approx(0.450)

    legacy_rows = df[df["wepp_id"] != 1]
    assert not legacy_rows.empty
    assert legacy_rows["QRain"].isna().all()
    assert legacy_rows["QSnow"].isna().all()


def test_element_interchange_normalizes_missing_rust_optional_columns():
    columns = {"wepp_id": [1, 2], "Runoff": [0.0, 0.1]}

    normalized = element_module._normalize_rust_optional_columns(columns)
    assert normalized["QRain"] == [None, None]
    assert normalized["QSnow"] == [None, None]
    assert normalized["wepp_id"] == [1, 2]
    assert normalized["Runoff"] == [0.0, 0.1]

    already_extended = {"wepp_id": [9], "QRain": [0.7], "QSnow": [0.3]}
    assert element_module._normalize_rust_optional_columns(already_extended) is already_extended
