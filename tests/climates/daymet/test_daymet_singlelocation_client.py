from __future__ import annotations

import datetime as _dt
from calendar import isleap
import sys
import types
from dataclasses import dataclass
from typing import Iterable

import importlib

import numpy as np
import pandas as pd
import pytest

module = sys.modules.get("wepppy")
if module is None or getattr(module, "__name__", "") != "wepppy" or not hasattr(module, "__path__"):
    sys.modules.pop("wepppy", None)
    importlib.import_module("wepppy")

climates_module = importlib.import_module("wepppy.climates")
sys.modules["wepppy"].climates = climates_module

if "pyproj" not in sys.modules:
    pyproj_module = types.ModuleType("pyproj")

    class _FakeProj:
        def __init__(self, *args, **kwargs):
            pass

    pyproj_module.Proj = _FakeProj
    pyproj_module.transform = lambda *args, **kwargs: (0.0, 0.0)
    sys.modules["pyproj"] = pyproj_module

sys.modules.setdefault("utm", types.ModuleType("utm"))
sys.modules.setdefault("geopandas", types.ModuleType("geopandas"))
if "deprecated" not in sys.modules:
    deprecated_module = types.ModuleType("deprecated")
    sys.modules["deprecated"] = deprecated_module
else:
    deprecated_module = sys.modules["deprecated"]

