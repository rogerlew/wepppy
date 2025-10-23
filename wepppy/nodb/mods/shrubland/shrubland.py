"""Shrubland fractional cover controller.

This module retrieves NLCD shrubland fractional cover rasters, aggregates
per-band values to TOPAZ hillslopes, and exposes summaries for WEPPcloud UI
dashboards and downstream NoDb mods. Each dataset (annual herb, bare ground,
sagebrush height, etc.) is downloaded via WMESque, clipped to the project
extent, and stored in the run's `shrubland/` directory.

Inputs:
- Ron map extent and cell size used to constrain WMESque downloads.
- Watershed `subwta` raster that maps raster cells to TOPAZ hillslope ids.

Outputs and integrations:
- Geo rasters cached under `shrubland/*.asc` for reproducibility and inspection.
- `self.data` providing per-hillslope summaries by shrubland dataset; consumed
  by terrestrial cover analytics and exported through the NoDb API.
- `report` property returning spatial statistics for UI panels.
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
from typing import ClassVar, Dict, Iterator, Optional, Tuple, TypeAlias

from osgeo import gdal

from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.nodb.base import NoDbBase, TriggerEvents
from wepppy.nodb.core import Ron, Watershed
from wepppy.query_engine.activate import update_catalog_entry

from .shrubland_map import ShrublandMap

__all__: list[str] = [
    'ShrublandNoDbLockedException',
    'nlcd_shrubland_layers',
    'ShrublandPointData',
    'Shrubland',
]

ShrublandDataset: TypeAlias = str
ShrublandLayerSummary: TypeAlias = Dict[ShrublandDataset, float]
ShrublandData: TypeAlias = Dict[int | str, ShrublandLayerSummary]
ShrublandReport: TypeAlias = Dict[ShrublandDataset, Dict[str, float]]

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class ShrublandNoDbLockedException(Exception):
    pass


nlcd_shrubland_layers: Tuple[ShrublandDataset, ...] = (
    'annual_herb',
    'bare_ground',
    'big_sagebrush',
    'sagebrush',
    'herbaceous',
    'sagebrush_height',
    'litter',
    'shrub',
    'shrub_height',
)


class ShrublandPointData:
    def __init__(self, **kwds: Optional[float]) -> None:
        self.annual_herb: Optional[float] = kwds.get('annual_herb')
        self.bare_ground: Optional[float] = kwds.get('bare_ground')
        self.big_sagebrush: Optional[float] = kwds.get('big_sagebrush')
        self.sagebrush: Optional[float] = kwds.get('sagebrush')
        self.herbaceous: Optional[float] = kwds.get('herbaceous')
        self.sagebrush_height: Optional[float] = kwds.get('sagebrush_height')
        self.litter: Optional[float] = kwds.get('litter')
        self.shrub: Optional[float] = kwds.get('shrub')
        self.shrub_height: Optional[float] = kwds.get('shrub_height')

    @property
    def total_cover(self) -> float:
        assert self.annual_herb is not None
        assert self.bare_ground is not None
        assert self.big_sagebrush is not None
        assert self.sagebrush is not None
        assert self.herbaceous is not None
        assert self.litter is not None
        assert self.shrub is not None
        return (
            self.annual_herb
            + self.bare_ground
            + self.big_sagebrush
            + self.sagebrush
            + self.herbaceous
            + self.litter
            + self.shrub
        )

    @property
    def annual_herb_normalized(self) -> float:
        assert self.annual_herb is not None
        return 100.0 * self.annual_herb / self.total_cover

    @property
    def bare_ground_normalized(self) -> float:
        assert self.bare_ground is not None
        return 100.0 * self.bare_ground / self.total_cover

    @property
    def big_sagebrush_normalized(self) -> float:
        assert self.big_sagebrush is not None
        return 100.0 * self.big_sagebrush / self.total_cover

    @property
    def sagebrush_normalized(self) -> float:
        assert self.sagebrush is not None
        return 100.0 * self.sagebrush / self.total_cover

    @property
    def herbaceous_normalized(self) -> float:
        assert self.herbaceous is not None
        return 100.0 * self.herbaceous / self.total_cover

    @property
    def litter_normalized(self) -> float:
        assert self.litter is not None
        return 100.0 * self.litter / self.total_cover

    @property
    def shrub_normalized(self) -> float:
        assert self.shrub is not None
        return 100.0 * self.shrub / self.total_cover

    @property
    def isvalid(self) -> bool:
        return (
            self.annual_herb is not None
            and self.bare_ground is not None
            and self.big_sagebrush is not None
            and self.sagebrush is not None
            and self.herbaceous is not None
            and self.sagebrush_height is not None
            and self.shrub is not None
            and self.shrub_height is not None
        )

    def __str__(self) -> str:
        return (
            'ShrublandPointData(annual_herb={0.annual_herb},\n'
            '                   bare_ground={0.bare_ground},\n'
            '                   big_sagebrush={0.big_sagebrush},\n'
            '                   sagebrush={0.sagebrush},\n'
            '                   herbaceous={0.herbaceous},\n'
            '                   sagebrush_height={0.sagebrush_height},\n'
            '                   litter={0.litter},\n'
            '                   shrub={0.shrub},\n'
            '                   shrub_height={0.shrub_height})'
        ).format(self)

    def __repr__(self) -> str:
        return self.__str__().replace(' ', '').replace(',\n', ', ')


class Shrubland(NoDbBase):
    __name__: ClassVar[str] = 'Shrubland'

    filename: ClassVar[str] = 'shrubland.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self.data: Optional[ShrublandData] = None

        with self.locked():
            os.mkdir(self.shrubland_dir)
            self.data = None

    @property
    def shrubland_dir(self) -> str:
        return _join(self.wd, 'shrubland')

    def acquire_rasters(self) -> None:
        _map = Ron.getInstance(self.wd).map
        for ds in nlcd_shrubland_layers:
            fn = _join(self.shrubland_dir, f'{ds}.asc')
            wmesque_retrieve(
                f'nlcd_shrubland/2016/{ds}',
                _map.extent,
                fn,
                _map.cellsize,
                v=self.wmesque_version,
                wmesque_endpoint=self.wmesque_endpoint
            )

            update_catalog_entry(self.wd, self.shrubland_dir)

    def on(self, evt: TriggerEvents) -> None:
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()

    def load_shrub_map(self, ds: ShrublandDataset) -> ShrublandMap:
        assert ds in nlcd_shrubland_layers

        fn = _join(self.shrubland_dir, f'{ds}.asc')
        assert _exists(fn)

        return ShrublandMap(fn)

    def analyze(self) -> None:
        subwta_fn = Watershed.getInstance(self.wd).subwta
        assert _exists(subwta_fn)

        with self.locked():
            data_ds: Dict[ShrublandDataset, Dict[int | str, float]] = {}
            for ds in nlcd_shrubland_layers:
                shrubland_map = self.load_shrub_map(ds)
                data_ds[ds] = shrubland_map.spatial_aggregation(subwta_fn)

            data: ShrublandData = {}
            litter_data = data_ds['litter']
            for topaz_id in litter_data:
                data[topaz_id] = {
                    ds: data_ds[ds][topaz_id] for ds in nlcd_shrubland_layers
                }

            self.data = data

    @property
    def report(self) -> Optional[ShrublandReport]:
        if self.data is None:
            return None

        watershed = Watershed.getInstance(self.wd)
        bound_fn = watershed.bound
        assert _exists(bound_fn)

        report: ShrublandReport = {}
        for ds in nlcd_shrubland_layers:
            shrubland_map = self.load_shrub_map(ds)
            report[ds] = shrubland_map.spatial_stats(bound_fn)

        return report

    def __iter__(self) -> Iterator[Tuple[int | str, ShrublandPointData]]:
        assert self.data is not None

        for topaz_id, band_values in self.data.items():
            yield topaz_id, ShrublandPointData(**band_values)
