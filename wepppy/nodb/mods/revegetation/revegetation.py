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

from copy import deepcopy

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

from glob import glob

import shutil
from time import sleep
from enum import IntEnum

# non-standard
import jsonpickle

from datetime import datetime

# non-standard


from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture

# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase

from wepppy.nodb.mods import RangelandCover
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.wepp.soils.utils import WeppSoilUtil, SoilMultipleOfeSynth

from wepppy.nodb.climate import Climate

from wepppy.nodb.wepp import Wepp

from wepppy.all_your_base import isfloat, NCPU

from ...base import NoDbBase, TriggerEvents

from wepppy.nodb.mods.disturbed.disturbed import read_disturbed_land_soil_lookup, migrate_land_soil_lookup


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class RevegetationNoDbLockedException(Exception):
    pass


class Revegetation(NoDbBase, LogMixin):
    __name__ = 'Revegetation'

    def __init__(self, wd, cfg_fn):
        super(Revegetation, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self.clean()

            self._h0_max_om = self.config_get_float('revegetation', 'h0_max_om')
            self._sol_ver = self.config_get_float('revegetation', 'sol_ver')

            self.reset_land_soil_lookup()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def lookup_fn(self):
        land_soil_lookup_path = self.config_get_path('revegetation', 'land_soil_lookup_path', None)
        if land_soil_lookup_path is None:
            return _join(self.revegetation_dir, 'revegetation_land_soil_lookup.csv')
        else:
            assert _exists(land_soil_lookup_path), land_soil_lookup_path
            return land_soil_lookup_path

    @property
    def default_land_soil_lookup_fn(self):
        _lookup_path = self.config_get_path('revegetation', 'land_soil_lookup', None)
        if _lookup_path is None:
            _lookup_path = _join(_data_dir, 'revegetation_land_soil_lookup.csv')
        return _lookup_path

    def reset_land_soil_lookup(self):
        if _exists(self.lookup_fn):
            os.remove(self.lookup_fn)
        shutil.copyfile(self.default_land_soil_lookup_fn, self.lookup_fn)

    @property
    def land_soil_replacements_d(self):
        default_fn = self.default_land_soil_lookup_fn
        _lookup_fn = self.lookup_fn

        lookup = read_disturbed_land_soil_lookup(_lookup_fn)
        for k in lookup:
            if 'pmet_kcb' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['pmet_kcb', 'pmet_rawp', 'rdmax', 'xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

            elif 'rdmax' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['rdmax', 'xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

            elif 'xmxlai' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['xmxlai'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

            elif 'keffflag' not in lookup[k]:
                migrate_land_soil_lookup(
                    default_fn, _lookup_fn, ['keffflag', 'lkeff'], {})
                return read_disturbed_land_soil_lookup(_lookup_fn)

        if ('loam', 'forest moderate sev fire') not in lookup:
            migrate_land_soil_lookup(
                default_fn, _lookup_fn, [], {})
            return read_disturbed_land_soil_lookup(_lookup_fn)

        return lookup

    @property
    def revegetation_dir(self):
        return _join(self.wd, 'revegetation')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.revegetation_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'revegetation.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Revegetation)

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'revegetation.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'revegetation.nodb.lock')

    def clean(self):
        revegetation_dir = self.revegetation_dir
        if _exists(revegetation_dir):
            shutil.rmtree(revegetation_dir)
        os.mkdir(revegetation_dir)


    def on(self, evt):

        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            pass

        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()

    @property
    def sol_ver(self):
        return getattr(self, '_sol_ver', 9005.0)

    @sol_ver.setter
    def sol_ver(self, value):
        self.lock()

        try:
            self._sol_ver = float(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def h0_max_om(self):
        return getattr(self, '_h0_max_om', None)

    def modify_soils(self):
        from wepppy.nodb import Ron, Landuse

        wd = self.wd
        sol_ver = self.sol_ver

        watershed = Watershed.getInstance(self.wd)
        soils = Soils.getInstance(wd)
        _land_soil_replacements_d = self.land_soil_replacements_d
        _h0_max_om= self.h0_max_om

        soils.lock()
        try:

            mukey_map = {}

            # burn all the soils
            soils_d = deepcopy(soils.soils)
            for mukey, soil_summary in soils.soils.items():
                soil_path = _join(soils.soils_dir, soil_summary.fname)

                soil_u = WeppSoilUtil(soil_path)
                texid = soil_u.simple_texture

                stack = []
                desc = []
                for disturbed_class in ('forest',
                                        'forest high sev fire',
                                        'forest moderate sev fire',
                                        'forest low sev fire'):
                    key = texid, disturbed_class
                    if key not in _land_soil_replacements_d:
                        texid = 'all'
                        key = (texid, disturbed_class)

                    replacements = _land_soil_replacements_d[key]
                    new = soil_u.to_over9000(replacements, h0_max_om=_h0_max_om,
                                             version=sol_ver)

                    disturbed_mukey = f'{mukey}-{texid}-{disturbed_class}'
                    disturbed_fn = f'{disturbed_mukey}.sol'
                    new.write(_join(soils.soils_dir, disturbed_fn))

                    desc.append(disturbed_class)
                    stack.append(_join(soils.soils_dir, disturbed_fn))

                # create soils with high, moderate, and low fire severity
                mofe_synth = SoilMultipleOfeSynth()
                mofe_synth.stack = stack
                sol_fn = soil_summary.fname.replace('.sol', '.reveg.sol')
                mofe_synth.write(_join(soils.soils_dir, sol_fn))

                # add soil to the soils dictionary
                reveg_mukey = mukey + '-reveg'
                soils_d[reveg_mukey] = SoilSummary(mukey=reveg_mukey,
                                                           fname=sol_fn,
                                                           soils_dir=soils.soils_dir,
                                                           desc=soil_summary.desc + ' reveg',
                                                           meta_fn=None,
                                                           build_date=str(datetime.now()))
                mukey_map[mukey] = reveg_mukey
            soils.soils = soils_d

            # update the soils dictionary to use the reveg soils
            domsoil_d = {}
            for topaz_id, mukey in soils.domsoil_d.items():
                domsoil_d[topaz_id] = mukey_map[mukey]

            soils.domsoil_d = domsoil_d

            # need to recalculate the pct_coverages
            for k in soils.soils:
                soils.soils[k].area = 0.0

            total_area = 0.0
            for topaz_id, k in soils.domsoil_d.items():
                sub_area = watershed.area_of(topaz_id)
                soils.soils[k].area += sub_area
                total_area += sub_area

            for k in soils.soils:
                coverage = 100.0 * soils.soils[k].area / total_area
                soils.soils[k].pct_coverage = coverage

            soils.dump_and_unlock()

        except Exception:
            soils.unlock('-f')
            raise
