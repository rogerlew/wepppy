# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import csv

import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
from enum import IntEnum
import time

# non-standard
import jsonpickle

# wepppy
from wepppy.landcover import LandcoverMap
from wepppy.wepp.management import get_management_summary
from wepppy.watershed_abstraction import ischannel
from wepppy.all_your_base import wmesque_retrieve

# wepppy submodules
from .base import NoDbBase, TriggerEvents, DEFAULT_NLCD_DB
from .ron import Ron
from .watershed import Watershed


class LanduseNoDbLockedException(Exception):
    pass


class LanduseMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    RRED_Unburned = 2
    RRED_Burned = 3


def read_cover_defaults(fn):
    with open(fn) as fp:
        d = {}
        rdr = csv.DictReader(fp)
        for row in rdr:
            d[row['key']] = row

    return d


class Landuse(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Landuse'

    def __init__(self, wd, cfg_fn):
        super(Landuse, self).__init__(wd, cfg_fn)

        self.lock()

        config = self.config

        # noinspection PyBroadException
        try:
            self._mode = LanduseMode.Gridded
            self._single_selection = 0  # No Data
            self._single_man = None
            self.domlc_d = None  # topaz_id keys, ManagementSummary values
            self.managements = None
            cover_defaults_fn = config.get('landuse', 'cover_defaults')

            if cover_defaults_fn is not None and cover_defaults_fn != '':
                from wepppy.nodb.mods import MODS_DIR
                cover_defaults_fn = cover_defaults_fn.replace('MODS_DIR', MODS_DIR)
                self.cover_defaults_d = read_cover_defaults(cover_defaults_fn)
            else:
                self.cover_defaults_d = None

            self._nlcd_db = config.get('landuse', 'nlcd_db')

            lc_dir = self.lc_dir
            if not _exists(lc_dir):
                os.mkdir(lc_dir)

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
        with open(_join(wd, 'landuse.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Landuse)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'landuse.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'landuse.nodb.lock')

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            if isinstance(value, LanduseMode):
                self._mode = value

            elif isinstance(value, int):
                self._mode = LanduseMode(value)

            else:
                raise ValueError('most be LanduseMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def single_selection(self):
        """
        id of the selected management
        """
        return self._single_selection

    @single_selection.setter
    def single_selection(self, landuse_single_selection):
        self.lock()

        # noinspection PyBroadException
        try:
            k = landuse_single_selection
            self._single_selection = k
            self._single_man = get_management_summary(k)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def single_man(self):
        """
        management summary object
        """
        return self._single_man

    @property
    def has_landuse(self):
        mode = self._mode

        if mode == LanduseMode.Undefined:
            return False

        else:
            return self.domlc_d is not None

    #
    # build
    #
    
    def clean(self):

        lc_dir = self.lc_dir
        if _exists(lc_dir):
            shutil.rmtree(lc_dir)
        os.mkdir(lc_dir)

    def _build_ESDAC(self):
        from wepppy.eu.soils.esdac import ESDAC
        esd = ESDAC()
        _map = Ron.getInstance(self.wd).map

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, summary in watershed.sub_iter():
            lng, lat = summary.centroid.lnglat
            d = esd.query(lng, lat, ['usedo'])
            assert 'usedom' in d, d
            dom = d['usedom'][1]
            domlc_d[topaz_id] = str(dom)

        for topaz_id, _ in watershed.chn_iter():
            lng, lat = summary.centroid.lnglat
            d = esd.query(lng, lat, ['usedo'])
            dom = d['usedom'][1]
            domlc_d[topaz_id] = str(dom)

        self.domlc_d = domlc_d

    def _build_lu10v5ua(self):
        from wepppy.au.landuse_201011 import Lu10v5ua
        lu = Lu10v5ua()
        _map = Ron.getInstance(self.wd).map

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, summary in watershed.sub_iter():
            lng, lat = summary.centroid.lnglat
            dom = lu.query_dom(lng, lat)
            domlc_d[topaz_id] = dom

        for topaz_id, _ in watershed.chn_iter():
            lng, lat = summary.centroid.lnglat
            dom = lu.query_dom(lng, lat)
            domlc_d[topaz_id] = dom

        self.domlc_d = domlc_d

    @property
    def nlcd_db(self):
        if not hasattr(self, "_nlcd_db"):
            return DEFAULT_NLCD_DB

        return self._nlcd_db

    @nlcd_db.setter
    def nlcd_db(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._nlcd_db = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_NLCD(self):
        _map = Ron.getInstance(self.wd).map

        # Get NLCD 2011 from wmesque webservice
        lc_fn = self.lc_fn
        wmesque_retrieve(self.nlcd_db, _map.extent, lc_fn, _map.cellsize)

        # create LandcoverMap instance
        lc = LandcoverMap(lc_fn)

        # build the grid
        # domlc_fn map is a property of NoDbBase
        # domlc_d is a dictionary with topaz_id keys
        self.domlc_d = lc.build_lcgrid(self.subwta_arc, None)

    def _build_single_selection(self):
        assert self.single_selection is not None

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, _ in watershed.sub_iter():
            domlc_d[topaz_id] = str(self.single_selection)

        for topaz_id, _ in watershed.chn_iter():
            domlc_d[topaz_id] = str(self.single_selection)

        self.domlc_d = domlc_d

    def build(self):

        if self._mode in [LanduseMode.RRED_Burned, LanduseMode.RRED_Unburned]:
            import wepppy
            rred = wepppy.nodb.mods.Rred.getInstance(self.wd)
            rred.build_landuse(self._mode)
            self = self.getInstance(self.wd)  # reload instance from .nodb
            self.build_managements()
            return

        self.lock()

        # noinspection PyBroadException
        try:
            self.clean()

            if self._mode == LanduseMode.Gridded:
                if self.config_stem in ['eu', 'eu-fire', 'eu-fire2']:
                    self._build_ESDAC()
                elif self.config_stem in ['au', 'au-fire']:
                    self._build_lu10v5ua()
                else:
                    self._build_NLCD()

            elif self._mode == LanduseMode.Single:
                self._build_single_selection()

            elif self._mode == LanduseMode.Undefined:
                raise Exception('LanduseMode is not set')

            self.dump_and_unlock()

            self.trigger(TriggerEvents.LANDUSE_DOMLC_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb
            self.build_managements()
            self.set_cover_defaults()

        except Exception:
            self.unlock('-f')
            raise

    def set_cover_defaults(self):

        defaults = self.cover_defaults_d

        if defaults is None:
            return

        time.sleep(0.5)
        self.lock()

        # noinspection PyBroadException
        try:
            for dom in self.managements:
                if dom in defaults:
                    for cover in ['cancov', 'inrcov', 'rilcov']:
                        self._modify_coverage(dom, cover, defaults[dom][cover])

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _modify_coverage(self, dom, cover, value):
        dom = str(dom)
        assert dom in self.managements

        assert cover in ['cancov', 'inrcov', 'rilcov']

        value = float(value)
        assert value >= 0.0
        assert value <= 1.0

        if cover in 'cancov':
            self.managements[dom].cancov_override = value
        elif cover in 'inrcov':
            self.managements[dom].inrcov_override = value
        elif cover in 'rilcov':
            self.managements[dom].rilcov_override = value

    def modify_coverage(self, dom, cover, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._modify_coverage(dom, cover, value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def modify_mapping(self, dom, newdom):
        self.lock()

        # noinspection PyBroadException
        try:
            dom = str(dom)
            newdom = str(newdom)
            assert dom in self.managements

            for topazid in self.domlc_d:
                if self.domlc_d[topazid] == dom:
                    self.domlc_d[topazid] = newdom

            self.dump_and_unlock()

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb
            self.build_managements()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def landuseoptions(self):
        from wepppy.wepp import management

        if self._mode in [LanduseMode.RRED_Unburned, LanduseMode.RRED_Burned]:
            _map = 'rred'
        elif self._mode == LanduseMode.Gridded and self.config_stem in ['eu']:
            _map = 'esdac'
        elif self._mode == LanduseMode.Gridded and self.config_stem in ['au']:
            _map = 'lu10v5ua'
        else:
            _map = None

        landuseoptions = management.load_map(_map).values()
        landuseoptions = sorted(landuseoptions, key=lambda d: d['Key'])
        landuseoptions = [opt for opt in landuseoptions if 'DisturbedWEPPManagement' not in opt['ManagementFile']]

        if 'baer' in self.mods:
            landuseoptions = [opt for opt in landuseoptions if 'Agriculture' not in opt['ManagementFile']]

        if "lt" in self.mods:
            landuseoptions = [opt for opt in landuseoptions if 'Tahoe' in opt['ManagementFile']]

        return landuseoptions

    def build_managements(self):
        self.lock()

        if self._mode in [LanduseMode.RRED_Unburned, LanduseMode.RRED_Burned]:
            _map = 'rred'
        elif self._mode == LanduseMode.Gridded and self.config_stem in ['eu']:
            _map = 'esdac'
        elif self._mode == LanduseMode.Gridded and self.config_stem in ['au']:
            _map = 'lu10v5ua'
        else:
            _map = None

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(self.wd)
            domlc_d = self.domlc_d
    
            # create a dictionary of management keys and
            # wepppy.landcover.ManagementSummary values
            managements = {}

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            total_area = watershed.totalarea
            for topaz_id, k in domlc_d.items():
                area = watershed.area_of(topaz_id)
                
                if k not in managements:
                    man = get_management_summary(k, _map)
                    man.area = area
                    managements[k] = man
                else:
                    managements[k].area += area

            for k in managements:
                coverage = 100.0 * managements[k].area / total_area
                managements[k].pct_coverage = coverage
                        
            # store the managements dict
            self.managements = managements
            self.dump_and_unlock()

            self.trigger(TriggerEvents.LANDUSE_BUILD_COMPLETE)

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        """
        returns a list of managements sorted by coverage in
        descending order
        """
        used_mans = set(self.domlc_d.values())
        report = [s for s in list(self.managements.values()) if str(s.key) in used_mans]
        report.sort(key=lambda x: x.pct_coverage, reverse=True)
        return [man.as_dict() for man in report]

    #
    # modify
    #
    def modify(self, topaz_ids, landuse):
        self.lock()

        # noinspection PyBroadException
        try:
            landuse = str(int(landuse))
            assert self.domlc_d is not None
            
            for topaz_id in topaz_ids:
                assert topaz_id in self.domlc_d
                self.domlc_d[topaz_id] = landuse
                
            self.dump_and_unlock()
            self.build_managements()
            
        except Exception:
            self.unlock('-f')
            raise
            
    def _x_summary(self, topaz_id):
        domlc_d = self.domlc_d
        
        if domlc_d is None:
            return None
            
        if str(topaz_id) in domlc_d:
            dom = str(domlc_d[str(topaz_id)])
            return self.managements[dom].as_dict()
        else:
            return None

    @property
    def legend(self):
        doms = sorted(set(self.domlc_d.values()))
        mans = [self.managements[dom] for dom in doms]
        descs = [man.desc for man in mans]
        colors = [man.color for man in mans]

        return list(zip(doms, descs, colors))

    def sub_summary(self, topaz_id):
        return self._x_summary(topaz_id)
        
    def chn_summary(self, topaz_id):
        return self._x_summary(topaz_id)
        
    @property
    def subs_summary(self):
        """
        returns a dictionary of topaz_id keys and
        management summaries as dicts
        """
        domlc_d = self.domlc_d
        mans = self.managements

        summary = {}
        for topaz_id, k in domlc_d.items():
            if ischannel(topaz_id):
                continue

            summary[topaz_id] = mans[k].as_dict()

        return summary

    def sub_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements
        
        assert mans is not None

        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if ischannel(topaz_id):
                    continue

                yield topaz_id, mans[k]
        
    @property
    def chns_summary(self):
        """
        returns a dictionary of topaz_id keys and jsonified 
        managements values
        """
        domlc_d = self.domlc_d
        mans = self.managements

        assert mans is not None
        
        summary = {}
        for topaz_id, k in domlc_d.items():
            if not ischannel(topaz_id):
                continue

            summary[topaz_id] = mans[k].as_dict()

        return summary

    def chn_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements
        
        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if not ischannel(topaz_id):
                    continue

                yield topaz_id, mans[k]

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        wd = self.wd
        
        translator = Watershed.getInstance(wd).translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        domlc_d = self.domlc_d
        
        if topaz_id in domlc_d:
            key = domlc_d[topaz_id]
            return self.managements[key]
            
        raise IndexError
