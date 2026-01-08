from __future__ import annotations

from collections.abc import Sequence
from typing import Tuple

__all__ = [
    "build_windowed_vrt",
    "build_windowed_vrt_from_window",
    "calculate_src_window",
]


def calculate_src_window(
    src_path: str,
    bbox: Sequence[float],
    bbox_crs: str,
    pad_px: int = ...,
) -> Tuple[int, int, int, int]: ...


def build_windowed_vrt(
    src_path: str,
    dst_path: str,
    bbox: Sequence[float],
    bbox_crs: str,
    pad_px: int = ...,
) -> Tuple[int, int, int, int]: ...


def build_windowed_vrt_from_window(
    src_path: str,
    dst_path: str,
    src_window: Sequence[int],
    *,
    reference_geotransform: Sequence[float] | None = ...,
    reference_shape: Sequence[int] | None = ...,
) -> Tuple[int, int, int, int]: ...
