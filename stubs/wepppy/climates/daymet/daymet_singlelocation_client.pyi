from __future__ import annotations

import logging
from typing import Mapping, MutableMapping, TypedDict

import numpy as np
import pandas as pd


class HillslopeLocation(TypedDict, total=False):
    latitude: float
    longitude: float
    easting: float
    northing: float


InterpolationSpec = Mapping[str, dict[str, float | str]]
RawDaymetCube = Mapping[str, np.ndarray]


def retrieve_historical_timeseries(
    lon: float,
    lat: float,
    start_year: int,
    end_year: int,
    fill_leap_years: bool = ...,
    gridmet_wind: bool = ...,
) -> pd.DataFrame: ...


def _retrieve_historical_timeseries_wrapper(
    lon: float,
    lat: float,
    start_year: int,
    end_year: int,
    fill_leap_years: bool = ...,
    gridmet_wind: bool = ...,
    attrs: tuple[int, int] | None = ...,
) -> tuple[tuple[int, int] | None, pd.DataFrame]: ...


def interpolate_daily_timeseries(
    hillslope_locations: MutableMapping[str, HillslopeLocation],
    start_year: int = ...,
    end_year: int = ...,
    output_dir: str = ...,
    output_type: str = ...,
    logger: logging.Logger | None = ...,
    max_workers: int = ...,
) -> None: ...


def interpolate_daily_timeseries_for_location(
    topaz_id: str,
    loc: HillslopeLocation,
    dates: pd.DatetimeIndex,
    eastings: np.ndarray,
    northings: np.ndarray,
    raw_data: RawDaymetCube,
    interpolation_spec: InterpolationSpec,
    output_dir: str,
    start_year: int,
    end_year: int,
    output_type: str = ...,
) -> str: ...
