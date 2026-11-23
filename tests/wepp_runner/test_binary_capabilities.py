"""Read actual sidecar files and reject malformed executable declarations."""
import hashlib
import json
from pathlib import Path

import pytest
from wepp_runner import wepp_binary_capabilities as capabilities

pytestmark = pytest.mark.unit


@pytest.fixture
def pair(tmp_path, monkeypatch):
    paths = [tmp_path / 'wepp_new', tmp_path / 'wepp_new_hill']
    for role, path in zip(('watershed', 'hillslope'), paths):
        path.write_bytes(role.encode())
        path.chmod(0o755)
        Path(str(path) + '.json').write_text(json.dumps({
            'schema': 'wepp-binary-release-metadata-v1', 'binary_role': role,
            'binary_name': path.name, 'release_tag': 'new', 'source_repo': 'wepp-forest',
            'source_branch': 'default', 'source_commit': 'a' * 40,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'features': {'mofe_supported': True, 'single_user_defined_inputs_supported': True},
        }))
    monkeypatch.setattr(capabilities, 'get_linux_wepp_bin_opts', lambda: ['wepp_new'])
    monkeypatch.setattr(capabilities, 'get_linux_wepp_bin_role_paths', lambda _: tuple(map(str, paths)))
    return paths


def update(path, field, value):
    sidecar = Path(str(path) + '.json')
    payload = json.loads(sidecar.read_text())
    payload['features'][field] = value
    sidecar.write_text(json.dumps(payload))


def test_fresh_capability_changes_are_seen_without_restart(pair):
    assert capabilities.get_compatible_wepp_bin_opts(multi_ofe=True) == ('wepp_new',)
    for path in pair:
        update(path, 'mofe_supported', False)
    assert capabilities.get_compatible_wepp_bin_opts(multi_ofe=True) == ()
    assert capabilities.get_compatible_wepp_bin_opts() == ('wepp_new',)
    assert capabilities.get_compatible_wepp_bin_opts(single_user_defined_inputs=True) == ('wepp_new',)


def test_absent_sidecars_preserve_single_ofe_availability(pair):
    for path in pair:
        Path(str(path) + '.json').unlink()
    assert capabilities.get_compatible_wepp_bin_opts() == ('wepp_new',)
    assert capabilities.get_compatible_wepp_bin_opts(multi_ofe=True) == ()


@pytest.mark.parametrize('bad', [None, 1, 'true', [], {}])
def test_nonboolean_flags_rejected(pair, bad):
    update(pair[0], 'mofe_supported', bad)
    with pytest.raises(ValueError, match='boolean'):
        capabilities.get_binary_capabilities('wepp_new')


def test_role_disagreement_rejected(pair):
    update(pair[1], 'mofe_supported', False)
    with pytest.raises(ValueError, match='disagree'):
        capabilities.get_binary_capabilities('wepp_new')


def test_stale_binary_hash_rejected(pair):
    pair[0].write_bytes(b'different executable')
    with pytest.raises(ValueError, match='sha256'):
        capabilities.get_binary_capabilities('wepp_new')


@pytest.mark.parametrize('value', ['../wepp_new', '/tmp/wepp_new', 'uninstalled', 'wepp_new;echo'])
def test_nonprovider_ids_rejected_before_resolution(pair, monkeypatch, value):
    def forbidden(_):
        pytest.fail('Untrusted ID reached path resolution')
    monkeypatch.setattr(capabilities, 'get_linux_wepp_bin_role_paths', forbidden)
    with pytest.raises(ValueError, match='not installed'):
        capabilities.get_binary_capabilities(value)


@pytest.mark.parametrize('field', ['release_tag', 'source_commit', 'source_branch', 'source_repo', 'binary_name'])
def test_mixed_or_copied_sidecar_identity_rejected(pair, field):
    sidecar = Path(str(pair[1]) + '.json')
    payload = json.loads(sidecar.read_text())
    payload[field] = 'different'
    sidecar.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='identities disagree|binary_name'):
        capabilities.get_binary_capabilities('wepp_new')


def test_revision_tracks_metadata_and_executable_replacement(pair):
    before = capabilities.binary_selection_revision(('wepp_new',))
    for path in pair:
        update(path, 'mofe_supported', False)
    metadata_revision = capabilities.binary_selection_revision(('wepp_new',))
    assert metadata_revision != before
    path = pair[0]
    path.write_bytes(b'new build')
    sidecar = Path(str(path) + '.json')
    payload = json.loads(sidecar.read_text())
    payload['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps(payload))
    assert capabilities.binary_selection_revision(('wepp_new',)) != metadata_revision


def test_in_place_binary_change_with_restored_mtime_rejects_stale_sidecar(pair):
    import os
    capabilities.get_binary_capabilities('wepp_new')
    path = pair[0]
    before = path.stat()
    path.write_bytes(b'x' * before.st_size)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(ValueError, match='sha256'):
        capabilities.get_binary_capabilities('wepp_new')


def test_capacity_is_separate_from_boolean_features_and_tracks_revision(pair):
    original=capabilities.get_binary_capabilities('wepp_new')
    assert capabilities.get_soil_input_capacity('wepp_new')==10
    before=capabilities.binary_selection_revision(('wepp_new',))
    for path in pair:update(path,'soil_input_capacity',23)
    assert capabilities.get_soil_input_capacity('wepp_new')==23
    assert capabilities.get_binary_capabilities('wepp_new')==original
    assert capabilities.binary_selection_revision(('wepp_new',))!=before


@pytest.mark.parametrize('bad',[None,True,False,0,24,23.0,'23',[],{}])
def test_invalid_capacity_declaration(pair,bad):
    update(pair[0],'soil_input_capacity',bad)
    with pytest.raises(ValueError,match='soil_input_capacity'):
        capabilities.get_soil_input_capacity('wepp_new')


def test_capacity_mismatch_and_absence(pair):
    update(pair[0],'soil_input_capacity',23)
    with pytest.raises(ValueError,match='capacities disagree'):
        capabilities.get_soil_input_capacity('wepp_new')
    for path in pair:Path(str(path)+'.json').unlink()
    assert capabilities.get_soil_input_capacity('wepp_new')==10


def test_actual_run_soil_rejected_after_binary_downgrade(pair,tmp_path):
    from wepp_runner.wepp_runner import _validate_run_soil_capacity
    depths=[200+50*i for i in range(23)]
    text="7778\ncomment\n1 0\n'profile' 'loam' 23 0.2 0.75 400000 0.00008 2\n"
    text+=''.join(f'{d} 1.3 36 2 .3 .1 40 20 2 15 5\n' for d in depths)+'1 10000 .01\n'
    soil=tmp_path/'actual.sol';soil.write_text(text)
    deck=tmp_path/'p1.run';deck.write_text('actual.sol\n')
    before=soil.read_bytes()
    for path in pair:update(path,'soil_input_capacity',23)
    _validate_run_soil_capacity(deck,tmp_path,'wepp_new')
    for path in pair:update(path,'soil_input_capacity',10)
    with pytest.raises(ValueError,match='10-layer limit'):
        _validate_run_soil_capacity(deck,tmp_path,'wepp_new')
    assert soil.read_bytes()==before
