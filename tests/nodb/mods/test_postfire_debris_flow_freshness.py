"""Real filesystem regressions for accepted content versus read-time identity."""
import os
from pathlib import Path

import pytest

from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.runtime_paths.wepp_inputs import copy_input_file

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('operation', ['link', 'unlink', 'touch', 'chmod', 'replace'])
@pytest.mark.parametrize('strong', [False, True])
def test_accepted_artifact_survives_same_content(tmp_path, operation, strong):
    source = tmp_path/'source'
    source.write_bytes(b'accepted bytes')
    linked = tmp_path/'linked'
    os.link(source, linked)
    record = {'artifacts': {'source': p.signature(tmp_path, source, strong=True)}}
    if operation == 'link':
        copy_input_file(str(tmp_path), 'source', tmp_path/'wepp/runs/pw0.cli')
    elif operation == 'unlink':
        linked.unlink()
    elif operation == 'touch':
        st = source.stat()
        os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns + 1000000))
    elif operation == 'chmod':
        source.chmod(0o600)
    else:
        replacement = tmp_path/'replacement'
        replacement.write_bytes(source.read_bytes())
        os.replace(replacement, source)
    assert p.artifacts_current(tmp_path, record, strong=strong)


@pytest.mark.parametrize('strong', [False, True])
def test_equal_size_restored_mtime_invalidates_artifact(tmp_path, strong):
    source = tmp_path/'source'
    source.write_bytes(b'before')
    record = {'artifacts': {'source': p.signature(tmp_path, source, strong=True)}}
    assert p.artifacts_current(tmp_path, record, strong=strong)
    st = source.stat()
    source.write_bytes(b'AFTER!')
    os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert not p.artifacts_current(tmp_path, record, strong=strong)


def snapshot(root, path):
    return {'selections': {'model': 'M3'}, 'files': {'cli': p.signature(root, path)},
            'content_sha256': {'cli': p.cached_digest(path)}}


def test_source_snapshots_legacy_and_content(tmp_path):
    from copy import deepcopy
    path = tmp_path/'source'
    path.write_bytes(b'before')
    accepted = snapshot(tmp_path, path)
    legacy = {key: value for key, value in accepted.items() if key != 'content_sha256'}
    assert p._source_snapshots_current(legacy, accepted)
    os.link(path, tmp_path/'linked')
    current = snapshot(tmp_path, path)
    assert p._source_snapshots_current(accepted, current)
    assert p._source_snapshots_current(legacy, current) == (legacy['files'] == current['files'])
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
    assert not p._source_snapshots_current(legacy, snapshot(tmp_path, path))
    for change in ('missing', 'extra', 'null', 'malformed'):
        bad = deepcopy(accepted)
        if change == 'missing':
            bad['content_sha256'].clear()
        elif change == 'extra':
            bad['content_sha256']['unrecorded'] = 'a'*64
        else:
            bad['content_sha256']['cli'] = None if change == 'null' else 'invalid'
        assert not p._source_snapshots_current(bad, current)
    st = path.stat()
    path.write_bytes(b'AFTER!')
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert not p._source_snapshots_current(accepted, snapshot(tmp_path, path))
    assert not p._source_snapshots_current(accepted, {**current, 'selections': {'model': 'M1'}})


def test_empty_absent_and_strict_publication(tmp_path):
    path = tmp_path/'empty'
    path.touch()
    accepted = snapshot(tmp_path, path)
    absent = {'selections': accepted['selections'], 'files': {'cli': None},
              'content_sha256': {'cli': None}}
    assert p._source_snapshots_current(absent, absent)
    assert not p._source_snapshots_current(accepted, absent)
    record = {'artifacts': {'empty': p.signature(tmp_path, path, strong=True)}}
    os.link(path, tmp_path/'linked')
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
    assert p.artifacts_current(tmp_path, record, strong=False)
    assert not p.artifacts_current(tmp_path, record, strong=False, strict=True)
    path.unlink()
    assert not p.artifacts_current(tmp_path, record, strong=False)
    path.symlink_to(tmp_path/'linked')
    assert not p.artifacts_current(tmp_path, record, strong=False)


def test_cached_digest_detects_change_during_hash(tmp_path, monkeypatch):
    path = tmp_path/'source'
    path.write_bytes(b'before')
    original = p.hashlib.sha256
    def changing_hash():
        checksum = original()
        class ChangingHash:
            def update(self, block):
                checksum.update(block)
                previous = path.stat()
                path.write_bytes(b'AFTER!')
                os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1))
            def hexdigest(self):
                return checksum.hexdigest()
        return ChangingHash()
    with monkeypatch.context() as patch:
        patch.setattr(p.hashlib, 'sha256', changing_hash)
        with pytest.raises(p.WorkflowError, match='changed'):
            p.cached_digest(path)
    assert p.cached_digest(path) == original(b'AFTER!').hexdigest()


