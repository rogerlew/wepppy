"""Convenience wrappers around the OpenET monthly time-series API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
import json
import os
from pathlib import Path
from typing import Any, Final, TypeAlias

from os.path import exists as _exists
from os.path import join as _join

import numpy as np
import requests

_THISDIR = Path(__file__).resolve().parent
_API_ENV_PATH = _THISDIR / ".env"
_API_KEY: str | None = os.getenv("OPENET_API_KEY")
if _API_KEY is None and _API_ENV_PATH.exists():
    _API_KEY = _API_ENV_PATH.read_text(encoding="utf-8").strip()

_OPENET_POINT_URL: Final[str] = "https://openet-api.org/raster/timeseries/point"
_OPENET_POLYGON_URL: Final[str] = "https://openet-api.org/raster/timeseries/polygon"

PolygonCoordinates: TypeAlias = Sequence[Sequence[Sequence[float]]]

__all__ = [
    "fetch_monthly_multipolygon_timeseries",
    "fetch_monthly_point_timeseries",
    "fetch_monthly_polygon_timeseries",
]


def _get_header() -> dict[str, str]:
    """Return the Authorization header, raising if the API key is missing."""
    if not _API_KEY:
        raise RuntimeError(
            "OpenET API key is not configured. Set OPENET_API_KEY or provide "
            "wepppy/locales/conus/openet/.env."
        )
    return {"Authorization": _API_KEY}


def fetch_monthly_point_timeseries(
    lon: float,
    lat: float,
    start_date: date,
    end_date: date,
    variable: str = "ET",
) -> dict[str, Any]:
    """Request a monthly OpenET time series at a single coordinate.

    Args:
        lon: Longitude in decimal degrees (EPSG:4326).
        lat: Latitude in decimal degrees (EPSG:4326).
        start_date: Inclusive start of the requested date range.
        end_date: Inclusive end of the requested date range.
        variable: OpenET variable identifier (default ``"ET"``).

    Returns:
        Parsed JSON payload from OpenET describing the requested time series.
    Raises:
        RuntimeError: If the OpenET API key has not been configured.
    """
    payload = {
        "date_range": [
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        ],
        "interval": "monthly",
        "geometry": [lon, lat],
        "model": "Ensemble",
        "variable": variable,
        "reference_et": "gridMET",
        "units": "mm",
        "file_format": "JSON",
    }

    resp = requests.post(
        headers=_get_header(),
        json=payload,
        url=_OPENET_POINT_URL,
        timeout=60,
    )
    if resp.status_code != 200:
        print(resp.text)

    return resp.json()


def fetch_monthly_polygon_timeseries(
    coordinates: PolygonCoordinates,
    start_date: date,
    end_date: date,
    variable: str = "ET",
) -> dict[str, Any]:
    """Request a monthly OpenET time series aggregated across a polygon.

    Args:
        coordinates: GeoJSON-style list-of-rings for the polygon.
        start_date: Inclusive start of the requested date range.
        end_date: Inclusive end of the requested date range.
        variable: OpenET variable identifier (default ``"ET"``).

    Returns:
        Parsed JSON payload from OpenET describing the requested time series.
    Raises:
        RuntimeError: If the OpenET API key has not been configured.
    """
    geometry = np.array(coordinates).flatten().tolist()

    payload = {
        "date_range": [
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        ],
        "interval": "monthly",
        "geometry": geometry,
        "model": "Ensemble",
        "reducer": "mean",
        "variable": variable,
        "reference_et": "gridMET",
        "units": "mm",
        "file_format": "JSON",
    }

    resp = requests.post(
        headers=_get_header(),
        json=payload,
        url=_OPENET_POLYGON_URL,
        timeout=60,
    )
    if resp.status_code != 200:
        print(resp.text)

    return resp.json()


def fetch_monthly_multipolygon_timeseries(
    geojson_fn: str,
    start_date: date,
    end_date: date,
    variable: str = "ET",
    properties_key: str = "TopazID",
    outdir: str = "./",
) -> dict[str, Any]:
    """Batch OpenET requests for every feature in the supplied GeoJSON file.

    Args:
        geojson_fn: Path to a GeoJSON FeatureCollection containing polygon or
            multipolygon geometries.
        start_date: Inclusive start of the requested date range.
        end_date: Inclusive end of the requested date range.
        variable: OpenET variable identifier (default ``"ET"``).
        properties_key: Name of the feature property used to label outputs.
        outdir: Directory where individual JSON payloads and the aggregate
            ``openet.json`` file will be written.

    Returns:
        Dictionary keyed by the requested property whose values mirror the API
        responses written to disk.
    Raises:
        RuntimeError: If the OpenET API key has not been configured.
    """
    with open(geojson_fn, encoding="utf-8") as fp:
        geojson = json.load(fp)

    features: Sequence[Mapping[str, Any]] = geojson["features"]
    results: dict[str, Any] = {}
    for feature in features:
        properties = feature["properties"]
        feature_id = str(properties[properties_key])
        out_fn = _join(outdir, f"openet-{feature_id}.json")
        if _exists(out_fn):
            print(f"Skipping {feature_id}")
            continue

        coordinates = feature["geometry"]["coordinates"]
        try:
            result = fetch_monthly_polygon_timeseries(
                coordinates, start_date, end_date, variable
            )
            results[feature_id] = result

            with open(out_fn, "w", encoding="utf-8") as fp:
                json.dump(result, fp)
        except Exception as exc:  # pragma: no cover - API/network errors
            print(f"Error fetching {feature_id}: {exc}")

    with open(_join(outdir, "openet.json"), "w", encoding="utf-8") as fp:
        json.dump(results, fp)

    return results


def _test_fetch_monthly_point_timeseries() -> None:
    """Manual smoke test that prints a point-level response."""
    js = fetch_monthly_point_timeseries(
        lon=-117.0,
        lat=47.0,
        start_date=date(2019, 1, 1),
        end_date=date(2024, 6, 30),
        variable="ET",
    )
    print(js)


def _test_fetch_monthly_polygon_timeseries() -> None:
    """Manual smoke test that prints a polygon response."""
    coordinates = [
        [
            [-105.80453420153871, 33.49700722498243],
            [-105.80453169877966, 33.49673666204813],
            [-105.8042087640977, 33.496738758489066],
            [-105.80421126585242, 33.497009321444764],
            [-105.80453420153871, 33.49700722498243],
        ]
    ]
    js = fetch_monthly_polygon_timeseries(
        coordinates=coordinates,
        start_date=date(2019, 1, 1),
        end_date=date(2023, 12, 21),
        variable="ET",
    )
    print(js)


def _test_fetch_monthly_multipolygon_timeseries() -> None:
    """Manual smoke test that prints a multipolygon response."""
    js = fetch_monthly_multipolygon_timeseries(
        geojson_fn="/geodata/weppcloud_runs/mdobre-anadromous-cartridge/dem/topaz/SUBCATCHMENTS.WGS.JSON",
        start_date=date(2019, 1, 1),
        end_date=date(2023, 12, 21),
        variable="ET",
        properties_key="TopazID",
        outdir="/geodata/weppcloud_runs/mdobre-anadromous-cartridge/openet",
    )
    print(js)


if __name__ == "__main__":
    # _test_fetch_monthly_point_timeseries()
    # _test_fetch_monthly_polygon_timeseries()
    _test_fetch_monthly_multipolygon_timeseries()


def _test_fetch_monthly_point_timeseries():
    js = fetch_monthly_point_timeseries(lon=-117.0, lat=47.0, start_date=date(2019,1,1), end_date=date(2024,6,30), variable='ET')
    print(js)


def _test_fetch_monthly_polygon_timeseries():
    coordinates = [
          [
            [
              -105.80453420153871,
              33.49700722498243
            ],
            [
              -105.80453169877966,
              33.49673666204813
            ],
            [
              -105.8042087640977,
              33.496738758489066
            ],
            [
              -105.80421126585242,
              33.497009321444764
            ],
            [
              -105.80453420153871,
              33.49700722498243
            ]
          ]
        ]
    js = fetch_monthly_polygon_timeseries(coordinates=coordinates, start_date=date(2019,1,1), end_date=date(2023,12,21), variable='ET')
    print(js)


def _test_fetch_monthly_multipolygon_timeseries():
    js = fetch_monthly_multipolygon_timeseries(geojson_fn='/geodata/weppcloud_runs/mdobre-anadromous-cartridge/dem/topaz/SUBCATCHMENTS.WGS.JSON', start_date=date(2019,1,1), end_date=date(2023,12,21), variable='ET', properties_key='TopazID', outdir='/geodata/weppcloud_runs/mdobre-anadromous-cartridge/openet')
    print(js)


if __name__ == "__main__":
    #_test_fetch_monthly_point_timeseries()
    #_test_fetch_monthly_polygon_timeseries()
    _test_fetch_monthly_multipolygon_timeseries()
