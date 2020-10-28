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

from time import time
from enum import Enum
from glob import glob

# non-standard
import jsonpickle


from configparser import (
    RawConfigParser,
    NoOptionError,
    NoSectionError
)


from wepppy.all_your_base import isfloat, isint, isbool

_thisdir = os.path.dirname(__file__)
_config_dir = _join(_thisdir, 'configs')
_default_config = _join(_config_dir, '_defaults.cfg')


def get_configs():
    return [_split(fn)[-1][:-4] for fn in glob(_join(_config_dir, '*.cfg'))]


class TriggerEvents(Enum):
    ON_INIT_FINISH = 1
    LANDUSE_DOMLC_COMPLETE = 2
    LANDUSE_BUILD_COMPLETE = 5
    SOILS_BUILD_COMPLETE = 3
    PREPPING_PHOSPHORUS = 4
    WATERSHED_ABSTRACTION_COMPLETE = 5
    CLIMATE_BUILD_COMPLETE = 6
    WEPP_PREP_WATERSHED_COMPLETE = 7


class NoDbBase(object):
    def __init__(self, wd, cfg_fn):
        assert _exists(wd)
        self.wd = wd
        self._config = cfg_fn
        self._load_mods()

        # noinspection PyUnresolvedReferences
        if _exists(self._nodb):
            raise Exception('NoDb has already been initialized')

    @property
    def config_stem(self):
        return self._config.replace('.cfg', '')

    def config_get_bool(self, section: str, option: str, default=None):
        assert default is None or isbool(default)
        try:

            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return val.startswith('true')
        except (NoSectionError, NoOptionError):
            return default

    def config_get_float(self, section: str, option: str, default=None):
        assert default is None or isfloat(default)

        try:
            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return float(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_get_int(self, section: str, option: str, default=None):
        assert default is None or isint(default)

        try:
            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return int(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_get_str(self, section: str, option: str, default=None):

        try:
            val = self._configparser.get(section, option)
            if val.lower().startswith('none') or val == '':
                return default
            return val
        except (NoSectionError, NoOptionError):
            return default

    def config_get_path(self, section: str, option: str, default=None):
        from .mods import MODS_DIR
        path = self.config_get_str(section, option, default)
        if path is None:
            return None
        path = path.replace('MODS_DIR', MODS_DIR)
        return path

    def config_get_raw(self, section: str, option: str, default=None):
        val = self._configparser.get(section, option, fallback=default)
        return val

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
    def _configparser(self):
        cfg = _join(_config_dir, self._config)

        parser = RawConfigParser(allow_no_value=True)
        with open(_default_config) as fp:
            parser.read_file(fp)

        with open(cfg) as fp:
            parser.read_file(fp)

        return parser

    def _load_mods(self):
        config_parser = self._configparser
        mods = self.config_get_raw('nodb', 'mods')

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

        if 'general' in self.mods:
            general = wepppy.nodb.mods.locations.GeneralMod.getInstance(self.wd)
            general.on(evt)

        if 'baer' in self.mods:
            baer = wepppy.nodb.mods.Baer.getInstance(self.wd)
            baer.on(evt)

        if 'disturbed' in self.mods:
            disturbed = wepppy.nodb.mods.Disturbed.getInstance(self.wd)
            disturbed.on(evt)

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
