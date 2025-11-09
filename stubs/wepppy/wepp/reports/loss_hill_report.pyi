from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["HillSummaryReport", "HillSummary"]


class HillSummaryReport(ReportBase):
    header: list[str]
    _dataframe: pd.DataFrame

    def __init__(
        self,
        wd: str | Path | Any,
        *,
        fraction_under: float | None = ...,
        **_unused_kwargs: Any,
    ) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


HillSummary = HillSummaryReport
