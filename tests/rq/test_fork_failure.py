from __future__ import annotations

import errno
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis
from rq import Queue, SimpleWorker
from rq.job import Job, JobStatus

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq import fork_failure, wepp_rq_pipeline
from wepppy.rq.job_info import get_wepppy_rq_job_status
from wepppy.rq.project_rq import _set_fork_destination_outcome

pytestmark = pytest.mark.integration


def _missing_input(runid):
    # Actual open/ENOENT, using a unique path never created by this fixture.
    Path('/tmp', runid, 'wepp.nodb').read_text()


def _success(runid):
    return runid


@pytest.fixture
def fork_jobs():
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        connection.ping()
    except redis.RedisError as exc:
        pytest.skip(f"compose Redis is unavailable: {exc}")
    token = str(uuid.uuid4())
    source = 'fork-read-source-' + token
    target = 'fork-read-target-' + token
    queue = Queue('fork-read-test-' + token, connection=connection)
    root = Job.create(
        'wepppy.rq.project_rq.fork_rq', args=(source, target, True),
        connection=connection, origin='fork-archive', status=JobStatus.FINISHED,
    )
    root.meta['fork_failure'] = dict(root_job_id=root.id, source_runid=source, target_runid=target)
    root.save()
    receipt = 'rq:fork:destination:' + target
    planned = 'rq:fork:planned:' + target
    connection.set(receipt, root.id)
    connection.hset(planned, mapping=dict(job_id=root.id, source_runid=source, target_runid=target, state='running'))
    pubsub = connection.pubsub()
    pubsub.subscribe(source + ':fork')
    pubsub.get_message(timeout=1)  # consume the subscription acknowledgment
    jobs = [root]
    context = SimpleNamespace(connection=connection, queue=queue, root=root, source=source, target=target,
                              receipt=receipt, planned=planned, pubsub=pubsub, jobs=jobs)
    try:
        yield context
    finally:
        pubsub.close()
        for job in reversed(jobs):
            if job.get_status(refresh=True) == JobStatus.DEFERRED:
                job.cancel(enqueue_dependents=False)
            job.delete()
        queue.delete(delete_jobs=True)
        connection.delete(receipt, planned)


def _child(ctx, func=_missing_input):
    job = wepp_rq_pipeline._enqueue(
        ctx.queue, ctx.root, key='jobs:0,func:input', func=func, args=(ctx.target,),
    )
    ctx.jobs.append(job)
    return job


def _messages(ctx):
    messages = []
    while True:
        message = ctx.pubsub.get_message(timeout=0.05)
        if message is None:
            return messages
        if message['type'] == 'message':
            messages.append(message['data'].decode())


def test_actual_rq_callback_records_failure_and_preserves_strict_tree(fork_jobs, monkeypatch):
    ctx = fork_jobs
    child = _child(ctx)
    sibling = ctx.queue.enqueue(_success, ctx.target)
    dependent = ctx.queue.enqueue(_success, ctx.target, depends_on=child)
    ctx.jobs.extend([sibling, dependent])
    ctx.root.meta.update({'jobs:1,func:sibling': sibling.id, 'jobs:2,func:dependent': dependent.id})
    ctx.root.save()
    worker = SimpleWorker([ctx.queue], connection=ctx.connection)
    worker.work(burst=True, max_jobs=1, logging_level='WARNING')
    assert child.get_status(refresh=True) == JobStatus.FAILED
    assert 'FileNotFoundError' in child.exc_info
    assert ctx.connection.hget(ctx.planned, 'state') == b'failed'
    assert ctx.connection.hget(ctx.planned, 'failed_job_id') == child.id.encode()
    messages = _messages(ctx)
    assert len(messages) == 2
    assert child.id in messages[0]
    assert 'FORK_FAILED' in messages[1]
    assert '/tmp/' not in ''.join(messages)
    monkeypatch.setattr('wepppy.rq.job_info.redis.Redis', redis.StrictRedis)
    assert get_wepppy_rq_job_status(ctx.root.id)['status'] == 'queued'
    worker.work(burst=True, logging_level='WARNING')
    assert dependent.get_status(refresh=True) == JobStatus.DEFERRED
    assert get_wepppy_rq_job_status(ctx.root.id)['status'] == 'failed'
    # Duplicate callbacks cannot repeat publication; late parent progress cannot
    # erase failure even when the finalizer was not enqueued when the leaf failed.
    fork_failure.report_fork_failure(child, ctx.connection, OSError, None, None)
    _set_fork_destination_outcome(ctx.connection, ctx.source, ctx.target, ctx.root.id, 'waiting_finalizer')
    assert ctx.connection.hget(ctx.planned, 'state') == b'failed'
    assert _messages(ctx) == []


