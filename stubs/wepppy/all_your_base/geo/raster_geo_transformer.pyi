from __future__ import annotations

from typing import Tuple, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__: list[str]


class UtmGeoTransformer:
    raster_fn: str
    transform: tuple[float, ...]
    num_cols: int
    num_rows: int
    cellsize: float
    ul_x: int
    ul_y: int
    lr_x: float
    lr_y: float
    ll_x: int
    ll_y: int
    dtype: str
    datum: str
    hemisphere: str
    northern: bool
    utm_zone: int
    epsg: str
    srs_proj4: str
    extent: tuple[float, float, float, float]
    srs_wkt: str
    min_value: float
    max_value: float

    def __init__(self, raster_fn: str) -> None: ...
    def utm_to_px(
        self,
        easting: Union[float, ArrayLike],
        northing: Union[float, ArrayLike],
    ) -> Tuple[Union[int, NDArray[np.int_]], Union[int, NDArray[np.int_]]]: ...
    def lnglat_to_px(self, lng: float, lat: float) -> Tuple[int, int]: ...
    def px_to_utm(self, x: int, y: int) -> Tuple[float, float]: ...
    def lnglat_to_utm(self, lng: float, lat: float) -> Tuple[float, float]: ...
    def px_to_lnglat(self, x: int, y: int) -> Tuple[float, float]: ...
