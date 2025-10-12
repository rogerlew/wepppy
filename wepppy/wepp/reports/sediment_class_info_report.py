from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Sequence

import pandas as pd

from .report_base import ReportBase
from .row_data import RowData


class SedimentClassInfoReport(ReportBase):
    """Channel sediment particle class information (loss_pw0.class_data)."""

    def __init__(self, class_table: pd.DataFrame):
        self._frame = class_table.copy()
        self.header = [
            "Class",
            "Diameter (mm)",
            "Specific Gravity",
            "Sand (%)",
            "Silt (%)",
            "Clay (%)",
            "Organic Matter (%)",
        ]

    def __iter__(self) -> Iterable[RowData]:
        for _, row in self._frame.iterrows():
            data = OrderedDict()
            data["Class"] = int(row["class"])
            data["Diameter (mm)"] = float(row["diameter_mm"])
            data["Specific Gravity"] = float(row["specific_gravity"])
            data["Sand (%)"] = float(row["pct_sand"])
            data["Silt (%)"] = float(row["pct_silt"])
            data["Clay (%)"] = float(row["pct_clay"])
            data["Organic Matter (%)"] = float(row["pct_om"])
            yield RowData(data)


__all__: Sequence[str] = ["SedimentClassInfoReport"]
