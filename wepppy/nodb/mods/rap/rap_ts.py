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
from ...mixins.log_mixin import LogMixin

from wepppy.landcover.rap import (
    RangelandAnalysisPlatformV2, 
    RangelandAnalysisPlatformV3, 
    RAP_Band, 
    RangelandAnalysisPlatformV2Dataset,
    RangelandAnalysisPlatformV3Dataset
)

try:
    import rustpy_geo
except:
    rustpy_geo = None

from .rap import RAPPointData

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class RAPNoDbLockedException(Exception):
    pass


class RAP_TS(NoDbBase, LogMixin):
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

            if db.data is not None:
                data = {}
                for key in RAP_Band:
                    if repr(key) not in db.data:
                        continue
                    data[key] = db.data[repr(key)]

                db.data = data
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
    def status_log(self):
        return os.path.abspath(_join(self.rap_dir, 'status.log'))

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

            for year in range(start_year, end_year+1):
                self.log(f'  retrieving rap {year}...')
                rap_mgr.retrieve([year])
                self.log_done()

            self._rap_mgr = rap_mgr
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
        
    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()


    def analyze(self, use_sbs=False, verbose=True):
        global rustpy_geo
        from wepppy.nodb import Ron
        from wepppy.nodb.mods import Disturbed

        start_year = self.rap_start_year
        end_year = self.rap_end_year

        wd = self.wd

        subwta_fn = Watershed.getInstance(wd).subwta
        ron = Ron.getInstance(wd)

        assert _exists(subwta_fn)

        rap_mgr = self._rap_mgr

        self.lock()
        try:

            if ron.has_sbs and use_sbs:
                disturbed = Disturbed.getInstance(wd)
                sbs = disturbed.get_sbs_4class()
                disturbed_fn = disturbed.sbs_4class_path
            else:
                disturbed_fn = None

            data_ds = {}
            px_counts = None

            for year in range(start_year, end_year+1):
                if verbose:
                    print(year)
                rap_ds_fn = rap_mgr.get_dataset_fn(year=year)

                for i, band in enumerate([RAP_Band.ANNUAL_FORB_AND_GRASS,
                                          RAP_Band.BARE_GROUND,
                                          RAP_Band.LITTER,
                                          RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                          RAP_Band.SHRUB,
                                          RAP_Band.TREE]):
                    if verbose:
                        print(band)

                    if band not in data_ds:
                        data_ds[band] = {}

                    self.log(f'  analyzing rap {year} {band}...')
                    data_ds[band][year] = rustpy_geo.median_identify(subwta_fn=subwta_fn,
                                                                      parameter_fn=rap_ds_fn,
                                                                      band_indx=band,
                                                                      lcmap_fn=disturbed_fn)
                    self.log_done()

            self.data = data_ds

            self.dump_and_unlock()

            self.log('analysis complete...')
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, RAPPointData(**{band.name.lower(): v for band, v in self.data[topaz_id].items()})

    def prep_cover(self, runs_dir):
        data = self.data

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        with open(_join(runs_dir, 'cancov.txt'), 'w') as fp:
            fp.write("")

        years = [yr for yr in data[RAP_Band.TREE]]

        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = translator.top(wepp=wepp_id)

            with open(_join(runs_dir, f'p{wepp_id}.cov'), 'w') as fp:
                fp.write(' \t'.join([str(yr) for yr in years]))
                fp.write('\n')

                for band in [RAP_Band.TREE,
                             RAP_Band.SHRUB,
                             RAP_Band.PERENNIAL_FORB_AND_GRASS,
                             RAP_Band.ANNUAL_FORB_AND_GRASS]:
                    fp.write(' \t'.join([str(data[band][yr][str(topaz_id)]) for yr in years]))
                    fp.write('\n')


