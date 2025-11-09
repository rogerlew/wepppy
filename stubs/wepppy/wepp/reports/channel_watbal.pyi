from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["ChannelWatbalReport", "ChannelWatbal"]


class ChannelWatbalReport(ReportBase):
    header: list[str]

    def __init__(self, wd: str | Path) -> None: ...

    @property
    def header(self) -> list[str]: ...

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


ChannelWatbal = ChannelWatbalReport
