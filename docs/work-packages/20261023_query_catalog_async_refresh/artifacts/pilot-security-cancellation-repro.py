"""Independent disposable-Redis reproduction; no production/project access."""
import json
import multiprocessing
import time

from tests.rq.test_batch_task_boundary import isolated_rq
from tests.rq.test_query_catalog_rq import catalog_queue
from tests.rq.test_query_catalog_pilot import enable_pilot
from wepppy.rq import query_catalog_rq as tasks
from wepppy.rq import _query_catalog_admission as guard
from wepppy.rq import _query_catalog_pilot as pilot
from wepppy.query_engine import catalog_refresh as core


def test_claimed_cancellation_retains_live_work_permit(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    identifier, token, paths = enable_pilot(root, queue, worker, monkeypatch, count=8)
    for path in paths:
        core.record_catalog_refresh(path)
    jobs = [tasks.enqueue_catalog_refresh(path, queue=queue, pilot_id=identifier,
                                         controller_token=token)['job_id']
            for path in paths[:7]]
    context = multiprocessing.get_context('fork')
    entered = context.Event()
    release = context.Event()

    def blocked_refresh(*args, **kwargs):
        entered.set()
        assert release.wait(15)

    def execute_one():
        worker.register_death()
        worker.work(burst=True, max_jobs=1)

    monkeypatch.setattr(core, 'refresh_catalog', blocked_refresh)
    process = context.Process(target=execute_one)
    process.start()
    try:
        assert entered.wait(10)
        ledger = json.loads(queue.connection.get(guard.LEDGER_KEY))
        assert ledger['jobs'][jobs[0]]['claimed']
        queue.fetch_job(jobs[0]).cancel()
        assert process.is_alive() and not release.is_set()
        status = pilot.pilot_status(queue.connection, identifier)
        result = tasks.enqueue_catalog_refresh(paths[7], queue=queue,
                                              pilot_id=identifier, controller_token=token)
        print(json.dumps({'work_still_running': process.is_alive(),
                          'claimed_job_status': queue.fetch_job(jobs[0]).get_status(),
                          'reported_outstanding_before': status['outstanding'],
                          'actual_outstanding_before': 7,
                          'new_admission': result}, default=str))
        assert not result.get('job_id'), 'Live claimed cancellation freed a global permit'
    finally:
        release.set()
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join(5)
