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