@pytest.mark.parametrize('invalid', [
    'missing_lineage', 'missing_root', 'wrong_function', 'wrong_queue', 'wrong_source',
    'wrong_target', 'not_undisturbify', 'unregistered_child', 'wrong_child_target',
    'replaced_receipt', 'missing_receipt', 'wrong_planned_root', 'succeeded',
])
def test_invalid_or_legacy_callback_cannot_publish(fork_jobs, invalid):
    ctx = fork_jobs
    child = _child(ctx)
    if invalid == 'missing_lineage':
        child.meta.clear()
    elif invalid == 'missing_root':
        child.meta['fork_failure']['root_job_id'] = str(uuid.uuid4())
    elif invalid == 'wrong_function':
        ctx.root.func_name = 'tests.rq.test_fork_failure._success'
        ctx.root.save()
    elif invalid == 'wrong_queue':
        ctx.root.origin = 'default'
        ctx.root.save()
    elif invalid in ('wrong_source', 'wrong_target', 'not_undisturbify'):
        args = list(ctx.root.args)
        args[{'wrong_source': 0, 'wrong_target': 1, 'not_undisturbify': 2}[invalid]] = False if invalid == 'not_undisturbify' else 'foreign'
        ctx.root.args = tuple(args)
        ctx.root.save()
    elif invalid == 'unregistered_child':
        ctx.root.meta.pop('jobs:0,func:input')
        ctx.root.save()
    elif invalid == 'wrong_child_target':
        child.args = ('foreign',)
    elif invalid == 'replaced_receipt':
        ctx.connection.set(ctx.receipt, str(uuid.uuid4()))
    elif invalid == 'missing_receipt':
        ctx.connection.delete(ctx.receipt)
    elif invalid == 'wrong_planned_root':
        ctx.connection.hset(ctx.planned, 'job_id', str(uuid.uuid4()))
    elif invalid == 'succeeded':
        ctx.connection.hset(ctx.planned, 'state', 'succeeded')
    before = ctx.connection.hgetall(ctx.planned)
    fork_failure.report_fork_failure(child, ctx.connection, OSError, OSError(errno.ENOENT, 'missing'), None)
    assert ctx.connection.hgetall(ctx.planned) == before
    assert _messages(ctx) == []


def test_receipt_replaced_between_validation_and_atomic_update(fork_jobs):
    ctx = fork_jobs
    child = _child(ctx)

    class RacingConnection:
        def __getattr__(self, attr):
            return getattr(ctx.connection, attr)

        def eval(self, *args):
            ctx.connection.set(ctx.receipt, 'replacement')
            return ctx.connection.eval(*args)

    fork_failure.report_fork_failure(child, RacingConnection(), OSError, None, None)
    assert ctx.connection.hget(ctx.planned, 'state') == b'running'
    assert _messages(ctx) == []


def test_successful_prerequisite_has_no_failure_side_effect(fork_jobs):
    ctx = fork_jobs
    child = _child(ctx, _success)
    SimpleWorker([ctx.queue], connection=ctx.connection).work(burst=True, logging_level='WARNING')
    assert child.get_status(refresh=True) == JobStatus.FINISHED
    assert ctx.connection.hget(ctx.planned, 'state') == b'running'
    assert _messages(ctx) == []


def test_reporting_error_preserves_job_failure(fork_jobs, monkeypatch, caplog):
    ctx = fork_jobs
    child = _child(ctx)

    def unavailable(*_args):
        raise redis.ConnectionError('injected callback failure')

    monkeypatch.setattr(fork_failure, '_report_failure', unavailable)
    SimpleWorker([ctx.queue], connection=ctx.connection).work(burst=True, logging_level='WARNING')
    assert child.get_status(refresh=True) == JobStatus.FAILED
    assert 'FileNotFoundError' in child.exc_info
    assert 'Could not report fork prerequisite failure' in caplog.text


def _exit_work_horse(runid):
    import os
    os._exit(17)


@pytest.mark.slow
def test_actual_work_horse_death_reports_fork_failure(fork_jobs):
    from wepppy.rq.rq_worker import WepppyRqWorker

    ctx = fork_jobs
    child = _child(ctx, _exit_work_horse)
    # A real forked child exits without an exception callback. The surviving
    # production worker supervisor must still record the fork's failure.
    WepppyRqWorker([ctx.queue], connection=ctx.connection).work(
        burst=True, max_jobs=1, logging_level='WARNING',
    )
    assert child.get_status(refresh=True) == JobStatus.FAILED
    assert ctx.connection.hget(ctx.planned, 'state') == b'failed'
    assert ctx.connection.hget(ctx.planned, 'failed_job_id') == child.id.encode()
    assert any('FORK_FAILED' in message for message in _messages(ctx))
