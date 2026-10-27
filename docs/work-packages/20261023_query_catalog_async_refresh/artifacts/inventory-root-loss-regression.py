from tests.rq.test_query_catalog_rq import catalog_queue, drain
from tests.rq.test_batch_task_boundary import isolated_rq
from wepppy.rq import query_catalog_rq as tasks


def test_required_root_loss_after_completed_cycle_degrades(catalog_queue):
    root, queue, worker = catalog_queue
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state('idle')
    assert tasks.reconcile_query_catalogs(queue=queue)['state'] == 'completed'
    root.rmdir()
    outcome = tasks.reconcile_query_catalogs(queue=queue)
    print(outcome)
    assert outcome['state'] == 'degraded'
    assert outcome['completed_at'] is None
