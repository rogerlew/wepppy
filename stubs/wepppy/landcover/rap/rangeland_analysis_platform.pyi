from __future__ import annotations

from enum import IntEnum
from typing import Any, Optional, Sequence, Union

import numpy as np

__all__ = [
    "RangelandAnalysisPlatform",
    "RangelandAnalysisPlatformV2",
    "RangelandAnalysisPlatformV3",
    "RAP_Band",
    "RangelandAnalysisPlatformDataset",
    "RangelandAnalysisPlatformV2Dataset",
    "RangelandAnalysisPlatformV3Dataset",
]

IS_WINDOWS: bool
DEFAULT_VERSION: str


class RangelandAnalysisPlatform:
    wd: str
    bbox: list[float] | None
    ds: dict[str, str]
    cellsize: int
    proj4: str | None
    version: str
    ul_x: float
    ul_y: float
    lr_x: float
    lr_y: float

    def __init__(
        self,
        wd: str = ...,
        bbox: Sequence[float] | None = ...,
        cellsize: int = ...,
        version: str = ...,
    ) -> None: ...
    def retrieve(self, years: Sequence[Union[int, str]]) -> int: ...
    def validate_raster(self, filename: str) -> bool: ...
    def get_dataset_fn(self, year: int | str) -> str: ...
    def get_dataset(self, year: int | str) -> "RangelandAnalysisPlatformDataset": ...
    def _attribution(self) -> None: ...


class RangelandAnalysisPlatformV2(RangelandAnalysisPlatform):
    def __init__(self, wd: str = ..., bbox: Sequence[float] | None = ..., cellsize: int = ...) -> None: ...


class RangelandAnalysisPlatformV3(RangelandAnalysisPlatform):
    def __init__(self, wd: str = ..., bbox: Sequence[float] | None = ..., cellsize: int = ...) -> None: ...


class RAP_Band(IntEnum):
    ANNUAL_FORB_AND_GRASS = 1
    BARE_GROUND = 2
    LITTER = 3
    PERENNIAL_FORB_AND_GRASS = 4
    SHRUB = 5
    TREE = 6
    ANNUAL_FORB_AND_GRASS_UNCERTAINTY = 7
    BARE_GROUND_UNCERTAINTY = 8
    LITTER_UNCERTAINTY = 9
    PERRENIAL_FORB_AND_GRASS_UNCERTAINTY = 10
    SHRUB_UNCERTAINTY = 11
    TREE_UNCERTAINTY = 12


class RangelandAnalysisPlatformDataset:
    ds: Any

    def __init__(self, fn: str) -> None: ...
    @property
    def shape(self) -> tuple[int, int]: ...
    def get_band(self, band: RAP_Band) -> np.ma.MaskedArray | None: ...
    def spatial_stats(self, band: RAP_Band, bound_fn: str) -> dict[str, object] | None: ...


RangelandAnalysisPlatformV2Dataset = RangelandAnalysisPlatformDataset
RangelandAnalysisPlatformV3Dataset = RangelandAnalysisPlatformDataset
