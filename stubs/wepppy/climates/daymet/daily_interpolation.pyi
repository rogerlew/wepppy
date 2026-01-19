from __future__ import annotations

from typing import Any, DefaultDict, Literal, MutableMapping, TypedDict

import pandas as pd

AnySRS = Any
LocationInfoSRS = Any

class HillslopeLocation(TypedDict, total=False):
    latitude: float
    longitude: float
    pixel_q: float
    line_q: float


class ProcessedMeasure(TypedDict):
    year: int
    measure: str
    data: pd.Series


AggregatedData = DefaultDict[str, DefaultDict[str, dict[int, pd.Series]]]


def process_measure(
    year: int,
    measure: str,
    hillslope_locations: MutableMapping[str, HillslopeLocation],
    daymet_version: Literal['v3', 'v4'] = 'v4',
) -> dict[str, ProcessedMeasure]: ...


def interpolate_daily_timeseries(
    hillslope_locations: MutableMapping[str, HillslopeLocation],
    start_year: int = ...,
    end_year: int = ...,
    output_dir: str = ...,
    output_type: str = ...,
    status_channel: str | None = ...,
    max_workers: int = ...,
) -> None: ...


def identify_pixel_coords(
    hillslope_locations: MutableMapping[str, HillslopeLocation],
    srs: AnySRS | LocationInfoSRS | None = ...,
    daymet_version: Literal['v3', 'v4'] = ...,
) -> MutableMapping[str, HillslopeLocation]: ...
