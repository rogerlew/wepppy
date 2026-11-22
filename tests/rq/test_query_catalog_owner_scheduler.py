"""Exercise owner saturation and recovery through general catalog reconciliation."""
import json

import pytest

from tests.rq.test_batch_task_boundary import isolated_rq
from tests.rq.test_query_catalog_rq import catalog_queue, discover, drain, project
from wepppy.query_engine import catalog_refresh as core
from wepppy.rq import _query_catalog_admission as admission
from wepppy.rq import query_catalog_rq as tasks

pytestmark = pytest.mark.integration


def test_scheduler_defers_alias_sibling_admits_peer_and_recovers(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    conn = queue.connection
    alias = root.with_name('alias')
    alias.mkdir()
    batch = dict(tasks.catalog_worker_configuration()['roots'][0], layout='batch')
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([batch, dict(batch, path=str(alias))]))
    for consumer in [worker, *worker._catalog_test_companions]:
        conn.hset(consumer.key, tasks.WORKER_FIELD, json.dumps(tasks.catalog_worker_configuration()))

    first_runs = root / 'owner-a' / 'runs'
    first_runs.mkdir(parents=True)
    reserved = [project(first_runs, name) for name in ('one', 'two')]
    sibling = project(first_runs, 'three')
    receipt = core.record_catalog_refresh(sibling, 'values.csv')
    # Move the same directory/receipt across configured root spellings.
    alias_runs = alias / 'owner-a' / 'runs'
    alias_runs.mkdir(parents=True)
    sibling = sibling.rename(alias_runs / sibling.name)
    other_runs = alias / 'owner-b' / 'runs'
    other_runs.mkdir(parents=True)
    peer = project(other_runs)
    assert core.catalog_guard_identity(reserved[0]) == core.catalog_guard_identity(sibling)
    discover(queue, worker)

    for child in reserved:
        core.record_catalog_refresh(child, 'values.csv')
        assert tasks.enqueue_catalog_refresh(child, queue=queue)['job_id']
    conn.set(admission.OWNER_POLICY_KEY, batch['namespace'])
    try:
        tasks.reconcile_query_catalogs(queue=queue)
        key = 'query-catalog:inventory:' + tasks._configuration_id()
        assert json.loads(conn.get(key + ':health'))['owner_deferrals'] == 1
        queued_paths = {job.kwargs['wd'] for job in queue.jobs}
        assert queued_paths == {str(child) for child in [*reserved, peer]}
        assert receipt['request_id'] in {r['request_id'] for r in core.pending_catalog_requests(sibling)}
        drain(queue, worker)
        worker.register_birth()
        worker.set_state('idle')

        tasks.reconcile_query_catalogs(queue=queue)
        assert [job.kwargs['wd'] for job in queue.jobs] == [str(sibling)]
        drain(queue, worker)
        assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'completed'
        for child in [*reserved, peer, sibling]:
            assert core.pending_catalog_requests(child) == []
            catalog = json.loads((child / '_query_engine/catalog.json').read_text())
            assert any(entry['path'] == 'values.csv' for entry in catalog['files'])
        assert receipt['request_id'] in core.catalog_refresh_status(sibling)['acknowledged']
    finally:
        conn.delete(admission.OWNER_POLICY_KEY)
