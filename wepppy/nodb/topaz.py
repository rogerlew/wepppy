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
import inspect

import numpy as np
import numpy.ma as ma

from wepppy.topo.topaz import TopazRunner
from wepppy.all_your_base.geo import read_arc

from .base import NoDbBase


# this needs to be here to unpickle old projects
# wepppy.nodb.topaz.Outlet should be wepppy.nodb.watershed.Outlet
# then it should be possible to remove this class
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

    filename = 'topaz.nodb'
    
    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(Topaz, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self.csa = self.config_get_float('topaz', 'csa')
            self.mcl = self.config_get_float('topaz', 'mcl')
            # self.zoom_min = self.config_get_int('topaz', 'zoom_min')

            self._outlet = None

            self.wsarea = None
            self.area_gt30 = None
            self.ruggedness = None
            self.minz = None
            self.maxz = None

            topaz_wd = self.topaz_wd
            if not _exists(topaz_wd):
                os.mkdir(topaz_wd)

    @property
    def subwta_arc(self):
        return _join(self.topaz_wd, 'SUBWTA.ARC')

    @property
    def bound_arc(self):
        return _join(self.topaz_wd, 'BOUND.ARC')

    @property
    def chnjnt_arc(self):
        return _join(self.topaz_wd, 'CHNJNT.ARC')

    @property
    def netful_arc(self):
        return _join(self.topaz_wd, 'NETFUL.ARC')

    @property
    def uparea_out(self):
        return _join(self.topaz_wd, 'UPAREA.ARC')

    @property
    def discha_out(self):
        return _join(self.topaz_wd, 'DISCHA.ARC')

    @property
    def eldcha_out(self):
        return _join(self.topaz_wd, 'ELDCHA.ARC')

    @property
    def fvslop_arc(self):
        return _join(self.topaz_wd, 'FVSLOP.ARC')

    @property
    def relief_arc(self):
        return _join(self.topaz_wd, 'RELIEF.ARC')

    @property
    def topaz_pass(self):
        if _exists(self.subwta_arc):
            return 2

        if _exists(self.netful_arc):
            return 1

        return 0

    #
    # channels
    #
    @property
    def has_channels(self) -> bool:
        return _exists(self.netful_arc)

    def build_channels(self, csa=4, mcl=60):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(csa={csa}, mcl={mcl})')

        with self.locked():
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
        
    #
    # outlet
    #
    @property
    def outlet(self):
        return self._outlet

    @property
    def has_outlet(self):
        return self._outlet is not None

    def set_outlet(self, lng, lat, pixelcoords=False, da=0.0):
        from wepppy.nodb.watershed import Outlet
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(lng={lng}, lat={lat}, pixelcoords={pixelcoords}, da={da})')

        with self.locked():
            top_runner = TopazRunner(self.topaz_wd, self.dem_fn,
                                     csa=self.csa, mcl=self.mcl)

            if da>0:
                (x, y), distance = top_runner.find_closest_da_match(lng, lat, da, pixelcoords=pixelcoords)
            else:
                (x, y), distance = top_runner.find_closest_channel2(lng, lat, pixelcoords=pixelcoords)
            
            _lng, _lat = top_runner.pixel_to_lnglat(x, y)

            self._outlet = Outlet(requested_loc=(lng, lat), actual_loc=(_lng, _lat),
                                  distance_from_requested=distance, pixel_coords=(x, y))

    #
    # subcatchments
    #
    @property
    def has_subcatchments(self):
        return _exists(self.subwta_arc)

    def build_subcatchments(self):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        
        with self.locked():
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
