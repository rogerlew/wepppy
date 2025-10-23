from __future__ import annotations

from typing import ClassVar, Dict, Iterator, Optional, Tuple

from ...base import NoDbBase, TriggerEvents
from wepppy.landcover.rap import RAP_Band, RangelandAnalysisPlatformV3

__all__: list[str] = ["RAPNoDbLockedException", "RAPPointData", "RAP"]

BandValues = Dict[int | str, float]
BandSummary = Dict[RAP_Band, BandValues]


class RAPNoDbLockedException(Exception):
    ...


class RAPPointData:
    annual_forb_and_grass: Optional[float]
    bare_ground: Optional[float]
    litter: Optional[float]
    perennial_forb_and_grass: Optional[float]
    shrub: Optional[float]
    tree: Optional[float]

    def __init__(self, **kwds: Optional[float]) -> None: ...

    @property
    def total_cover(self) -> float: ...

    @property
    def annual_forb_and_grass_normalized(self) -> float: ...

    @property
    def bare_ground_normalized(self) -> float: ...

    @property
    def litter_normalized(self) -> float: ...

    @property
    def perennial_forb_and_grass_normalized(self) -> float: ...

    @property
    def shrub_normalized(self) -> float: ...

    @property
    def tree_normalized(self) -> float: ...

    @property
    def isvalid(self) -> bool: ...


class RAP(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]
    data: Optional[BandSummary]
    mofe_data: Optional[BandSummary]
    _rap_year: Optional[int]
    _rap_mgr: Optional[RangelandAnalysisPlatformV3]

    def __new__(cls, *args: object, **kwargs: object) -> RAP: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @classmethod
    def _post_instance_loaded(cls, instance: RAP) -> RAP: ...

    @property
    def rap_year(self) -> Optional[int]: ...

    @rap_year.setter
    def rap_year(self, value: int) -> None: ...

    @property
    def rap_dir(self) -> str: ...

    def acquire_rasters(self, year: int) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...

    def analyze(self) -> None: ...

    def get_cover(self, topaz_id: int | str) -> float: ...

    @property
    def report(self) -> Optional[Dict[str, Dict[str, float]]]: ...

    def __iter__(self) -> Iterator[Tuple[int | str, RAPPointData]]: ...
