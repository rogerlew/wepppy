from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .support import FlowpathSummary, ChannelSummary, HillSummary, CentroidSummary
from .wepp_top_translator import WeppTopTranslator

__all__ = [
    "transform_px_to_wgs",
    "weighted_slope_average_from_fps",
    "ChannelRoutingError",
    "WatershedAbstraction",
]

def transform_px_to_wgs(args): ...

def weighted_slope_average_from_fps(
    flowpaths,
    slopes,
    distances,
    max_points: int = ...,
): ...

class ChannelRoutingError(Exception): ...

class WatershedAbstraction:
    wd: str
    wat_dir: str
    translator: WeppTopTranslator

    def __init__(self, wd: str, wat_dir: str) -> None: ...
    @property
    def structure(self) -> List[List[int]]: ...
    @property
    def linkdata(self) -> Dict[int, Dict[str, List[int | float]]]: ...
    @property
    def network(self) -> Dict[int, List[int]]: ...
    @property
    def centroid(self) -> CentroidSummary: ...
    def abstract(
        self,
        wepp_chn_type: str = ...,
        verbose: bool = ...,
        warn: bool = ...,
        clip_hillslopes: bool = ...,
        clip_hillslope_length: float = ...,
    ) -> None: ...
    def write_slps(self, channels: int = ..., subcatchments: int = ..., flowpaths: int = ...) -> None: ...
    def abstract_channels(self, wepp_chn_type: str = ..., verbose: bool = ...) -> None: ...
    def abstract_subcatchments(
        self,
        verbose: bool = ...,
        warn: bool = ...,
        clip_hillslopes: bool = ...,
        clip_hillslope_length: float = ...,
    ) -> None: ...
    def abstract_flowpaths(
        self,
        sub_id: int,
        flowpaths: List[np.ndarray],
        slopes: List[np.ndarray],
        distances: List[np.ndarray],
    ) -> Tuple[Dict[str, FlowpathSummary], List[List[int]]]: ...
    def abstract_flowpath(
        self,
        flowpath: np.ndarray,
        slope: np.ndarray,
        distance: np.ndarray,
    ) -> FlowpathSummary: ...
    def abstract_structure(self, verbose: bool = ...) -> None: ...
