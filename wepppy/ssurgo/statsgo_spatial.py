# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists

from wepppy.all_your_base import isint, isfloat, Extent

from shapely.geometry import Polygon, Point

import sqlite3
import io
import numpy as np

_thisdir = os.path.dirname(__file__)
_statsgo_spatial_db = _join(_thisdir, 'data', 'statsgo', 'statsgo_spatial.db')


def adapt_array(arr):
    """
    """
    # https://stackoverflow.com/a/18622264
    # http://stackoverflow.com/a/31312102/190597 (SoulNibbler)

    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


class StatsgoSpatial(object):
    def __init__(self):
        assert _exists(_statsgo_spatial_db)

        # Converts np.array to TEXT when inserting
        sqlite3.register_adapter(np.ndarray, adapt_array)

        # Converts TEXT to np.array when selecting
        sqlite3.register_converter("array", convert_array)

        self.conn = sqlite3.connect(_statsgo_spatial_db,
                                    detect_types=sqlite3.PARSE_DECLTYPES)
        self.cur = self.conn.cursor()

    @property
    def mukeys(self):

        cur = self.cur

        cur.execute('SELECT mukey FROM poly_bounds')

        results = cur.fetchall()
        if len(results) == 0:
            return None

        return sorted(r[0] for r in results)

    def identify_mukeys_extent(self, extent):
        xmin, ymin, xmax, ymax = extent

        assert isfloat(xmin)
        assert isfloat(xmax)
        assert isfloat(ymin)
        assert isfloat(ymax)

        assert float(xmin) < float(xmax)
        assert float(ymin) < float(ymax)

        cur = self.cur

        cur.execute('SELECT mukey FROM poly_bounds '
                    'WHERE (xmin <= {xmax} AND xmax >= {xmin}) AND '
                    '      (ymin <= {ymax} AND ymax >= {ymin})'
                    .format(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))

        results = cur.fetchall()
        if len(results) == 0:
            return None

        return sorted(r[0] for r in results)

    def build_mukey_polys(self, mukey):

        assert isint(mukey)

        cur = self.cur

        cur.execute('SELECT coords FROM mukey_polys '
                    'WHERE mukey = {mukey}'
                    .format(mukey=int(mukey)))

        coordss = cur.fetchall()

        polys = []
        for coords in coordss:
            polys.append(Polygon(coords[0]))
        return polys

    def identify_mukey_point(self, lng, lat):

        assert isfloat(lng)
        assert isfloat(lat)

        cur = self.cur
        cur.execute('SELECT mukey FROM poly_bounds '
                    'WHERE xmin < {lng} AND xmax > {lng} '
                    'AND ymin < {lat} AND ymax > {lat}'
                    .format(lng=float(lng), lat=float(lat)))
        mukeys = [t[0] for t in cur.fetchall()]

        point = Point(lng, lat)
        for mukey in mukeys:
            polys = self.build_mukey_polys(mukey)
            for poly in polys:
                if point.within(poly):
                    return mukey
