from __future__ import annotations

from typing import ClassVar, Dict, Iterator, Optional, Tuple

from ...base import NoDbBase, TriggerEvents

from .shrubland_map import ShrublandMap

__all__: list[str] = [
    "ShrublandNoDbLockedException",
    "nlcd_shrubland_layers",
    "ShrublandPointData",
    "Shrubland",
]

ShrublandDataset = str
ShrublandLayerSummary = Dict[ShrublandDataset, float]
ShrublandData = Dict[int | str, ShrublandLayerSummary]
ShrublandReport = Dict[ShrublandDataset, Dict[str, float]]

nlcd_shrubland_layers: Tuple[ShrublandDataset, ...]


class ShrublandNoDbLockedException(Exception):
    ...


class ShrublandPointData:
    annual_herb: Optional[float]
    bare_ground: Optional[float]
    big_sagebrush: Optional[float]
    sagebrush: Optional[float]
    herbaceous: Optional[float]
    sagebrush_height: Optional[float]
    litter: Optional[float]
    shrub: Optional[float]
    shrub_height: Optional[float]

    def __init__(self, **kwds: Optional[float]) -> None: ...

    @property
    def total_cover(self) -> float: ...

    @property
    def annual_herb_normalized(self) -> float: ...

    @property
    def bare_ground_normalized(self) -> float: ...

    @property
    def big_sagebrush_normalized(self) -> float: ...

    @property
    def sagebrush_normalized(self) -> float: ...

    @property
    def herbaceous_normalized(self) -> float: ...

    @property
    def litter_normalized(self) -> float: ...

    @property
    def shrub_normalized(self) -> float: ...

    @property
    def isvalid(self) -> bool: ...


class Shrubland(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    data: Optional[ShrublandData]

    def __new__(cls, *args: object, **kwargs: object) -> Shrubland: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def shrubland_dir(self) -> str: ...

    def acquire_rasters(self) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...

    def load_shrub_map(self, ds: ShrublandDataset) -> ShrublandMap: ...

    def analyze(self) -> None: ...

    @property
    def report(self) -> Optional[ShrublandReport]: ...

    def __iter__(self) -> Iterator[Tuple[int | str, ShrublandPointData]]: ...
