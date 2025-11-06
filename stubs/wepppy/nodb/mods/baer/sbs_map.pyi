from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, Optional, Tuple, TypeAlias

import numpy as np
from numpy.typing import NDArray

from wepppy.landcover import LandcoverMap

RGBColor: TypeAlias = Tuple[int, int, int]
ColorIndexMap: TypeAlias = dict[Literal["unburned", "low", "mod", "high"], list[int]]
ColorCounts: TypeAlias = list[tuple[int, int]]
ColorLookup: TypeAlias = dict[RGBColor, Optional[str]]

__all__ = [
    "classify",
    "ct_classify",
    "get_sbs_color_table",
    "sbs_map_sanity_check",
    "SoilBurnSeverityMap",
]


def get_sbs_color_table(
    fn: str,
    color_to_severity_map: Optional[Mapping[RGBColor, str]] = ...,
) -> tuple[Optional[ColorIndexMap], ColorCounts, Optional[ColorLookup]]: ...


def classify(
    v: int | float,
    breaks: Sequence[int | float],
    nodata_vals: Optional[Sequence[int | float]] = ...,
    offset: int = ...,
) -> int: ...


def ct_classify(
    v: int | float,
    ct: Mapping[Literal["unburned", "low", "mod", "high"], Sequence[int]],
    offset: int = ...,
    nodata_vals: Optional[Sequence[int | float]] = ...,
) -> int: ...


def sbs_map_sanity_check(fname: str) -> tuple[int, str]: ...


class SoilBurnSeverityMap(LandcoverMap):
    ct: Optional[ColorIndexMap]
    is256: bool
    classes: list[int | float]
    counts: ColorCounts
    color_map: Optional[ColorLookup]
    breaks: Optional[Sequence[int | float]]
    fname: str
    nodata_vals: Sequence[int | float]

    def __init__(
        self,
        fname: str,
        breaks: Optional[Sequence[int | float]] = ...,
        nodata_vals: Optional[Sequence[int | float]] = ...,
        color_map: Optional[Mapping[RGBColor, str]] = ...,
        ignore_ct: bool = ...,
    ) -> None: ...

    @property
    def transform(self) -> tuple[float, float, float, float, float, float]: ...

    @property
    def proj(self) -> str: ...

    @property
    def burn_class_counts(self) -> dict[str, int]: ...

    @property
    def data(self) -> NDArray[np.uint8]: ...

    def export_wgs_map(self, fn: str) -> list[list[float]]: ...

    @property
    def class_map(self) -> list[tuple[int, str, int]]: ...

    @property
    def class_pixel_map(self) -> dict[str, str]: ...

    def export_rgb_map(self, wgs_fn: str, fn: str, rgb_png: str) -> None: ...

    def export_4class_map(self, fn: str, cellsize: Optional[float] = ...) -> None: ...
