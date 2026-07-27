from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.wepp.interchange.versioning", "wepppy/wepp/interchange/versioning.py")
_watershed_loss = load_module(
    "wepppy.wepp.interchange.watershed_loss_interchange",
    "wepppy/wepp/interchange/watershed_loss_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_loss_interchange = _watershed_loss.run_wepp_watershed_loss_interchange
AVERAGE_FILENAMES = _watershed_loss.AVERAGE_FILENAMES
ALL_YEARS_FILENAMES = _watershed_loss.ALL_YEARS_FILENAMES


def _read(path: Path) -> pd.DataFrame:
    return pq.read_table(path).to_pandas()


def test_watershed_loss_interchange_outputs_expected_tables(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    outputs = run_wepp_watershed_loss_interchange(workdir)

    interchange_dir = workdir / "interchange"
    expected_paths = {
        "average_hill": interchange_dir / AVERAGE_FILENAMES["hill"],
        "average_chn": interchange_dir / AVERAGE_FILENAMES["chn"],
        "average_out": interchange_dir / AVERAGE_FILENAMES["out"],
        "average_class": interchange_dir / AVERAGE_FILENAMES["class_data"],
        "all_years_hill": interchange_dir / ALL_YEARS_FILENAMES["hill"],
        "all_years_chn": interchange_dir / ALL_YEARS_FILENAMES["chn"],
        "all_years_out": interchange_dir / ALL_YEARS_FILENAMES["out"],
        "all_years_class": interchange_dir / ALL_YEARS_FILENAMES["class_data"],
    }

    assert set(outputs.keys()) == set(expected_paths.keys())
    for key, path in expected_paths.items():
        assert outputs[key] == path
        assert path.exists()

    avg_hill = _read(expected_paths["average_hill"])
    assert list(avg_hill.columns) == [
        "Type",
        "wepp_id",
        "Runoff Volume",
        "Subrunoff Volume",
        "Baseflow Volume",
        "Soil Loss",
        "Sediment Deposition",
        "Sediment Yield",
        "Hillslope Area",
        "Solub. React. Pollutant",
        "Particulate Pollutant",
        "Total Pollutant",
    ]
    assert avg_hill.shape == (3, 12)
    hill1 = avg_hill.loc[avg_hill["wepp_id"] == 1].iloc[0]
    assert hill1["Subrunoff Volume"] == pytest.approx(22061.2)
    assert hill1["Hillslope Area"] == pytest.approx(10.5)

    avg_table = pq.read_table(expected_paths["average_hill"])
    assert avg_table.schema.metadata[b"schema_version"] == b"1"
    assert avg_table.schema.metadata[b"average_years"] == b"6"

    avg_out = _read(expected_paths["average_out"]).set_index("key")
    assert avg_out.at["Avg. Ann. water discharge from outlet", "value"] == pytest.approx(50205.0)
    assert avg_out.at["Avg. Ann. Sed. delivery per unit area of watershed", "units"] == "tonne/ha/yr"

    avg_class = _read(expected_paths["average_class"])
    assert avg_class.shape == (5, 8)
    assert avg_class.loc[avg_class["Class"] == 5, "Fraction In Flow Exiting"].iloc[0] == pytest.approx(0.465)

    hill_all = _read(expected_paths["all_years_hill"])
    assert sorted(hill_all["year"].unique()) == [2000, 2001, 2002, 2003, 2004, 2005]
    assert hill_all.shape == (18, 13)
    assert "Hillslope Area" in hill_all.columns
    assert hill_all["Hillslope Area"].isna().all()
    legacy_table = pq.read_table(expected_paths["all_years_hill"])
    assert legacy_table.column("Hillslope Area").null_count == legacy_table.num_rows
    hill_2001_2 = hill_all[(hill_all["year"] == 2001) & (hill_all["wepp_id"] == 2)].iloc[0]
    assert hill_2001_2["Baseflow Volume"] == pytest.approx(144.9)

    chn_all = _read(expected_paths["all_years_chn"])
    assert chn_all.shape == (6, 12)
    channel_2000 = chn_all[chn_all["year"] == 2000].iloc[0]
    assert channel_2000["chn_enum"] == 1
    assert channel_2000["Discharge Volume"] == pytest.approx(71409.1)
    assert channel_2000["Upland Charge"] == pytest.approx(71486.3)

    out_all = _read(expected_paths["all_years_out"])
    assert out_all["year"].nunique() == 6
    sediment_row = out_all[(out_all["year"] == 2004) & (out_all["key"] == "Total sediment discharge from outlet")].iloc[0]
    assert sediment_row["value"] == pytest.approx(0.5)

    class_all = _read(expected_paths["all_years_class"])
    assert class_all.shape == (30, 9)
    assert class_all["year"].nunique() == 6
    class_year_match = class_all[(class_all["year"] == 2003) & (class_all["Class"] == 4)].iloc[0]
    assert class_year_match["Diameter"] == pytest.approx(0.3)
    assert class_year_match["Fraction In Flow Exiting"] == pytest.approx(0.255)


def test_watershed_loss_interchange_maps_current_annual_hillslope_area(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "output"
    shutil.copytree(PROJECT_OUTPUT, workdir)
    source = workdir / "loss_pw0.txt"
    lines = source.read_text(encoding="ascii").splitlines()
    annual_header = next(
        idx
        for idx, line in enumerate(lines)
        if "ANNUAL SUMMARY FOR WATERSHED IN YEAR" in line
    )
    average_header = next(
        idx
        for idx, line in enumerate(lines)
        if "YEAR AVERAGE ANNUAL VALUES FOR WATERSHED" in line
    )
    annual_hill_rows = [
        idx
        for idx in range(annual_header + 1, average_header)
        if lines[idx].split()[:1] == ["Hill"]
    ]
    for idx in annual_hill_rows:
        tokens = lines[idx].split()
        tokens.insert(8, "1.000")
        lines[idx] = " ".join(tokens)
    lines[annual_hill_rows[0]] = (
        "Hill 1 768.0 13741.4 118.0 0.0 -0.0 0.0 "
        "1.539 0.1 0.2 0.3"
    )
    source.write_text("\n".join(lines) + "\n", encoding="ascii")

    outputs = run_wepp_watershed_loss_interchange(workdir)

    table = pq.read_table(outputs["all_years_hill"])
    assert table.schema.metadata[b"schema_version"] == b"2"
    assert table.schema.field("Hillslope Area").metadata == {b"units": b"ha"}
    frame = table.to_pandas()
    row = frame.iloc[0]
    assert row["Sediment Yield"] == pytest.approx(0.0)
    assert row["Hillslope Area"] == pytest.approx(1.539)
    assert row["Solub. React. Pollutant"] == pytest.approx(0.1)
    assert row["Particulate Pollutant"] == pytest.approx(0.2)
    assert row["Total Pollutant"] == pytest.approx(0.3)
