from __future__ import annotations

import datetime as _dt
from calendar import isleap
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
import pytest

from wepppy.climates.daymet.daymet_singlelocation_client import retrieve_historical_timeseries


@dataclass(frozen=True)
class _DaymetRow:
    year: int
    yday: int
    prcp: float
    tmax: float
    tmin: float
    dayl: float
    srad: float
    vp: float


def _build_daymet_response(rows: Iterable[_DaymetRow]) -> str:
    header_lines = [
        "# Daymet metadata line 1",
        "# Daymet metadata line 2",
        "YEAR,DAY,prcp(mm/day),tmax(degc),tmin(degc),dayl(s),srad(W/m^2),vp(Pa)",
    ]
    body_lines = [
        f"{row.year},{row.yday},{row.prcp},{row.tmax},{row.tmin},{row.dayl},{row.srad},{row.vp}"
        for row in rows
    ]
    return "\n".join(header_lines + body_lines)


def _expected_index(rows: Iterable[_DaymetRow]) -> pd.DatetimeIndex:
    dates: list[_dt.datetime] = []
    for row in rows:
        base_date = _dt.datetime(row.year, 1, 1) + _dt.timedelta(days=row.yday - 1)
        dates.append(base_date)
        if isleap(row.year) and row.yday == 365:
            dates.append(_dt.datetime(row.year, 1, 1) + _dt.timedelta(days=366 - 1))
    dates.sort()
    return pd.to_datetime(dates)


def _install_fake_daymet(monkeypatch, response_text: str):
    class _FakeResponse:
        def __init__(self, payload: str):
            self.status_code = 200
            self.text = payload

    def _fake_get(url):
        return _FakeResponse(response_text)

    monkeypatch.setattr("wepppy.climates.daymet.daymet_singlelocation_client.requests.get", _fake_get)


def test_retrieve_historical_timeseries_leap_handling_and_conversions(monkeypatch):
    rows = [
        _DaymetRow(1980, 100, 5.0, 15.0, 5.0, 36_000.0, 200.0, 150.0),
        _DaymetRow(1980, 365, 10.0, 12.0, 3.0, 40_000.0, 150.0, 120.0),
        _DaymetRow(1981, 1, 1.0, 10.0, -2.0, 32_000.0, 180.0, 90.0),
    ]
    _install_fake_daymet(monkeypatch, _build_daymet_response(rows))

    df = retrieve_historical_timeseries(-116.0, 47.0, 1980, 1981)

    leap_rows = df[(df["year"] == 1980) & (df["yday"] == 366)]
    assert len(leap_rows) == 1, "Leap day should be synthesized from day 365"

    base_row = df[(df["year"] == 1980) & (df["yday"] == 100)].iloc[0]
    expected_srad_l_day = (base_row["srad(W/m^2)"] * base_row["dayl(s)"]) / 41840.0
    assert pytest.approx(base_row["srad(l/day)"]) == expected_srad_l_day

    clipped_row = df[(df["year"] == 1980) & (df["yday"] == 365)].iloc[0]
    assert clipped_row["tdew(degc)"] >= clipped_row["tmin(degc)"]

    assert df.index.dtype == "datetime64[ns]"


def test_retrieve_historical_timeseries_with_gridmet_wind(monkeypatch):
    rows = [
        _DaymetRow(1980, 100, 5.0, 15.0, 5.0, 36_000.0, 200.0, 150.0),
        _DaymetRow(1980, 365, 10.0, 12.0, 3.0, 40_000.0, 150.0, 120.0),
    ]
    _install_fake_daymet(monkeypatch, _build_daymet_response(rows))

    expected_index = _expected_index(rows)

    def _fake_wind(lon, lat, start_year, end_year):
        assert start_year == 1980
        assert end_year == 1980
        assert pytest.approx(lon) == -116.0
        assert pytest.approx(lat) == 47.0
        data = {
            "vs(m/s)": np.full(expected_index.size, 2.5),
            "th(DegreesClockwisefromnorth)": np.full(expected_index.size, 90.0),
        }
        return pd.DataFrame(data, index=expected_index)

    monkeypatch.setattr("wepppy.climates.gridmet.retrieve_historical_wind", _fake_wind, raising=False)

    df = retrieve_historical_timeseries(-116.0, 47.0, 1980, 1980, gridmet_wind=True)

    assert "vs(m/s)" in df.columns
    assert "th(DegreesClockwisefromnorth)" in df.columns
    assert np.allclose(df["vs(m/s)"].values, 2.5)
    assert np.allclose(df["th(DegreesClockwisefromnorth)"].values, 90.0)
