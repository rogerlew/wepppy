from __future__ import annotations

from pathlib import Path
from typing import Union

from .sediment_channel_distribution_report import ChannelSedimentDistribution
from .sediment_class_info_report import SedimentClassInfoReport
from .sediment_hillslope_distribution_report import HillslopeSedimentDistribution

__all__ = ["SedimentCharacteristics"]


class SedimentCharacteristics:
    class_info_report: SedimentClassInfoReport
    channel: ChannelSedimentDistribution
    hillslope: HillslopeSedimentDistribution
    specific_surface_index: float
    enrichment_ratio_of_spec_surface: float

    def __init__(self, wd: Union[str, Path, object]) -> None: ...
