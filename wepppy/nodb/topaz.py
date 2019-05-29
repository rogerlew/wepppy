# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists

import math
import jsonpickle
import utm

import numpy as np
import numpy.ma as ma

from wepppy.topaz import TopazRunner
from wepppy.all_your_base import read_arc, utm_srid

from .base import NoDbBase


class Outlet(object):
    def __init__(self,
                 requested_loc,
                 actual_loc,
                 distance_from_requested,
                 pixel_coords):
        self.requested_loc = requested_loc
        self.actual_loc = actual_loc
        self.distance_from_requested = distance_from_requested
        self.pixel_coords = pixel_coords
        
    def as_dict(self):
        return dict(lng=self.actual_loc[0], 
                    lat=self.actual_loc[1])


class TopazNoDbLockedException(Exception):
    pass


class Topaz(NoDbBase):
    __name__ = 'Topaz'

    def __init__(self, wd, cfg_fn):
        super(Topaz, self).__init__(wd, cfg_fn)

        self.lock()

        config = self.config

        # noinspection PyBroadException
        try:
            self.csa = config.getfloat('topaz', 'csa')
            self.mcl = config.getfloat('topaz', 'mcl')
            self.zoom_min = config.getint('topaz', 'zoom_min')

            self._outlet = None
            
            self._utmproj4 = None
            self._utmextent = None

            self.cellsize = None
            self.num_cols = None
            self.num_rows = None

            self.wsarea = None
            self.area_gt30 = None
            self.ruggedness = None
            self.minz = None
            self.maxz = None

            topaz_wd = self.topaz_wd
            if not _exists(topaz_wd):
                os.mkdir(topaz_wd)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'topaz.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Topaz)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'topaz.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'topaz.nodb.lock')

    @property
    def topaz_pass(self):
        if _exists(self.subwta_arc):
            return 2

        if _exists(self.netful_arc):
            return 1

        return 0

    @property
    def utmproj4(self):
        return self._utmproj4

    @property
    def utmzone(self):
        assert 'utm' in self._utmproj4
        return int([tok for tok in self._utmproj4.split() if tok.startswith('+zone=')][0].replace('+zone=', ''))

    @property
    def srid(self):
        return utm_srid(self.utmzone)

    @property
    def utmextent(self):
        return self._utmextent

    def longlat_to_pixel(self, long, lat):
        """
        return the x,y pixel coords of long, lat
        """

        ul_x, lr_y, lr_x, ul_y,  = self.utmextent

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows

        # find easting and northing
        x, y, _, _ = utm.from_latlon(lat, long, self.utmzone)

        # assert this makes sense with the stored extent
        assert round(x) >= round(ul_x), (x, ul_x)
        assert round(x) <= round(lr_x), (x, lr_x)
        assert round(y) >= round(lr_y), (y, lr_y)
        assert round(y) <= round(ul_y), (y, ul_y)

        # determine pixel coords
        _x = int(round((x - ul_x) / cellsize))
        _y = int(round((ul_y - y) / cellsize))

        # sanity check on the coords
        assert 0 <= _x < num_cols, str(x)
        assert 0 <= _y < num_rows, str(y)

        return _x, _y

    def sub_intersection(self, extent):
        assert extent[0] < extent[2]
        assert extent[1] < extent[3]

        x0, y0 = self.longlat_to_pixel(extent[0], extent[3])
        xend, yend = self.longlat_to_pixel(extent[2], extent[1])

        assert x0 < xend
        assert y0 < yend

        data, transform, proj = read_arc(self.subwta_arc)
        topaz_ids = set(data[x0:xend, y0:yend].flatten())
        topaz_ids.discard(0)
        return sorted(topaz_ids)

    #
    # channels
    #
    @property
    def has_channels(self):
        return _exists(self.netful_arc)

    def build_channels(self, csa=4, mcl=60):
        self.lock()

        # noinspection PyBroadException
        try:
            top_runner = TopazRunner(self.topaz_wd, self.dem_fn,
                                     csa=csa, mcl=mcl)

            top_runner.build_channels()
            assert self.has_channels

            self.csa = csa
            self.mcl = mcl    

            data, transform, proj = read_arc(self.netful_arc)
            n, m = data.shape

            self.num_cols = n
            self.num_rows = m
            self.cellsize = top_runner.cellsize
            
            xmin = transform[0]
            ymin = transform[3] + transform[5] * m
            xmax = transform[0] + transform[1] * n
            ymax = transform[3]
            
            assert xmin < xmax
            assert ymin < ymax
            
            self._utmproj4 = proj
            self._utmextent = xmin, ymin, xmax, ymax
        
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # outlet
    #
    @property
    def outlet(self):
        return self._outlet

    @property
    def has_outlet(self):
        return self._outlet is not None

    def set_outlet(self, lng, lat, pixelcoords=False):
        self.lock()

        # noinspection PyBroadException
        try:
            top_runner = TopazRunner(self.topaz_wd, self.dem_fn,
                                     csa=self.csa, mcl=self.mcl)

            (x, y), distance = top_runner.find_closest_channel(lng, lat, pixelcoords=pixelcoords)

            _lng, _lat = top_runner.pixel_to_longlat(x, y)

            self._outlet = Outlet((lng, lat), (_lng, _lat),
                                  distance, (x, y))

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
            
    #
    # subcatchments
    #
    @property
    def has_subcatchments(self):
        return _exists(self.subwta_arc)

    def build_subcatchments(self):
        self.lock()

        # noinspection PyBroadException
        try:
            top_runner = TopazRunner(self.topaz_wd, self.dem_fn,
                                     csa=self.csa, mcl=self.mcl)

            outlet_px = self._outlet.pixel_coords
            top_runner.build_subcatchments(outlet_px)
            assert self.has_subcatchments

            # calculate descriptive statistics
            cellsize = self.cellsize
            bound, transform, proj = read_arc(self.bound_arc, dtype=np.int32)
            wsarea = float(np.sum(bound) * cellsize * cellsize)
            mask = -1 * bound + 1

            # determine area with slope > 30
            fvslop, transform, proj = read_arc(self.fvslop_arc)
            fvslop_ma = ma.masked_array(fvslop, mask=mask)
            indx, indy = ma.where(fvslop_ma > 0.3)
            area_gt30 = float(len(indx) * cellsize * cellsize)

            # determine ruggedness of watershed
            relief, transform, proj = read_arc(self.relief_arc)
            relief_ma = ma.masked_array(relief, mask=mask)
            minz = float(np.min(relief_ma))
            maxz = float(np.max(relief_ma))
            ruggedness = float((maxz - minz) / math.sqrt(wsarea))

            self.wsarea = wsarea
            self.area_gt30 = area_gt30
            self.ruggedness = ruggedness
            self.minz = minz
            self.maxz = maxz

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
