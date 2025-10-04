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

from wepppy.nodb.core import *
from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter

from wepppy.landcover.rap import (
    RangelandAnalysisPlatformV3,
    RAP_Band,
    RangelandAnalysisPlatformV3Dataset
)

import wepppyo3
from wepppyo3.raster_characteristics import identify_median_single_raster_key
from wepppyo3.raster_characteristics import identify_median_intersecting_raster_keys

__all__ = [
    'RAPNoDbLockedException',
    'RAPPointData',
    'RAP',
]


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

    filename = 'rap.nodb'

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(RAP, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            os.mkdir(self.rap_dir)
            self.data = None
            self.mofe_data = None
            self._rap_year = None
            self._rap_mgr = None

    @classmethod
    def _post_instance_loaded(cls, instance):
        instance = super()._post_instance_loaded(instance)

        if getattr(instance, 'data', None) is not None:
            instance.data = {
                key: value for key, (_key, value) in zip(RAP_Band, instance.data.items())
            }

        if getattr(instance, 'mofe_data', None) is not None:
            instance.mofe_data = {
                key: value for key, (_key, value) in zip(RAP_Band, instance.mofe_data.items())
            }

        return instance

    @property
    def rap_year(self):
        return self._rap_year

    @rap_year.setter
    @nodb_setter
    def rap_year(self, value: int):
        self._rap_year = value

    @property
    def rap_dir(self):
        return _join(self.wd, 'rap')

    def acquire_rasters(self, year):
        _map = Ron.getInstance(self.wd).map
        rap_mgr = RangelandAnalysisPlatformV3(wd=self.rap_dir, bbox=_map.extent)
        rap_mgr.retrieve([year])

        with self.locked():
            self._rap_year = year
            self._rap_mgr = rap_mgr

    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()


    def analyze(self):
        wd = self.wd

        watershed = Watershed.getInstance(wd)
        subwta_fn = watershed.subwta
        assert _exists(subwta_fn)

        rap_mgr = self._rap_mgr
        rap_ds_fn = rap_mgr.get_dataset_fn(year=self.rap_year)

        with self.locked():
            data_ds = {}
            mofe_data = {}
            for i, band in enumerate([RAP_Band.ANNUAL_FORB_AND_GRASS,
                                      RAP_Band.BARE_GROUND,
                                      RAP_Band.LITTER,
                                      RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                      RAP_Band.SHRUB,
                                      RAP_Band.TREE]):

                if self.multi_ofe:
                    mofe_data[band] = identify_median_intersecting_raster_keys(
                        key_fn=subwta_fn, key2_fn=watershed.mofe_map, parameter_fn=rap_ds_fn, band_indx=band)

                data_ds[band] = identify_median_single_raster_key(
                    key_fn=subwta_fn, parameter_fn=rap_ds_fn, band_indx=band)


            self.data = data_ds
            self.mofe_data = mofe_data

    def get_cover(self, topaz_id):
        cover = 0.0
        for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                     RAP_Band.SHRUB,
                     RAP_Band.TREE]:
            cover += self.data[str(topaz_id)][band]
        return cover

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

        for topaz_id in self.data[RAP_Band.TREE]:
            d = {}
            for i, band in enumerate([RAP_Band.ANNUAL_FORB_AND_GRASS,
                                      RAP_Band.BARE_GROUND,
                                      RAP_Band.LITTER,
                                      RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                      RAP_Band.SHRUB,
                                      RAP_Band.TREE]):

                d[band.name.lower()] = self.data[band][topaz_id]

            yield topaz_id, RAPPointData(**d)
