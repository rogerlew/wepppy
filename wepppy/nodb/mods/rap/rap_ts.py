# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.
from typing import Dict, Tuple

import os
import jsonpickle

from os.path import join as _join
from os.path import exists as _exists

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

from osgeo import gdal

import numpy as np

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

from ...redis_prep import RedisPrep, TaskEnum

import wepppyo3
from wepppyo3.raster_characteristics import identify_median_single_raster_key
from wepppyo3.raster_characteristics import identify_median_intersecting_raster_keys

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
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
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

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return RAP_TS.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)


    @property
    def _status_channel(self):
        return f'{self.runid}:rap_ts'

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

        def retrieve_rap_year(year):
            self.log(f'  retrieving rap {year}...')
            retries = rap_mgr.retrieve([year])
            if retries > 0:
                self.log(f'  retries: {retries}\n')
            self.log_done()
            return year

        def oncomplete(future):
            year = future.result()
            self.log(f'  retrieving rap {year} completed.\n')

        self.lock()

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
            rap_mgr = RangelandAnalysisPlatformV3(wd=self.rap_dir, bbox=_map.extent, cellsize=_map.cellsize)

            futures = []
            with ThreadPoolExecutor() as pool:
                for year in range(start_year, end_year + 1):
                    future = pool.submit(retrieve_rap_year, year)
                    future.add_done_callback(oncomplete)
                    futures.append(future)

                wait(futures, return_when=FIRST_EXCEPTION)

            self._rap_mgr = rap_mgr
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()

    def get_cover(self, topaz_id, year, fallback=True):
        cover = 0.0
        for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                     RAP_Band.SHRUB,
                     RAP_Band.TREE]:
            _cover = self.data[band][str(year)].get(str(topaz_id), None)
            if _cover is not None and fallback:
                _cover = self.data[band][str(year)].get(str(topaz_id), 0.0)
            cover += _cover
        return cover

    def analyze(self, use_sbs=False, verbose=False):
        from wepppy.nodb import Ron
        from wepppy.nodb.mods import Disturbed

        start_year = self.rap_start_year
        end_year = self.rap_end_year

        wd = self.wd
        watershed = Watershed.getInstance(wd)
        rap_mgr = self._rap_mgr

        self.lock()
        try:
            data_ds = {}

            def analyze_band_year(year, band):
                if verbose:
                    print(year, band)

                if band not in data_ds:
                    data_ds[band] = {}

                self.log(f'  analyzing rap {year} {band}...')

                rap_ds_fn = rap_mgr.get_dataset_fn(year=year)
                if self.multi_ofe:
                    result = identify_median_intersecting_raster_keys(
                        key_fn=watershed.subwta, key2_fn=watershed.mofe_map, parameter_fn=rap_ds_fn, band_indx=band)
                else:
                    result = identify_median_single_raster_key(
                        key_fn=watershed.subwta, parameter_fn=rap_ds_fn, band_indx=band)

                data_ds[band][year] = result
                self.log_done()
                return year, band

            def oncomplete(future):
                year, band = future.result()
                self.log(f'  analyzing rap {year} {band} completed.\n')

            futures = []
            with ThreadPoolExecutor() as pool:
                for year in range(start_year, end_year + 1):
                    for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                                 RAP_Band.BARE_GROUND,
                                 RAP_Band.LITTER,
                                 RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                 RAP_Band.SHRUB,
                                 RAP_Band.TREE]:
                        future = pool.submit(analyze_band_year, year, band)
                        future.add_done_callback(oncomplete)
                        futures.append(future)

                wait(futures, return_when=FIRST_EXCEPTION)

            self.data = data_ds
            self.dump_and_unlock()

            self.log('analysis complete...')
            self.log_done()

        except Exception:
            self.unlock('-f')
            raise
        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.fetch_rap_ts)
        except FileNotFoundError:
            pass

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, RAPPointData(**{band.name.lower(): v for band, v in self.data[topaz_id].items()})

    def prep_cover(self, runs_dir, fallback=True):
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.revegetation import Revegetation

        wd = self.wd

        disturbed = Disturbed.getInstance(wd)
        fire_date = None
        if disturbed is not None:
            fire_date = disturbed.fire_date

        try:
            reveg = Revegetation.getInstance(wd)
        except:
            reveg = None

        cover_transform = None
        if reveg is not None:
            cover_transform = reveg.cover_transform

        if fire_date is not None and  cover_transform is not None:
            return self._prep_transformed_cover(runs_dir)

        self.log('RAP_TS::prep_cover\n')
        data = self.data

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        with open(_join(runs_dir, 'cancov.txt'), 'w') as fp:
            fp.write("")

        years = sorted([yr for yr in data[RAP_Band.TREE]])

        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = str(translator.top(wepp=wepp_id))

            with open(_join(runs_dir, f'p{wepp_id}.cov'), 'w') as fp:
                fp.write(' \t'.join([str(yr) for yr in years]))
                fp.write('\n')

                if self.multi_ofe:
                    for fp_id in sorted(data[RAP_Band.TREE][years[0]][str(topaz_id)]):
                        self.log(f'  topaz_id={topaz_id}, fp_id={fp_id}\n')

                        for band in [RAP_Band.TREE,
                                     RAP_Band.SHRUB,
                                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                     RAP_Band.ANNUAL_FORB_AND_GRASS,
                                     RAP_Band.LITTER,
                                     RAP_Band.BARE_GROUND,
                                     ]:
                            fp.write(' \t'.join([str(data[band][yr][topaz_id][fp_id]) for yr in years]))
                            fp.write('\n')

                else:
                    self.log(f'  topaz_id={topaz_id}\n')

                    for band in [RAP_Band.TREE,
                                 RAP_Band.SHRUB,
                                 RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                 RAP_Band.ANNUAL_FORB_AND_GRASS,
                                 RAP_Band.LITTER,
                                 RAP_Band.BARE_GROUND,
                                 ]:
                        _covers = []
                        for yr in years:
                            _cover = data[band][yr].get(topaz_id, None)
                            if _cover is None and yr-1 in data[band] and fallback:
                                _cover = data[band][yr-1].get(topaz_id, 0.0)
                            if _cover is None:
                                _cover = 0.0
                            _covers.append(_cover)
                        fp.write(' \t'.join([str(_cover) for _cover in _covers]))
                        fp.write('\n')

    def _prep_transformed_cover(self, runs_dir):
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.revegetation import Revegetation
        from wepppy.nodb.landuse import Landuse

        self.log('RAP_TS::_prep_transformed_cover\n')

        wd = self.wd

        disturbed = Disturbed.getInstance(wd)
        reveg = Revegetation.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        fire_date = disturbed.fire_date
        cover_transform = reveg.cover_transform
        managements = landuse.managements

        data = self.data

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        with open(_join(runs_dir, 'simfire.txt'), 'w') as fp:
            fp.write("")

        with open(_join(runs_dir, 'cancov.txt'), 'w') as fp:
            fp.write("")

        years = sorted([yr for yr in data[RAP_Band.TREE]])
        fire_mo, fire_da, fire_year = fire_date.replace('-', ' ').replace('/', ' ').split()
        fire_year = int(fire_year)
        fire_years = {str(yr): int(yr) - fire_year for yr in years}

        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = str(translator.top(wepp=wepp_id))

            with open(_join(runs_dir, f'p{wepp_id}.cov'), 'w') as fp:
                fp.write(' \t'.join([str(yr) for yr in years]))
                fp.write('\n')

                if self.multi_ofe:
                    for mofe_id in sorted(data[RAP_Band.TREE][years[0]][str(topaz_id)]):

                        burn_class = landuse.identify_burn_class(topaz_id, mofe_id)

                        for band, name in [(RAP_Band.TREE, 'Tree'),
                                    (RAP_Band.SHRUB, 'Shrub'),
                                    (RAP_Band.PERENNIAL_FORB_AND_GRASS, 'Perennial'),
                                    (RAP_Band.ANNUAL_FORB_AND_GRASS, 'Annual'),
                                    (RAP_Band.LITTER, 'Litter'),
                                    (RAP_Band.BARE_GROUND, 'Bare')
                                    ]:
                            key = (burn_class, name)

                            self.log(f'  topaz_id={topaz_id}, mofe_id={mofe_id}, burn_class={burn_class}, rap_band={name}\n')
                            
                            if key in cover_transform:
                                x = []
                                for yr in years:
                                    indx = fire_years.get(str(yr), None)

                                    if indx is not None and indx < 0:
                                        x.append(data[band][yr][topaz_id][mofe_id])
                                        continue

                                    if indx is None:
                                        scale = cover_transform[key][-1]
                                    else:
                                        scale = cover_transform[key][indx]
                                    x.append(data[band][str(fire_year)][topaz_id][mofe_id] * scale)
                                fp.write(' \t'.join([f'{v:0.1f}' for v in x]))
                            else:
                                fp.write(' \t'.join([str(data[band][yr][topaz_id][mofe_id]) for yr in years]))
                            fp.write('\n')

                else:
                    burn_class = landuse.identify_burn_class(topaz_id)

                    for band, name in [(RAP_Band.TREE, 'Tree'),
                                 (RAP_Band.SHRUB, 'Shrub'),
                                 (RAP_Band.PERENNIAL_FORB_AND_GRASS, 'Perennial'),
                                 (RAP_Band.ANNUAL_FORB_AND_GRASS, 'Annual'),
                                 (RAP_Band.LITTER, 'Litter'),
                                 (RAP_Band.BARE_GROUND, 'Bare')
                                 ]:
                        key = (burn_class, name)
                        
                        self.log(f'  topaz_id={topaz_id}, burn_class={burn_class}, rap_band={name}\n')

                        if key in cover_transform:
                            x = []
                            for yr in years:
                                indx = fire_years.get(str(yr), None)

                                if indx is not None and indx < 0:
                                    x.append(data[band][yr][topaz_id])
                                    continue

                                if indx is None:
                                    scale = cover_transform[key][-1]
                                else:
                                    scale = cover_transform[key][indx]
                                x.append(data[band][str(fire_year)][topaz_id] * scale)
                            fp.write(' \t'.join([f'{v:0.1f}' for v in x]))
                        else:
                            fp.write(' \t'.join([str(data[band][yr][topaz_id]) for yr in years]))
                        fp.write('\n')

