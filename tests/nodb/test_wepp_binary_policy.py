"""Live executable choices preserve saved project configuration and NoDb state."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from wepppy.nodb.wepp_binary_policy import project_wepp_binary_options, validate_project_wepp_binary_selection
from wepppy.nodb.locales.capability_graph import (
    build_continental_us_capability_graph, capability_structure_payload, CapabilityGraphError,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def old_project(tmp_path, monkeypatch):
    from wepppy.nodb.config_builder import registry as registry_module
    from wepppy.nodb.config_builder.snapshot import parse_builder_selections, resolve_builder_candidate
    from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot
    from wepppy.nodb.core import Climate, Watershed, Wepp
    installed = registry_module.get_linux_wepp_bin_opts()
    with monkeypatch.context() as isolated:
        isolated.setattr(registry_module, 'get_linux_wepp_bin_opts', lambda: [item for item in installed if item not in ('wepp_261010', 'wepp_261021', 'wepp_261026')])
        registry = registry_module.load_registry()
    selections = parse_builder_selections(dict(
        locale='continental-us', dem='usgs-ned13-2022', delineation_backend='wbt',
        watershed_representation='multiple-ofe', wepp_binary='wepp_260803',
        soil='ssurgo-gnatsgso-2025', landuse='nlcd-2019', climate='vanilla_cligen',
        climate_station_database='cligen-stations-2015', mods=[],
    ))
    candidate = resolve_builder_candidate(selections, registry=registry)
    assert 'wepp_261010' not in candidate.artifact.config_bytes.decode()
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    monkeypatch.setenv('WEPPPY_PROJECT_CONFIG_READER_ENABLED', '1')
    (tmp_path / 'dem').mkdir()
    Climate(str(tmp_path), 'config.cfg')
    Watershed(str(tmp_path), 'config.cfg')
    return Wepp(str(tmp_path), 'config.cfg')


@pytest.mark.parametrize('binary', ['wepp_261010', 'wepp_261021', 'wepp_261026'])
def test_old_builder_project_can_persist_new_release_without_config_migration(old_project, tmp_path, binary):
    from wepppy.nodb.core import Wepp
    before = {name: (tmp_path / name).read_bytes() for name in ('config.cfg', 'config-manifest.json')}
    assert project_wepp_binary_options(old_project) == ('wepp_260803', 'wepp_261010', 'wepp_261021', 'wepp_261026')
    old_project.parse_inputs({'wepp_bin': binary})
    assert Wepp.load_detached(str(tmp_path)).wepp_bin == binary
    assert all((tmp_path / name).read_bytes() == content for name, content in before.items())


@pytest.mark.parametrize('binary', ['../wepp_261010', '/tmp/solver', 'not-installed', '', 'wepp_dcc52a6'])
def test_rejected_change_does_not_mutate_nodb(old_project, tmp_path, binary):
    before = (tmp_path / 'wepp.nodb').read_bytes()
    with pytest.raises(ValueError, match='not installed or does not support'):
        old_project.parse_inputs({'wepp_bin': binary, 'kslast': 99})
    assert (tmp_path / 'wepp.nodb').read_bytes() == before
    assert old_project.wepp_bin == 'wepp_260803'


@pytest.mark.parametrize('binary', [None, ['']])
def test_empty_list_or_none_preserves_current_binary(old_project, binary):
    old_project.parse_inputs({'wepp_bin': binary})
    assert old_project.wepp_bin == 'wepp_260803'


def test_saved_legacy_upload_choice_survives_actual_parser(old_project, tmp_path, monkeypatch):
    from wepppy.nodb.core import Wepp
    # Isolate the optional upload flag; real parser, locks, sidecar policy and persistence remain active.
    getter = Wepp.config_get_str
    monkeypatch.setattr(Wepp, 'config_get_str', lambda self, section, option, default=None:
                        'True' if (section, option) == ('nodb', 'single_user_defined_uploads')
                        else getter(self, section, option, default))
    monkeypatch.setattr(Wepp, 'mods', property(lambda self: []))
    with old_project.locked():
        old_project._wepp_bin = 'wepp_260726'  # Installed legacy release, no new declarations.
    old_project.parse_inputs({})
    old_project.parse_inputs({'wepp_bin': 'wepp_260726'})
    assert Wepp.load_detached(str(tmp_path)).wepp_bin == 'wepp_260726'
    before = (tmp_path / 'wepp.nodb').read_bytes()
    with pytest.raises(ValueError):
        old_project.parse_inputs({'wepp_bin': 'wepp_250217'})
    assert (tmp_path / 'wepp.nodb').read_bytes() == before


class V1Config:
    wepp_bin = 'wepp_260803'
    multi_ofe = True
    watershed_instance = SimpleNamespace(delineation_backend='wbt')
    def config_get_bool(self, section, option, default=None):
        return True if (section, option) == ('config', 'flattened') else default
    def config_get_raw(self, section, option, default=None):
        return {'schema_version': '1', 'wepp_binaries': ['wepp_260803'],
                'delineation_backends': ['wbt'], 'watershed_representations': ['multiple-ofe']}.get(option, default)
    config_get_list = config_get_raw


def test_v1_choices_expand_only_binary_axis_and_preserve_geometry():
    config = V1Config()
    assert project_wepp_binary_options(config) == ('wepp_260803', 'wepp_261010', 'wepp_261021', 'wepp_261026')
    validate_project_wepp_binary_selection(config, 'wepp_261010')
    assert project_wepp_binary_options(config, backend='topaz') == ()
    assert project_wepp_binary_options(config, multi_ofe=False) == ()


def test_zero_mofe_and_historical_graphs_keep_structure_identity():
    binaries = ('wepp_260803',)
    revisions = {binaries[0]: 'provider-v1:watershed=' + 'a' * 64 + ':hillslope=' + 'b' * 64}
    empty = build_continental_us_capability_graph(binaries, revisions)
    historical = build_continental_us_capability_graph(binaries, revisions, wepp_binary_capabilities={binaries[0]: ('mofe_supported',)})
    empty.validate()
    historical.validate()
    assert not any('|multiple-ofe|' in value for value in empty.allowed_model_tuples)
    # The pre-change algorithm derived these pairs from historical executable tuples.
    old_payload = capability_structure_payload(historical)
    old_payload['allowed_model_pairs'] = sorted({tuple(value.split('|')[:2]) for value in historical.allowed_model_tuples})
    assert capability_structure_payload(empty) == old_payload
    with pytest.raises(CapabilityGraphError):
        replace(empty, allowed_model_tuples=(*empty.allowed_model_tuples, 'topaz|multiple-ofe|wepp_260803')).validate()


def test_explicit_v1_saved_config_persists_new_binary(old_project, tmp_path):
    import hashlib
    import json
    from wepppy.project_config_serialization import parse_config_text, serialize_config
    from wepppy.nodb.core import Wepp
    config = parse_config_text((tmp_path / 'config.cfg').read_text())
    for section in list(config):
        if section.startswith('capabilities.') or section == 'capability_defaults':
            del config[section]
    config['capabilities'] = {'schema_version': 1, 'wepp_binaries': ['wepp_260803'],
                              'delineation_backends': ['wbt'], 'watershed_representations': ['multiple-ofe']}
    serialized = serialize_config(config)
    (tmp_path / 'config.cfg').write_bytes(serialized)
    manifest_path = tmp_path / 'config-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['config']['sha256'] = hashlib.sha256(serialized).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    before = (serialized, manifest_path.read_bytes())
    reloaded = Wepp.load_detached(str(tmp_path))
    assert project_wepp_binary_options(reloaded) == ('wepp_260803', 'wepp_261010', 'wepp_261021', 'wepp_261026')
    reloaded.parse_inputs({'wepp_bin': 'wepp_261010'})
    assert Wepp.load_detached(str(tmp_path)).wepp_bin == 'wepp_261010'
    assert ((tmp_path / 'config.cfg').read_bytes(), manifest_path.read_bytes()) == before
