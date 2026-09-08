from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, Mapping, Optional, Sequence, Tuple

import pandas as pd

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.nodb.base import NoDbBase

from .ash import Ash

__all__ = ["AshPostNoDbLockedException", "AshPost"]

common_cols: list[str]
out_cols: list[str]
ASH_POST_FILES: Dict[str, str]
COLUMN_DESCRIPTIONS: Dict[str, str]
UINT16_COLUMNS: set[str]
UINT8_COLUMNS: set[str]
ReturnPeriodEntry = Dict[str, Any]
ReturnPeriods = Dict[int, ReturnPeriodEntry]
BurnClassReturnPeriods = Dict[int, Dict[str, ReturnPeriods]]


def _base_column_name(column: str) -> str: ...

def _infer_units(column: str) -> str | None: ...

def _describe_column(column: str) -> str | None: ...

def watershed_daily_aggregated(
    wd: str,
    recurrence: Sequence[int] = ...,
    verbose: bool = ..., 
) -> Optional[Tuple[ReturnPeriods, ReturnPeriods, BurnClassReturnPeriods]]: ...


class AshPostNoDbLockedException(Exception):
    ...


class AshPost(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    _js_decode_replacements: ClassVar[Tuple[Tuple[str, str], ...]]
    _return_periods: Optional[ReturnPeriods]
    _cum_return_periods: Optional[ReturnPeriods]
    _burn_class_return_periods: Optional[BurnClassReturnPeriods]

    def __init__(self, wd: str, cfg_fn: str, run_group: Optional[str] = ..., group_name: Optional[str] = ...) -> None: ...

    @property
    def return_periods(self) -> Optional[ReturnPeriods]: ...

    @property
    def burn_class_return_periods(self) -> Optional[BurnClassReturnPeriods]: ...

    @property
    def cum_return_periods(self) -> Optional[ReturnPeriods]: ...

    @property
    def pw0_stats(self) -> Dict[str, Dict[str, float]]: ...

    @property
    def recurrence_intervals(self) -> list[str]: ...

    def run_post(self, recurrence: Sequence[int] = ...) -> None: ...

    @property
    def meta(self) -> Mapping[str, Any]: ...

    @property
    def fire_date(self) -> YearlessDate: ...

    @property
    def ash_post_dir(self) -> str: ...

    @property
    def hillslope_annuals(self) -> Dict[str, Dict[str, Any]]: ...

    @property
    def watershed_annuals(self) -> Dict[str, Dict[str, Any]]: ...

    @property
    def ash_out(self) -> Dict[str, Dict[str, Any]]: ...
