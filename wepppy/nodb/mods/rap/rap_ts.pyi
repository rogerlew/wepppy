from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterator, Optional, Tuple

from ...base import NoDbBase, TriggerEvents
from wepppy.landcover.rap import RAP_Band, RangelandAnalysisPlatformV3

from .rap import RAPPointData

__all__: list[str] = ["RAPNoDbLockedException", "RAP_TS"]

YearKey = int | str
TopazId = int | str
MofeId = int | str
SingleOFEValues = Dict[TopazId, float]
MultiOFEValues = Dict[TopazId, Dict[MofeId, float]]
BandYearSummary = Dict[YearKey, SingleOFEValues | MultiOFEValues]
RAPTimeSeriesData = Dict[RAP_Band, BandYearSummary]


class RAPNoDbLockedException(Exception):
    ...


class RAP_TS(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    data: Optional[RAPTimeSeriesData]
    _rap_start_year: Optional[int]
    _rap_end_year: Optional[int]
    _rap_mgr: Optional[RangelandAnalysisPlatformV3]

    def __new__(cls, *args: object, **kwargs: object) -> RAP_TS: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def __getstate__(self) -> Dict[str, Any]: ...

    @classmethod
    def _post_instance_loaded(cls, instance: RAP_TS) -> RAP_TS: ...

    @property
    def rap_end_year(self) -> Optional[int]: ...

    @rap_end_year.setter
    def rap_end_year(self, value: int) -> None: ...

    @property
    def rap_start_year(self) -> Optional[int]: ...

    @rap_start_year.setter
    def rap_start_year(self, value: int) -> None: ...

    @property
    def rap_dir(self) -> str: ...

    def acquire_rasters(
        self,
        start_year: Optional[int] = ...,
        end_year: Optional[int] = ...,
    ) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...

    def get_cover(
        self,
        topaz_id: TopazId,
        year: YearKey,
        fallback: bool = ...,
    ) -> float: ...

    def analyze(self, use_sbs: bool = ..., verbose: bool = ...) -> None: ...

    def __iter__(self) -> Iterator[Tuple[str, RAPPointData]]: ...

    def prep_cover(self, runs_dir: str, fallback: bool = ...) -> None: ...

    def _prep_transformed_cover(self, runs_dir: str) -> None: ...
