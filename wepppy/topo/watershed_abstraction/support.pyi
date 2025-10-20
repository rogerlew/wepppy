from __future__ import annotations

from typing import Dict, Iterable, List, Tuple, Union

import numpy as np

__all__ = [
    "is_channel",
    "garbrecht_length",
    "cummnorm_distance",
    "representative_normalized_elevations",
    "read_geojson",
    "interpolate_slp",
    "write_slp",
    "identify_subflows",
    "weighted_slope_average",
    "compute_direction",
    "slp_asp_color",
    "rect_to_polar",
    "json_to_wgs",
    "polygonize_netful",
    "polygonize_bound",
    "polygonize_subcatchments",
    "identify_edge_hillslopes",
]

def is_channel(topaz_id: Union[int, str]) -> bool: ...

def garbrecht_length(distances: List[List[float]]) -> float: ...

def cummnorm_distance(distance: List[float]) -> np.ndarray: ...

def representative_normalized_elevations(x: List[float], dy: List[float]) -> List[float]: ...

def read_geojson(fname: str) -> Dict[str, np.ndarray]: ...

def interpolate_slp(distances: Iterable[float], slopes: Iterable[float], max_points: int) -> Tuple[np.ndarray, np.ndarray]: ...

def write_slp(
    aspect: float,
    width: float,
    cellsize: float,
    length: float,
    slope: Iterable[float],
    distance_p: Iterable[float],
    fp,
    version: float = ...,
    max_points: int = ...,
) -> None: ...

def identify_subflows(flowpaths: List[np.ndarray]) -> List[List[int]]: ...

def weighted_slope_average(
    areas: Iterable[float],
    slopes: Iterable[float],
    lengths: Iterable[float],
    max_points: int = ...,
) -> Tuple[List[float], List[float]]: ...

def compute_direction(head: List[float], tail: List[float]) -> float: ...

def slp_asp_color(slope: float, aspect: float) -> str: ...

def rect_to_polar(d: Dict[str, Tuple[float, float]]) -> float: ...

def json_to_wgs(src_fn: str, s_srs: str | None = ...) -> str: ...

def polygonize_netful(src_fn: str, dst_fn: str) -> None: ...

def polygonize_bound(bound_fn: str, dst_fn: str) -> None: ...

def polygonize_subcatchments(subwta_fn: str, dst_fn: str, dst_fn2: str | None = ...) -> None: ...

def identify_edge_hillslopes(raster_path: str, logger=None): ...
