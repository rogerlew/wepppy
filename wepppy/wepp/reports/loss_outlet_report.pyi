from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

__all__ = ["OutletSummaryReport", "OutletSummary"]


@dataclass(slots=True)
class OutletRow:
    label: str
    value: Optional[float]
    units: Optional[str]
    per_area_value: Optional[float]
    per_area_units: Optional[str]


class OutletSummaryReport:
    _rows: List[OutletRow]

    def __init__(self, wd: str | Path | Any) -> None: ...

    def rows(self, include_extraneous: bool = ...) -> List[OutletRow]: ...


OutletSummary = OutletSummaryReport
