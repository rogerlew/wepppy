# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import jsonpickle

from os.path import join as _join
from os.path import exists as _exists

from osgeo import gdal

from wepppy.all_your_base.geo.webclients import wmesque_retrieve

from ...ron import Ron
from ...base import NoDbBase, TriggerEvents
from ...watershed import Watershed

from wepppy.landcover.rap import (
    RangelandAnalysisPlatformV2, 
    RAP_Band, 
    RangelandAnalysisPlatformV2Dataset
)

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class RAPNoDbLockedException(Exception):
    pass


class RAPPointData(object):
    def __init__(self, **kwds):
        for band in RAP_Band:
            setattr(self, band.name.lower(), kwds.get(band.name.lower(), None))

    @property
    def total_cover(self):
        return (self.annual_forb_and_grass +
                self.bare_ground +
                self.litter +
                self.perennial_forb_and_grass +
                self.shrub +
                self.tree)

    @property
    def annual_forb_and_grass_normalized(self):
        return 100.0 * self.annual_forb_and_grass / self.total_cover

    @property
    def bare_ground_normalized(self):
        return 100.0 * self.bare_ground / self.total_cover

    @property
    def litter_normalized(self):
        return 100.0 * self.litter / self.total_cover

    @property
    def perennial_forb_and_grass_normalized(self):
        return 100.0 * self.perennial_forb_and_grass / self.total_cover

    @property
    def shrub_normalized(self):
        return 100.0 * self.shrub / self.total_cover

    @property
    def tree_normalized(self):
        return 100.0 * self.tree / self.total_cover

    @property
    def isvalid(self):
        return (self.annual_forb_and_grass is not None
                and self.bare_ground is not None
                and self.litter is not None
                and self.perennial_forb_and_grass is not None
                and self.shrub is not None
                and self.tree is not None)

    def __str__(self):
        return 'RAPPointData(' + \
            ', '.join([f'%s=%i' % (band.name.lower(), getattr(self, band.name.lower())) for band in RAP_Band]) + \
            ')'


    def __repr__(self):
        return self.__str__().replace(' ', '') \
                             .replace(',\n', ', ')


class RAP(NoDbBase):
    __name__ = 'RAP'

    def __init__(self, wd, cfg_fn):
        super(RAP, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.rap_dir)
            self.data = None
            self._rap_year = None
            self._rap_mgr = None
            
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
        with open(_join(wd, 'rap.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, RAP), db

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'rap.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rap.nodb.lock')

    @property
    def rap_year(self):
        return self._rap_year

    @rap_year.setter
    def rap_year(self, value: int):
        self.lock()

        # noinspection PyBroadException
        try:
            self._rap_year = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
  
    @property
    def rap_dir(self):
        return _join(self.wd, 'rap')

    def acquire_rasters(self, year):
        _map = Ron.getInstance(self.wd).map
        rap_mgr = RangelandAnalysisPlatformV2(wd=self.rap_dir, bbox=_map.extent)
        rap_mgr.retrieve([year])

        self.lock()

        # noinspection PyBroadException
        try:
            self._rap_year = year
            self._rap_mgr = rap_mgr
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
        
    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()


    def analyze(self):
        wd = self.wd

        subwta_fn = Watershed.getInstance(wd).subwta

        assert _exists(subwta_fn)

        rap_mgr = self._rap_mgr
        rap_ds = rap_mgr.get_dataset(year=self.rap_year)       

        self.lock()
        try:

            data_ds = {}
            for band in RAP_Band:
                data_ds[band], px_counts = rap_ds.spatial_aggregation(band=band, subwta_fn=subwta_fn)

            data = {}
            for topaz_id in data_ds[RAP_Band.LITTER]:
                data[topaz_id] = {band: data_ds[band][topaz_id] for band in RAP_Band}

            self.data = data
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        if self.data is None:
            return None
        
        watershed = Watershed.getInstance(self.wd)
        bound_fn = watershed.bound
        assert _exists(bound_fn)

        rap_mgr = self._rap_mgr
        rap_ds = rap_mgr.get_dataset(year=self.rap_year)       

        d = {}
        for band in RAP_Band:
            name = ' '.join([t[0] + t[1:].lower() for t in band.name.split('_')])
            d[name] = rap_ds.spatial_stats(band=band, bound_fn=bound_fn)

        return d

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, RAPPointData(**{band.name.lower(): v for band, v in self.data[topaz_id].items()})

