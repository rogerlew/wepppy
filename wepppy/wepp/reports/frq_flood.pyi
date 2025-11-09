from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["FrqFloodReport", "FrqFlood"]


class FrqFloodReport(ReportBase):
    header: list[str]
    units_d: dict[str, str]
    has_phosphorus: bool
    years: int
    wsarea: float
    num_events: int

    def __init__(self, wd: str | Path, recurrence: Sequence[int] = ...) -> None: ...

    def __iter__(self) -> Iterator[RowData]: ...


FrqFlood = FrqFloodReport
