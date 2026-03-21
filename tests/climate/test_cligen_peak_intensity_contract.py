from __future__ import annotations

import math
from pathlib import Path

import pytest

from wepppy.climates.cligen import ClimateFile
from wepppy.climates.cligen.cligen import (
    cli_calculate_static_r,
    wepp_peak_intensities_from_hyetograph,
)

pytestmark = pytest.mark.unit


def _breakpoint_cli_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "wepppy"
        / "climates"
        / "cligen"
        / "tests"
        / "data"
        / "breakpoint.cli"
    )


def _write_simple_breakpoint_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "0.00",
                "   1   1   0",
                "Station: Test",
                " Latitude Longitude Elevation (m) Obs. Years    Beginning year  Years simulated",
                "    33.66  -109.31             1831             6             2011             2",
                " Observed monthly ave max temperature (C)",
                " 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0",
                " Observed monthly ave min temperature (C)",
                "  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0",
                " Observed monthly ave solar radiation (Langleys)",
                " 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0",
                " Observed monthly ave rainfall (mm)",
                "  20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0",
                "   day mon year nbrkpt tmax  tmin    rad   w-vel  w-dir   dew",
                "                (mm)    (C)   (C) (ly/day) m/sec    deg    (C)",
                "    1   1  2011   3    -4.28  -23.72 277.6    2.20  290.0 -25.6",
                "00.75     0.000",
                "01.00     10.000",
                "05.00     10.254",
                "",
            ]
        )
    )


def test_breakpoint_dataframe_has_real_peak_intensities_and_nullable_tp_ip() -> None:
    cli_path = _breakpoint_cli_path()
    assert cli_path.exists()

    df = ClimateFile(str(cli_path)).as_dataframe(calc_peak_intensities=True)

    for column in ("dur", "tp", "ip", "peak_intensity_10", "peak_intensity_15", "peak_intensity_30", "peak_intensity_60"):
        assert column in df.columns

    assert not (df["peak_intensity_30"] < 0.0).any()

    first_breakpoint = df[df["nbrkpt"] > 0].iloc[0]
    assert first_breakpoint["dur"] > 0.0
    assert math.isnan(first_breakpoint["tp"])
    assert math.isnan(first_breakpoint["ip"])
    assert first_breakpoint["peak_intensity_30"] > 0.0


def test_breakpoint_peak_intensities_match_expected_windows_for_simple_cli(tmp_path: Path) -> None:
    cli_path = tmp_path / "simple_breakpoint.cli"
    _write_simple_breakpoint_cli(cli_path)

    df = ClimateFile(str(cli_path)).as_dataframe(calc_peak_intensities=True)
    first_breakpoint = df[df["nbrkpt"] > 0].iloc[0]

    assert first_breakpoint["peak_intensity_10"] == pytest.approx(40.0)
    assert first_breakpoint["peak_intensity_15"] == pytest.approx(40.0)
    assert first_breakpoint["peak_intensity_30"] == pytest.approx(20.03175)
    assert first_breakpoint["peak_intensity_60"] == pytest.approx(10.047625)


def test_non_breakpoint_peak_intensity_path_is_stable_under_repeated_calls() -> None:
    for _ in range(200):
        values = wepp_peak_intensities_from_hyetograph(
            30.0,
            2.0,
            0.35,
            2.2,
            max_time=[10, 15, 30, 60],
        )
        assert len(values) == 4
        assert all(math.isfinite(value) and value >= 0.0 for value in values)


def test_cli_calculate_static_r_returns_expected_schema() -> None:
    result = cli_calculate_static_r(str(_breakpoint_cli_path()))

    assert "mean_annual_r" in result
    assert "annual_ei30" in result
    assert "units" in result
    assert result["units"] == "MJ mm ha^-1 h^-1"
    assert isinstance(result["annual_ei30"], list)
    annual = result["annual_ei30"]
    assert all("year" in row and "ei30" in row for row in annual)
    years = [int(row["year"]) for row in annual]
    assert years == sorted(years)
    annual_values = [float(row["ei30"]) for row in annual]
    expected_mean = (sum(annual_values) / len(annual_values)) if annual_values else 0.0
    assert result["mean_annual_r"] == pytest.approx(expected_mean)
    assert 0 <= int(result.get("storms_used", 0)) <= int(result.get("storms_total", 0))
    assert result["mean_annual_r"] >= 0.0
