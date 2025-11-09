from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["ChannelSummaryReport", "ChannelSummary"]


class ChannelSummaryReport(ReportBase):
    header: list[str]
    _dataframe: pd.DataFrame

    def __init__(self, wd: str | Path | Any) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


ChannelSummary = ChannelSummaryReport
