# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from datetime import datetime
import shutil
from enum import IntEnum
from copy import deepcopy

from collections import Counter

# non-standard
import jsonpickle

import pandas as pd

# wepppy
from wepppy.soils.ssurgo import (
    SurgoMap, 
    StatsgoSpatial, 
    SurgoSoilCollection,
    SoilSummary
)
from wepppy.topo.watershed_abstraction.support import is_channel
from wepppy.all_your_base.geo import read_raster, raster_stacker
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.wepp.soils.soilsdb import load_db, get_soil

# wepppy submodules
from .base import (
    NoDbBase,
    TriggerEvents
)

from .ron import Ron
from .watershed import Watershed, WatershedNotAbstractedError
from .redis_prep import RedisPrep as Prep
from .mixins.log_mixin import LogMixin

try:
    import wepppyo3
    from wepppyo3.raster_characteristics import identify_mode_single_raster_key
    from wepppyo3.raster_characteristics import identify_mode_multiple_raster_key
except:
    wepppyo3 = None


class SoilsNoDbLockedException(Exception):
    pass


class SoilsMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    SingleDb = 2
    RRED_Unburned = 3
    RRED_Burned = 4


# noinspection PyPep8Naming
class Soils(NoDbBase, LogMixin):
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
            self._single_dbselection = None

            self._ssurgo_db = self.config_get_path('soils', 'ssurgo_db')

            self.domsoil_d = None  # topaz_id keys
            self.ssurgo_domsoil_d = None

            self.soils = None
            self._subs_summary = None
            self._chns_summary = None
            
            self._initial_sat = 0.75
            self._ksflag = self.config_get_bool('soils', 'ksflag')
            self._clip_soils = self.config_get_bool('soils', 'clip_soils', False)
            self._clip_soils_depth = self.config_get_float('soils', 'clip_soils', 1000)

            soils_dir = self.soils_dir
            if not _exists(soils_dir):
                os.mkdir(soils_dir)

            self._soils_map = self.config_get_path('soils', 'soils_map', None)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd, allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'soils.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read().replace('"simple_texture"', '"_simple_texture"')
                                            .replace('"texture"', '"_texture"')
                                            .replace('"clay_pct"', '"_deprecated_clay_pct"')
                                            .replace('"sand"', '"_deprecated_sand"')
                                            .replace('"avke"', '"_deprecated_avke"')
                                            .replace('"ll"', '"_deprecated_ll"')
                                            .replace('"liquid_limit"', '"_deprecated_liquid_limit"')
                                            .replace('"clay"', '"_deprecated_clay"'))
            assert isinstance(db, Soils)

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @property
    def _status_channel(self):
        return f'{self.runid}:soils'

    @property
    def _nodb(self):
        return _join(self.wd, 'soils.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'soils.nodb.lock')

    @property
    def clip_soils(self):
        return getattr(self, '_clip_soils', False)

    @clip_soils.setter
    def clip_soils(self, value: bool):
        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_soils = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def clip_soils_depth(self):
        return getattr(self, '_clip_soils_depth', 1000)

    @clip_soils_depth.setter
    def clip_soils_depth(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_soils_depth = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def initial_sat(self):
        return getattr(self, '_initial_sat', 0.75)

    @initial_sat.setter
    def initial_sat(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._initial_sat = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def ksflag(self):
        if not hasattr(self, '_ksflag'):
            return True

        return self._ksflag

    @ksflag.setter
    def ksflag(self, value):
        assert value in (True, False)

        self.lock()

        # noinspection PyBroadException
        try:
            self._ksflag = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

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
    def soils_map(self):
        return getattr(self, '_soils_map', None)

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
    def single_dbselection(self):
        return getattr(self, '_single_dbselection', None)

    @single_dbselection.setter
    def single_dbselection(self, sol):
        self.lock()

        # noinspection PyBroadException
        try:
            self._single_dbselection = sol
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

    @property
    def ssurgo_db(self):
        return getattr(self, '_ssurgo_db', self.config_get_str('soils', 'ssurgo_db'))

    @ssurgo_db.setter
    def ssurgo_db(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._ssurgo_db = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build_statsgo(self, initial_sat=None, ksflag=None):
        wd = self.wd
        watershed = Watershed.getInstance(wd)
        if not watershed.is_abstracted:
            raise WatershedNotAbstractedError()

        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = bool(ksflag)
 
            statsgoSpatial = StatsgoSpatial()
            watershed = Watershed.getInstance(wd)

            domsoil_d = {}
            for topaz_id, sub in watershed.sub_iter():
                lng, lat = sub.centroid.lnglat
                mukey = statsgoSpatial.identify_mukey_point(lng, lat)
                domsoil_d[str(topaz_id)] = str(mukey)

            for topaz_id, chn in watershed.chn_iter():
                lng, lat = chn.centroid.lnglat
                mukey = statsgoSpatial.identify_mukey_point(lng, lat)
                domsoil_d[str(topaz_id)] = str(mukey)

            mukeys = set(domsoil_d.values())
            surgo_c = SurgoSoilCollection(mukeys, use_statsgo=True)
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

            # all the mukeys might not be valid. Need to identify the most common so we can use this instead
            valid_k_counts = Counter() 
            for topaz_id, k in domsoil_d.items():
                if k in soils:
                    valid_k_counts[k] += 1

            # now assign hillslopes with invalid mukeys the most common valid mukey
            most_common_k = valid_k_counts.most_common()[0][0]
            for topaz_id, k in domsoil_d.items():
                if k not in soils:
                    domsoil_d[topaz_id] = most_common_k

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.area_of(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils
#            self.clay_pct = self._calc_clay_pct(clay_d)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    def _build_by_identify(self, build_func):
        soils_dir = self.soils_dir
        wd = self.wd
        self.lock()

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(wd)

            orders = []
            for topaz_id, sub in watershed.sub_iter():
                orders.append([topaz_id, sub.centroid.lnglat])

            for topaz_id, chn in watershed.chn_iter():
                orders.append([topaz_id, chn.centroid.lnglat])

            soils, domsoil_d = build_func(orders, soils_dir)
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.area_of(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise


    def _build_from_map_db(self):
        from wepppy.wepp.soils.utils import WeppSoilUtil

        wd = self.wd
        watershed = Watershed.getInstance(wd)

        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            assert _exists(self.soils_map)
            soils_db_dir = _join(_split(self.soils_map)[0], 'db')

            soils_fn = _join(soils_dir, 'soils.tif')
            if _exists(soils_fn):
                os.remove(soils_fn)

            raster_stacker(self.soils_map, watershed.dem_fn, soils_fn)

            domsoil_d = identify_mode_single_raster_key(
                key_fn=watershed.subwta, parameter_fn=soils_fn, ignore_channels=True, ignore_keys=set())
            domsoil_d = {str(k): str(v) for k, v in domsoil_d.items()}

            self.log(f'domsoil_d: {repr(domsoil_d)}')

            soils = {}
            for topaz_id, mukey in domsoil_d.items():
                sol_fn = _join(soils_dir, f'{mukey}.sol')
                if not _exists(sol_fn):
                    shutil.copyfile(_join(soils_db_dir,  f'{mukey}.sol'), sol_fn)

                if mukey not in soils:
                    wsu = WeppSoilUtil(sol_fn)
                    soils[mukey] = SoilSummary(
                        mukey=mukey,
                        fname=f'{mukey}.sol',
                        soils_dir=soils_dir,
                        build_date=str(datetime.now()),
                        desc=wsu.obj['ofes'][0]['slid'],
                        pct_coverage=0.0
                    )

            self.log(repr(soils))

            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.area_of(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise



    def build(self, initial_sat=None, ksflag=None):

        wd = self.wd
        watershed = Watershed.getInstance(wd)
        if not watershed.is_abstracted:
            raise WatershedNotAbstractedError()

        ron = Ron.getInstance(wd)

        if self.soils_map is not None:
             self._build_from_map_db()
        elif self.config_stem.startswith('ak'):
            self._build_ak()
        elif self.mode == SoilsMode.Gridded:
            if 'eu' in ron.locales:
                from wepppy.eu.soils import build_esdac_soils
                self._build_by_identify(build_esdac_soils)
            elif 'au' in ron.locales:
                from wepppy.au.soils import build_asris_soils
                self._build_by_identify(build_asris_soils)
            else:
                self._build_gridded(initial_sat=initial_sat, ksflag=ksflag)
        elif self.mode == SoilsMode.Single:
            self._build_single(initial_sat=initial_sat, ksflag=ksflag)
        elif self.mode == SoilsMode.SingleDb:
            self._build_singledb()
        elif self._mode in [SoilsMode.RRED_Burned, SoilsMode.RRED_Unburned]:
            import wepppy
            rred = wepppy.nodb.mods.Rred.getInstance(self.wd)
            rred.build_soils(self._mode)
            return

        self = Soils.getInstance(self.wd)
        self.dump_soils_parquet()

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('build_soils')
        except FileNotFoundError:
            pass

    @property
    def bd_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.bd
        return d 

    @property
    def clay_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.clay
        return d 

    @property
    def sand_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.clay
        return d 

    @property
    def ll_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.liquid_limit
        return d 

    @property
    def clay_pct(self):
        clay_d = self.clay_d
        domsoil_d = self.ssurgo_domsoil_d

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

        clay_pct = wsum / totalarea

        return clay_pct

    @property
    def liquid_limit(self):
        ll_d = self.ll_d

        domsoil_d = self.domsoil_d
        assert domsoil_d is not None

        totalarea = 0.0
        wsum = 0.0
        watershed = Watershed.getInstance(self.wd)
        for topaz_id, ss in watershed.sub_iter():
            mukey = domsoil_d[str(topaz_id)]
            ll = ll_d[str(mukey)]
            if ll is None:
                continue

            area = ss.area
            wsum += area * ll
            totalarea += area

        ll_pct = wsum / totalarea

        return ll_pct

    def _build_ak(self):
        wd = self.wd
        self.lock()

        # noinspection PyBroadException
        try:

            watershed = Watershed.getInstance(wd)
            mukey = -9999

            domsoil_d = {}
            soils = {str(mukey): SoilSummary(
                        mukey=mukey,
                        fname=None,
                        soils_dir=None,
                        build_date=str(datetime.now()),
                        desc=None,
                        pct_coverage=100.0
                    )}

            for topaz_id, sub in watershed.sub_iter():
                domsoil_d[str(topaz_id)] = str(mukey)

            for topaz_id, chn in watershed.chn_iter():
                domsoil_d[str(topaz_id)] = str(mukey)

            soils[str(mukey)].pct_coverage = 100.0

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    def _build_single(self, initial_sat=None, ksflag=True):

        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = None

            watershed = Watershed.getInstance(self.wd)
            mukey = self.single_selection
            surgo_c = SurgoSoilCollection([mukey])
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)
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
                soils[k].area += watershed.area_of(topaz_id)

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)

            self.soils = soils
            #self.clay_pct = self._calc_clay_pct(clay_d)

            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb

        except Exception:
            self.unlock('-f')
            raise

    def _build_singledb(self):

        wd = self.wd

        if self.single_dbselection is None:
            self.single_dbselection = load_db()[0]
            self = self.getInstance(wd)

        soils_dir = self.soils_dir

        self.lock()

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(wd)
            key = self.single_dbselection

            sol = get_soil(key)
            fn = _split(sol)[-1]

            mukey = key.replace('/', '-').replace('.sol', '')
            soils = {mukey: SoilSummary(
                mukey=mukey,
                fname=fn,
                soils_dir=soils_dir,
                build_date=str(datetime.now()),
                desc=key
            )}

            shutil.copyfile(sol, _join(soils_dir, fn))

            domsoil_d = {}
            for topaz_id, sub in watershed.sub_iter():
                domsoil_d[str(topaz_id)] = mukey

            for topaz_id, chn in watershed.chn_iter():
                domsoil_d[str(topaz_id)] = mukey

            soils[mukey].pct_coverage = 100.0

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, sub in watershed.sub_iter():
                soils[mukey].area += watershed.area_of(topaz_id)

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)

            self.soils = soils
            self.dump_and_unlock()

            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb
        except Exception:
            self.unlock('-f')
            raise

    @property
    def status_log(self):
        return os.path.abspath(_join(self.soils_dir, 'status.log'))

    def _build_gridded(self, initial_sat=None, ksflag=None):
        global wepppyo3

        soils_dir = self.soils_dir
        self.lock()

        # noinspection PyBroadException
        try:
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = ksflag

            _map = Ron.getInstance(self.wd).map
            watershed = Watershed.getInstance(self.wd)

            ssurgo_fn = self.ssurgo_fn

            wmesque_retrieve(self.ssurgo_db, _map.extent,
                             ssurgo_fn, _map.cellsize)

            # Make SSURGO Soils
            sm = SurgoMap(ssurgo_fn)
            mukeys = set(sm.mukeys)
            self.log(f"ssurgo mukeys: {mukeys}")
            self.log_done()

            surgo_c = SurgoSoilCollection(mukeys)
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)

            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

            self.log(f"valid mukeys: {soils.keys()}")
            self.log_done()


            valid = list(int(v) for v in soils.keys())

            if wepppyo3 is None:
                self.log(f"using build_soilgrid {valid}")
                domsoil_d = sm.build_soilgrid(
                    watershed.subwta
                )
                self.log_done()
            else:
                self.log(f"using wepppyo3 {valid}")
                domsoil_d = identify_mode_single_raster_key(
                    key_fn=watershed.subwta, parameter_fn=ssurgo_fn, ignore_channels=True, ignore_keys=set())
                domsoil_d = {k: str(v) for k, v in domsoil_d.items()}
                self.log_done()

            dom_mukey = None
            for mukey, count in Counter(domsoil_d.values()).most_common():
                if mukey in soils:
                    dom_mukey = mukey
                    break

            if dom_mukey is None:
                if len(valid) > 0:
                    dom_mukey = str(valid[0])


            if dom_mukey is None:
                self.log('no surgo keys found, falling back to statsgo')
                self.dump_and_unlock()
                self.build_statsgo(initial_sat=self.initial_sat,
                                   ksflag=self.ksflag)
                return

            for topaz_id, mukey in domsoil_d.items():
                if mukey not in soils:
                    domsoil_d[topaz_id] = dom_mukey

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            self.log('calculating soil coverage')
            for k in soils:
                soils[k].area = 0.0

            total_area = watershed.wsarea
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.area_of(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / total_area
                soils[k].pct_coverage = coverage


            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = {str(k): v for k, v in soils.items()}

            self.dump_and_unlock()

            self.log('triggering SOILS_BUILD_COMPLETE')
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
        used_soils = set([str(x) for x in self.domsoil_d.values()])
        report = [s for s in list(self.soils.values()) if str(s.mukey) in used_soils]

        return [soil.as_dict(abbreviated=True) for soil in report]

    def _x_summary(self, topaz_id, abbreviated=False):
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        if str(topaz_id) in domsoil_d:
            mukey = str(domsoil_d[str(topaz_id)])
            return self.soils[mukey].as_dict(abbreviated=abbreviated)
        else:
            return None
            
    def sub_summary(self, topaz_id, abbreviated=False):
        return self._x_summary(topaz_id, abbreviated=abbreviated)
        
    def chn_summary(self, topaz_id, abbreviated=False):
        return self._x_summary(topaz_id, abbreviated=abbreviated)
        
    @property
    def subs_summary(self):
        """
        Returns a dictionary with topaz_id keys and dictionary soils values.
        """
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        soils = self.soils
        
        # Cache soil dictionaries to avoid multiple calls to as_dict for the same soil
        soil_dicts_cache = {mukey: soil.as_dict() for mukey, soil in soils.items()}

        # Compile the summary using cached soil dictionaries
        summary = {
            topaz_id: soil_dicts_cache[mukey] 
            for topaz_id, mukey in domsoil_d.items() 
            if not is_channel(topaz_id)
        }

        return summary

    def dump_soils_parquet(self):
        """
        Dumps the subs_summary to a Parquet file using Pandas.
        """
        self.log('creating soils parquet table')
        subs_summary = self.subs_summary
        assert subs_summary is not None

        df = pd.DataFrame.from_dict(subs_summary, orient='index')
        df.index.name = 'TopazID'
        df.reset_index(inplace=True)
        df['TopazID'] = df['TopazID'].astype(str).astype('int64')
        df['mukey'] = df['mukey'].astype(str)

        df.to_parquet(_join(self.soils_dir, 'soils.parquet'))


    def sub_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if is_channel(topaz_id):
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
            if not is_channel(topaz_id):
                continue

            summary[topaz_id] = soils[k].as_dict()

        return summary

    def chn_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if not is_channel(topaz_id):
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

