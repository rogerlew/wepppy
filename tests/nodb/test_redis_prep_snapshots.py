"""Real Redis/process/file regressions for RPS-01; disposable server only."""
from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import shutil
import threading

import pytest
import redis

from tests.rq.test_rq212_lifecycle import lifecycle  # reusable disposable server fixture

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def reap_test_processes():
    """A failing concurrency assertion must not leave blocked children behind."""
    existing = {child.pid for child in multiprocessing.active_children()}
    yield
    for child in multiprocessing.active_children():
        if child.pid not in existing:
            child.kill()
            child.join(5)
            assert not child.is_alive()


@pytest.fixture
def state(lifecycle, tmp_path, monkeypatch):
    from wepppy.nodb import redis_prep as module
    socket_path = lifecycle.connection.connection_pool.connection_kwargs['path']
    client = redis.StrictRedis(unix_socket_path=socket_path, db=0, decode_responses=True)
    client.delete('project', 'profile;;fork;;project')
    monkeypatch.setattr(module, 'redis_client', lambda *a, **k: client)
    root = tmp_path / 'runs'
    root.mkdir()
    wd = root / 'project'
    wd.mkdir()
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([
        {'path': str(root), 'namespace': 'rps-test', 'layout': 'flat',
         'coordination': str(tmp_path / 'coordination')}]))
    yield module, client, wd
    client.close()


def content(wd):
    return json.loads((wd / 'redisprep.dump').read_text())


def cold(module, client, wd):
    client.delete(module.RedisPrep(str(wd)).run_id)
    return module.RedisPrep.getInstance(str(wd))


