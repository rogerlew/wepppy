"""Real Redis pilot authority, capacity, failure and disabled-mode boundaries."""
from concurrent.futures import ThreadPoolExecutor
import json
import time
from uuid import uuid4

import pytest
from rq.job import Job, JobStatus

from tests.rq.test_query_catalog_rq import catalog_queue, project, drain
from tests.rq.test_batch_task_boundary import isolated_rq
from wepppy.rq import query_catalog_rq as tasks
from wepppy.rq import _query_catalog_pilot as pilot
from wepppy.rq import _query_catalog_admission as guard
from wepppy.query_engine import catalog_refresh as core

pytestmark = pytest.mark.integration


def enable_pilot(root, queue, worker, monkeypatch, count=2):
    monkeypatch.setenv('QUERY_CATALOG_REFRESH_ENABLED', 'false')
    for consumer in [worker, *worker._catalog_test_companions]:
        consumer.register_death()
        consumer.register_birth()
        consumer.set_state('idle')
    identifier = 'pilot-' + uuid4().hex
    paths = []
    for i in range(count):
        path = project(root, 'fixture-' + str(i))
        (path / pilot.MARKER).write_text(json.dumps({'pilot_id': identifier}))
        core.resolve_scope(path, create=True)
        paths.append(path)
    pilot.register_pilot(queue.connection, identifier, list(map(str, paths)))
    token = pilot.acquire_controller(queue.connection, identifier)
    pilot.observe_pilot(queue.connection, identifier, token)
    pilot.resume_pilot(queue.connection, identifier, token)
    return identifier, token, paths


def tick(queue, identifier, token):
    return tasks.reconcile_query_catalogs(queue=queue, pilot_id=identifier, controller_token=token)


def work(queue, worker):
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')


def test_legacy_batch_pilot_is_readable_but_cannot_resume_or_admit(catalog_queue, monkeypatch):
    import hashlib

    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    data = pilot.read(queue.connection, identifier)
    data['manifest']['queue'] = 'batch'
    data['manifest']['configuration'].pop('queue')
    data['manifest_sha256'] = hashlib.sha256(json.dumps(data['manifest'], sort_keys=True).encode()).hexdigest()
    retained = json.dumps(data).encode()
    queue.connection.set(pilot.key(identifier), retained)
    assert pilot.read(queue.connection, identifier)['manifest']['queue'] == 'batch'
    with pytest.raises(RuntimeError, match='configuration changed'):
        pilot.resume_pilot(queue.connection, identifier, token)
    with pytest.raises(RuntimeError, match='configuration changed'):
        pilot.authorize_receipt(queue.connection, identifier, str(paths[0]), token)
    assert queue.connection.get(pilot.key(identifier)) == retained


@pytest.mark.parametrize('uncertain', [False, True])
def test_legacy_ledger_keeps_permits_across_queue_change(catalog_queue, uncertain):
    from rq import Queue

    root, queue, _ = catalog_queue
    for i in range(7):
        path = project(root, str(i))
        core.record_catalog_refresh(path)
        assert tasks.enqueue_catalog_refresh(path, queue=queue)['state'] == 'queued'
    ledger = json.loads(queue.connection.get(guard.LEDGER_KEY))
    batch = Queue('batch', connection=queue.connection)
    for jid, binding in ledger['jobs'].items():
        binding['configuration'].pop('queue')
        queue.connection.hset(Job.key_for(jid), 'origin', 'batch')
        queue.connection.lrem(queue.key, 0, jid)
        queue.connection.rpush(batch.key, jid)
    if uncertain:
        jid = next(iter(ledger['jobs']))
        ledger['jobs'][jid]['claimed'] = True
        queue.connection.hset(Job.key_for(jid), 'status', 'canceled')
    retained = json.dumps(ledger).encode()
    queue.connection.set(guard.LEDGER_KEY, retained)
    try:
        guard.initialize_admission(queue.connection, queue)
        path = project(root, 'new')
        core.record_catalog_refresh(path)
        result = tasks.enqueue_catalog_refresh(path, queue=queue)
        expected = 'query_catalog_accounting_uncertain' if uncertain else 'query_catalog_capacity_pending'
        assert result['error_code'] == expected
        assert queue.connection.get(guard.LEDGER_KEY) == retained
        assert queue.count == 0
    finally:
        batch.delete(delete_jobs=True)


