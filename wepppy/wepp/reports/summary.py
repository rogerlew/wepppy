from __future__ import annotations

from .loss_channel_report import ChannelSummaryReport
from .loss_hill_report import HillSummaryReport
from .loss_outlet_report import OutletSummaryReport

__all__ = [
    "HillSummaryReport",
    "ChannelSummaryReport",
    "OutletSummaryReport",
    "HillSummary",
    "ChannelSummary",
    "OutletSummary",
]

HillSummary = HillSummaryReport
ChannelSummary = ChannelSummaryReport
OutletSummary = OutletSummaryReport