def test_round_trip_receipts_flags_timestamps_and_locks(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    prep.has_sbs = True
    prep['run_wepp'] = 123
    prep.set_rq_job_id('run_wepp', 'accepted-job')
    prep.set_archive_job_id('archive-job')
    client.hset(prep.run_id, mapping={'locked:wepp.nodb': 'true', 'last_modified': '999'})
    prep.dump()
    assert 'locked:wepp.nodb' not in content(wd)
    recovered = cold(module, client, wd)
    assert recovered['run_wepp'] == 123 and recovered.has_sbs
    assert recovered.get_rq_job_id('run_wepp') == 'accepted-job'
    assert recovered.get_archive_job_id() == 'archive-job'
    assert 'run_wepp: 123' not in recovered.timestamps_report()  # arbitrary key is not an enum task
    assert not client.hexists(prep.run_id, 'locked:wepp.nodb')


def test_cold_restore_preserves_independent_live_fields(state):
    module, client, wd = state
    (wd / 'redisprep.dump').write_text(json.dumps({'attrs:loaded': 'true', 'timestamps:build_soils': '42',
                                                 'locked:wepp.nodb': 'false', 'last_modified': '1'}))
    client.hset('project', mapping={'locked:wepp.nodb': 'true', 'last_modified': '999'})
    prep = module.RedisPrep.getInstance(str(wd))
    assert prep[module.TaskEnum.build_soils] == 42
    assert client.hget('project', 'last_modified') == '999'
    assert client.hget('project', 'locked:wepp.nodb') == 'true'


@pytest.mark.parametrize('raw', ['{', '[]', 'null', '{"a":null}', '{"a":{}}', '{"a":NaN}'])
def test_corrupt_recovery_preserves_evidence(state, raw):
    module, client, wd = state
    (wd / 'redisprep.dump').write_text(raw)
    with pytest.raises((ValueError, TypeError)):
        module.RedisPrep.getInstance(str(wd))
    assert not client.hgetall('project')
    assert (wd / 'redisprep.dump').read_text() == raw


@pytest.mark.parametrize('payload', [{}, {'attrs:loaded': 'false'}, {'attrs:loaded': 'true'}])
def test_empty_legacy_snapshot(state, payload):
    module, client, wd = state
    (wd / 'redisprep.dump').write_text(json.dumps(payload))
    assert module.RedisPrep.getInstance(str(wd))._get_bool_config('loaded')
    assert client.hgetall('project') == {'attrs:loaded': 'true'}


def test_missing_file_preserves_live_hash_and_missing_directory_is_not_created(state):
    module, client, wd = state
    client.hset('project', mapping={'attrs:loaded': 'true', 'rq:x': 'job'})
    prep = module.RedisPrep.getInstance(str(wd))
    assert content(wd)['rq:x'] == 'job'
    shutil.rmtree(wd)
    prep.dump()
    assert not wd.exists()


def test_ambiguous_partial_unloaded_state_is_not_blessed(state):
    module, client, wd = state
    (wd / 'redisprep.dump').write_text('{"attrs:loaded":"true","rq:a":"a","rq:b":"b"}')
    client.hset('project', 'rq:a', 'newer-or-partial')
    with pytest.raises(module.RedisPrepSnapshotError, match='ambiguous'):
        module.RedisPrep.getInstance(str(wd))
    assert client.hgetall('project') == {'rq:a': 'newer-or-partial'}
    # Accepted historical limit: a true marker cannot identify earlier damage.
    client.hset('project', 'attrs:loaded', 'true')
    prep = module.RedisPrep.getInstance(str(wd))
    assert prep.get_rq_job_id('b') is None  # never invent a missing/deleted receipt


def test_restore_conflicts_with_direct_live_writer_without_partial_loaded_state(state, monkeypatch):
    module, client, wd = state
    (wd / 'redisprep.dump').write_text('{"attrs:loaded":"true","rq:a":"old","rq:b":"b"}')
    read = module.read_snapshot
    def interleave(fd):
        payload = read(fd)
        assert client.hgetall('project') == {}
        client.hset('project', 'rq:a', 'new')
        return payload
    monkeypatch.setattr(module, 'read_snapshot', interleave)
    with pytest.raises(module.RedisPrepSnapshotError, match='conflicted'):
        module.RedisPrep.getInstance(str(wd))
    assert client.hgetall('project') == {'rq:a': 'new'}


def test_old_capture_cannot_publish_after_new_capture_two_processes(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('x', 'old')
    ctx = multiprocessing.get_context('fork')
    captured, resume = ctx.Event(), ctx.Event()
    publish = module.publish_snapshot
    def older():
        def paused(fd, payload):
            captured.set()
            assert resume.wait(10)
            publish(fd, payload)
        module.publish_snapshot = paused
        prep.dump()
    process = ctx.Process(target=older)
    process.start()
    try:
        assert captured.wait(10)
        client.hdel(prep.run_id, 'rq:x')  # actual direct-mutation-plus-dump consumer
        client.hset(prep.run_id, 'timestamps:run_rhem', '456')
        attempting = ctx.Event()
        def newer():
            from wepppy.query_engine import catalog_refresh as catalog
            lockf = catalog.fcntl.lockf
            def prove_contention(fd, operation):
                if operation == catalog.fcntl.LOCK_EX:
                    try:
                        lockf(fd, operation | catalog.fcntl.LOCK_NB)
                    except BlockingIOError:
                        attempting.set()  # actual kernel contention, not scheduling
                    else:
                        raise AssertionError('older capture did not retain serialization')
                return lockf(fd, operation)
            catalog.fcntl.lockf = prove_contention
            prep.dump()
        second = ctx.Process(target=newer)
        second.start()
        assert attempting.wait(10)
        resume.set()
        process.join(10)
        second.join(10)
        assert process.exitcode == second.exitcode == 0
        assert 'rq:x' not in content(wd)
        recovered = cold(module, client, wd)
        assert recovered.get_rq_job_id('x') is None
        assert recovered[module.TaskEnum.run_rhem] == 456
    finally:
        resume.set()
        if process.is_alive():
            process.kill()
        process.join()


def test_readers_only_observe_complete_large_snapshots(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    values = ['A' * 300000, 'B' * 300000]
    prep.update_metadata({'large': values[0]})
    started, done = threading.Event(), threading.Event()
    errors = []
    def reader():
        started.set()
        while not done.is_set():
            try:
                assert content(wd)['large'] in values
            except (ValueError, AssertionError, KeyError) as exc:
                errors.append(exc)
                return
    thread = threading.Thread(target=reader)
    thread.start()
    assert started.wait(5)
    try:
        for i in range(12):
            prep.update_metadata({'large': values[i % 2]})
    finally:
        done.set()
        thread.join(5)
        assert not thread.is_alive()
    assert not errors


@pytest.mark.parametrize('stage', ['serialize', 'create', 'write', 'zero_write', 'fsync', 'replace'])
def test_precommit_failures_retain_previous_snapshot(state, monkeypatch, stage):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('x', 'old')
    previous = (wd / 'redisprep.dump').read_bytes()
    client.hset(prep.run_id, 'rq:x', 'new')
    def fail(*args, **kwargs):
        raise OSError('injected ' + stage)
    if stage == 'serialize':
        monkeypatch.setattr(io.json, 'dumps', fail)
    elif stage == 'create':
        original = io.os.open
        def fail_create(path, flags, *args, **kwargs):
            if flags & os.O_EXCL:
                fail()
            return original(path, flags, *args, **kwargs)
        monkeypatch.setattr(io.os, 'open', fail_create)
    else:
        monkeypatch.setattr(io.os, 'write' if stage == 'zero_write' else stage,
                            (lambda *a: 0) if stage == 'zero_write' else fail)
    with pytest.raises((OSError, module.RedisPrepSnapshotError)):
        prep.dump()
    assert (wd / 'redisprep.dump').read_bytes() == previous
    assert not list(wd.glob('.redisprep.dump.*.tmp'))


def test_short_writes_complete_and_postreplace_fsync_is_honest(state, monkeypatch):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    write = io.os.write
    monkeypatch.setattr(io.os, 'write', lambda fd, value: write(fd, value[:7]))
    prep.set_rq_job_id('x', 'short-written')
    assert content(wd)['rq:x'] == 'short-written'
    fsync = io.os.fsync
    def fail_directory(fd):
        if fd == prep._directory_fd:
            raise OSError('directory durability unavailable')
        fsync(fd)
    monkeypatch.setattr(io.os, 'fsync', fail_directory)
    with pytest.raises(module.RedisPrepSnapshotError) as caught:
        prep.set_rq_job_id('x', 'committed')
    assert caught.value.published
    assert content(wd)['rq:x'] == 'committed'
    assert not list(wd.glob('.redisprep.dump.*.tmp'))


def test_killed_prepublication_writer_keeps_last_good_snapshot(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('x', 'good')
    ctx = multiprocessing.get_context('fork')
    staged = ctx.Event()
    def writer():
        from wepppy.nodb import _redis_prep_snapshot as io
        def kill_before_replace(*args, **kwargs):
            staged.set()
            ctx.Event().wait(20)
        io.os.replace = kill_before_replace
        prep.set_rq_job_id('x', 'unpublished')
    child = ctx.Process(target=writer)
    child.start()
    try:
        assert staged.wait(10)
        child.kill()
        child.join(5)
        assert content(wd)['rq:x'] == 'good'
        assert list(wd.glob('.redisprep.dump.*.tmp'))
        client.delete(prep.run_id)
        def fresh_restore():
            recovered = module.RedisPrep.getInstance(str(wd))
            assert recovered.get_rq_job_id('x') == 'good'
        recovery = ctx.Process(target=fresh_restore)
        recovery.start()
        recovery.join(10)
        assert recovery.exitcode == 0
        assert client.hget(prep.run_id, 'rq:x') == 'good'
    finally:
        if child.is_alive():
            child.kill()
        child.join()


def test_mode_and_symlink_safety(state):
    module, client, wd = state
    old_umask = os.umask(0o027)
    try:
        prep = module.RedisPrep.getInstance(str(wd))
    finally:
        os.umask(old_umask)
    path = wd / 'redisprep.dump'
    assert path.stat().st_mode & 0o777 == 0o640
    path.chmod(0o660)
    prep.dump()
    assert path.stat().st_mode & 0o777 == 0o660
    outside = wd.parent / 'outside'
    outside.write_text('preserve')
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(OSError):
        prep.dump()
    assert outside.read_text() == 'preserve'


def test_recreated_and_inplace_restored_incarnations_fence_old_wrapper(state):
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard, invalidate_catalog_incarnation
    prep = module.RedisPrep.getInstance(str(wd))
    with catalog_lifecycle_guard(wd):
        invalidate_catalog_incarnation(wd)
    with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
        prep.set_rq_job_id('x', 'stale')
    new = module.RedisPrep.getInstance(str(wd))
    with catalog_lifecycle_guard(wd):
        shutil.rmtree(wd)
        wd.mkdir()
    with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
        new.dump()
    assert not (wd / 'redisprep.dump').exists()


def test_explicit_reset_preserves_unrelated_live_state_and_deletes_old_receipts(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('old', 'old-job')
    client.hset('project', mapping={'locked:x': 'true', 'foreign:field': 'live', 'last_modified': '99'})
    prep.restore_snapshot({'timestamps:build_soils': '42', 'last_modified': '1'})
    assert client.hgetall('project') == {'attrs:loaded': 'true', 'timestamps:build_soils': '42',
                                       'last_modified': '99', 'locked:x': 'true', 'foreign:field': 'live'}
    assert cold(module, client, wd).get_rq_job_id('old') is None


def test_profile_namespace_and_missing_rq_job_are_not_synthetic_success(state):
    module, client, wd = state
    (wd / '.redisprep-run-id').write_text('profile;;fork;;project')
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('run_rhem', 'missing-job')
    recovered = cold(module, client, wd)
    assert recovered.run_id == 'profile;;fork;;project'
    assert not client.exists('project')
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    with pytest.raises(NoSuchJobError):
        Job.fetch(recovered.get_rq_job_id('run_rhem'), connection=client)


def test_two_cold_loaders_and_kill_before_atomic_restore(state):
    module, client, wd = state
    payload = {'attrs:loaded': 'true', 'rq:first': 'first', 'rq:last': 'last'}
    (wd / 'redisprep.dump').write_text(json.dumps(payload))
    ctx = multiprocessing.get_context('fork')
    read_complete = ctx.Event()
    def loader():
        read = module.read_snapshot
        def pause(fd):
            result = read(fd)
            read_complete.set()
            ctx.Event().wait(20)
            return result
        module.read_snapshot = pause
        module.RedisPrep.getInstance(str(wd))
    child = ctx.Process(target=loader)
    child.start()
    try:
        assert read_complete.wait(10)
        assert client.hgetall('project') == {}  # saved loaded marker never leaked
        second = ctx.Process(target=module.RedisPrep.getInstance, args=(str(wd),))
        second.start()
        child.kill()
        child.join(5)
        second.join(10)
        assert second.exitcode == 0
        recovered = module.RedisPrep.getInstance(str(wd))
        assert recovered.get_rq_job_ids() == {'first': 'first', 'last': 'last'}
        assert client.hgetall('project') == payload
    finally:
        if child.is_alive():
            child.kill()
        child.join()


def test_concurrent_fresh_constructors_retry_after_contention(state):
    module, client, wd = state
    ctx = multiprocessing.get_context('fork')
    publishing, release = ctx.Event(), ctx.Event()
    publish = module.publish_snapshot
    def first():
        def pause(fd, payload):
            publishing.set()
            assert release.wait(10)
            publish(fd, payload)
        module.publish_snapshot = pause
        module.RedisPrep.getInstance(str(wd))
    child = ctx.Process(target=first)
    child.start()
    try:
        assert publishing.wait(10)
        second = ctx.Process(target=module.RedisPrep.getInstance, args=(str(wd),))
        second.start()
        release.set()
        child.join(10)
        second.join(10)
        assert child.exitcode == second.exitcode == 0
        module.RedisPrep.getInstance(str(wd)).has_sbs = True
        assert content(wd) == {'attrs:loaded': 'true', 'attrs:has_sbs': 'true'}
    finally:
        release.set()
        if child.is_alive():
            child.kill()
        child.join()


def test_release_failure_closes_guard_and_does_not_rollback(state, monkeypatch):
    module, client, wd = state
    from wepppy.query_engine import catalog_refresh as catalog
    prep = module.RedisPrep.getInstance(str(wd))
    lockf = catalog.fcntl.lockf
    def fail_release(fd, operation):
        if operation == catalog.fcntl.LOCK_UN:
            raise OSError('injected unlock error')
        return lockf(fd, operation)
    with monkeypatch.context() as patch:
        patch.setattr(catalog.fcntl, 'lockf', fail_release)
        with pytest.raises(module.RedisPrepSnapshotError, match='release failed') as caught:
            prep.set_rq_job_id('x', 'published')
        assert caught.value.published
    assert content(wd)['rq:x'] == 'published'
    # Fresh process proves the leaked lock did not survive the failed unlock.
    ctx = multiprocessing.get_context('fork')
    child = ctx.Process(target=prep.dump)
    child.start()
    child.join(10)
    if child.is_alive():
        child.kill()
        child.join()
        pytest.fail('release failure leaked coordination')
    assert child.exitcode == 0


def test_cleanup_failure_after_replace_reports_commit(state, monkeypatch):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    unlink = io.os.unlink
    def fail_cleanup(path, *args, **kwargs):
        if str(path).startswith('.redisprep.dump.'):
            raise OSError('cleanup failure')
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(io.os, 'unlink', fail_cleanup)
    with pytest.raises(module.RedisPrepSnapshotError) as caught:
        prep.set_rq_job_id('x', 'new')
    assert caught.value.published
    assert content(wd)['rq:x'] == 'new'


def test_snapshot_receipt_recovery_blocks_duplicate_accepted_work(state, lifecycle):
    module, client, wd = state
    from rq.job import Job
    from wepppy.rq.submission_recovery import prepare_redisprep_job_id, RqSubmissionConflict
    prep = module.RedisPrep.getInstance(str(wd))
    # Persist an actual queued RQ job without executing expensive work.
    job = Job.create('wepppy.rq.wepp_rq.run_wepp_rq', args=('project',),
                     connection=lifecycle.connection, origin='default', status='queued')
    job.save()
    prep.set_rq_job_id('run_wepp', job.id)
    recovered = cold(module, client, wd)
    with pytest.raises(RqSubmissionConflict):
        prepare_redisprep_job_id(recovered, job_key='run_wepp', replacement_job_id='duplicate',
                                connection=lifecycle.connection, runid='project')
    assert recovered.get_rq_job_id('run_wepp') == job.id
    assert Job.fetch(job.id, connection=lifecycle.connection).get_status() == 'queued'


def test_copied_fork_reset_and_real_omni_snapshot_consumer(state):
    module, client, wd = state
    from wepppy.rq.project_rq_fork import _rewrite_fork_redisprep_dump
    from wepppy.nodb.mods.omni.omni_state_contrast_mixin import OmniStateContrastMixin
    prep = module.RedisPrep.getInstance(str(wd))
    prep[module.TaskEnum.build_soils] = 42
    prep[module.TaskEnum.run_wepp_watershed] = 43
    prep[module.TaskEnum.run_omni_scenarios] = 50
    prep.set_rq_job_id('work', 'job')
    destination = wd.parent / 'copy'
    shutil.copytree(wd, destination)
    (destination / '.redisprep-run-id').write_text('profile;;fork;;copy')
    payload = _rewrite_fork_redisprep_dump(str(destination))
    copy = module.RedisPrep(str(destination))
    copy.restore_snapshot(payload)
    assert not copy.get_rq_job_ids()
    assert copy[module.TaskEnum.run_omni_scenarios] is None
    assert prep.get_rq_job_id('work') == 'job'
    # Existing contrast consumer reads real emitted JSON and normalizes timestamps.
    consumer = object.__new__(OmniStateContrastMixin)
    snapshot = consumer._redisprep_snapshot(str(destination / 'redisprep.dump'))
    assert snapshot['timestamps:run_wepp_watershed'] == '43'


def test_normal_catalog_initialization_is_not_replacement(state):
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import resolve_scope, invalidate_catalog_incarnation
    prep = module.RedisPrep.getInstance(str(wd))
    assert prep._scope.incarnation is None
    first = resolve_scope(wd, create=True)
    assert first.initialization_only
    prep.set_rq_job_id('x', 'normal')
    assert prep._scope.incarnation == first.incarnation
    invalidate_catalog_incarnation(wd)
    assert not resolve_scope(wd).initialization_only
    with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
        prep.set_rq_job_id('x', 'stale')


def test_loaded_reader_requires_no_write_permission(state):
    module, client, wd = state
    # Test runs as the actual unprivileged web-container identity.
    assert os.geteuid() != 0
    (wd / 'redisprep.dump').write_text('{"attrs:loaded":"true","rq:x":"job"}')
    client.hset('project', mapping={'attrs:loaded': 'true', 'rq:x': 'job'})
    wd.chmod(0o555)
    try:
        prep = module.RedisPrep.getInstance(str(wd))
        assert prep.get_rq_job_id('x') == 'job'
        assert not (wd / '_query_engine').exists()
    finally:
        wd.chmod(0o755)


def test_deleted_wrapper_cannot_seed_recreated_run(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    shutil.rmtree(wd)
    with pytest.raises(module.RedisPrepSnapshotError, match='deleted'):
        prep.set_rq_job_id('x', 'stale')
    prep.lazy_load()
    wd.mkdir()
    fresh = module.RedisPrep.getInstance(str(wd))
    assert fresh.get_rq_job_id('x') is None
    assert 'rq:x' not in content(wd)


def test_replace_then_error_reports_uncertain_committed_bytes(state, monkeypatch):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    replace = io.os.replace
    def commit_then_error(*args, **kwargs):
        replace(*args, **kwargs)
        raise OSError('NFS response lost after replacement')
    monkeypatch.setattr(io.os, 'replace', commit_then_error)
    with pytest.raises(module.RedisPrepSnapshotError) as caught:
        prep.set_rq_job_id('x', 'new')
    assert caught.value.published is None
    assert content(wd)['rq:x'] == 'new'


def test_fork_rejects_root_symlink_without_external_mutation(state):
    _, _, wd = state
    from wepppy.rq.project_rq_fork import _rewrite_fork_redisprep_dump
    outside = wd.parent / 'external'
    outside.mkdir()
    (outside / 'redisprep.dump').write_text('{}')
    alias = wd / 'alias'
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        _rewrite_fork_redisprep_dump(str(alias))
    assert list(outside.iterdir()) == [outside / 'redisprep.dump']


@pytest.fixture
def archive_runtime(state, monkeypatch):
    from types import SimpleNamespace
    import wepppy.rq.project_rq as project
    module, client, wd = state
    monkeypatch.setattr(project, 'get_current_job', lambda: SimpleNamespace(id='rps-archive-test'))
    monkeypatch.setattr(project, 'get_wd', lambda runid: str(wd))
    monkeypatch.setattr(project, '_project_config_authority_wd', lambda runid: str(wd))
    monkeypatch.setattr(project.StatusMessenger, 'publish', lambda *args: None)
    monkeypatch.setattr(project.RedisPrep, 'getInstanceFromRunID', lambda runid: module.RedisPrep.getInstance(str(wd)))
    monkeypatch.setattr(project, 'lock_statuses', lambda runid: {})
    monkeypatch.setattr(project, 'clear_nodb_file_cache', lambda runid: [])
    monkeypatch.setattr(project.shutil, 'disk_usage', lambda _: SimpleNamespace(total=10**12, used=0, free=10**12))
    return project


def test_real_archive_roundtrip_and_incoming_mode_before_visibility(state, archive_runtime, monkeypatch):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    prep[module.TaskEnum.run_rhem] = 42
    prep.set_rq_job_id('run_rhem', 'archived')
    (wd / 'redisprep.dump').chmod(0o600)
    archive_runtime.archive_rq('project', 'RPS-01')
    archive = next((wd / 'archives').glob('*.zip'))
    prep.set_rq_job_id('run_rhem', 'newer-live')
    (wd / 'redisprep.dump').chmod(0o664)
    replace = io.os.replace
    seen = []
    def inspect_mode(src, dst, *args, **kwargs):
        if dst == 'redisprep.dump':
            info = os.stat(src, dir_fd=kwargs['src_dir_fd'])
            seen.append(info.st_mode & 0o777)
        return replace(src, dst, *args, **kwargs)
    monkeypatch.setattr(io.os, 'replace', inspect_mode)
    archive_runtime.restore_archive_rq('project', archive.name)
    recovered = module.RedisPrep.getInstance(str(wd))
    assert recovered.get_rq_job_id('run_rhem') == 'archived'
    assert recovered[module.TaskEnum.run_rhem] == 42
    assert recovered.get_archive_job_id() is None
    assert seen and set(seen) == {0o600}
    assert content(wd)['rq:run_rhem'] == 'archived'
    with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
        prep.dump()


def test_failed_restore_retains_incoming_snapshot_and_replacement_fence(state, archive_runtime, monkeypatch):
    import zipfile
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import resolve_scope
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('work', 'old-live')
    assert prep._scope.incarnation is None
    archives = wd / 'archives'
    archives.mkdir()
    incoming = {'attrs:loaded': 'true', 'rq:work': 'incoming'}
    with zipfile.ZipFile(archives / 'test.zip', 'w') as archive:
        archive.writestr('redisprep.dump', json.dumps(incoming))
        archive.writestr('late.txt', 'later member')
    original = zipfile.ZipFile.open
    def fail_late(self, name, *args, **kwargs):
        # testzip validates before extraction: fail only after incoming commit.
        if getattr(name, 'filename', name) == 'late.txt' and content(wd).get('rq:work') == 'incoming':
            raise OSError('late extraction failure')
        return original(self, name, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, 'open', fail_late)
    with pytest.raises(OSError, match='late extraction'):
        archive_runtime.restore_archive_rq('project', 'test.zip')
    assert content(wd) == incoming  # receipt cleanup must not overwrite it
    scope = resolve_scope(wd, create=True)
    assert scope.incarnation and not scope.initialization_only
    with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
        prep.set_rq_job_id('work', 'stale')


def test_namespace_bound_during_restore_cannot_mutate_wrong_hash(state):
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard, invalidate_catalog_incarnation
    marker = wd / '.redisprep-run-id'
    marker.write_text('profile;;fork;;project')
    module.RedisPrep.getInstance(str(wd))
    with catalog_lifecycle_guard(wd):
        invalidate_catalog_incarnation(wd)
        marker.unlink()
        # A write-free reader may observe the transient missing namespace.
        transient = module.RedisPrep(str(wd))
        assert transient.run_id == 'project'
        marker.write_text('profile;;fork;;project')
    with pytest.raises(module.RedisPrepSnapshotError, match='namespace changed'):
        transient.set_rq_job_id('work', 'wrong-hash')
    assert not client.hget('project', 'rq:work')


def test_nested_archived_snapshot_is_not_authority_to_replace_other_hash(state, archive_runtime):
    import zipfile
    module, client, wd = state
    module.RedisPrep.getInstance(str(wd))
    client.hset('shared-scenario', mapping={'attrs:loaded': 'true', 'rq:work': 'other-project'})
    (wd / 'archives').mkdir()
    with zipfile.ZipFile(wd / 'archives' / 'nested.zip', 'w') as archive:
        archive.writestr('redisprep.dump', '{"attrs:loaded":"true"}')
        archive.writestr('history/shared-scenario/redisprep.dump', '{"attrs:loaded":"true","rq:work":"archive"}')
    archive_runtime.restore_archive_rq('project', 'nested.zip')
    assert client.hget('shared-scenario', 'rq:work') == 'other-project'
    assert json.loads((wd / 'history/shared-scenario/redisprep.dump').read_text())['rq:work'] == 'archive'


def test_parallel_setters_complete_without_caller_retry(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    ctx = multiprocessing.get_context('fork')
    start = ctx.Barrier(5)
    def worker(index):
        start.wait(10)
        for step in range(8):
            prep.set_rq_job_id(f'worker-{index}', f'job-{step}')
    children = [ctx.Process(target=worker, args=(index,)) for index in range(4)]
    for child in children:
        child.start()
    start.wait(10)
    for child in children:
        child.join(15)
        if child.is_alive():
            child.kill()
            child.join()
        assert child.exitcode == 0
    assert prep.get_rq_job_ids() == {f'worker-{index}': 'job-7' for index in range(4)}
    assert cold(module, client, wd).get_rq_job_ids() == prep.get_rq_job_ids()


def test_killed_restore_retains_pre_destructive_fence(state, archive_runtime, monkeypatch):
    import zipfile
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import resolve_scope
    old = module.RedisPrep.getInstance(str(wd))
    assert old._scope.incarnation is None
    (wd / 'archives').mkdir()
    with zipfile.ZipFile(wd / 'archives/killed.zip', 'w') as archive:
        archive.writestr('redisprep.dump', '{"attrs:loaded":"true","rq:x":"incoming"}')
        archive.writestr('late.txt', 'late')
    ctx = multiprocessing.get_context('fork')
    committed = ctx.Event()
    def restore():
        original = zipfile.ZipFile.open
        def pause_late(self, name, *args, **kwargs):
            if getattr(name, 'filename', name) == 'late.txt' and content(wd).get('rq:x') == 'incoming':
                committed.set()
                ctx.Event().wait(20)
            return original(self, name, *args, **kwargs)
        zipfile.ZipFile.open = pause_late
        archive_runtime.restore_archive_rq('project', 'killed.zip')
    child = ctx.Process(target=restore)
    child.start()
    try:
        assert committed.wait(10)
        child.kill()
        child.join(5)
        assert content(wd)['rq:x'] == 'incoming'
        assert not resolve_scope(wd, create=True).initialization_only
        with pytest.raises(module.RedisPrepSnapshotError, match='replaced'):
            old.set_rq_job_id('x', 'stale')
    finally:
        if child.is_alive():
            child.kill()
        child.join()


def test_lifecycle_contention_fails_before_mutation_and_retry_succeeds(state):
    module, client, wd = state
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard
    prep = module.RedisPrep.getInstance(str(wd))
    ctx = multiprocessing.get_context('fork')
    held, release = ctx.Event(), ctx.Event()
    def lifecycle_owner():
        with catalog_lifecycle_guard(wd):
            held.set()
            assert release.wait(10)
    child = ctx.Process(target=lifecycle_owner)
    child.start()
    try:
        assert held.wait(10)
        with pytest.raises(BlockingIOError):
            prep.set_rq_job_id('x', 'busy')
        assert prep.get_rq_job_id('x') is None
        release.set()
        child.join(10)
        assert child.exitcode == 0
        prep.set_rq_job_id('x', 'retry')
        assert content(wd)['rq:x'] == 'retry'
    finally:
        release.set()
        if child.is_alive():
            child.kill()
        child.join()


def test_direct_receipt_removal_consumer_survives_reload(state):
    module, client, wd = state
    from wepppy.weppcloud.routes.weppcloudr import _clear_tracked_job
    prep = module.RedisPrep.getInstance(str(wd))
    prep.set_rq_job_id('render', 'old')
    prep.set_rq_job_id('keep', 'keep')
    _clear_tracked_job(prep, 'render')
    recovered = cold(module, client, wd)
    assert recovered.get_rq_job_ids() == {'keep': 'keep'}


def test_restore_exec_uncertainty_and_committed_live_file_failure(state, monkeypatch):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    execute = redis.client.Pipeline.execute
    def commit_then_disconnect(pipe, *args, **kwargs):
        execute(pipe, *args, **kwargs)
        raise redis.exceptions.ConnectionError('response lost after EXEC')
    with monkeypatch.context() as patch:
        patch.setattr(redis.client.Pipeline, 'execute', commit_then_disconnect)
        with pytest.raises(module.RedisPrepSnapshotError, match='transaction outcome uncertain') as caught:
            prep.restore_snapshot({'rq:work': 'committed-redis'})
        assert caught.value.live_committed is None
        assert client.hget('project', 'rq:work') == 'committed-redis'
    def fail_snapshot(*args, **kwargs):
        raise OSError('file write unavailable')
    monkeypatch.setattr(module, 'publish_snapshot', fail_snapshot)
    with pytest.raises(module.RedisPrepSnapshotError, match='live mutation committed') as caught:
        prep.restore_snapshot({'rq:work': 'next-redis'})
    assert caught.value.live_committed is True
    assert client.hget('project', 'rq:work') == 'next-redis'
    assert 'rq:work' not in content(wd)


def test_two_batch_leaf_initializations_serialize_without_caller_retry(state, monkeypatch):
    module, client, wd = state
    import wepppy.nodb.batch_runner as batch
    from tests.nodb.test_batch_runner import _runner_stub, _NoopLogger, _FeatureStub, _StopBeforeControllers
    from wepppy.query_engine import catalog_refresh as catalog
    root = wd.parent / 'batches'
    root.mkdir()
    runner = _runner_stub(root, rmtree_enabled=True)
    base = Path(runner.base_wd)
    base.mkdir()
    (base / 'redisprep.dump').write_text('{"attrs:loaded":"true","attrs:has_sbs":"true","timestamps:run_rhem":"42"}')
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([
        {'path': str(root), 'namespace': 'rps-batches', 'layout': 'batch',
         'coordination': str(root.parent / 'batch-locks')}]))
    catalog.resolve_scope(base, create=True)
    monkeypatch.setattr(batch, 'get_wd', lambda runid: str(Path(runner.wd) / 'runs' / runid.split(';;')[-1]))
    monkeypatch.setattr(batch.BatchRunner, '_get_run_logger', lambda *args: _NoopLogger())
    monkeypatch.setattr(batch, '_clear_batch_leaf_nodb_state', lambda *args: [])
    def stop_before_model(*args):
        raise _StopBeforeControllers()
    monkeypatch.setattr(batch.BatchRunner, '_resync_base_project_attributes_owned', stop_before_model)
    client.delete('leaf-a', 'leaf-b')
    ctx = multiprocessing.get_context('fork')
    copying, second_contended, release = ctx.Event(), ctx.Event(), ctx.Event()
    def initialize(name):
        if name == 'leaf-a':
            copytree = batch.shutil.copytree
            def paused_copy(*args, **kwargs):
                copying.set()
                assert release.wait(10)
                return copytree(*args, **kwargs)
            batch.shutil.copytree = paused_copy
        else:
            lockf = catalog.fcntl.lockf
            def observed_lock(fd, operation):
                if operation == catalog.fcntl.LOCK_EX and not second_contended.is_set():
                    try:
                        lockf(fd, operation | catalog.fcntl.LOCK_NB)
                    except BlockingIOError:
                        second_contended.set()
                    else:
                        raise AssertionError('batch owner did not serialize initialization')
                return lockf(fd, operation)
            catalog.fcntl.lockf = observed_lock
        try:
            runner._run_batch_hillslopes_owned(_FeatureStub(name))
        except _StopBeforeControllers:
            return
        raise AssertionError('model boundary should not run')
    first = ctx.Process(target=initialize, args=('leaf-a',))
    second = ctx.Process(target=initialize, args=('leaf-b',))
    first.start()
    try:
        assert copying.wait(10)
        second.start()
        assert second_contended.wait(10)
        release.set()
        first.join(15)
        second.join(15)
        assert first.exitcode == second.exitcode == 0
        for leaf in ('leaf-a', 'leaf-b'):
            destination = Path(runner.wd) / 'runs' / leaf
            prep = module.RedisPrep.getInstance(str(destination))
            assert prep.has_sbs and prep[module.TaskEnum.run_rhem] is None
            assert catalog.resolve_scope(destination).incarnation != catalog.resolve_scope(base).incarnation
    finally:
        release.set()
        for process in (first, second):
            if process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join(5)


def test_unreadable_snapshot_fails_without_empty_recovery(state):
    module, client, wd = state
    path = wd / 'redisprep.dump'
    path.write_text('{"rq:x":"retained"}')
    path.chmod(0)
    try:
        with pytest.raises(PermissionError):
            module.RedisPrep.getInstance(str(wd))
        assert client.hgetall('project') == {}
    finally:
        path.chmod(0o600)
    assert json.loads(path.read_text()) == {'rq:x': 'retained'}


def test_all_timestamp_reset_preserves_receipts_after_reload(state):
    module, client, wd = state
    prep = module.RedisPrep.getInstance(str(wd))
    prep.update_metadata({f'timestamps:{task}': 42 for task in module.TaskEnum})
    prep.set_rq_job_id('keep', 'retained')
    prep.remove_all_timestamp()
    recovered = cold(module, client, wd)
    assert all(recovered[task] is None for task in module.TaskEnum)
    assert recovered.get_rq_job_id('keep') == 'retained'
    assert not any(key.startswith('timestamps:') for key in content(wd))


def test_failed_writer_cleans_only_its_own_staging_file(state, monkeypatch):
    module, client, wd = state
    from wepppy.nodb import _redis_prep_snapshot as io
    prep = module.RedisPrep.getInstance(str(wd))
    previous = (wd / 'redisprep.dump').read_bytes()
    foreign = wd / '.redisprep.dump.another-owner.tmp'
    foreign.write_text('another writer evidence')
    def fail_write(*args):
        raise OSError('write failed')
    monkeypatch.setattr(io.os, 'write', fail_write)
    with pytest.raises(module.RedisPrepSnapshotError):
        prep.dump()
    assert list(wd.glob('.redisprep.dump.*.tmp')) == [foreign]
    assert foreign.read_text() == 'another writer evidence'
    assert (wd / 'redisprep.dump').read_bytes() == previous
