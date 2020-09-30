# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import ast
import os

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import sys

from time import time
from enum import Enum
from glob import glob

# non-standard
import jsonpickle

if sys.version_info > (2, 7):
    from configparser import RawConfigParser
else:
    # noinspection PyUnresolvedReferences
    from ConfigParser import RawConfigParser

_thisdir = os.path.dirname(__file__)
_config_dir = _join(_thisdir, 'configs')


def get_configs():
    return [_split(fn)[-1][:-4] for fn in glob(_join(_config_dir, '*.cfg'))]


DEFAULT_DEM_DB = 'ned1/2016'
DEFAULT_NLCD_DB = 'nlcd/2016'
DEFAULT_SSURGO_DB = 'ssurgo/201703'
DEFAULT_WEPP_CHN_TYPE = 'Default'
DEFAULT_CLIGEN_DB = '2015_stations.db'


class TriggerEvents(Enum):
    ON_INIT_FINISH = 1
    LANDUSE_DOMLC_COMPLETE = 2
    LANDUSE_BUILD_COMPLETE = 5
    SOILS_BUILD_COMPLETE = 3
    PREPPING_PHOSPHORUS = 4
    WATERSHED_ABSTRACTION_COMPLETE = 5
    CLIMATE_BUILD_COMPLETE = 6
    WEPP_PREP_WATERSHED_COMPLETE = 7

# .nodb are jsonpickle files
# The .nodb is used to distinguish these from regular json datafiles


