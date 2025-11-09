from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["SedimentClassInfoReport"]


class SedimentClassInfoReport(ReportBase):
    def __init__(self, class_table: pd.DataFrame) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...