def test_disabled_pilot_real_workers_exact_inventory_and_catalogs(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    sentinel = project(root, 'held-out')
    nested = paths[0] / '_pups/runs'
    nested.mkdir(parents=True)
    unlisted = project(nested, 'unlisted')
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'disabled'
    assert not core.catalog_refresh_enabled()
    first = tick(queue, identifier, token)
    assert first['inventory_job_id']
    work(queue, worker)
    assert tick(queue, identifier, token)['admitted'] == 2
    work(queue, worker)
    assert tick(queue, identifier, token)['state'] == 'completed'
    status = pilot.pilot_status(queue.connection, identifier)
    assert status['counters'] == {'refresh': 2, 'inventory': 1}
    assert status['outstanding'] == 0
    assert len(status['jobs']) == 3
    assert not (sentinel / '_query_engine').exists()
    assert not (unlisted / '_query_engine').exists()
    for path in paths:
        assert not core.pending_catalog_requests(path)
        assert 'values.csv' in {entry['path'] for entry in json.loads((path / '_query_engine/catalog.json').read_text())['files']}


def test_shared_cap_limits_concurrent_distinct_scope_admission(catalog_queue):
    root, queue, _ = catalog_queue
    paths = [project(root, str(i)) for i in range(12)]
    for path in paths:
        core.record_catalog_refresh(path)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda p: tasks.enqueue_catalog_refresh(p, queue=queue), paths))
    # Retry known WATCH conflicts; cap still applies to the final distinct set.
    for path in paths:
        tasks.enqueue_catalog_refresh(path, queue=queue)
    assert queue.count == 7
    assert len(json.loads(queue.connection.get(guard.LEDGER_KEY))['jobs']) == 7
    assert tasks.reconcile_query_catalogs(queue=queue)['inventory_job_id'] is None
    assert queue.count == 7


