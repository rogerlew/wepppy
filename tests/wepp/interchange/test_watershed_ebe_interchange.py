from __future__ import annotations

from functools import partial
from pathlib import Path
import shutil

import pyarrow.parquet as pq

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_ebe = load_module(
    "wepppy.wepp.interchange.watershed_ebe_interchange",
    "wepppy/wepp/interchange/watershed_ebe_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_ebe_interchange = _watershed_ebe.run_wepp_watershed_ebe_interchange
EBE_PARQUET = _watershed_ebe.EBE_PARQUET


def test_watershed_ebe_interchange_writes_parquet(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    start_year = 2000
    target = run_wepp_watershed_ebe_interchange(workdir, start_year=start_year)
    assert target == workdir / "interchange" / EBE_PARQUET
    assert target.exists()

    table = pq.read_table(target)
    schema = table.schema

    expected_measurements = {
        "precip": b"mm",
        "runoff_volume": b"m^3",
        "peak_runoff": b"m^3/s",
        "sediment_yield": b"kg",
        "soluble_pollutant": b"kg",
        "particulate_pollutant": b"kg",
        "total_pollutant": b"kg",
    }

    for column, units in expected_measurements.items():
        field = schema.field(schema.get_field_index(column))
        assert field.metadata.get(b"units") == units

    df = table.to_pandas()
    assert not df.empty
    assert df["year"].min() == start_year
    assert df["year"].max() == start_year + 6 - 1
    assert set(df["element_id"].unique()) == {4}
    assert set(df.columns) == {
        "year",
        "simulation_year",
        "month",
        "day_of_month",
        "julian",
        "water_year",
        "precip",
        "runoff_volume",
        "peak_runoff",
        "sediment_yield",
        "soluble_pollutant",
        "particulate_pollutant",
        "total_pollutant",
        "element_id",
    }

    first_row = df.iloc[0]
    assert first_row["simulation_year"] == 1
    assert first_row["year"] == start_year
    assert first_row["julian"] == 1


def test_watershed_ebe_interchange_supports_legacy_file(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    workdir = tmp_path / "legacy_output"
    shutil.copytree(src, workdir)

    legacy_path = Path(__file__).resolve().parent / "legacy_ebe_pw0.txt"
    (workdir / "ebe_pw0.txt").write_text(legacy_path.read_text())

    legacy_start_year = 1997
    target = run_wepp_watershed_ebe_interchange(workdir, start_year=legacy_start_year)
    assert target.exists()

    table = pq.read_table(target)
    df = table.to_pandas()
    assert not df.empty
    assert set(df["element_id"].dropna().unique()) == {4}
    assert df["year"].min() == legacy_start_year


def test_watershed_ebe_interchange_handles_leap_year_in_future_climate(tmp_path: Path) -> None:
    """Test that Feb 29 is handled correctly when start_year creates leap year dates.
    
    Regression test for issue where future climate with Feb 29 in simulation year 11
    would fail because start_year was not being passed (defaulted to simulation year 11,
    which is not a leap year).
    """
    from io import StringIO
    
    workdir = tmp_path / "leap_year_output"
    workdir.mkdir()
    
    # Create a minimal ebe_pw0.txt with Feb 29 dates in simulation years that map to leap years
    # Format matches actual WEPP output: day month year precip runoff peak sediment sol_poll part_poll total_poll [element]
    ebe_content = StringIO()
    ebe_content.write("WATERSHED OUTPUT: DISCHARGE FROM WATERSHED OUTLET\n")
    ebe_content.write("(Results listed for Runoff Volume > 0.005m^3)\n")
    ebe_content.write("\n")
    ebe_content.write("Day          Precip.    Runoff      Peak       Sediment    Solub. React.  Particulate  Total           Elmt\n")
    ebe_content.write("   Month     Depth      Volume      Runoff     Yield       Phosphorus     Phosphorus   Phosphorus       ID\n")
    ebe_content.write("       Year  (mm)       (m^3)       (m^3/s)    (kg)        (kg)           (kg)         (kg)              -\n")
    ebe_content.write("-" * 100 + "\n")
    ebe_content.write("\n")
    # Simulation year 11 with start_year=2030 -> 2040 (leap year)
    ebe_content.write("   29    2    11  23.6   100.0    0.01   10.0    0.5    0.3    0.8     1\n")
    # Simulation year 19 with start_year=2030 -> 2048 (leap year)
    ebe_content.write("   29    2    19  15.2    80.0    0.01    8.0    0.4    0.2    0.6     1\n")
    
    (workdir / "ebe_pw0.txt").write_text(ebe_content.getvalue())
    
    # This should not raise ValueError: day is out of range for month
    start_year = 2030
    target = run_wepp_watershed_ebe_interchange(workdir, start_year=start_year)
    assert target.exists()
    
    table = pq.read_table(target)
    df = table.to_pandas()
    assert not df.empty
    
    # Verify the dates are correct
    feb29_rows = df[(df["month"] == 2) & (df["day_of_month"] == 29)]
    assert len(feb29_rows) == 2
    assert set(feb29_rows["year"]) == {2040, 2048}
    assert set(feb29_rows["simulation_year"]) == {11, 19}
