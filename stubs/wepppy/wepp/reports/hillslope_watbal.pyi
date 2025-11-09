from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["HillslopeWatbalReport", "HillslopeWatbal"]


class HillslopeWatbalReport(ReportBase):
    header: list[str]
    years: list[int]
    areas: dict[int, float]
    wsarea: float
    units_d: dict[str, str]

    def __init__(self, wd: str | Path) -> None: ...

    @property
    def avg_annual_header(self) -> list[str]: ...

    @property
    def avg_annual_units(self) -> list[str | None]: ...

    @property
    def yearly_header(self) -> list[str]: ...

    @property
    def yearly_units(self) -> list[str | None]: ...

    def avg_annual_iter(self) -> Iterator[RowData]: ...

    def yearly_iter(self) -> Iterator[RowData]: ...


HillslopeWatbal = HillslopeWatbalReport
