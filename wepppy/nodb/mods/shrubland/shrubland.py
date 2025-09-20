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

from osgeo import gdal

from wepppy.all_your_base.geo.webclients import wmesque_retrieve

from ...ron import Ron
from ...base import NoDbBase, TriggerEvents
from ...watershed import Watershed

from .shrubland_map import ShrublandMap

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class ShrublandNoDbLockedException(Exception):
    pass


nlcd_shrubland_layers = ('annual_herb', 'bare_ground', 'big_sagebrush', 'sagebrush',
                        'herbaceous', 'sagebrush_height', 'litter', 'shrub', 'shrub_height')


class ShrublandPointData(object):
    def __init__(self, **kwds):
        self.annual_herb = kwds.get('annual_herb', None)
        self.bare_ground = kwds.get('bare_ground', None)
        self.big_sagebrush = kwds.get('big_sagebrush', None)
        self.sagebrush = kwds.get('sagebrush', None)
        self.herbaceous = kwds.get('herbaceous', None)
        self.sagebrush_height = kwds.get('sagebrush_height', None)
        self.litter = kwds.get('litter', None)
        self.shrub = kwds.get('shrub', None)
        self.shrub_height = kwds.get('shrub_height', None)

    @property
    def total_cover(self):
        return self.annual_herb + \
               self.bare_ground + \
               self.big_sagebrush + \
               self.sagebrush + \
               self.herbaceous + \
               self.litter + \
               self.shrub

    @property
    def annual_herb_normalized(self):
        return 100.0 * self.annual_herb / self.total_cover

    @property
    def bare_ground_normalized(self):
        return 100.0 * self.bare_ground / self.total_cover

    @property
    def big_sagebrush_normalized(self):
        return 100.0 * self.big_sagebrush / self.total_cover

    @property
    def sagebrush_normalized(self):
        return 100.0 * self.sagebrush / self.total_cover

    @property
    def herbaceous_normalized(self):
        return 100.0 * self.herbaceous / self.total_cover

    @property
    def litter_normalized(self):
        return 100.0 * self.litter / self.total_cover

    @property
    def shrub_normalized(self):
        return 100.0 * self.shrub / self.total_cover

    @property
    def isvalid(self):
        return self.annual_herb is not None and \
               self.bare_ground is not None and \
               self.big_sagebrush is not None and \
               self.sagebrush is not None and \
               self.herbaceous is not None and \
               self.sagebrush_height is not None and \
               self.shrub is not None and \
               self.shrub_height is not None

    def __str__(self):
        return 'ShrublandPointData(annual_herb={0.annual_herb},\n'\
               '                   bare_ground={0.bare_ground},\n'\
               '                   big_sagebrush={0.big_sagebrush},\n'\
               '                   sagebrush={0.sagebrush},\n' \
               '                   herbaceous={0.big_sagebrush},\n' \
               '                   sagebrush_height={0.big_sagebrush},\n' \
               '                   litter={0.litter},\n' \
               '                   shrub={0.shrub},\n' \
               '                   shrub_height={0.shrub_height})'.format(self)

    def __repr__(self):
        return self.__str__().replace(' ', '') \
                             .replace(',\n', ', ')


class Shrubland(NoDbBase):
    __name__ = 'Shrubland'

    filename = 'shrubland.nodb'

    def __init__(self, wd, cfg_fn):
        super(Shrubland, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.shrubland_dir)
            self.data = None

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def shrubland_dir(self):
        return _join(self.wd, 'shrubland')

    def acquire_rasters(self):
        _map = Ron.getInstance(self.wd).map
        for ds in nlcd_shrubland_layers:

            fn = _join(self.shrubland_dir, '%s.asc' % ds)
            wmesque_retrieve('nlcd_shrubland/2016/%s' % ds, _map.extent,
                             fn, _map.cellsize, v=self.wmesque_version,
                             wmesque_endpoint=self.wmesque_endpoint)

    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()

    def load_shrub_map(self, ds):
        assert ds in nlcd_shrubland_layers

        fn = _join(self.shrubland_dir, '%s.asc' % ds)
        assert _exists(fn)

        return ShrublandMap(fn)

    def analyze(self):
        wd = self.wd
        subwta_fn = Watershed.getInstance(wd).subwta

        assert _exists(subwta_fn)

        self.lock()
        try:

            data_ds = {}
            for ds in nlcd_shrubland_layers:
                shrubland_map = self.load_shrub_map(ds)
                data_ds[ds] = shrubland_map.spatial_aggregation(subwta_fn)

            data = {}
            for topaz_id in data_ds['litter']:
                data[topaz_id] = {ds: data_ds[ds][topaz_id] for ds in nlcd_shrubland_layers}

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

        d = {}
        for ds in nlcd_shrubland_layers:
            shrubland_map = self.load_shrub_map(ds)
            d[ds] = shrubland_map.spatial_stats(bound_fn)

        return d

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, ShrublandPointData(**self.data[topaz_id])
