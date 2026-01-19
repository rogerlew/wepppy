from __future__ import annotations

from datetime import date
from typing import Any, TypeAlias

from collections.abc import Sequence

__all__ = [
    "fetch_monthly_multipolygon_timeseries",
    "fetch_monthly_point_timeseries",
    "fetch_monthly_polygon_timeseries",
]

PolygonCoordinates: TypeAlias = Sequence[Sequence[Sequence[float]]]

def fetch_monthly_point_timeseries(
    lon: float,
    lat: float,
    start_date: date,
    end_date: date,
    variable: str = ...,
) -> dict[str, Any]: ...

def fetch_monthly_polygon_timeseries(
    coordinates: PolygonCoordinates,
    start_date: date,
    end_date: date,
    variable: str = ...,
) -> dict[str, Any]: ...

def fetch_monthly_multipolygon_timeseries(
    geojson_fn: str,
    start_date: date,
    end_date: date,
    variable: str = ...,
    properties_key: str = ...,
    outdir: str = ...,
) -> dict[str, Any]: ...
