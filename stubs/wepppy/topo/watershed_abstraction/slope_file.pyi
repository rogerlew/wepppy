from __future__ import annotations

from typing import Iterable

import numpy as np

__all__ = [
    "clip_slope_file_length",
    "mofe_distance_fractions",
    "SlopeFile",
]

def clip_slope_file_length(src_fn: str, dst_fn: str, clip_length: float) -> None: ...

def mofe_distance_fractions(fname: str) -> np.ndarray: ...

class SlopeFile:
    fname: str
    length: float
    resolution: float
    nSegments: int
    distances: np.ndarray
    slopes: np.ndarray
    azm: float
    fwidth: float
    relative_elevs: np.ndarray

    def __init__(self, fname: str, z0: float = ...) -> None: ...
    def interp_slope(self, weights: Iterable[float]) -> np.ndarray: ...
    def slope_of_segment(self, d0: float = ..., dend: float = ...) -> float: ...
    @property
    def slope_scalar(self) -> float: ...
    def segmented_multiple_ofe(
        self,
        dst_fn: str | None = ...,
        target_length: float = ...,
        apply_buffer: bool = ...,
        buffer_length: float = ...,
        min_length: float = ...,
        max_ofes: int = ...,
    ) -> int: ...
