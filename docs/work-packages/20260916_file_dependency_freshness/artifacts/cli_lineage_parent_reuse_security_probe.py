"""Independent real directory identity/access probes for same-call fd reuse."""
import errno
import os
from pathlib import Path
import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from wepppy.climates import cli_parquet
from wepppy.nodb.mods.postfire_debris_flow import production, rainfall_io

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('content', [False, True])
def test_parent_replacement_hardlinks_cannot_keep_lineage_current(owner_project, monkeypatch, content):
    root, _ = owner_project
    parent = root / 'climate'
    replacement = root / 'replacement-climate'
    replacement.mkdir()
    for item in parent.iterdir():
        if item.is_file():
            os.link(item, replacement / item.name)
    real = cli_parquet._read_proof
    def read_then_replace(stream, limit):
        result = real(stream, limit)
        parent.rename(root / 'former-climate')
        replacement.rename(parent)
        return result
    monkeypatch.setattr(cli_parquet, '_read_proof', read_then_replace)
    with pytest.raises(production.WorkflowError) as caught:
        production.sources(root, content=content)
    assert caught.value.code == 'changed_source'


def test_default_open_closes_leaf_when_parent_changes(tmp_path, monkeypatch):
    parent = tmp_path / 'parent'
    parent.mkdir()
    target = parent / 'leaf'
    target.write_bytes(b'original')
    replacement = tmp_path / 'replacement'
    replacement.mkdir()
    os.link(target, replacement / target.name)
    real = os.open
    leaf = []
    def open_then_replace(path, flags, *args, **kwargs):
        result = real(path, flags, *args, **kwargs)
        if path == 'leaf' and kwargs.get('dir_fd') is not None:
            leaf.append(result)
            parent.rename(tmp_path / 'former')
            replacement.rename(parent)
        return result
    monkeypatch.setattr(os, 'open', open_then_replace)
    with pytest.raises(OSError) as caught:
        rainfall_io.open_local(target)
    assert caught.value.errno == errno.ESTALE
    with pytest.raises(OSError) as closed:
        os.fstat(leaf[0])
    assert closed.value.errno == errno.EBADF


@pytest.mark.parametrize('mode', [0o111, 0o000])
def test_directory_read_authority_preserved(tmp_path, mode):
    assert os.getuid() != 0
    parent = tmp_path / 'private'
    parent.mkdir()
    target = parent / 'leaf'
    target.write_bytes(b'data')
    parent.chmod(mode)
    try:
        with pytest.raises(PermissionError):
            with rainfall_io._local_parent(parent):
                pytest.fail('Directory read denial was bypassed')
    finally:
        parent.chmod(0o700)


@pytest.mark.parametrize('component', ['ancestor', 'parent', 'leaf'])
def test_nofollow_component_policy_unchanged(tmp_path, component):
    real = tmp_path / 'real'
    parent = real / 'parent'
    parent.mkdir(parents=True)
    target = parent / 'leaf'
    target.write_bytes(b'data')
    if component == 'ancestor':
        selected = tmp_path / 'alias'
        selected.symlink_to(real, target_is_directory=True)
        target = selected / 'parent/leaf'
    elif component == 'parent':
        selected = real / 'alias'
        selected.symlink_to(parent, target_is_directory=True)
        target = selected / 'leaf'
    else:
        selected = parent / 'alias'
        selected.symlink_to(target)
        target = selected
    with pytest.raises(rainfall_io.RainfallError, match='Symlinks'):
        rainfall_io.open_local(target)


def test_reused_parent_preserves_leaf_read_denial(tmp_path):
    assert os.getuid() != 0
    target = tmp_path / 'leaf'
    target.write_bytes(b'data')
    with rainfall_io._local_parent(tmp_path) as descriptor:
        target.chmod(0)
        try:
            with pytest.raises(PermissionError):
                rainfall_io.open_local(target, _parent_fd=descriptor)
        finally:
            target.chmod(0o600)
