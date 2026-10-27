"""Real Redis streaming inventory: durable replay, fencing and bounded handoff."""
import json
from pathlib import Path

import pytest

from tests.rq.test_query_catalog_rq import catalog_queue, project, drain
from tests.rq.test_batch_task_boundary import isolated_rq
from wepppy.rq import query_catalog_rq as tasks
from wepppy.rq import _query_catalog_inventory as inventory
from wepppy.query_engine import catalog_refresh as core

pytestmark = pytest.mark.integration


def start(queue, roots):
    key = 'test:inventory'
    with queue.connection.pipeline() as pipe:
        inventory.initialize(pipe, key, 'cycle', roots)
        pipe.execute()
    value = inventory.state(queue.connection, key)
    value['job_id'] = 'attempt'
    queue.connection.set(key + ':discovery', json.dumps(value))
    return key


def test_streaming_job_and_scheduler_handoff(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    first = tasks.reconcile_query_catalogs(queue=queue)
    assert first['admitted'] == 0
    assert first['inventory_job_id']
    drain(queue, worker)
    assert not (path / '_query_engine').exists()  # Inventory writes no project files.
    worker.register_birth()
    worker.set_state('idle')
    second = tasks.reconcile_query_catalogs(queue=queue)
    assert second['admitted'] == 1
    drain(queue, worker)
    final = tasks.reconcile_query_catalogs(queue=queue)
    assert final['state'] == 'completed'
    assert (path / '_query_engine/catalog.json').is_file()


def test_restart_replays_without_duplicate_frontier(catalog_queue, monkeypatch):
    root, queue, _ = catalog_queue
    for i in range(7):
        project(root, str(i))
    roots = core.configured_roots()
    key = start(queue, roots)
    original = inventory.checkpoint
    calls = []

    def interrupt(*args, **kwargs):
        original(*args, **kwargs)
        if kwargs.get('entries'):
            calls.append(kwargs['entries'])
            raise KeyboardInterrupt('simulated worker death after durable checkpoint')

    monkeypatch.setattr(inventory, 'checkpoint', interrupt)
    with pytest.raises(KeyboardInterrupt):
        inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert queue.connection.llen(key + ':frontier') == 3
    monkeypatch.setattr(inventory, 'checkpoint', original)
    inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert inventory.state(queue.connection, key)['visited'] == 8
    assert queue.connection.xlen(key + ':stream') == 7
    assert inventory.state(queue.connection, key)['completed_at']


def test_replaced_worker_cannot_checkpoint(catalog_queue):
    root, queue, _ = catalog_queue
    key = start(queue, core.configured_roots())
    state = inventory.state(queue.connection, key)
    state['job_id'] = 'replacement'
    queue.connection.set(key + ':discovery', json.dumps(state))
    with pytest.raises(inventory.InventorySuperseded):
        inventory.checkpoint(queue.connection, key, 'attempt', 'cycle', exhausted=True)
    assert queue.connection.llen(key + ':frontier') == 1


def test_missing_root_retained_then_recovered(catalog_queue):
    root, queue, _ = catalog_queue
    roots = core.configured_roots()
    key = start(queue, roots)
    root.rmdir()
    with pytest.raises(FileNotFoundError):
        inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert inventory.state(queue.connection, key)['errors']
    assert not inventory.state(queue.connection, key).get('completed_at')
    assert queue.connection.llen(key + ':frontier') == 1
    root.mkdir()
    project(root)
    inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert inventory.state(queue.connection, key)['completed_at']


def test_scope_drain_budget_is_records_not_batches(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    for i in range(7):
        project(root, str(i))
    monkeypatch.setenv('QUERY_CATALOG_INVENTORY_LIMIT', '2')
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    assert queue.connection.xlen(key + ':stream') == 7
    tasks.reconcile_query_catalogs(queue=queue)
    assert queue.connection.xlen(key + ':stream') == 5
    pending = json.loads(queue.connection.get(key))['pending']
    assert len(pending) == 2
    tasks.reconcile_query_catalogs(queue=queue)
    assert queue.connection.xlen(key + ':stream') == 3


def test_failed_scheduler_commit_does_not_ack_discoveries(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    project(root)
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    connection = queue.connection
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    original = connection.pipeline
    conflicted = []

    def pipeline(*args, **kwargs):
        pipe = original(*args, **kwargs)
        execute = pipe.execute

        def conflict(*args, **kwargs):
            if not conflicted and any(command[0][0] == 'SET' and command[0][1] == key for command in pipe.command_stack):
                conflicted.append(True)
                connection.delete(key + ':lock')
            return execute(*args, **kwargs)
        pipe.execute = conflict
        return pipe

    monkeypatch.setattr(connection, 'pipeline', pipeline)
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'lease_lost'
    assert conflicted
    assert connection.xlen(key + ':stream') == 1
    assert not json.loads(connection.get(key)).get('pending')
    monkeypatch.setattr(connection, 'pipeline', original)
    tasks.reconcile_query_catalogs(queue=queue)
    assert connection.xlen(key + ':stream') == 0
    assert len(json.loads(connection.get(key))['pending']) == 1


def test_inventory_worker_kill_replays_checkpoint(catalog_queue, monkeypatch):
    import multiprocessing
    import os
    import time
    from rq.registry import StartedJobRegistry
    from rq.job import JobStatus

    root, queue, worker = catalog_queue
    for i in range(7):
        project(root, str(i))
    monkeypatch.setenv('QUERY_CATALOG_INVENTORY_LIMIT', '2')
    first = tasks.reconcile_query_catalogs(queue=queue)['inventory_job_id']
    context = multiprocessing.get_context('fork')
    entered = context.Event()
    release = context.Event()
    original = os.scandir

    class SlowStream:
        def __init__(self, path):
            self.path = Path(path)
            self.stream = original(path)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def __iter__(self):
            for index, entry in enumerate(self.stream):
                if self.path == root and index == 2:
                    entered.set()
                    release.wait(30)
                yield entry

    monkeypatch.setattr(inventory.os, 'scandir', SlowStream)
    worker.register_death()
    process = context.Process(target=worker.work, kwargs={'burst': True})
    process.start()
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    try:
        assert entered.wait(10)
        assert inventory.state(queue.connection, key)['entries'] == 2
        assert queue.connection.llen(key + ':frontier') == 3
        assert not queue.connection.exists(key + ':lock')
        process.kill()
        process.join(10)
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)
    monkeypatch.setattr(inventory.os, 'scandir', original)
    StartedJobRegistry(queue=queue).cleanup(timestamp=time.time() + 7200)
    assert queue.fetch_job(first).get_status() == JobStatus.FAILED
    worker.register_death()
    worker.register_birth()
    worker.set_state('idle')
    tasks.reconcile_query_catalogs(queue=queue)
    current = inventory.state(queue.connection, key)
    assert current['retry_at'] > time.time()
    assert queue.count == 0
    current['retry_at'] = 0
    queue.connection.set(key + ':discovery', json.dumps(current))
    resumed = tasks.reconcile_query_catalogs(queue=queue)
    assert resumed['inventory_job_id'] != first
    drain(queue, worker)
    assert inventory.state(queue.connection, key)['completed_at']
    assert inventory.state(queue.connection, key)['visited'] == 8
    assert queue.connection.xlen(key + ':stream') == 7


def test_scheduler_renews_owned_lease_between_scope_admissions(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    project(root, 'one')
    project(root, 'two')
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    original = core.record_catalog_refresh
    ttls = []

    def record(*args, **kwargs):
        ttls.append(queue.connection.pttl(key + ':lock'))
        result = original(*args, **kwargs)
        queue.connection.pexpire(key + ':lock', 5000)
        return result

    monkeypatch.setattr(core, 'record_catalog_refresh', record)
    assert tasks.reconcile_query_catalogs(queue=queue)['admitted'] == 2
    assert len(ttls) == 2
    assert min(ttls) > 50000


def test_scheduler_does_not_resurrect_expired_lease(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    project(root, 'one')
    project(root, 'two')
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    original = core.record_catalog_refresh

    def expire(*args, **kwargs):
        result = original(*args, **kwargs)
        queue.connection.delete(key + ':lock')
        return result

    monkeypatch.setattr(core, 'record_catalog_refresh', expire)
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'lease_lost'
    assert not queue.connection.exists(key + ':lock')
    assert queue.connection.xlen(key + ':stream') == 2


def test_multiple_namespaces_nested_scopes_and_scientific_tree_exclusion(catalog_queue, tmp_path):
    from dataclasses import replace
    root, queue, _ = catalog_queue
    prototype = core.configured_roots()[0]
    roots = []
    for i, layout in enumerate(('sharded', 'batch', 'culverts')):
        base = tmp_path / layout
        base.mkdir()
        roots.append(replace(prototype, path=base, namespace='namespace-' + str(i), layout=layout))
        group = base / 'group'
        group.mkdir()
        parent = project(group)
        ignored = parent / 'scientific-output'
        ignored.mkdir()
        project(ignored)
        nested = parent / '_pups/omni/scenarios'
        nested.mkdir(parents=True)
        project(nested, 'child')
    key = start(queue, roots)
    inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert inventory.state(queue.connection, key)['completed_at']
    paths = [fields[b'path'].decode() for _, fields in queue.connection.xrange(key + ':stream')]
    assert len(paths) == 6
    assert not any('scientific-output' in path for path in paths)


@pytest.mark.parametrize('relative', ['../outside', '/etc', 'linked'])
def test_hostile_frontier_never_traverses(catalog_queue, tmp_path, relative):
    root, queue, _ = catalog_queue
    outside = tmp_path / 'outside'
    outside.mkdir()
    project(outside)
    (root / 'linked').symlink_to(outside, target_is_directory=True)
    roots = core.configured_roots()
    key = start(queue, roots)
    queue.connection.lset(key + ':frontier', 0, json.dumps({'root': 0, 'relative': relative}))
    with pytest.raises(ValueError):
        inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 2)
    assert queue.connection.xlen(key + ':stream') == 0
    assert inventory.state(queue.connection, key)['errors']
    assert not (outside / 'sample/_query_engine').exists()


def test_real_watch_conflict_fences_frontier_and_scope(catalog_queue, monkeypatch):
    root, queue, _ = catalog_queue
    key = start(queue, core.configured_roots())
    connection = queue.connection
    original = connection.pipeline

    def pipeline(*args, **kwargs):
        pipe = original(*args, **kwargs)
        execute = pipe.execute
        def replace(*args, **kwargs):
            current = inventory.state(connection, key)
            current['job_id'] = 'replacement'
            connection.set(key + ':discovery', json.dumps(current))
            return execute(*args, **kwargs)
        pipe.execute = replace
        return pipe

    monkeypatch.setattr(connection, 'pipeline', pipeline)
    with pytest.raises(inventory.InventorySuperseded):
        inventory.checkpoint(connection, key, 'attempt', 'cycle',
                             children=[{'root': 0, 'relative': 'child'}], scope=str(root), exhausted=True)
    assert connection.llen(key + ':frontier') == 1
    assert connection.scard(key + ':seen') == 0
    assert connection.xlen(key + ':stream') == 0


def test_replaced_directory_restarts_seen_state(catalog_queue, monkeypatch):
    root, queue, _ = catalog_queue
    project(root, 'one')
    project(root, 'two')
    roots = core.configured_roots()
    key = start(queue, roots)
    original = inventory.checkpoint

    def interrupt(*args, **kwargs):
        original(*args, **kwargs)
        if kwargs.get('entries'):
            raise KeyboardInterrupt
    monkeypatch.setattr(inventory, 'checkpoint', interrupt)
    with pytest.raises(KeyboardInterrupt):
        inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 1)
    old = root.with_name('old-runs')
    root.rename(old)
    root.mkdir()
    project(root, 'one')
    project(root, 'new')
    monkeypatch.setattr(inventory, 'checkpoint', original)
    inventory.run(queue.connection, key, 'attempt', 'cycle', roots, 1)
    paths = {fields[b'path'].decode() for _, fields in queue.connection.xrange(key + ':stream')}
    assert paths == {str(root / 'one'), str(root / 'new')}
    assert inventory.state(queue.connection, key)['completed_at']


@pytest.mark.parametrize('source', ['stream', 'dirty', 'pending'])
@pytest.mark.parametrize('inside', [False, True])
def test_scheduler_rejects_replaced_scope_before_metadata_writes(catalog_queue, source, inside):
    root, queue, worker = catalog_queue
    path = project(root)
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    connection = queue.connection
    key = 'query-catalog:inventory:' + tasks._configuration_id()
    if source != 'stream':
        connection.delete(key + ':stream')
    if source == 'dirty':
        connection.sadd('query-catalog:dirty:' + tasks._configuration_id(), str(path))
    if source == 'pending':
        cursor = json.loads(connection.get(key))
        cursor['pending'] = [{'path': str(path), 'reconcile': True, 'cycle': True}]
        connection.set(key, json.dumps(cursor))
    target = project(root if inside else root.parent, 'target')
    path.rename(root / 'old-sample')
    path.symlink_to(target, target_is_directory=True)
    outcome = tasks.reconcile_query_catalogs(queue=queue)
    assert outcome['state'] == 'degraded'
    assert outcome['admitted'] == 0
    assert queue.count == 0
    assert not (target / '_query_engine').exists()
    assert not (root / 'old-sample/_query_engine').exists()


def test_scheduler_rejects_unconfigured_dirty_path(catalog_queue):
    root, queue, worker = catalog_queue
    outside = project(root.parent, 'outside')
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    queue.connection.sadd('query-catalog:dirty:' + tasks._configuration_id(), str(outside))
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'degraded'
    assert not (outside / '_query_engine').exists()


def test_scheduler_deleted_child_does_not_mask_missing_required_root(catalog_queue):
    import shutil
    root, queue, worker = catalog_queue
    path = project(root)
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    root.rename(root.with_name('missing-root'))
    failed = tasks.reconcile_query_catalogs(queue=queue)
    assert failed['state'] == 'degraded'
    assert failed['completed_at'] is None
    root.with_name('missing-root').rename(root)
    shutil.rmtree(path)
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    recovered = tasks.reconcile_query_catalogs(queue=queue)
    assert recovered['state'] == 'completed'
    assert recovered['admitted'] == 0


def test_completed_inventory_detects_root_loss_and_rediscovers_without_daily_wait(catalog_queue):
    root, queue, worker = catalog_queue
    first = tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'completed'
    root.rmdir()
    missing = tasks.reconcile_query_catalogs(queue=queue)
    assert missing['state'] == 'degraded'
    assert missing['unavailable_namespaces']
    assert missing['completed_at'] is None
    root.mkdir()
    path = project(root)
    recovered = tasks.reconcile_query_catalogs(queue=queue)
    assert recovered['state'] == 'pending'
    assert recovered['unavailable_namespaces'] == []
    assert recovered['inventory_job_id'] != first['inventory_job_id']
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    assert tasks.reconcile_query_catalogs(queue=queue)['admitted'] == 1
    drain(queue, worker)
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'completed'
    assert (path / '_query_engine/catalog.json').is_file()


def test_inventory_protocol_capability_blocks_mixed_live_consumers(catalog_queue):
    from uuid import uuid4
    from tests.rq.test_query_catalog_rq import CatalogWorker

    root, queue, worker = catalog_queue
    old = CatalogWorker([queue], connection=queue.connection, name='old-inventory-' + uuid4().hex)
    old.register_birth()
    old.set_state('idle')
    configuration = tasks.catalog_worker_configuration()
    configuration.pop('inventory_protocol')
    queue.connection.hset(old.key, tasks.WORKER_FIELD, json.dumps(configuration))
    path = project(root)
    core.record_catalog_refresh(path)
    try:
        assert tasks.consumer_status(queue)['compatible'] == 8
        assert tasks.consumer_status(queue)['incompatible']
        assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'degraded'
        assert tasks.enqueue_catalog_refresh(path, queue=queue)['error_code'] == 'query_catalog_workers_unavailable'
        assert queue.count == 0
        queue.connection.hset(old.key, tasks.WORKER_FIELD, json.dumps(tasks.catalog_worker_configuration()))
        assert tasks.consumer_status(queue)['compatible'] == 9
        assert not tasks.consumer_status(queue)['incompatible']
        assert tasks.reconcile_query_catalogs(queue=queue)['inventory_job_id']
        assert queue.count == 2
    finally:
        old.register_death()


def test_pending_locator_rebases_only_explicit_namespace_alias(catalog_queue, monkeypatch):
    from dataclasses import replace
    root, queue, worker = catalog_queue
    path = project(root)
    alias = root.with_name('available-alias')
    roots = core.configured_roots()
    monkeypatch.setattr(core, 'configured_roots', lambda: roots + [replace(roots[0], path=alias)])
    for consumer in [worker, *worker._catalog_test_companions]:
        consumer.register_death()
        consumer.register_birth()
        consumer.set_state("idle")
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    # Renaming retains the exact project/root inodes while losing one spelling.
    original_identity = (path.stat().st_dev, path.stat().st_ino)
    dirty_key = 'query-catalog:dirty:' + tasks._configuration_id()
    queue.connection.sadd(dirty_key, str(path))
    root.rename(alias)
    assert (alias / path.name).stat().st_ino == original_identity[1]
    result = tasks.reconcile_query_catalogs(queue=queue)
    assert result['unavailable_namespaces'] == []
    assert result['unavailable_aliases'][0]['root'] == 0
    assert result['admitted'] == 1
    assert result['state'] == 'pending'
    drain(queue, worker)
    final = tasks.reconcile_query_catalogs(queue=queue)
    assert final['state'] == 'completed'
    assert queue.connection.scard(dirty_key) == 0
    assert (alias / path.name / '_query_engine/catalog.json').is_file()
