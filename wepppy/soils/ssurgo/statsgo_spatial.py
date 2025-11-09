# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
from __future__ import annotations

"""Spatial lookup helpers for the coarse STATSGO2 soil grid."""

import io
import os
import sqlite3
from os.path import exists as _exists
from os.path import join as _join
from typing import List, Optional, Sequence

import numpy as np
from shapely.geometry import Point, Polygon

from wepppy.all_your_base import isfloat, isint

_thisdir = os.path.dirname(__file__)
_statsgo_spatial_db = _join(_thisdir, "data", "statsgo", "statsgo_spatial.db")


def adapt_array(arr: np.ndarray) -> sqlite3.Binary:
    """Serialize NumPy arrays for storage inside SQLite BLOB columns."""

    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text: bytes) -> np.ndarray:
    """Deserialize byte buffers produced by :func:`adapt_array`."""
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


class StatsgoSpatial:
    """Expose STATSGO2 mukey footprints for quick point/extent queries."""

    def __init__(self) -> None:
        assert _exists(_statsgo_spatial_db)

        sqlite3.register_adapter(np.ndarray, adapt_array)
        sqlite3.register_converter("array", convert_array)

        self.conn = sqlite3.connect(
            _statsgo_spatial_db, detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.cur = self.conn.cursor()

    @property
    def mukeys(self) -> Optional[List[int]]:
        """Return every mukey present in the STATSGO spatial index."""
        cur = self.cur

        cur.execute("SELECT mukey FROM poly_bounds")

        results = cur.fetchall()
        if len(results) == 0:
            return None

        return sorted(r[0] for r in results)

    def identify_mukeys_extent(self, extent: Sequence[float]) -> Optional[List[int]]:
        """Return mukeys whose bounding boxes intersect the supplied extent."""
        xmin, ymin, xmax, ymax = extent

        assert isfloat(xmin)
        assert isfloat(xmax)
        assert isfloat(ymin)
        assert isfloat(ymax)

        assert float(xmin) < float(xmax)
        assert float(ymin) < float(ymax)

        cur = self.cur

        cur.execute(
            "SELECT mukey FROM poly_bounds "
            "WHERE (xmin <= {xmax} AND xmax >= {xmin}) AND "
            "      (ymin <= {ymax} AND ymax >= {ymin})".format(
                xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
            )
        )

        results = cur.fetchall()
        if len(results) == 0:
            return None

        return sorted(r[0] for r in results)

    def build_mukey_polys(self, mukey: int) -> List[Polygon]:
        """Construct shapely polygons for the provided mukey."""
        assert isint(mukey)

        cur = self.cur

        cur.execute(
            "SELECT coords FROM mukey_polys " "WHERE mukey = {mukey}".format(
                mukey=int(mukey)
            )
        )

        coordss = cur.fetchall()

        polys = []
        for coords in coordss:
            polys.append(Polygon(coords[0]))
        return polys

    def identify_mukey_point(self, lng: float, lat: float) -> Optional[int]:
        """Return the mukey covering the supplied lon/lat point."""

        assert isfloat(lng)
        assert isfloat(lat)

        cur = self.cur
        cur.execute(
            "SELECT mukey FROM poly_bounds "
            "WHERE xmin < {lng} AND xmax > {lng} "
            "AND ymin < {lat} AND ymax > {lat}".format(lng=float(lng), lat=float(lat))
        )
        mukeys = [t[0] for t in cur.fetchall()]

        point = Point(lng, lat)
        for mukey in mukeys:
            polys = self.build_mukey_polys(mukey)
            for poly in polys:
                if point.within(poly):
                    return mukey
        return None
