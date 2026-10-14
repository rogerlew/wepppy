"""Persist a current Builder config, reopen using the committed reader-floor class/catalog."""
import ast
import configparser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from wepppy.nodb.config_builder import BuilderSelections, resolve_builder_config
from wepppy.nodb.locales.capability_graph import capability_structure_sha256
import wepppy.nodb.project_config_capabilities as authority


class ParsedConfig:
    def __init__(self, text):
        self._configparser = configparser.ConfigParser(interpolation=None)
        self._configparser.optionxform = str
        self._configparser.read_string(text)

    def config_get_raw(self, section, option, default=None):
        return self._configparser.get(section, option, raw=True, fallback=default)

    def config_get_list(self, section, option, default=None):
        value = self.config_get_raw(section, option, default)
        return ast.literal_eval(value) if isinstance(value, str) else value


out = Path(__file__).parent
repo = Path('/workdir/wepppy')
revision = '26c9e86ca'
records = []
with TemporaryDirectory(prefix='edde-reader-floor-') as temporary:
    floor = Path(temporary)
    for relative in ['capability_graph.py', 'capability_structures/catalog.json']:
        content = subprocess.check_output(['git', 'show', revision + ':wepppy/nodb/locales/' + relative], cwd=repo)
        destination = floor / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    spec = importlib.util.spec_from_file_location('edde_reader_floor', floor / 'capability_graph.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for locale in ('continental-us', 'canada'):
        for single in (False, True):
            for representation in ('single-ofe','multiple-ofe'):
                us = locale == 'continental-us'
                resolved = resolve_builder_config(BuilderSelections(
                    locale=locale, capability_profile=f'{locale}-capabilities', dem='usgs-ned1-2024' if us else 'copernicus-dem-30',
                    delineation_backend='wbt', watershed_representation=representation,
                    wepp_binary='wepp_260803', soil='ssurgo-gnatsgso-2025' if us else 'isric-global',
                    landuse='nlcd-2019' if us else 'c3s-landcover-2020', climate='future_edde_v2',
                    climate_station_database='cligen-stations-2015' if us else 'cligen-stations-ghcn',
                    mods=(), single_user_defined_uploads=single))
                path = floor / f'{locale}-{single}-{representation}.cfg'
                path.write_bytes(resolved.config_bytes)
                before = path.read_bytes()
                current = authority.capability_authority(ParsedConfig(path.read_text()))
                original = authority.CapabilityGraph
                try:
                    authority.CapabilityGraph = module.CapabilityGraph
                    reopened = authority.capability_authority(ParsedConfig(path.read_text()))
                finally:
                    authority.CapabilityGraph = original
                assert reopened.as_config_sections() == current.as_config_sections()
                assert path.read_bytes() == before
                assert 'future_edde_v2' in reopened.climate_datasets
                records.append({'locale':locale,'single_inputs':single,'representation':representation,
                    'structure':capability_structure_sha256(reopened),'reopened_equal':True,'stored_bytes_unchanged':True})
(out/'reader-floor-reopen.json').write_text(json.dumps({'reader_revision':revision,'cases':records},indent=2)+'\n')
print('Exact committed reader reopened all eight persisted current-writer configurations unchanged')
