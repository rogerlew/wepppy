from __future__ import annotations

from typing import ClassVar, Dict, KeysView, Optional

from ...base import NoDbBase

__all__: list[str] = ["DebrisFlowNoDbLockedException", "DebrisFlow"]

DurationList = list[str]
RecurrenceList = list[float]
FloatMatrix = list[list[float]]
PrecipTable = Dict[str, FloatMatrix]
DurationTable = Dict[str, DurationList]
RecurrenceTable = Dict[str, RecurrenceList]
ResultTable = Dict[str, FloatMatrix]


def _duration_in_hours(duration: str) -> float: ...


class DebrisFlowNoDbLockedException(Exception):
    ...


class DebrisFlow(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    I: Optional[PrecipTable]
    T: Optional[PrecipTable]
    durations: Optional[DurationTable]
    rec_intervals: Optional[RecurrenceTable]
    volume: Optional[ResultTable]
    prob_occurrence: Optional[ResultTable]
    _datasource: Optional[str]

    A: Optional[float]
    B: Optional[float]
    A_pct: Optional[float]
    B_pct: Optional[float]
    C: Optional[float]
    LL: Optional[float]
    R: Optional[float]
    wsarea: Optional[float]

    def __new__(cls, *args: object, **kwargs: object) -> DebrisFlow: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def fetch_precip_data(self) -> None: ...

    @property
    def datasource(self) -> str: ...

    @property
    def datasources(self) -> Optional[KeysView[str]]: ...

    def run_debris_flow(
        self,
        cc: Optional[float | str] = ...,
        ll: Optional[float | str] = ...,
        req_datasource: Optional[str] = ...,
    ) -> None: ...
