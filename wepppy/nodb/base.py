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
from enum import Enum, IntEnum
from glob import glob

import json

# non-standard
import jsonpickle


from configparser import (
    RawConfigParser,
    NoOptionError,
    NoSectionError
)


from .redis_prep import RedisPrep
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
    DEBUG = 0

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
        return self._config.split('.cfg')[0]

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

            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]

            elif val.startswith('"') and val.endswith("'"):
                val = val[1:-1]

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

    def config_get_list(self, section: str, option: str, default=None):
        val = self._configparser.get(section, option, fallback=default)

        if val is not None:
            val = ast.literal_eval(val)

        if val is None:
            val = []
        return val

    def set_attrs(self, attrs):
        if attrs is None:
            return

        if len(attrs) == 0:
            return

        if self.islocked():
            for k, v in attrs.items():
                setattr(self, k, v)
        else:
            self.lock()
            try:
                for k, v in attrs.items():
                    setattr(self, k, v)
                self.dump_and_unlock()
            except Exception:
                self.unlock('-f')
                raise

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

    @property
    def locales(self):
        from .ron import Ron
        ron = Ron.getInstance(self.wd)

        if hasattr(ron, '_locales'):
            return ron._locales

        config_stem = self.config_stem

        if config_stem in ('au', 'au-fire'):
            return 'au',
        elif config_stem in ('eu', 'eu-75', 'eu-fire', 'eu-fire2'):
            return 'eu',
        elif config_stem in ('lt', 'lt-fire-future-snow', 'lt-wepp_347f3bd', 'lt-wepp_bd16b69-snow'):
            return 'us', 'lt',
        elif config_stem in ('portland', 'portland-simfire-eagle-snow', 'portland-simfire-norse-snow',
                             'portland-snow', 'portland-wepp_64bf5aa_snow', 'portland-wepp_347f3bd',
                             'portland-wepp_bd16b69'):
            return 'us', 'portland'
        elif config_stem in ('seattle-simfire-eagle-snow', 'seattle-simfire-norse-snow', 'seattle-snow'):
            return 'us', 'seattle'
        else:
            return 'us',

    @property
    def stub(self):

        js = jsonpickle.encode(self)
        obj = json.loads(js)
        del js

        exclude = getattr(self, '__exclude__', None)

        if exclude is not None:
            for attr in exclude:
                if attr in obj:
                    del obj[attr]
        return obj

        # noinspection PyUnresolvedReferences
        with open(self._nodb, 'w') as fp:
            fp.write(js)

    def lock(self):
        if self.islocked():
            raise Exception('lock() called on an already locked nodb')

        if self.readonly:
            raise Exception('lock() called on readonly project')

        # noinspection PyUnresolvedReferences
        with open(self._lock, 'w') as fp:
            fp.write(str(time()))

        try:
                RedisPrep.getInstance(self.wd).set_locked_status(self.basename, True)
        except:
            pass

    @property
    def basename(self):
        return _split(self._lock)[-1].replace('.nodb.lock', '')

    def unlock(self, flag=None):
        if self.islocked():
            # noinspection PyUnresolvedReferences
            os.remove(self._lock)
            try:
                RedisPrep.getInstance(self.wd).set_locked_status(self.basename, False)
            except:
                pass
        else:
            if flag != '-f':
                raise Exception('unlock() called on an already unlocked nodb')

    def islocked(self):
        # noinspection PyUnresolvedReferences
        return _exists(self._lock)

    @property
    def runid(self):
        wd = self.wd
        if wd.endswith('/'):
            wd = wd[:-1]
        return _split(wd)[-1]

    @property
    def multi_ofe(self):
        import wepppy
        return getattr(wepppy.nodb.Wepp.getInstance(self.wd), '_multi_ofe', False)

    @property
    def readonly(self):
        return _exists(_join(self.wd, 'READONLY'))

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
    def DEBUG(self):
        return _exists(_join(self.wd, 'DEBUG'))

    @DEBUG.setter
    def DEBUG(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'DEBUG')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.DEBUG

        else:
            if self.readonly:
                os.remove(path)

            assert not self.DEBUG

    @property
    def VERBOSE(self):
        return _exists(_join(self.wd, 'VERBOSE'))

    @VERBOSE.setter
    def VERBOSE(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'VERBOSE')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.VERBOSE

        else:
            if self.VERBOSE:
                os.remove(path)

            assert not self.VERBOSE

    @property
    def _configparser(self):
        _config = self._config.split('?')

        cfg = _join(_config_dir, _config[0])

        parser = RawConfigParser(allow_no_value=True)
        with open(_default_config) as fp:
            parser.read_file(fp)

        with open(cfg) as fp:
            parser.read_file(fp)

        if len(_config) == 2:
            overrides = _config[1].split('&')
            overrides_d = {}
            for override in overrides:
                key, value = override.split('=')
                section, name = key.split(':')

                if section not in overrides_d:
                    overrides_d[section] = {}
                overrides_d[section][name] = value

            parser.read_dict(overrides_d)

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
            try:
                seattle = wepppy.nodb.mods.locations.SeattleMod.getInstance(self.wd)
                seattle.on(evt)
            except:
                pass
        if 'general' in self.mods:
            general = wepppy.nodb.mods.locations.GeneralMod.getInstance(self.wd)
            general.on(evt)

        if 'baer' in self.mods:
            baer = wepppy.nodb.mods.Baer.getInstance(self.wd)
            baer.on(evt)

        if 'disturbed' in self.mods:
            disturbed = wepppy.nodb.mods.Disturbed.getInstance(self.wd)
            disturbed.on(evt)

        if 'revegetation' in self.mods:
            reveg = wepppy.nodb.mods.Revegetation.getInstance(self.wd)
            reveg.on(evt)

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
    def taudem_wd(self):
        return _join(self.wd, 'dem', 'taudem')

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
        return _join(self.wd, 'landuse', 'nlcd.tif')

    @property
    def domlc_fn(self):
        return _join(self.wd, 'landuse', 'landcov.asc')

    @property
    def soils_dir(self):
        return _join(self.wd, 'soils')

    @property
    def ssurgo_fn(self):
        return _join(self.wd, 'soils', 'ssurgo.tif')

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
    def export_legacy_arc_dir(self):
        return _join(self.wd, 'export', 'legacy_arcmap')

    @property
    def observed_dir(self):
        return _join(self.wd, 'observed')

    @property
    def observed_fn(self):
        return _join(self.observed_dir, 'observed.csv')

    @property
    def ash_dir(self):
        return _join(self.wd, 'ash')

