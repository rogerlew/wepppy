from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd

from wepppy.wepp.stats.report_base import ReportBase
from wepppy.wepp.stats.row_data import RowData


class ChannelClassFractionReport(ReportBase):
    """Distribution of outlet sediment discharge by particle class."""

    def __init__(self, rows: Iterable[OrderedDict[str, float]]):
        self._rows = list(rows)
        self.header = ["Class", "Fraction (ratio)", "Sediment Discharge (tonne/yr)"]

    def __iter__(self) -> Iterable[RowData]:
        for row in self._rows:
            yield RowData(row)


class ChannelParticleDistributionReport(ReportBase):
    """Distribution of outlet sediment discharge by particle type."""

    def __init__(self, rows: Iterable[OrderedDict[str, float]]):
        self._rows = list(rows)
        self.header = ["Particle Type", "Fraction (ratio)", "Sediment Discharge (tonne/yr)"]

    def __iter__(self) -> Iterable[RowData]:
        for row in self._rows:
            yield RowData(row)


@dataclass(slots=True)
class ChannelSedimentDistribution:
    total_discharge_tonne: float
    class_fraction_report: ChannelClassFractionReport
    particle_distribution_report: ChannelParticleDistributionReport


__all__: Sequence[str] = [
    "ChannelClassFractionReport",
    "ChannelParticleDistributionReport",
    "ChannelSedimentDistribution",
]
