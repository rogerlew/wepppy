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
revision = sys.argv[1] if len(sys.argv) > 1 else 'e25299022'
cases = [(False, 'single-ofe')] if revision == 'e25299022' else [
    (single, representation) for single in (False, True)
    for representation in ('single-ofe', 'multiple-ofe')]
records = []

with TemporaryDirectory(prefix='prism-reader-floor-') as temporary:
    floor = Path(temporary)
    files = ['capability_graph.py', 'capability_structures/catalog.json']
    for relative in files:
        source = revision + ':wepppy/nodb/locales/' + relative
        content = subprocess.check_output(['git', 'show', source], cwd=repo)
        destination = floor / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    spec = importlib.util.spec_from_file_location('prism_reader_floor', floor / 'capability_graph.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for single, representation in cases:
        resolved = resolve_builder_config(BuilderSelections(
            locale='continental-us', dem='usgs-ned1-2024', delineation_backend='wbt',
            watershed_representation=representation, wepp_binary='wepp_260803',
            soil='ssurgo-gnatsgso-2025', landuse='nlcd-2019',
            climate='observed_prism_800m', mods=(), single_user_defined_uploads=single,
        ))
        name = 'new-writer-project.cfg' if revision == 'e25299022' else f'new-writer-single-{single}-{representation}.cfg'
        path = out / name
        path.write_bytes(resolved.config_bytes)
        before = path.read_bytes()
        current = authority.capability_authority(ParsedConfig(path.read_text()))
        assert 'observed_prism_800m' in current.climate_datasets
        # Parsing code is unchanged; use the exact committed reader and catalog.
        original = authority.CapabilityGraph
        try:
            authority.CapabilityGraph = module.CapabilityGraph
            reopened = authority.capability_authority(ParsedConfig(path.read_text()))
        finally:
            authority.CapabilityGraph = original
        assert reopened.as_config_sections() == current.as_config_sections()
        assert path.read_bytes() == before
        identity = capability_structure_sha256(reopened)
        expected = ('545e2197c8a67a88da9c796246a2b0572427c8228bcb0e5d3ccd883f11b320a6' if single else
                    '2c2934682af720fac7d022aa22f830087a10f2f423e4cb329d2a23c88c6ef1d3')
        assert identity == expected
        records.append({'structure': identity, 'stored_config': path.name,
                        'single_inputs': single, 'representation': representation,
                        'reopened_equal': True, 'stored_bytes_unchanged': True})

record = {'reader_revision': revision, 'cases': records,
          'scope': 'Isolated persisted Builder configs; target project graph was not migrated'}
filename = 'reader-floor-reopen.json' if revision == 'e25299022' else 'aggregate-reader-floor-reopen.json'
(out / filename).write_text(json.dumps(record, indent=2) + '\n')
print(record)
