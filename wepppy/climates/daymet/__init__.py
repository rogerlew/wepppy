"""Public entry points for the Daymet climate helpers."""

from __future__ import annotations

from .daymet_singlelocation_client import retrieve_historical_timeseries
from .fast_single_point import single_point_extraction

__all__ = [
    'daymet_proj4',
    'retrieve_historical_timeseries',
    'single_point_extraction',
]

daymet_proj4: str = (
    '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 '
    '+ellps=WGS84 +units=m +no_defs'
)