class NoDbBase(object):
    def __init__(self, wd, cfg_fn):
        assert _exists(wd)
        self.wd = wd
        self._config = cfg_fn
        self._load_mods()

        # noinspection PyUnresolvedReferences
        if _exists(self._nodb):
            raise Exception('NoDb has already been initialized')

    def dump_and_unlock(self, validate=True):
        self.dump()
        self.unlock()

        if validate:
            nodb = type(self)

            # noinspection PyUnresolvedReferences
            nodb.getInstance(self.wd)

    def dump(self):
        if not self.islocked():
            raise Exception('cannot dump to unlocked db')

        js = jsonpickle.encode(self)
        # noinspection PyUnresolvedReferences
        with open(self._nodb, 'w') as fp:
            fp.write(js)

        # validate

    def lock(self):
        if self.islocked():
            raise Exception('lock() called on an already locked nodb')

        if self.readonly:
            raise Exception('lock() called on readonly project')

        # noinspection PyUnresolvedReferences
        with open(self._lock, 'w') as fp:
            fp.write(str(time()))

    def unlock(self, flag=None):
        if self.islocked():
            # noinspection PyUnresolvedReferences
            os.remove(self._lock)
        else:
            if flag != '-f':
                raise Exception('unlock() called on an already unlocked nodb')

    def islocked(self):
        # noinspection PyUnresolvedReferences
        return _exists(self._lock)

    @property
    def readonly(self):
        return _exists(_join(self.wd, 'READONLY'))

    @property
    def runid(self):
        return _split(self.wd)[-1].replace('/', '')

    @readonly.setter
    def readonly(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'READONLY')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.readonly

        else:
            if self.readonly:
                os.remove(path)

            assert not self.readonly

    @property
    def public(self):
        return _exists(_join(self.wd, 'PUBLIC'))

    @public.setter
    def public(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'PUBLIC')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.public

        else:
            if self.public:
                os.remove(path)

            assert not self.public


    @property
    def config(self):
        cfg = _join(_config_dir, self._config)

        parser = RawConfigParser(
            dict(boundary=None,
                 cover_defaults=None,
                 dem_db=DEFAULT_DEM_DB,
                 nlcd_db=DEFAULT_NLCD_DB,
                 ssurgo_db=DEFAULT_SSURGO_DB,
                 wepp_chn_type=DEFAULT_WEPP_CHN_TYPE,
                 cligen_db=DEFAULT_CLIGEN_DB),
            allow_no_value=True
        )
        with open(_join(_config_dir, '0.cfg')) as fp:
            parser.read_file(fp)

        with open(cfg) as fp:
            parser.read_file(fp)

        return parser

    @property
    def config_stem(self):
        return self._config.replace('.cfg', '')

    def _load_mods(self):
        cfg = self.config
        mods = cfg.get('nodb', 'mods')

        if mods is not None:
            mods = ast.literal_eval(mods)

        self._mods = mods

    def trigger(self, evt):
        assert isinstance(evt, TriggerEvents)
        import wepppy.nodb.mods

        if 'lt' in self.mods:
            lt = wepppy.nodb.mods.locations.LakeTahoe.getInstance(self.wd)
            lt.on(evt)

        if 'portland' in self.mods:
            portland = wepppy.nodb.mods.locations.PortlandMod.getInstance(self.wd)
            portland.on(evt)

        if 'seattle' in self.mods:
            seattle = wepppy.nodb.mods.locations.SeattleMod.getInstance(self.wd)
            seattle.on(evt)

        if 'baer' in self.mods:
            baer = wepppy.nodb.mods.Baer.getInstance(self.wd)
            baer.on(evt)

        if 'rred' in self.mods:
            rred = wepppy.nodb.mods.Rred.getInstance(self.wd)
            rred.on(evt)

        if 'shrubland' in self.mods:
            shrubland = wepppy.nodb.mods.Shrubland.getInstance(self.wd)
            shrubland.on(evt)

    @property
    def mods(self):
        return self._mods

    @property
    def dem_dir(self):
        return _join(self.wd, 'dem')

    @property
    def dem_fn(self):
        return _join(self.wd, 'dem', 'dem.tif')

    @property
    def topaz_wd(self):
        return _join(self.wd, 'dem', 'topaz')

    @property
    def chnjnt_arc(self):
        return _join(self.topaz_wd, 'CHNJNT.ARC')

    @property
    def netful_arc(self):
        return _join(self.topaz_wd, 'NETFUL.ARC')

    @property
    def subwta_arc(self):
        return _join(self.topaz_wd, 'SUBWTA.ARC')

    @property
    def bound_arc(self):
        return _join(self.topaz_wd, 'BOUND.ARC')

    @property
    def fvslop_arc(self):
        return _join(self.topaz_wd, 'FVSLOP.ARC')

    @property
    def relief_arc(self):
        return _join(self.topaz_wd, 'RELIEF.ARC')

    @property
    def wat_dir(self):
        return _join(self.wd, 'watershed')

    @property
    def wat_js(self):
        return _join(self.wd, 'watershed', 'wat.json')

    @property
    def lc_dir(self):
        return _join(self.wd, 'landuse')

    @property
    def lc_fn(self):
        return _join(self.wd, 'landuse', 'nlcd.asc')

    @property
    def domlc_fn(self):
        return _join(self.wd, 'landuse', 'landcov.asc')

    @property
    def soils_dir(self):
        return _join(self.wd, 'soils')

    @property
    def ssurgo_fn(self):
        return _join(self.wd, 'soils', 'ssurgo.asc')

    @property
    def domsoil_fn(self):
        return _join(self.wd, 'soils', 'soilscov.asc')

    @property
    def cli_dir(self):
        return _join(self.wd, 'climate')

    @property
    def wepp_dir(self):
        return _join(self.wd, 'wepp')

    @property
    def runs_dir(self):
        return _join(self.wd, 'wepp', 'runs')

    @property
    def output_dir(self):
        return _join(self.wd, 'wepp', 'output')

    @property
    def fp_runs_dir(self):
        return _join(self.wd, 'wepp', 'flowpaths', 'runs')

    @property
    def fp_output_dir(self):
        return _join(self.wd, 'wepp', 'flowpaths', 'output')

    @property
    def plot_dir(self):
        return _join(self.wd, 'wepp', 'plots')

    @property
    def stats_dir(self):
        return _join(self.wd, 'wepp', 'stats')

    @property
    def export_dir(self):
        return _join(self.wd, 'export')

    @property
    def export_winwepp_dir(self):
        return _join(self.wd, 'export', 'winwepp')

    @property
    def export_arc_dir(self):
        return _join(self.wd, 'export', 'arcmap')

    @property
    def observed_dir(self):
        return _join(self.wd, 'observed')

    @property
    def observed_fn(self):
        return _join(self.observed_dir, 'observed.csv')

    @property
    def ash_dir(self):
        return _join(self.wd, 'ash')