if not hasattr(deprecated_module, "deprecated"):
    def _noop_deprecated(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    deprecated_module.deprecated = _noop_deprecated
if "imageio" not in sys.modules:
    imageio_module = types.ModuleType("imageio")
    sys.modules["imageio"] = imageio_module
else:
    imageio_module = sys.modules["imageio"]

if not hasattr(imageio_module, "imread"):
    imageio_module.imread = lambda *args, **kwargs: None

if "whitebox_tools" not in sys.modules:
    whitebox_module = types.ModuleType("whitebox_tools")
    sys.modules["whitebox_tools"] = whitebox_module
else:
    whitebox_module = sys.modules["whitebox_tools"]

if not hasattr(whitebox_module, "WhiteboxTools"):
    class _WhiteboxTools:
        def __init__(self, *args, **kwargs):
            pass

    whitebox_module.WhiteboxTools = _WhiteboxTools

try:
    import shapely  # type: ignore  # noqa: F401
    from shapely import geometry as _shapely_geometry  # noqa: F401
except Exception:
    if "shapely" not in sys.modules:
        shapely_module = types.ModuleType("shapely")
        sys.modules["shapely"] = shapely_module

    if "shapely.geometry" not in sys.modules:
        geometry_module = types.ModuleType("shapely.geometry")

        class _FakePolygon:
            def __init__(self, *args, **kwargs):
                pass

        class _FakePoint:
            def __init__(self, *args, **kwargs):
                pass

            def within(self, *_args, **_kwargs):
                return False

        geometry_module.Polygon = _FakePolygon
        geometry_module.Point = _FakePoint
        sys.modules["shapely.geometry"] = geometry_module

if "rasterio" not in sys.modules:
    rasterio_module = types.ModuleType("rasterio")
    rasterio_module.__path__ = []

    class _Env:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    rasterio_module.Env = _Env
    sys.modules["rasterio"] = rasterio_module
    warp_module = types.ModuleType("rasterio.warp")
    warp_module.reproject = lambda *args, **kwargs: None
    warp_module.calculate_default_transform = lambda *args, **kwargs: (None, None, None)

    class _Resampling:
        nearest = 0

    warp_module.Resampling = _Resampling
    sys.modules["rasterio.warp"] = warp_module

if "rasterio.transform" not in sys.modules:
    transform_module = types.ModuleType("rasterio.transform")
    transform_module.from_origin = lambda *args, **kwargs: None
    transform_module.rowcol = lambda *args, **kwargs: (0, 0)
    sys.modules["rasterio.transform"] = transform_module

if "metpy" not in sys.modules:
    sys.modules["metpy"] = types.ModuleType("metpy")

if "metpy.calc" not in sys.modules:
    calc_module = types.ModuleType("metpy.calc")

    class _FakeDewPoint:
        def __init__(self, data):
            self.magnitude = np.asarray(data, dtype=float)

    def _fake_dewpoint(value):
        data = np.asarray(value, dtype=float)
        return _FakeDewPoint(data * 0.0)

    calc_module.dewpoint = _fake_dewpoint
    calc_module.dewpoint_from_relative_humidity = lambda *args, **kwargs: _FakeDewPoint(0.0)
    sys.modules["metpy.calc"] = calc_module

if "metpy.units" not in sys.modules:
    units_module = types.ModuleType("metpy.units")

    class _FakeUnits:
        Pa = 1.0

    units_module.units = _FakeUnits()
    sys.modules["metpy.units"] = units_module
if "flask" not in sys.modules:
    flask_module = types.ModuleType("flask")

    class _FakeFlask:
        def __init__(self, *args, **kwargs):
            pass

    flask_module.Flask = _FakeFlask
    flask_module.current_app = types.SimpleNamespace(config={})
    flask_module.g = types.SimpleNamespace()
    flask_module.request = types.SimpleNamespace(args={}, json=None)
    flask_module.Response = lambda *args, **kwargs: None
    flask_module.jsonify = lambda *args, **kwargs: None
    flask_module.make_response = lambda *args, **kwargs: None
    flask_module.render_template = lambda *args, **kwargs: ""
    flask_module.url_for = lambda *args, **kwargs: ""
    flask_module.Blueprint = _FakeFlask
    sys.modules["flask"] = flask_module
else:
    flask_module = sys.modules["flask"]

if "werkzeug" not in sys.modules:
    sys.modules["werkzeug"] = types.ModuleType("werkzeug")
if "werkzeug.exceptions" not in sys.modules:
    exceptions_module = types.ModuleType("werkzeug.exceptions")

    class _HTTPException(Exception):
        def __init__(self, code=None, description=None):
            super().__init__(description or "HTTPException")
            self.code = code
            self.description = description

    exceptions_module.HTTPException = _HTTPException
    sys.modules["werkzeug.exceptions"] = exceptions_module
else:
    exceptions_module = sys.modules["werkzeug.exceptions"]

if not hasattr(flask_module, "abort"):
    def _abort(status_code=None, description=None, **kwargs):
        raise exceptions_module.HTTPException(code=status_code, description=description)

    flask_module.abort = _abort
if "requests_toolbelt" not in sys.modules:
    requests_toolbelt_module = types.ModuleType("requests_toolbelt")
    requests_toolbelt_module.__path__ = []
    sys.modules["requests_toolbelt"] = requests_toolbelt_module
else:
    requests_toolbelt_module = sys.modules["requests_toolbelt"]

if "requests_toolbelt.multipart" not in sys.modules:
    multipart_module = types.ModuleType("requests_toolbelt.multipart")
    sys.modules["requests_toolbelt.multipart"] = multipart_module
else:
    multipart_module = sys.modules["requests_toolbelt.multipart"]

if "requests_toolbelt.multipart.encoder" not in sys.modules:
    encoder_module = types.ModuleType("requests_toolbelt.multipart.encoder")

    class _MultipartEncoder:
        def __init__(self, *args, **kwargs):
            pass

    encoder_module.MultipartEncoder = _MultipartEncoder
    sys.modules["requests_toolbelt.multipart.encoder"] = encoder_module
if "xarray" not in sys.modules:
    xarray_module = types.ModuleType("xarray")

    class _FakeDataset:
        def __init__(self, *args, **kwargs):
            self.dims = {}

        def close(self):
            pass

    xarray_module.Dataset = _FakeDataset
    xarray_module.open_dataset = lambda *args, **kwargs: _FakeDataset()
    sys.modules["xarray"] = xarray_module

if "wepppyo3" not in sys.modules:
    wepppyo3_module = types.ModuleType("wepppyo3")
    wepppyo3_module.__path__ = []
    sys.modules["wepppyo3"] = wepppyo3_module
else:
    wepppyo3_module = sys.modules["wepppyo3"]

if "wepppyo3.climate" not in sys.modules:
    climate_module = types.ModuleType("wepppyo3.climate")

    def _fake_interpolate_geospatial(*args, **kwargs):
        raise NotImplementedError

    climate_module.interpolate_geospatial = _fake_interpolate_geospatial
    climate_module.cli_revision = lambda *args, **kwargs: None

    def _climate_getattr(name):
        return lambda *args, **kwargs: None

    climate_module.__getattr__ = _climate_getattr
    sys.modules["wepppyo3.climate"] = climate_module
    wepppyo3_module.climate = climate_module

if "wepppyo3.raster_characteristics" not in sys.modules:
    raster_characteristics_module = types.ModuleType("wepppyo3.raster_characteristics")
    sys.modules["wepppyo3.raster_characteristics"] = raster_characteristics_module
else:
    raster_characteristics_module = sys.modules["wepppyo3.raster_characteristics"]

if not hasattr(raster_characteristics_module, "identify_mode_single_raster_key"):
    raster_characteristics_module.identify_mode_single_raster_key = lambda *args, **kwargs: None
if not hasattr(raster_characteristics_module, "identify_mode_intersecting_raster_keys"):
    raster_characteristics_module.identify_mode_intersecting_raster_keys = lambda *args, **kwargs: None
if not hasattr(raster_characteristics_module, "identify_median_single_raster_key"):
    raster_characteristics_module.identify_median_single_raster_key = lambda *args, **kwargs: None
if not hasattr(raster_characteristics_module, "identify_median_intersecting_raster_keys"):
    raster_characteristics_module.identify_median_intersecting_raster_keys = lambda *args, **kwargs: None

if "wepppyo3.wepp_viz" not in sys.modules:
    wepp_viz_module = types.ModuleType("wepppyo3.wepp_viz")
    sys.modules["wepppyo3.wepp_viz"] = wepp_viz_module
else:
    wepp_viz_module = sys.modules["wepppyo3.wepp_viz"]

if not hasattr(wepp_viz_module, "make_soil_loss_grid"):
    wepp_viz_module.make_soil_loss_grid = lambda *args, **kwargs: None
if not hasattr(wepp_viz_module, "make_soil_loss_grid_fps"):
    wepp_viz_module.make_soil_loss_grid_fps = lambda *args, **kwargs: None

if "wepp_runner" not in sys.modules:
    wepp_runner_module = types.ModuleType("wepp_runner")
    wepp_runner_module.__path__ = []
    sys.modules["wepp_runner"] = wepp_runner_module
else:
    wepp_runner_module = sys.modules["wepp_runner"]

if "wepp_runner.wepp_runner" not in sys.modules:
    wepp_runner_impl = types.ModuleType("wepp_runner.wepp_runner")
    sys.modules["wepp_runner.wepp_runner"] = wepp_runner_impl
else:
    wepp_runner_impl = sys.modules["wepp_runner.wepp_runner"]

if not hasattr(wepp_runner_impl, "make_hillslope_run"):
    wepp_runner_impl.make_hillslope_run = lambda *args, **kwargs: None

def _wepp_runner_getattr(name):
    return lambda *args, **kwargs: None

wepp_runner_impl.__getattr__ = _wepp_runner_getattr

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

    import importlib

    wepp_module = sys.modules.get("wepppy")
    if wepp_module is None or not hasattr(wepp_module, "climates"):
        climates_module = importlib.import_module("wepppy.climates")
        sys.modules["wepppy"].climates = climates_module

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
