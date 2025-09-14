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

from .treecanopy_map import TreecanopyMap

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')



class TreecanopyNoDbLockedException(Exception):
    pass


nlcd_treecanopy_layers = ('treecanopy')


class TreecanopyPointData(object):
    def __init__(self, **kwds):
        self.treecanopy = kwds.get('treecanopy', None)


    @property
    def isvalid(self):
        return self.treecanopy is not None

    def __str__(self):
        return 'TreecanopyPointData(treecanopy={0.treecanopy})'.format(self)

    def __repr__(self):
        return self.__str__().replace(' ', '') \
                             .replace(',\n', ', ')


class Treecanopy(NoDbBase):
    __name__ = 'Treecanopy'

    def __init__(self, wd, cfg_fn):
        super(Treecanopy, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.treecanopy_dir)
            self.data = None

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
        with open(_join(wd, 'treecanopy.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Treecanopy), db

        if _exists(_join(wd, 'READONLY')):
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            if not db.islocked():
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Treecanopy.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
    
    @property
    def _nodb(self):
        return _join(self.wd, 'treecanopy.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'treecanopy.nodb.lock')

    @property
    def treecanopy_dir(self):
        return _join(self.wd, 'treecanopy')

    @property
    def treecanopy_fn(self):
        return _join(self.treecanopy_dir, 'treecanopy.asc')
    

    def acquire_raster(self):
        _map = Ron.getInstance(self.wd).map

        wmesque_retrieve('nlcd_treecanopy/2016', _map.extent,
                         self.treecanopy_fn, _map.cellsize,
                         v=self.wmesque_version, 
                         wmesque_endpoint=self.wmesque_endpoint)

    def on(self, evt):
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()

    def load_map(self):
        fn = self.treecanopy_fn
        assert _exists(fn)
        return TreecanopyMap(fn)

    def analyze(self):
        wd = self.wd
        subwta_fn = Watershed.getInstance(wd).subwta

        assert _exists(subwta_fn)

        self.lock()
        try:         
            treecanopy_map = self.load_map()
            self.data = treecanopy_map.spatial_aggregation(subwta_fn)

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

        treecanopy_map = self.load_map()
        d = treecanopy_map.spatial_stats(bound_fn)

        return d

    def __iter__(self):
        assert self.data is not None

        for topaz_id in self.data:
            yield topaz_id, TreecanopyPointData(treecanopy=self.data[topaz_id])
