import os

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle

from wepppy.topaz import TopazRunner
from wepppy.all_your_base import read_arc

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
    def utmextent(self):
        return self._utmextent
        
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

    def set_outlet(self, lng, lat):
        self.lock()

        # noinspection PyBroadException
        try:
            top_runner = TopazRunner(self.topaz_wd, self.dem_fn,
                                     csa=self.csa, mcl=self.mcl)

            (x, y), distance = top_runner.find_closest_channel(lng, lat)

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

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
