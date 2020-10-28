from os.path import join as _join

from wepppy.all_your_base import isbool, isint, isfloat

from configparser import (
    RawConfigParser,
    ConverterMapping,
    SectionProxy,
    Interpolation,
    NoOptionError,
    NoSectionError
)

class ConfigMixin(object):


    @property
    def _config(self):
        cfg = _join(_config_dir, self._config)

        parser = RawConfigParser(allow_no_value=True)
        with open(_join(_config_dir, '0.cfg')) as fp:
            parser.read_file(fp)

        with open(cfg) as fp:
            parser.read_file(fp)

        return parser

    @property
    def config_stem(self):
        return self._config.replace('.cfg', '')


    def config_get_bool(self, section: str, option: str, default=None):
        assert default is None or isbool(default)
        try:

            val = self._config.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return val.startswith('true')
        except (NoSectionError, NoOptionError):
            return default

    def config_get_float(self, section: str, option: str, default=None):
        assert default is None or isfloat(default)

        try:
            val = self._config.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return float(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_get_int(self, section: str, option: str, default=None):
        assert default is None or isint(default)

        try:
            val = self._config.get(section, option).lower()
            if val.startswith('none') or val == '':
                return default
            return int(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_get_str(self, section: str, option: str, default=None):

        try:
            val = self._config.get(section, option)
            if val.lower().startswith('none') or val == '':
                return default
            return val
        except (NoSectionError, NoOptionError):
            return default

    def config_get_path(self, section: str, option: str, default=None):
        from ..mods import MODS_DIR
        path = self.config_get_str(section, option, default)
        if path is None:
            return None
        path = path.replace('MODS_DIR', MODS_DIR)
        return path

    def config_get_raw(self, section: str, option: str, default=None):
        val = self._config.get(section, option)
        return val