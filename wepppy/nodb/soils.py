# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os

from os.path import join as _join
from os.path import exists as _exists
from datetime import datetime
import shutil
from enum import IntEnum

# non-standard
import jsonpickle

# wepppy
from wepppy.ssurgo import SurgoMap, StatsgoSpatial, SurgoSoilCollection, NoValidSoilsException
from wepppy.wepp.soilbuilder.webClient import validatemukeys, fetchsoils
from wepppy.watershed_abstraction import ischannel
from wepppy.all_your_base import wmesque_retrieve
from wepppy.wepp.management import get_management_summary

# wepppy submodules
from .base import NoDbBase, TriggerEvents
from .ron import Ron
from .watershed import Watershed


class SoilsNoDbLockedException(Exception):
    pass


class SoilsMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1


# noinspection PyPep8Naming
class Soils(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Soils'

    def __init__(self, wd, cfg_fn):
        super(Soils, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._mode = SoilsMode.Gridded
            self._single_selection = 0

            self.domsoil_d = None  # topaz_id keys
            self.soils = None
            self.clay_pct = None
            self._subs_summary = None
            self._chns_summary = None

            soils_dir = self.soils_dir
            if not _exists(soils_dir):
                os.mkdir(soils_dir)

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
        with open(_join(wd, 'soils.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Soils)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'soils.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'soils.nodb.lock')

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            if isinstance(value, SoilsMode):
                self._mode = value

            elif isinstance(value, int):
                self._mode = SoilsMode(value)

            else:
                raise ValueError('most be SoilsMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def single_selection(self):
        return self._single_selection

    @single_selection.setter
    def single_selection(self, mukey):
        self.lock()

        # noinspection PyBroadException
        try:
            self._single_selection = mukey
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_soils(self):
        mode = self.mode
        assert isinstance(mode, SoilsMode)

        if mode == SoilsMode.Undefined:
            return False

        else:
            return self.domsoil_d is not None

    @property
    def legend(self):
        mukeys = sorted(set(self.domsoil_d.values()))
        soils = [self.soils[mukey] for mukey in mukeys]
        descs = [soil.desc for soil in soils]
        colors = [soil.color for soil in soils]

        return list(zip(mukeys, descs, colors))

    #
    # build
    #
    
    def clean(self):

        soils_dir = self.soils_dir
        if _exists(soils_dir):
            shutil.rmtree(soils_dir)
        os.mkdir(soils_dir)

    def build_statsgo(self):
        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            statsgoSpatial = StatsgoSpatial()
            watershed = Watershed.getInstance(self.wd)

            domsoil_d = {}
            for topaz_id, sub in watershed.sub_iter():
                lng, lat = sub.centroid.lnglat
                mukey = statsgoSpatial.identify_mukey_point(lng, lat)
                domsoil_d[str(topaz_id)] = str(mukey)

            for topaz_id, chn in watershed.chn_iter():
                lng, lat = sub.centroid.lnglat
                mukey = statsgoSpatial.identify_mukey_point(lng, lat)
                domsoil_d[str(topaz_id)] = str(mukey)

            mukeys = set(domsoil_d.values())
            surgo_c = SurgoSoilCollection(mukeys, use_statsgo=True)
            surgo_c.makeWeppSoils()
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                summary = watershed.sub_summary(topaz_id)
                if summary is not None:  # subcatchment
                    soils[k].area += summary["area"]

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.totalarea
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.soils = soils
            self.clay_pct = self._calc_clay_pct(surgo_c)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    def build(self):
        if self.mode == SoilsMode.Gridded:
            self._build_gridded()
        elif self.mode == SoilsMode.Single:
            self._build_single()

    def _calc_clay_pct(self, surgo_c):
        fp = open(_join(self.soils_dir, 'clay_rpt.log'), 'w')
        fp.write('determining clay content for run {}\n'.format(self.wd))
        fp.write(str(datetime.now()) + '\n\n')

        clay_d = {}
        for mukey, soil in surgo_c.weppSoils.items():
            horizon0 = soil.getFirstHorizon()
            if horizon0 is None:
                clay_d[str(mukey)] = 0.0
                cokey = None
            else:
                clay_d[str(mukey)] = float(horizon0.claytotal_r)
                cokey = horizon0.cokey

            fp.write('mukey={}, cokey={}, clay={}\n'.format(mukey, cokey, clay_d[str(mukey)]))

        domsoil_d = self.domsoil_d
        assert clay_d is not None
        assert domsoil_d is not None

        totalarea = 0.0
        wsum = 0.0
        watershed = Watershed.getInstance(self.wd)
        for topaz_id, ss in watershed.sub_iter():
            mukey = domsoil_d[str(topaz_id)]
            clay = clay_d[str(mukey)]
            area = ss.area
            wsum += area * clay
            totalarea += area

            fp.write('topaz_id={} has mukey={} and area={}\n'.format(topaz_id, mukey, area))

        clay_pct = wsum / totalarea

        fp.write('\nclay_pct={}'.format(clay_pct))
        fp.close()

        return clay_pct

    def _build_single(self):

        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(self.wd)
            mukey = self.single_selection
            surgo_c = SurgoSoilCollection([mukey])
            surgo_c.makeWeppSoils()
            surgo_c.logInvalidSoils(wd=soils_dir)

            assert surgo_c.weppSoils[mukey].valid()
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}

            domsoil_d = {}
            for topaz_id, sub in watershed.sub_iter():
                domsoil_d[str(topaz_id)] = str(mukey)

            for topaz_id, chn in watershed.chn_iter():
                domsoil_d[str(topaz_id)] = str(mukey)

            soils[str(mukey)].pct_coverage = 100.0

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                summary = watershed.sub_summary(topaz_id)
                if summary is not None:  # subcatchment
                    soils[k].area += summary["area"]

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.soils = soils
            self.clay_pct = self._calc_clay_pct(surgo_c)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    def _build_gridded(self):
        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            _map = Ron.getInstance(self.wd).map
            watershed = Watershed.getInstance(self.wd)

            subwta_arc = self.subwta_arc
            ssurgo_fn = self.ssurgo_fn

            wmesque_retrieve('ssurgo/201703', _map.extent,
                             ssurgo_fn, _map.cellsize)

            # Make SSURGO Soils
            sm = SurgoMap(ssurgo_fn)
            mukeys = set(sm.mukeys)
            surgo_c = SurgoSoilCollection(mukeys)
            surgo_c.makeWeppSoils()
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

            valid = list(int(v) for v in soils.keys())

            try:
                domsoil_d = sm.build_soilgrid(
                    subwta_arc,
                    None,
                    valid_mukeys=valid
                )
            except NoValidSoilsException:
                self.dump_and_unlock()
                self.build_statsgo()
                return

            domsoil_d = {str(k): str(v) for k, v in domsoil_d.items()}

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                summary = watershed.sub_summary(topaz_id)
                if summary is not None:  # subcatchment
                    soils[k].area += summary["area"]

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.totalarea
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = {str(k): str(v) for k, v in domsoil_d.items()}
            self.soils = {str(k): v for k, v in soils.items()}
            self.clay_pct = self._calc_clay_pct(surgo_c)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        """
        returns a list of managements sorted by coverage in
        descending order
        """
        report = list(self.soils.values())
        report.sort(key=lambda x: x.pct_coverage, reverse=True)
        return [soil.as_dict() for soil in report]

    def _x_summary(self, topaz_id):
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        if str(topaz_id) in domsoil_d:
            mukey = str(domsoil_d[str(topaz_id)])
            return self.soils[mukey].as_dict()
        else:
            return None
            
    def sub_summary(self, topaz_id):
        return self._x_summary(topaz_id)
        
    def chn_summary(self, topaz_id):
        return self._x_summary(topaz_id)
        
    @property
    def subs_summary(self):
        """
        returns a dictionary of topaz_id keys and dictionary soils
        values
        """
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        soils = self.soils

        summary = {}
        for topaz_id, k in domsoil_d.items():
            if ischannel(topaz_id):
                continue

            summary[topaz_id] = soils[k].as_dict()

        return summary

    def sub_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if ischannel(topaz_id):
                    continue

                yield topaz_id, soils[k]
        
    @property
    def chns_summary(self):
        """
        returns a dictionary of topaz_id keys and jsonified soils
        values
        """
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        soils = self.soils

        summary = {}
        for topaz_id, k in domsoil_d.items():
            topaz_id = str(topaz_id)
            if not ischannel(topaz_id):
                continue

            summary[topaz_id] = soils[k].as_dict()

        return summary

    def chn_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if not ischannel(topaz_id):
                    continue

                yield topaz_id, soils[k]
        
    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is None:
            raise IndexError
        
        translator = Watershed.getInstance(self.wd).translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        
        if topaz_id in domsoil_d:
            topaz_id = str(topaz_id)
            k = domsoil_d[topaz_id]
            return soils[k]
    
        raise IndexError
