from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["TotalWatbalReport", "TotalWatbal"]


class TotalWatbalReport(ReportBase):
    header: list[str]
    years: list[int]

    def __init__(
        self,
        wd: str | Path,
        exclude_yr_indxs: Iterable[int] | None = ...,
        *,
        dataframe: pd.DataFrame | None = ...,
    ) -> None: ...

    def _initialise_empty(self) -> None: ...

    def __iter__(self) -> Iterator[RowData]: ...

    @property
    def means(self) -> RowData: ...

    @property
    def stdevs(self) -> RowData: ...

    @property
    def pratios(self) -> RowData: ...


TotalWatbal = TotalWatbalReport
