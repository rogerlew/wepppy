"""Rangeland Analysis Platform (RAP) NoDb controller.

This module retrieves RAP fractional cover rasters for a watershed, summarizes
band values to TOPAZ hillslopes, and surfaces the results to downstream mods
such as Rangeland Cover and RHEM. It relies on the watershed geometry
configured by `Ron` and caches per-band statistics so repeated UI interactions
do not trigger additional raster processing.

Key inputs:
* `rhem.rap_year` configuration or runtime override for the RAP dataset year.
* Watershed rasters (`subwta`, optional `mofe_map`) used to aggregate band
  values via the RAP band rasters.
* Ron map extent for bounding RAP downloads.

Outputs and integrations:
* `self.data` storing fractional cover summaries for each RAP band by hillslope.
* Optional `self.mofe_data` providing multi-OFE breakdowns when enabled.
* `report` property returning spatial statistics for UI dashboards.
"""

from __future__ import annotations

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Dict, Iterator, Optional, Tuple

from osgeo import gdal

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.core import Ron, Watershed

from wepppy.landcover.rap import (
    RangelandAnalysisPlatformV3,
    RAP_Band,
    RangelandAnalysisPlatformV3Dataset
)

from wepppyo3.raster_characteristics import identify_median_single_raster_key
from wepppyo3.raster_characteristics import identify_median_intersecting_raster_keys

from wepppy.query_engine import update_catalog_entry

__all__ = [
    'RAPNoDbLockedException',
    'RAPPointData',
    'RAP',
]


gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

BandValues = Dict[int | str, float]
BandSummary = Dict[RAP_Band, BandValues]



class RAPNoDbLockedException(Exception):
    pass


class RAPPointData:
    def __init__(self, **kwds: Optional[float]) -> None:
        for band in RAP_Band:
            setattr(self, band.name.lower(), kwds.get(band.name.lower(), None))

    @property
    def total_cover(self) -> float:
        return (self.annual_forb_and_grass +
                self.bare_ground +
                self.litter +
                self.perennial_forb_and_grass +
                self.shrub +
                self.tree)

    @property
    def annual_forb_and_grass_normalized(self) -> float:
        return 100.0 * self.annual_forb_and_grass / self.total_cover

    @property
    def bare_ground_normalized(self) -> float:
        return 100.0 * self.bare_ground / self.total_cover

    @property
    def litter_normalized(self) -> float:
        return 100.0 * self.litter / self.total_cover

    @property
    def perennial_forb_and_grass_normalized(self) -> float:
        return 100.0 * self.perennial_forb_and_grass / self.total_cover

    @property
    def shrub_normalized(self) -> float:
        return 100.0 * self.shrub / self.total_cover

    @property
    def tree_normalized(self) -> float:
        return 100.0 * self.tree / self.total_cover

    @property
    def isvalid(self) -> bool:
        return (self.annual_forb_and_grass is not None
                and self.bare_ground is not None
                and self.litter is not None
                and self.perennial_forb_and_grass is not None
                and self.shrub is not None
                and self.tree is not None)

    def __str__(self) -> str:
        return 'RAPPointData(' + \
            ', '.join([f'%s=%i' % (band.name.lower(), getattr(self, band.name.lower())) for band in RAP_Band]) + \
            ')'


    def __repr__(self) -> str:
        return self.__str__().replace(' ', '') \
                             .replace(',\n', ', ')


class RAP(NoDbBase):
    __name__ = 'RAP'

    filename = 'rap.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            os.mkdir(self.rap_dir)
            self.data: Optional[BandSummary] = None
            self.mofe_data: Optional[BandSummary] = None
            self._rap_year: Optional[int] = None
            self._rap_mgr: Optional[RangelandAnalysisPlatformV3] = None

    @classmethod
    def _post_instance_loaded(cls, instance: 'RAP') -> 'RAP':
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
    def rap_year(self) -> Optional[int]:
        return self._rap_year

    @rap_year.setter
    @nodb_setter
    def rap_year(self, value: int) -> None:
        self._rap_year = value

    @property
    def rap_dir(self) -> str:
        return _join(self.wd, 'rap')

    def acquire_rasters(self, year: int) -> None:
        _map = Ron.getInstance(self.wd).map
        rap_mgr = RangelandAnalysisPlatformV3(wd=self.rap_dir, bbox=_map.extent)
        rap_mgr.retrieve([year])

        with self.locked():
            self._rap_year = year
            self._rap_mgr = rap_mgr

        update_catalog_entry(self.wd, self.rap_dir)

    def on(self, evt: TriggerEvents) -> None:
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()


    def analyze(self) -> None:
        wd = self.wd

        watershed = Watershed.getInstance(wd)
        subwta_fn = watershed.subwta
        assert _exists(subwta_fn)

        rap_mgr = self._rap_mgr
        assert rap_mgr is not None
        assert self.rap_year is not None
        rap_ds_fn = rap_mgr.get_dataset_fn(year=self.rap_year)

        with self.locked():
            data_ds: BandSummary = {}
            mofe_data: BandSummary = {}
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
            self.mofe_data = mofe_data or None

    def get_cover(self, topaz_id: int | str) -> float:
        assert self.data is not None
        key = str(topaz_id)
        cover = 0.0
        for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                     RAP_Band.SHRUB,
                     RAP_Band.TREE]:
            band_values = self.data.get(band, {})
            if key in band_values:
                cover += band_values[key]
            elif topaz_id in band_values:
                cover += band_values[topaz_id]
        return cover

    @property
    def report(self) -> Optional[Dict[str, Dict[str, float]]]:
        if self.data is None:
            return None

        watershed = Watershed.getInstance(self.wd)
        bound_fn = watershed.bound
        assert _exists(bound_fn)

        rap_mgr = self._rap_mgr
        assert rap_mgr is not None
        assert self.rap_year is not None
        rap_ds = rap_mgr.get_dataset(year=self.rap_year)

        d: Dict[str, Dict[str, float]] = {}
        for band in RAP_Band:
            name = ' '.join([t[0] + t[1:].lower() for t in band.name.split('_')])
            d[name] = rap_ds.spatial_stats(band=band, bound_fn=bound_fn)

        return d

    def __iter__(self) -> Iterator[Tuple[int | str, RAPPointData]]:
        assert self.data is not None

        band_values = self.data.get(RAP_Band.TREE, {})
        for topaz_id in band_values:
            d: Dict[str, float] = {}
            for i, band in enumerate([RAP_Band.ANNUAL_FORB_AND_GRASS,
                                      RAP_Band.BARE_GROUND,
                                      RAP_Band.LITTER,
                                      RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                      RAP_Band.SHRUB,
                                      RAP_Band.TREE]):

                d[band.name.lower()] = self.data[band][topaz_id]

            yield topaz_id, RAPPointData(**d)
