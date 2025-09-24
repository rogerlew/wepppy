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

from ...ron import Ron
from ...base import NoDbBase, TriggerEvents, nodb_setter
from ...watershed import Watershed

from wepppy.landcover.emapr import (
    OSUeMapR,
    OSUeMapR_Measures,
    OSUeMapR_Dataset
)


gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class OSUeMapRNoDbLockedException(Exception):
    pass


class OSUeMapR_TS(NoDbBase):
    __name__ = 'OSUeMapR_TS'
    filename = 'emapr_ts.nodb'

    def __init__(self, wd, cfg_fn):
        super(OSUeMapR_TS, self).__init__(wd, cfg_fn)

        with self.locked():
            os.mkdir(self.emapr_dir)
            self.data = None
            self._emapr_start_year = None
            self._emapr_end_year = None
            self._emapr_mgr = None

    @property
    def emapr_end_year(self):
        return self._emapr_end_year

    @emapr_end_year.setter
    @nodb_setter
    def emapr_end_year(self, value: int):
        self._emapr_end_year = value
  
    @property
    def emapr_start_year(self):
        return self._emapr_start_year

    @emapr_start_year.setter
    @nodb_setter
    def emapr_start_year(self, value: int):
        self._emapr_start_year = value
  
    @property
    def emapr_dir(self):
        return _join(self.wd, 'emapr')

    def acquire_rasters(self, start_year=None, end_year=None):
        with self.locked():
            if start_year is not None:
                self._emapr_start_year = start_year
            else:
                start_year = self.emapr_start_year

            if end_year is not None:
                self._emapr_end_year = end_year
            else:
                end_year = self.emapr_end_year

            _map = Ron.getInstance(self.wd).map
            emapr_mgr = OSUeMapR(wd=self.emapr_dir, bbox=_map.extent)
            emapr_mgr.retrieve(list(range(start_year, end_year+1)))

            self._emapr_mgr = emapr_mgr
        
    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()


    def analyze(self):
        start_year = self.emapr_start_year
        end_year = self.emapr_end_year

        wd = self.wd

        subwta_fn = Watershed.getInstance(wd).subwta

        assert _exists(subwta_fn)

        emapr_mgr = self._emapr_mgr

        with self.locked():
            data_ds = {}

            for year in range(start_year, end_year+1):
                for measure, statistic in OSUeMapR_Measures:
                    key = measure, statistic, year

                    emapr_ds = emapr_mgr.get_dataset(year=year, measure=measure, statistic=statistic)
                    data_ds[key] = emapr_ds.spatial_aggregation(subwta_fn=subwta_fn)

            key0 = list(data_ds.keys())[0]

            data = {topaz_id: {} for topaz_id in data_ds[key0]}
            for topaz_id in data_ds[key0]:
                for year in range(start_year, end_year+1):
                    data[topaz_id][year] = {}
                    for measure, statistic in OSUeMapR_Measures:
                        key = measure, statistic, year
                        data[topaz_id][year][(measure, statistic)] = data_ds[key][topaz_id]

            self.data = data
