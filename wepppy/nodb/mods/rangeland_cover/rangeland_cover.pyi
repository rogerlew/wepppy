from __future__ import annotations

from enum import IntEnum
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional

from ...base import NoDbBase, TriggerEvents

__all__: list[str] = ...

CoverValues = Dict[str, float]
CoverMap = Dict[int | str, CoverValues]


def gen_cover_color(cover: Mapping[str, float]) -> str: ...


class RangelandCoverNoDbLockedException(Exception):
    ...


class RangelandCoverMode(IntEnum):
    Undefined = ...
    Gridded = ...
    Single = ...
    GriddedRAP = ...


class RangelandCover(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]
    covers: Optional[CoverMap]

    def __new__(cls, *args: Any, **kwargs: Any) -> RangelandCover: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...

    @property
    def rap_year(self) -> int: ...

    @rap_year.setter
    def rap_year(self, value: int) -> None: ...

    @property
    def mode(self) -> RangelandCoverMode: ...

    @mode.setter
    def mode(self, value: RangelandCoverMode | int) -> None: ...

    @property
    def bunchgrass_cover_default(self) -> float: ...

    @bunchgrass_cover_default.setter
    def bunchgrass_cover_default(self, value: float) -> None: ...

    @property
    def forbs_cover_default(self) -> float: ...

    @forbs_cover_default.setter
    def forbs_cover_default(self, value: float) -> None: ...

    @property
    def sodgrass_cover_default(self) -> float: ...

    @sodgrass_cover_default.setter
    def sodgrass_cover_default(self, value: float) -> None: ...

    @property
    def shrub_cover_default(self) -> float: ...

    @shrub_cover_default.setter
    def shrub_cover_default(self, value: float) -> None: ...

    @property
    def basal_cover_default(self) -> float: ...

    @basal_cover_default.setter
    def basal_cover_default(self, value: float) -> None: ...

    @property
    def rock_cover_default(self) -> float: ...

    @rock_cover_default.setter
    def rock_cover_default(self, value: float) -> None: ...

    @property
    def litter_cover_default(self) -> float: ...

    @litter_cover_default.setter
    def litter_cover_default(self, value: float) -> None: ...

    @property
    def cryptogams_cover_default(self) -> float: ...

    @cryptogams_cover_default.setter
    def cryptogams_cover_default(self, value: float) -> None: ...

    def set_default_covers(self, default_covers: Mapping[str, float]) -> None: ...

    def build(
        self,
        rap_year: Optional[int] = ...,
        default_covers: Optional[Mapping[str, float]] = ...,
    ) -> None: ...

    def _build_single(self) -> None: ...

    @property
    def rap_report(self) -> Any: ...

    def _build_gridded_rap(self, rap_year: Optional[int] = ...) -> None: ...

    @property
    def usgs_shrubland_report(self) -> Any: ...

    def _build_gridded_usgs_shrubland(self) -> None: ...

    @property
    def has_covers(self) -> bool: ...

    def current_cover_summary(self, topaz_ids: Iterable[int | str]) -> Dict[str, str]: ...

    def modify_covers(
        self,
        topaz_ids: Iterable[int | str],
        new_cover: Mapping[str, float],
    ) -> None: ...

    @property
    def subs_summary(self) -> Dict[int | str, Dict[str, float | str]]: ...