def test_warm_digest_reads_no_content_and_rechecks_access(tmp_path, monkeypatch):
    path = tmp_path/'source'
    path.write_bytes(b'accepted')
    expected = p.cached_digest(path)
    settled = p.monotonic_ns() + 1_000_000_001
    monkeypatch.setattr(p, 'monotonic_ns', lambda: settled)
    assert p.cached_digest(path) == expected  # First mature observation hashes anew.
    def unexpected_hash():
        raise AssertionError('Warm cache must not hash again')
    with monkeypatch.context() as patch:
        patch.setattr(p.hashlib, 'sha256', unexpected_hash)
        for _ in range(100):
            assert p.cached_digest(path) == expected
    path.chmod(0)
    try:
        if os.getuid() != 0:
            with pytest.raises(PermissionError):
                p.cached_digest(path)
    finally:
        path.chmod(0o600)


def test_observation_eviction_requires_fresh_admission(tmp_path, monkeypatch):
    path = tmp_path/'source'
    path.write_bytes(b'accepted')
    clock = [0]
    monkeypatch.setattr(p, 'monotonic_ns', lambda: clock[0])
    p.cached_digest(path)
    clock[0] = 1_000_000_001
    p.cached_digest(path)
    misses = p._digest_version.cache_info().misses
    # Evict only the observation; the old digest deliberately survives.
    for index in range(512):
        p._digest_observed_at(str(tmp_path/f'other-{index}'), (index,))
    clock[0] += 1
    p.cached_digest(path)  # New observation hashes uncached.
    assert p._digest_version.cache_info().misses == misses
    clock[0] += 1_000_000_001
    p.cached_digest(path)
    assert p._digest_version.cache_info().misses == misses + 1


def test_rapid_rewrites_never_reuse_a_young_digest(tmp_path):
    import hashlib
    path = tmp_path/'source'
    for index in range(100):
        path.write_bytes(b'before')
        original = path.stat()
        assert p.cached_digest(path, local=True) == hashlib.sha256(b'before').hexdigest()
        path.write_bytes(b'AFTER!')
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        assert p.cached_digest(path, local=True) == hashlib.sha256(b'AFTER!').hexdigest()


def test_complete_uncached_read_has_a_point_in_time(tmp_path, monkeypatch):
    path = tmp_path/'source'
    path.write_bytes(b'before')
    original = p.hashlib.sha256
    def changing_hash():
        checksum = original()
        class ChangingHash:
            def update(self, block):
                checksum.update(block)
                path.write_bytes(b'AFTER!')  # All old bytes were already read.
            def hexdigest(self):
                return checksum.hexdigest()
        return ChangingHash()
    misses = p._digest_version.cache_info().misses
    with monkeypatch.context() as patch:
        patch.setattr(p.hashlib, 'sha256', changing_hash)
        try:
            observed = p.cached_digest(path)
        except p.WorkflowError:
            pass  # An observable timestamp change is rejected.
        else:
            assert observed == original(b'before').hexdigest()
    assert p._digest_version.cache_info().misses == misses
    assert p.cached_digest(path) == original(b'AFTER!').hexdigest()


def test_default_open_closes_leaf_when_parent_changes(tmp_path, monkeypatch):
    import errno
    from wepppy.nodb.mods.postfire_debris_flow import rainfall_io
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


def worker_snapshot(root, path, *, content=True):
    record = {'selections': {'model': 'M3'}, 'files': {'active_cli': p.signature(root, path)}}
    if content:
        record['content_sha256'] = {'active_cli': p.signature(root, path, strong=True)[4]}
    # Separate subsequent mutations from this filesystem's timestamp quantum.
    import time
    time.sleep(.01)
    return record


@pytest.mark.parametrize('operation', ['link', 'unlink', 'rematerialize'])
def test_worker_cli_hardlink_identity(tmp_path, operation):
    path = tmp_path/'climate.cli'
    path.write_bytes(b'original climate')
    linked = tmp_path/'wepp/runs/pw0.cli'
    if operation != 'link':
        copy_input_file(str(tmp_path), path.name, linked)
    admitted = worker_snapshot(tmp_path, path)
    if operation == 'unlink':
        linked.unlink()
    else:
        copy_input_file(str(tmp_path), path.name, linked)
    current = worker_snapshot(tmp_path, path, content=False)
    assert admitted['files'] != current['files']
    assert p._worker_source_snapshots_current(tmp_path, admitted, current)
    assert p._worker_source_snapshots_current(tmp_path, admitted, worker_snapshot(tmp_path, path))


