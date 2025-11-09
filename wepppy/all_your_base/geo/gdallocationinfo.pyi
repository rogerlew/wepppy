from __future__ import annotations

from enum import Enum
from numbers import Real
from typing import Any, Optional, Sequence, Tuple, Union

import numpy as np
from osgeo import gdal, osr
from osgeo_utils.auxiliary.gdal_argparse import GDALArgumentParser, GDALScript
from osgeo_utils.auxiliary.osr_util import AnySRS, OAMS_AXIS_ORDER
from osgeo_utils.auxiliary.util import PathOrDS

CoordinateTransformationOrSRS = Optional[
    Union[osr.CoordinateTransformation, "LocationInfoSRS", AnySRS]
]

class LocationInfoSRS(Enum): ...

class LocationInfoOutput(Enum): ...

def gdallocationinfo(
    filename_or_ds: PathOrDS,
    x: Any,
    y: Any,
    srs: CoordinateTransformationOrSRS = ...,
    axis_order: Optional[OAMS_AXIS_ORDER] = ...,
    open_options: Optional[dict[str, Any]] = ...,
    ovr_idx: Optional[int] = ...,
    band_nums: Optional[Sequence[int]] = ...,
    inline_xy_replacement: bool = ...,
    return_ovr_pixel_line: bool = ...,
    transform_round_digits: Optional[float] = ...,
    allow_xy_outside_extent: bool = ...,
    pixel_offset: Real = ...,
    line_offset: Real = ...,
    resample_alg: int = ...,
    quiet_mode: bool = ...,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]: ...


def gdallocationinfo_util(
    filename_or_ds: PathOrDS,
    x: Any,
    y: Any,
    open_options: Optional[dict[str, Any]] = ...,
    band_nums: Optional[Sequence[int]] = ...,
    resample_alg: int = ...,
    output_mode: Optional[LocationInfoOutput] = ...,
    **kwargs: Any,
) -> np.ndarray: ...


def val_at_coord(
    filename: str,
    longitude: Real,
    latitude: Real,
    coordtype_georef: bool,
    print_xy: bool,
    print_values: bool,
) -> np.ndarray: ...


class GDALLocationInfo(GDALScript):
    title: str
    description: str
    interactive_mode: Optional[bool]

    def __init__(self) -> None: ...

    def get_parser(self, argv: Sequence[str]) -> GDALArgumentParser: ...

    def augment_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]: ...

    def doit(self, **kwargs: Any) -> Optional[np.ndarray]: ...


def main(argv: Sequence[str] = ...) -> int: ...
