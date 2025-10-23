"""Tree canopy fractional cover controller.

This module retrieves NLCD tree canopy rasters, caches them under the run
directory, and summarizes canopy fractions to TOPAZ hillslopes. The resulting
metrics populate WEPPcloud dashboards and augment watershed analytics that
blend canopy coverage with other vegetation datasets.

Inputs:
- Ron map extent and cell size used for WMESque downloads.
- Watershed `subwta` raster mapping cells to hillslope identifiers.

Outputs and integrations:
- `treecanopy/treecanopy.asc` cached in the run workspace for reproducibility.
- `self.data` storing canopy coverage per hillslope, consumed by reports and
  downstream mods.
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
from wepppy.query_engine import update_catalog_entry

from .treecanopy_map import TreecanopyMap

__all__: list[str] = [
    'TreecanopyNoDbLockedException',
    'nlcd_treecanopy_layers',
    'TreecanopyPointData',
    'Treecanopy',
]

gdal.UseExceptions()

_THISDIR = os.path.dirname(__file__)
_DATA_DIR = _join(_THISDIR, 'data')

TreecanopyDataset: TypeAlias = str
TreecanopyData: TypeAlias = Dict[int | str, float]
TreecanopyReport: TypeAlias = Dict[str, float]


class TreecanopyNoDbLockedException(Exception):
    """Raised when the tree canopy controller cannot acquire its NoDb lock."""


nlcd_treecanopy_layers: Tuple[TreecanopyDataset, ...] = ('treecanopy',)


class TreecanopyPointData:
    def __init__(self, **kwds: Optional[float]) -> None:
        self.treecanopy: Optional[float] = kwds.get('treecanopy')

    @property
    def isvalid(self) -> bool:
        return self.treecanopy is not None

    def __str__(self) -> str:
        return f'TreecanopyPointData(treecanopy={self.treecanopy})'

    def __repr__(self) -> str:
        return self.__str__().replace(' ', '').replace(',\n', ', ')


class Treecanopy(NoDbBase):
    __name__: ClassVar[str] = 'Treecanopy'
    filename: ClassVar[str] = 'treecanopy.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self.data: Optional[TreecanopyData] = None

        with self.locked():
            os.mkdir(self.treecanopy_dir)
            self.data = None

    @property
    def treecanopy_dir(self) -> str:
        return _join(self.wd, 'treecanopy')

    @property
    def treecanopy_fn(self) -> str:
        return _join(self.treecanopy_dir, 'treecanopy.asc')

    def acquire_raster(self) -> None:
        _map = Ron.getInstance(self.wd).map

        wmesque_retrieve(
            'nlcd_treecanopy/2016',
            _map.extent,
            self.treecanopy_fn,
            _map.cellsize,
            v=self.wmesque_version,
            wmesque_endpoint=self.wmesque_endpoint
        )

        update_catalog_entry(self.wd, self.treecanopy_dir)

    def on(self, evt: TriggerEvents) -> None:
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_raster()

    def load_map(self) -> TreecanopyMap:
        fn = self.treecanopy_fn
        assert _exists(fn)
        return TreecanopyMap(fn)

    def analyze(self) -> None:
        subwta_fn = Watershed.getInstance(self.wd).subwta

        assert _exists(subwta_fn)

        with self.locked():
            treecanopy_map = self.load_map()
            self.data = treecanopy_map.spatial_aggregation(subwta_fn)

    @property
    def report(self) -> Optional[TreecanopyReport]:
        if self.data is None:
            return None

        watershed = Watershed.getInstance(self.wd)
        bound_fn = watershed.bound
        assert _exists(bound_fn)

        treecanopy_map = self.load_map()
        return treecanopy_map.spatial_stats(bound_fn)

    def __iter__(self) -> Iterator[Tuple[int | str, TreecanopyPointData]]:
        assert self.data is not None

        for topaz_id, value in self.data.items():
            yield topaz_id, TreecanopyPointData(treecanopy=value)