@pytest.mark.parametrize('change', ['bytes', 'mtime', 'path', 'selection', 'other_ctime',
                                    'legacy', 'bad_old_hash', 'missing_old_hash', 'bad_new_hash'])
def test_worker_cli_exception_rejects_other_changes(tmp_path, change):
    from copy import deepcopy
    path = tmp_path/'climate.cli'
    path.write_bytes(b'original climate')
    admitted = worker_snapshot(tmp_path, path)
    st = path.stat()
    os.link(path, tmp_path/'linked')
    if change == 'bytes':
        path.write_bytes(b'CHANGED! climate')
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    if change == 'mtime':
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
    current = worker_snapshot(tmp_path, path, content=False)
    if change == 'path':
        current['files']['active_cli'][0] = 'linked'
    elif change == 'selection':
        current['selections']['model'] = 'M1'
    elif change == 'other_ctime':
        admitted['files']['dem'] = deepcopy(admitted['files']['active_cli'])
        admitted['content_sha256']['dem'] = admitted['content_sha256']['active_cli']
        current['files']['dem'] = deepcopy(current['files']['active_cli'])
    elif change == 'legacy':
        admitted.pop('content_sha256')
    elif change == 'bad_old_hash':
        admitted['content_sha256']['active_cli'] = 'invalid'
    elif change == 'missing_old_hash':
        admitted['content_sha256'] = {}
    elif change == 'bad_new_hash':
        current['content_sha256'] = {'active_cli': '0'*64}
    assert not p._worker_source_snapshots_current(tmp_path, admitted, current)


def test_worker_cli_does_not_trust_cached_digest(tmp_path, monkeypatch):
    path = tmp_path/'climate.cli'
    path.write_bytes(b'before')
    admitted = worker_snapshot(tmp_path, path)
    st = path.stat()
    path.write_bytes(b'AFTER!')
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    current = worker_snapshot(tmp_path, path, content=False)
    real = p._digest_version
    def stale(*args, **kwargs):
        return admitted['content_sha256']['active_cli']
    stale.__wrapped__ = real.__wrapped__
    monkeypatch.setattr(p, '_digest_version', stale)
    assert not p._worker_source_snapshots_current(tmp_path, admitted, current)


@pytest.mark.parametrize('mutation', ['symlink', 'replace', 'during_read', 'before_strong_read'])
def test_worker_cli_generation_race_rejected(tmp_path, monkeypatch, mutation):
    from contextlib import contextmanager
    from wepppy.nodb.mods.postfire_debris_flow import rainfall_io
    path = tmp_path/'climate.cli'
    path.write_bytes(b'original climate')
    admitted = worker_snapshot(tmp_path, path)
    linked = tmp_path/'linked'
    import time
    time.sleep(.01)  # Filesystem timestamps can coalesce adjacent metadata operations.
    os.link(path, linked)
    current = worker_snapshot(tmp_path, path, content=False)
    if mutation == 'symlink':
        path.unlink()
        path.symlink_to(linked)
    elif mutation in ('replace', 'during_read'):
        original = rainfall_io.open_local
        @contextmanager
        def racing(*args, **kwargs):
            with original(*args, **kwargs) as stream:
                if mutation == 'replace':
                    replacement = tmp_path/'replacement'
                    replacement.write_bytes(path.read_bytes())
                    os.replace(replacement, path)
                yield stream
                if mutation == 'during_read':
                    os.link(path, tmp_path/'another_link')
                    st = path.stat()
                    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
        monkeypatch.setattr(rainfall_io, 'open_local', racing)
    else:
        original = p.signature
        def racing(*args, **kwargs):
            st = path.stat()
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
            return original(*args, **kwargs)
        monkeypatch.setattr(p, 'signature', racing)
    try:
        result = p._worker_source_snapshots_current(tmp_path, admitted, current)
    except (p.WorkflowError, OSError, ValueError):
        pass  # Explicit coherent-read/path failure is the established contract.
    else:
        assert result is False


@pytest.mark.parametrize('malformed', [None, [], {'files': None}, {'files': []}])
@pytest.mark.parametrize('side', ['admitted', 'current'])
def test_worker_snapshot_shape_rejects_without_untyped_error(tmp_path, malformed, side):
    path = tmp_path/'climate.cli'
    path.write_bytes(b'original climate')
    valid = worker_snapshot(tmp_path, path)
    admitted, current = (malformed, valid) if side == 'admitted' else (valid, malformed)
    assert not p._worker_source_snapshots_current(tmp_path, admitted, current)
