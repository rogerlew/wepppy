from __future__ import annotations

import sqlite3
from typing import List, Optional, Sequence

import numpy as np
from shapely.geometry import Polygon


def adapt_array(arr: np.ndarray) -> sqlite3.Binary: ...


def convert_array(text: bytes) -> np.ndarray: ...


class StatsgoSpatial:
    conn: sqlite3.Connection
    cur: sqlite3.Cursor

    def __init__(self) -> None: ...
    @property
    def mukeys(self) -> Optional[List[int]]: ...
    def identify_mukeys_extent(self, extent: Sequence[float]) -> Optional[List[int]]: ...
    def build_mukey_polys(self, mukey: int) -> List[Polygon]: ...
    def identify_mukey_point(self, lng: float, lat: float) -> Optional[int]: ...