def test_ordinary_backlog_latches_pause_without_spending_budget(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    ordinary = queue.enqueue_call('builtins.str', args=('ordinary',))
    result = tick(queue, identifier, token)
    assert not result.get('inventory_job_id')
    status = pilot.pilot_status(queue.connection, identifier)
    assert status['state'] == 'paused'
    assert status['counters'] == {'refresh': 0, 'inventory': 0}
    ordinary.cancel()
    assert not tick(queue, identifier, token).get('inventory_job_id')
    pilot.observe_pilot(queue.connection, identifier, token)
    pilot.resume_pilot(queue.connection, identifier, token)
    assert tick(queue, identifier, token)['inventory_job_id']


def test_observer_loss_blocks_new_work_but_admitted_job_drains(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    queued = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    queue.connection.delete(pilot.key(identifier) + ':observer')
    with pytest.raises(RuntimeError):
        pilot.authorize_receipt(queue.connection, identifier, str(paths[1]), token)
    tick(queue, identifier, token)
    assert pilot.pilot_status(queue.connection, identifier)['state'] == 'paused'
    work(queue, worker)
    assert queue.fetch_job(queued['job_id']).get_status() == JobStatus.FINISHED
    assert not core.pending_catalog_requests(paths[0])


def test_manifest_counters_and_phase_survive_controller_restart(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    pilot.record_phase(queue.connection, identifier, token, 'receipt_wave_started', True)
    core.record_catalog_refresh(paths[0])
    tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    original = pilot.pilot_status(queue.connection, identifier)
    queue.connection.delete(pilot.key(identifier) + ':observer')
    replacement = pilot.acquire_controller(queue.connection, identifier)
    pilot.observe_pilot(queue.connection, identifier, replacement)
    pilot.resume_pilot(queue.connection, identifier, replacement)
    restored = pilot.pilot_status(queue.connection, identifier)
    assert restored['manifest'] == original['manifest']
    assert restored['counters'] == original['counters']
    assert restored['phases']['receipt_wave_started'] is True
    with pytest.raises(ValueError):
        pilot.register_pilot(queue.connection, identifier, list(map(str, paths)))
    with pytest.raises(ValueError):
        pilot.record_phase(queue.connection, identifier, replacement, 'receipt_wave_started', False)


def test_missing_ledger_does_not_recreate_pilot_budget(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    queue.connection.delete(guard.LEDGER_KEY)
    assert not tick(queue, identifier, token).get('inventory_job_id')
    assert not queue.connection.exists(guard.LEDGER_KEY)
    with pytest.raises(guard.AdmissionDenied):
        guard.initialize_admission(queue.connection, queue)
    assert pilot.read(queue.connection, identifier)['counters'] == {'refresh': 0, 'inventory': 0}


def test_pilot_refuses_changed_or_unlisted_scope_before_creation(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    outside = project(root.parent, 'outside')
    paths[0].rename(root / 'old-fixture')
    paths[0].symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        pilot.authorize_receipt(queue.connection, identifier, str(paths[0]), token)
    with pytest.raises(ValueError):
        tasks.enqueue_catalog_refresh(outside, queue=queue, pilot_id=identifier, controller_token=token)
    assert not (outside / '_query_engine').exists()
    assert queue.count == 0


def test_same_id_manual_reexecution_cannot_reuse_authority(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    result = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    work(queue, worker)
    catalog = (paths[0] / '_query_engine/catalog.json').read_bytes()
    # The real RQ enqueue API can queue an old job, but execution authority cannot.
    queue.enqueue_job(queue.fetch_job(result['job_id']))
    work(queue, worker)
    assert queue.fetch_job(result['job_id']).get_status() == JobStatus.FAILED
    assert (paths[0] / '_query_engine/catalog.json').read_bytes() == catalog
    assert pilot.pilot_status(queue.connection, identifier)['counters']['refresh'] == 1


def test_counter_corruption_cannot_restore_attempt_budget(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    data = pilot.read(queue.connection, identifier)
    data['counters']['refresh'] = 0
    queue.connection.set(pilot.key(identifier), json.dumps(data))
    with pytest.raises(ValueError, match='counters disagree'):
        pilot.authorize_receipt(queue.connection, identifier, str(paths[1]), token)
    assert queue.count == 1


def test_duplicate_known_queue_entries_cannot_mask_ordinary_tail(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    admitted = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    queue.connection.rpush(queue.key, *([admitted['job_id']] * 8))
    queue.enqueue_call('builtins.str', args=('ordinary',))
    before = pilot.read(queue.connection, identifier)['counters']
    assert not tick(queue, identifier, token).get('inventory_job_id')
    assert pilot.read(queue.connection, identifier)['counters'] == before
    assert pilot.pilot_status(queue.connection, identifier)['state'] == 'paused'
    # Avoid duplicate queue cleanup obscuring the admission assertion.
    queue.connection.lrem(queue.key, 0, admitted['job_id'])


def test_pilot_requires_all_twelve_real_registered_consumers(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    worker._catalog_test_companions[0].register_death()
    assert not tick(queue, identifier, token).get('inventory_job_id')
    assert pilot.read(queue.connection, identifier)['counters'] == dict(refresh=0, inventory=0)
    assert pilot.pilot_status(queue.connection, identifier)['state'] == 'paused'


def test_inode_identity_ignores_host_mount_device_but_rejects_replacement(catalog_queue, monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    original = Path.stat
    def mounted_stat(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path == paths[0]:
            return SimpleNamespace(st_ino=result.st_ino, st_dev=result.st_dev + 100, st_mode=result.st_mode)
        return result
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'stat', mounted_stat)
        assert pilot._directory_identity(paths[0]) == pilot.read(queue.connection, identifier)['manifest']['scopes'][0]['directory_identity']
    paths[0].rename(root / 'original-inode')
    replacement = project(root, paths[0].name)
    import shutil
    shutil.copytree(root / 'original-inode' / '_query_engine', replacement / '_query_engine')
    (replacement / pilot.MARKER).write_text(json.dumps({'pilot_id': identifier}))
    with pytest.raises(ValueError, match='identity changed'):
        pilot.authorize_receipt(queue.connection, identifier, str(replacement), token)


def test_missing_reserved_job_fails_closed_without_freeing_slot(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    admitted = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    queue.connection.delete(Job.key_for(admitted['job_id']))
    assert not tick(queue, identifier, token).get('inventory_job_id')
    assert admitted['job_id'] in guard._ledger(queue.connection)['jobs']
    assert pilot.pilot_status(queue.connection, identifier)['global_uncertain']


def test_retry_attempts_exhaust_refresh_budget_without_reset(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    ids = set()
    for _ in range(25):
        result = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
        ids.add(result['job_id'])
        queue.fetch_job(result['job_id']).cancel()
    result = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    assert not result.get('job_id')
    assert len(ids) == 25
    assert pilot.read(queue.connection, identifier)['counters']['refresh'] == 25
    assert core.pending_catalog_requests(paths[0])


def test_independent_pilots_share_global_capacity(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    first, token, paths = enable_pilot(root, queue, worker, monkeypatch, count=7)
    for path in paths:
        core.record_catalog_refresh(path)
        assert tasks.enqueue_catalog_refresh(path, queue=queue, pilot_id=first, controller_token=token)['job_id']
    second = 'pilot-' + uuid4().hex
    other = project(root, 'second-pilot')
    (other / pilot.MARKER).write_text(json.dumps({'pilot_id': second}))
    core.resolve_scope(other, create=True)
    pilot.register_pilot(queue.connection, second, [str(other)])
    second_token = pilot.acquire_controller(queue.connection, second)
    pilot.observe_pilot(queue.connection, second, second_token)
    pilot.resume_pilot(queue.connection, second, second_token)
    core.record_catalog_refresh(other)
    assert not tasks.enqueue_catalog_refresh(other, queue=queue, pilot_id=second, controller_token=second_token).get('job_id')
    assert pilot.read(queue.connection, second)['counters'] == dict(refresh=0, inventory=0)
    assert pilot.pilot_status(queue.connection, second)['global_outstanding'] == 7


def test_unknown_raw_payload_is_backlog_not_deserialized(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    unknown = 'query_catalog_refresh_unknown'
    queue.connection.hset(Job.key_for(unknown), mapping={'data': b'not a pickle', 'status': 'queued'})
    queue.connection.rpush(queue.key, unknown)
    assert not tick(queue, identifier, token).get('inventory_job_id')
    assert pilot.read(queue.connection, identifier)['counters'] == dict(refresh=0, inventory=0)
    queue.connection.lrem(queue.key, 0, unknown)
    queue.connection.delete(Job.key_for(unknown))


def test_inventory_retries_debit_distinct_attempts(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    first = tick(queue, identifier, token)['inventory_job_id']
    queue.fetch_job(first).cancel()
    tick(queue, identifier, token)  # Persist the normal retry backoff.
    discovery = next(queue.connection.scan_iter('*:pilot:' + identifier + ':discovery'))
    state = json.loads(queue.connection.get(discovery))
    assert state['retry_at'] > time.time()
    state['retry_at'] = 0  # Advance the scheduling boundary without a wall-clock sleep.
    queue.connection.set(discovery, json.dumps(state))
    second = tick(queue, identifier, token)['inventory_job_id']
    assert second != first
    queue.fetch_job(second).cancel()
    tick(queue, identifier, token)
    state = json.loads(queue.connection.get(discovery))
    state['retry_at'] = 0
    queue.connection.set(discovery, json.dumps(state))
    third = tick(queue, identifier, token)
    assert third.get('inventory_job_id') in {None, second}
    assert queue.count == 0
    assert pilot.read(queue.connection, identifier)['counters']['inventory'] == 2


def test_concurrent_claims_commit_once_per_admitted_job(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch, count=7)
    jobs = []
    for path in paths:
        core.record_catalog_refresh(path)
        result = tasks.enqueue_catalog_refresh(path, queue=queue, pilot_id=identifier, controller_token=token)
        job = queue.fetch_job(result['job_id'])
        queue.connection.lrem(queue.key, 0, job.id)
        job.set_status(JobStatus.STARTED)
        jobs.append((job, path))
    def claim(pair):
        job, path = pair
        scope = core.resolve_scope(path, create=False)
        return guard.authorize_job(queue.connection, job, kind='refresh', pilot_id=identifier,
                                   scope_id=scope.scope_id, wd=str(path))
    with ThreadPoolExecutor(max_workers=7) as pool:
        assert len(list(pool.map(claim, jobs))) == 7
    assert all(binding['claimed'] for binding in pilot.read(queue.connection, identifier)['jobs'].values())
    with pytest.raises(ValueError, match='unused admitted'):
        claim(jobs[0])


def test_ordinary_arrival_invalidates_admission_transaction(catalog_queue):
    root, queue, worker = catalog_queue
    from redis.exceptions import WatchError
    with queue.connection.pipeline() as pipe:
        ticket = guard.prepare(pipe, queue, job_id=tasks.PREFIX + str(uuid4()), kind='inventory',
                               configuration=tasks.catalog_worker_configuration())
        ordinary = queue.enqueue_call('builtins.str', args=('ordinary',))
        pipe.multi()
        guard.commit(pipe, ticket)
        with pytest.raises(WatchError):
            pipe.execute()
    assert guard._ledger(queue.connection)['jobs'] == {}
    assert queue.job_ids == [ordinary.id]



def test_claim_rechecks_concurrent_job_status_change(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch)
    core.record_catalog_refresh(paths[0])
    result = tasks.enqueue_catalog_refresh(paths[0], queue=queue, pilot_id=identifier, controller_token=token)
    job = queue.fetch_job(result['job_id'])
    queue.connection.lrem(queue.key, 0, job.id)
    job.set_status(JobStatus.STARTED)
    scope = core.resolve_scope(paths[0], create=False)
    original = pilot._scope
    def cancel_after_validation(manifest, path):
        approved = original(manifest, path)
        job.cancel()
        return approved
    monkeypatch.setattr(pilot, '_scope', cancel_after_validation)
    with pytest.raises(ValueError, match='not started'):
        guard.authorize_job(queue.connection, job, kind='refresh', pilot_id=identifier,
                            scope_id=scope.scope_id, wd=str(paths[0]))
    assert not pilot.read(queue.connection, identifier)['jobs'][job.id]['claimed']


def test_running_cancellation_retains_capacity_until_execution_exits(catalog_queue, monkeypatch):
    import multiprocessing
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch, count=8)
    for path in paths:
        core.record_catalog_refresh(path)
    jobs = [tasks.enqueue_catalog_refresh(path, queue=queue, pilot_id=identifier,
                                         controller_token=token)['job_id'] for path in paths[:7]]
    context = multiprocessing.get_context('fork')
    entered, release = context.Event(), context.Event()
    refresh = core.refresh_catalog
    def blocked_refresh(*args, **kwargs):
        entered.set()
        assert release.wait(20)
        return refresh(*args, **kwargs)
    def execute_one():
        worker.register_death()
        worker.work(burst=True, max_jobs=1)
    monkeypatch.setattr(core, 'refresh_catalog', blocked_refresh)
    process = context.Process(target=execute_one)
    process.start()
    try:
        assert entered.wait(10)
        queue.fetch_job(jobs[0]).cancel()
        assert process.is_alive()
        status = pilot.pilot_status(queue.connection, identifier)
        assert status['outstanding'] == status['global_outstanding'] == 7
        assert status['global_uncertain'] == 1
        assert not tasks.enqueue_catalog_refresh(paths[7], queue=queue, pilot_id=identifier,
                                                 controller_token=token).get('job_id')
        observed = pilot.observe_pilot(queue.connection, identifier, token)
        assert observed['state'] == 'paused' and observed['global_uncertain']
        # Rejected replay must not mark the real admitted execution as exited.
        job = queue.fetch_job(jobs[0])
        with pytest.raises(ValueError):
            guard.authorize_job(queue.connection, job, kind='refresh', pilot_id=identifier,
                                scope_id=core.resolve_scope(paths[0], create=False).scope_id, wd=str(paths[0]))
        assert not pilot.read(queue.connection, identifier)['jobs'][jobs[0]].get('execution_exited_at')
    finally:
        release.set()
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert process.exitcode == 0
    binding = pilot.read(queue.connection, identifier)['jobs'][jobs[0]]
    assert binding['execution_exited_at'] >= binding['claimed_at']
    assert not core.pending_catalog_requests(paths[0])
    status = pilot.pilot_status(queue.connection, identifier)
    assert status['global_outstanding'] == 6 and not status['global_uncertain']
    assert not guard.execution_outstanding(binding, 'canceled')


def test_pilot_observes_plain_job_id_from_real_execution_registry(catalog_queue):
    executions = pytest.importorskip("rq.executions")
    from tools.query_catalog_pilot import Runtime

    _root, queue, _worker = catalog_queue
    job = queue.enqueue(sum, [1, 2])
    job.started_at = job.enqueued_at
    job.set_status(JobStatus.STARTED)
    job.save()
    queue.remove(job.id)
    with queue.connection.pipeline() as pipeline:
        execution = executions.Execution.create(job, ttl=60, pipeline=pipeline)
        pipeline.execute()
    assert execution.composite_key.encode() in queue.connection.zrange(job.started_job_registry.key, 0, -1)
    runtime = Runtime.__new__(Runtime)
    runtime.connection, runtime.queue, runtime.ordinary_seen = queue.connection, queue, set()
    try:
        result = runtime.raw_ordinary({"global_job_ids": []})
        assert job.id in result["started_ids"]
        assert execution.composite_key not in result["jobs"]
        assert result["jobs"][job.id]["status"] == "started"
        assert result["wait_seconds"][job.id] == 0.0
        assert runtime.raw_ordinary({"global_job_ids": [job.id]})["started_ids"] == result["started_ids"]
    finally:
        with queue.connection.pipeline() as pipeline:
            execution.delete(job, pipeline)
            pipeline.execute()
