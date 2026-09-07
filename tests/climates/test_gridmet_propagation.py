"""Admission forwarding through indirect public climate clients."""
from __future__ import annotations

import json
import pickle
from types import SimpleNamespace

import pandas as pd
import pytest

import wepppy.climates.daymet.daymet_singlelocation_client as daymet
import wepppy.climates.gridmet as gridmet
import wepppy.climates.prism.daily_client as prism
from wepppy.climates.gridmet.admission import GridMetAdmissionConfig

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("enabled", [False, True])
def test_prism_wind_forwards_literal_admission(monkeypatch, enabled):
    config = GridMetAdmissionConfig() if enabled else None
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", "true")
    data = {key: [1.0] * 365 for key in ("ppt", "tmax", "tmin", "tdmean", "tmean", "vpdmin", "vpdmax")}
    monkeypatch.setattr(prism.requests, "post", lambda *_args, **_kwargs: SimpleNamespace(
        text=json.dumps({"result": {"data": data}})
    ))
    received = []

    def wind(*_args, admission=None):
        received.append(admission)
        return pd.DataFrame({"vs(m/s)": 2.0, "th(DegreesClockwisefromnorth)": 90.0},
                            index=pd.date_range("2001-01-01", "2001-12-31"))

    monkeypatch.setattr(gridmet, "retrieve_historical_wind", wind)
    result = prism.retrieve_historical_timeseries(start_year=2001, end_year=2001, gridmet_wind=True, admission=config)
    assert received == [config]
    assert (result["vs(m/s)"] == 2.0).all()


@pytest.mark.parametrize("enabled", [False, True])
def test_daymet_wrapper_forwards_policy_without_environment_resolution(monkeypatch, enabled):
    config = GridMetAdmissionConfig() if enabled else None
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", "true")
    received = []
    result = pd.DataFrame()

    def retrieve(*_args, admission=None, **_kwargs):
        received.append(admission)
        return result

    monkeypatch.setattr(daymet, "retrieve_historical_timeseries", retrieve)
    attrs, output = daymet._retrieve_historical_timeseries_wrapper(
        -116.0, 46.0, 2001, 2001, gridmet_wind=True, attrs=(1, 2), admission=config
    )
    assert attrs == (1, 2)
    assert output is result
    assert received == [config]


def test_daymet_download_pool_receives_pickle_safe_config(monkeypatch, tmp_path):
    config = GridMetAdmissionConfig()
    received = []

    class ReachedDownloadPool(Exception):
        pass

    class Executor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, function, *args, **kwargs):
            assert function is daymet._retrieve_historical_timeseries_wrapper
            received.append(pickle.loads(pickle.dumps((args, kwargs)))[1]["admission"])
            raise ReachedDownloadPool

    monkeypatch.setattr(daymet, "createProcessPoolExecutor", lambda **_kwargs: Executor())
    with pytest.raises(ReachedDownloadPool):
        daymet.interpolate_daily_timeseries(
            {"ws": {"longitude": -116.0, "latitude": 46.0}}, 2001, 2001,
            output_dir=str(tmp_path), admission=config,
        )
    assert received == [config]
