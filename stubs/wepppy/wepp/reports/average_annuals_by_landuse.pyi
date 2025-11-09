from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["AverageAnnualsByLanduseReport", "AverageAnnualsByLanduse"]


class AverageAnnualsByLanduseReport(ReportBase):
    header: list[str]

    def __init__(self, wd: str | Path) -> None: ...

    def _build_dataframe(self) -> pd.DataFrame: ...

    def _empty_dataframe(self) -> pd.DataFrame: ...

    def __iter__(self) -> Iterable[RowData]: ...


AverageAnnualsByLanduse = AverageAnnualsByLanduseReport
