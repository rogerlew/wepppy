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
    RangelandAnalysisPlatformV3, 
    RAP_Band, 
    RangelandAnalysisPlatformV2Dataset,
    RangelandAnalysisPlatformV3Dataset
)

from .rap import RAPPointData

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class RAPNoDbLockedException(Exception):
    pass


class RAP_TS(NoDbBase):
    __name__ = 'RAP_TS'

    def __init__(self, wd, cfg_fn):
        super(RAP_TS, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.rap_dir)
            self.data = None
            self._rap_start_year = None
            self._rap_end_year = None
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
        with open(_join(wd, 'rap_ts.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, RAP_TS), db

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
        return _join(self.wd, 'rap_ts.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rap_ts.nodb.lock')

    @property
    def rap_end_year(self):
        return self._rap_end_year

    @rap_end_year.setter
    def rap_end_year(self, value: int):
        self.lock()

        # noinspection PyBroadException
        try:
            self._rap_end_year = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
  
    @property
    def rap_start_year(self):
        return self._rap_start_year

    @rap_start_year.setter
    def rap_start_year(self, value: int):
        self.lock()

        # noinspection PyBroadException
        try:
            self._rap_start_year = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
  
    @property
    def rap_dir(self):
        return _join(self.wd, 'rap')

    def acquire_rasters(self, start_year=None, end_year=None):

        self.lock()

        # noinspection PyBroadException
        try:
            if start_year is not None:
                self._rap_start_year = start_year
            else:
                start_year = self.rap_start_year

            if end_year is not None:
                self._rap_end_year = end_year
            else:
                end_year = self.rap_end_year

            _map = Ron.getInstance(self.wd).map
            rap_mgr = RangelandAnalysisPlatformV3(wd=self.rap_dir, bbox=_map.extent)
            rap_mgr.retrieve(list(range(start_year, end_year+1)))

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
        start_year = self.rap_start_year
        end_year = self.rap_end_year

        wd = self.wd

        subwta_fn = Watershed.getInstance(wd).subwta

        assert _exists(subwta_fn)

        rap_mgr = self._rap_mgr

        self.lock()
        try:

            data_ds = {}

            for year in range(start_year, end_year+1):
                rap_ds = rap_mgr.get_dataset(year=year)
       
                for band in RAP_Band:
                    if band not in data_ds:
                        data_ds[band] = {}

                    data_ds[band][year] = rap_ds.spatial_aggregation(band=band, subwta_fn=subwta_fn)

            data = {topaz_id: {} for topaz_id in data_ds[RAP_Band.LITTER][start_year]}
            for topaz_id in data_ds[RAP_Band.LITTER][start_year]:
                for year in range(start_year, end_year+1):
                    data[topaz_id][year] = {band: data_ds[band][year][topaz_id] for band in RAP_Band}

            self.data = data
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

#    @property
#    def report(self):
#        if self.data is None:
#            return None
#        
#        watershed = Watershed.getInstance(self.wd)
#        bound_fn = watershed.bound
#        assert _exists(bound_fn)
#
#        rap_mgr = self._rap_mgr
#        rap_ds = rap_mgr.get_dataset(year=self.rap_year)       
#
#        d = {}
#        for band in RAP_Band:
#            name = ' '.join([t[0] + t[1:].lower() for t in band.name.split('_')])
#            d[name] = rap_ds.spatial_stats(band=band, bound_fn=bound_fn)
#
#        return d

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, RAPPointData(**{band.name.lower(): v for band, v in self.data[topaz_id].items()})

