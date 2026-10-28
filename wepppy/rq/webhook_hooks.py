"""RQ 2.12 publication/lifecycle instrumentation, inert for unsubscribed jobs.

Raw destinations never enter RQ metadata. Publication receipts share the caller's
transaction. Notification command errors are isolated from ordinary RQ commands;
missing closure and actual-job WATCH validation prevent stale completion.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
import logging
import os
import select
import threading
import time

import redis
from redis.client import Pipeline
from redis.exceptions import RedisError, ResponseError
from rq import get_current_job
from rq.job import Job

from . import webhook_policy as policy
from .webhook_settlement import Member
from .webhook_tracking import WebhookStore

LOG = logging.getLogger(__name__)
BINDING = '_webhook_tracking_v1'
_ADMISSION = ContextVar('webhook_admission', default=None)
_EXECUTION = ContextVar('webhook_execution', default=None)
_PROCESS_EXECUTION = None
_DETACHED = ContextVar('webhook_detached', default=False)
_INSTALLED = False
_STATUS_SIGNAL = {'finished': b'f', 'failed': b'e', 'stopped': b's', 'canceled': b'c',
                  'queued': b'q', 'scheduled': b't', 'deferred': b'd', 'started': b'a'}
_SIGNAL_STATUS = {value: key for key, value in _STATUS_SIGNAL.items()}


def _execution():
    # An RQ workhorse executes one task at a time. Joined helper threads must
    # inherit ownership too; ContextVar/RQ stacks alone are thread-local.
    return _EXECUTION.get() or _PROCESS_EXECUTION


@contextmanager
def detached_catalog_maintenance():
    """Audited server call site for independent query-catalog maintenance only."""
    state = _execution()
    if state is not None:
        LOG.info('Detached query catalog maintenance from webhook job=%s', state['job'].id)
    token = _DETACHED.set(True)
    try:
        yield
    finally:
        _DETACHED.reset(token)


def producers_exited(protected) -> bool:
    """Bounded positive observation of adopted helper exit; never terminate it."""
    from .directory_locks import _child_pids, _verify_protected_children, has_remaining_writers

    deadline = time.monotonic() + policy.CLOSURE_WAIT_SECONDS
    while True:
        _verify_protected_children(protected)
        if not has_remaining_writers(protected):
            _verify_protected_children(protected)
            return True
        descriptors = []
        try:
            for pid in _child_pids() - protected.keys():
                if time.monotonic() >= deadline:
                    return False
                try:
                    descriptors.append(os.pidfd_open(pid))
                except ProcessLookupError:
                    pass  # Re-scan and positively reap the exited child.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if descriptors:
                select.select(descriptors, [], [], remaining)
        finally:
            for fd in descriptors:
                os.close(fd)


@contextmanager
def admission(root_id: str, environment: str):
    token = _ADMISSION.set({'root': root_id, 'parent': None, 'environment': environment})
    try:
        yield
    finally:
        _ADMISSION.reset(token)


def binding(job) -> dict | None:
    meta = getattr(job, 'meta', None)
    value = meta.get(BINDING) if isinstance(meta, dict) else None
    if not isinstance(value, dict) or set(value) != {'root', 'parent', 'environment'}:
        return None
    if not all(isinstance(value[key], str) and value[key] for key in ('root', 'environment')):
        return None
    return value


def _failed() -> None:
    state = _execution()
    if state is not None:
        state['complete'] = False
        # Forked producers have private Python state. Poison the inherited
        # nonblocking handoff too, so a joined helper's failure cannot disappear.
        handoff = getattr(state['job'], '_webhook_handoff', None)
        if handoff and handoff['write'] is not None:
            try:
                os.write(handoff['write'], b'!')
            except OSError:
                # Full pipe already carries poison; closed/missing handoff has
                # no valid completion signal. The warning below records failure.
                pass
    LOG.warning('Webhook bookkeeping incomplete; computation continues')


def _bounded_connection(job):
    client = getattr(job.connection, '_webhook_bounded_client', None)
    if client is None or getattr(job.connection, '_webhook_bounded_pid', None) != os.getpid():
        options = dict(job.connection.connection_pool.connection_kwargs)
        options.update(socket_timeout=policy.HOOK_SECONDS / 10, socket_connect_timeout=policy.HOOK_SECONDS / 10,
                       retry_on_timeout=False, retry=redis.retry.Retry(redis.backoff.NoBackoff(), 0))
        # Never enter an inherited pool's fork lock (redis-py can wait five
        # seconds there). Only reuse notification pools inside the same process.
        client = type(job.connection)(connection_pool=redis.ConnectionPool(
            connection_class=job.connection.connection_pool.connection_class, **options))
        job.connection._webhook_bounded_client = client
        job.connection._webhook_bounded_pid = os.getpid()
    return client


def _member(job, info: dict, deadline=None) -> Member:
    status = getattr(job._status, 'value', job._status) or 'created'
    dependencies = []
    for index, key in enumerate(job._dependency_ids):
        if deadline is not None and index % policy.PAGE_SIZE == 0 and time.monotonic() >= deadline:
            raise ValueError('Webhook dependency construction budget exhausted')
        dependencies.append(str(key))
    return Member(str(job.id), info['root'], info['parent'], status,
                  tuple(dependencies), bool(job.allow_dependency_failures),
                  producer_closed=status != 'started' and job.started_at is None,
                  changed_at=time.time(), execution_id=getattr(job, '_webhook_execution_id', None))


def _record(job, info, connection, *, pipeline=None, mode='replace', deadline=None, **updates):
    deadline = min(deadline if deadline is not None else float('inf'),
                   time.monotonic() + policy.HOOK_SECONDS / 2)
    member = replace(_member(job, info, deadline), **updates)
    return WebhookStore(connection, info['environment']).record_member(
        member, pipeline=pipeline, mode=mode, deadline=deadline)


def _append_receipt(job, pipe) -> None:
    info = binding(job)
    if info is None:
        return
    if pipe.watching and not pipe.explicit_transaction:
        # WATCH without MULTI executes commands immediately. There is no atomic
        # publication receipt to tag/coalesce. Preserve the caller's RQ calls and
        # explicitly retain uncertainty instead of inventing a buffered command.
        _failed()
        try:
            with _bounded_connection(job) as connection:
                WebhookStore(connection, info['environment']).incomplete(info['root'], 'nontransactional_watch')
        except (RedisError, OSError, ValueError, TypeError):
            _failed()
        return
    if len(job._dependency_ids) > policy.ROOT_EDGES:
        _failed()
        return
    start = len(pipe.command_stack)
    try:
        _record(job, info, job.connection, pipeline=pipe, mode='state')
    except ValueError:
        _failed()
        return
    # Only the final state of each job in an atomic transaction is observable.
    # RQ commonly calls set_status and save together; retain one final receipt.
    indexes = getattr(pipe, '_webhook_command_indexes', set())
    receipts = getattr(pipe, '_webhook_receipts', {})
    key = (info['environment'], info['root'], job.id)
    previous = receipts.get(key) if pipe.transaction or pipe.explicit_transaction else None
    if previous is not None:
        pipe.command_stack[previous] = pipe.command_stack.pop()
    else:
        indexes.add(start)
        receipts[key] = start
    pipe._webhook_command_indexes = indexes
    pipe._webhook_receipts = receipts


def save_attempt_metadata(job, pipeline) -> None:
    """Ordinary pre-fork RQ write, independent of optional receipt success.

    Preserve the predecessor atomically so a later successfully tracked retry
    cannot erase an entirely missed overlapping attempt. Ordinary Job.save cannot
    overwrite these dedicated fields. Metadata errors keep their RQ behavior.
    """
    pipeline.eval("""
        local previous = redis.call('HGET', KEYS[1], ARGV[2]) or ''
        return redis.call('HSET', KEYS[1], 'meta', ARGV[1],
                         ARGV[2], ARGV[3], ARGV[4], previous)
        """, 1, job.key, job.serializer.dumps(job.meta), policy.GENERATION_FIELD,
        job._webhook_execution_id or '', policy.PREVIOUS_GENERATION_FIELD)


def begin_attempt(job, *, pipeline=None) -> None:
    info = binding(job)
    if info is None:
        return
    try:
        if pipeline is not None:
            index = len(pipeline.command_stack)
            _record(job, info, job.connection, pipeline=pipeline, mode='start')
            indexes = getattr(pipeline, '_webhook_command_indexes', set())
            indexes.add(index)
            pipeline._webhook_command_indexes = indexes
            return
        with _bounded_connection(job) as connection:
            if not _record(job, info, connection, mode='start'):
                _failed()
    except (RedisError, OSError, ValueError, TypeError):
        _failed()


def execution_started(job):
    global _PROCESS_EXECUTION
    info = binding(job)
    if info is None:
        return None
    state = {'complete': True, 'job': job, 'threads': set()}
    handoff = getattr(job, '_webhook_handoff', None)
    if handoff and handoff['pid'] != os.getpid():
        _PROCESS_EXECUTION = state
    return _EXECUTION.set(state)


def prepare_handoff(job) -> None:
    """One nonblocking local completion byte, bound to this execution's fork."""
    if binding(job) is None:
        return
    try:
        read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        job._webhook_handoff = {'pid': os.getpid(), 'read': read_fd, 'write': write_fd}
    except OSError:
        _failed()  # No handoff means no closure; computation still proceeds.


def parent_handoff(job) -> None:
    handoff = getattr(job, '_webhook_handoff', None)
    if handoff and handoff['write'] is not None:
        descriptor = handoff['write']
        handoff['write'] = None
        try:
            os.close(descriptor)
        except OSError:
            _failed()


def close_handoff(job) -> None:
    handoff = getattr(job, '_webhook_handoff', None)
    if handoff:
        for key in ('read', 'write'):
            if handoff[key] is not None:
                descriptor = handoff[key]
                handoff[key] = None
                try:
                    os.close(descriptor)
                except OSError:
                    _failed()


def execution_returned(job, token) -> None:
    if token is None:
        return
    try:
        state = _execution()
        handoff = getattr(job, '_webhook_handoff', None)
        if state['complete'] and handoff and handoff['write'] is not None:
            # The parent requires both this byte and waitpid/process containment.
            # A crash or failed notification command cannot manufacture the byte.
            status = getattr(job._status, 'value', job._status)
            # RQ dependency release refreshes STARTED into the job object, then
            # zero-TTL success deletes it without persisting FINISHED. The worker
            # marks successful cleanup; retries/failed transitions take precedence.
            if status == 'started' and getattr(job, '_webhook_zero_ttl_success', False):
                status = 'finished'
            signal = _STATUS_SIGNAL.get(status)
            if signal is not None:
                os.write(handoff['write'], signal)
    except OSError:
        _failed()
    finally:
        # Threads and forked helpers may publish between task return and process
        # death. Keep their process-wide ownership and poison descriptor alive;
        # the supervisor reads only after waitpid and descendant containment.
        # os._exit closes this workhorse's descriptors without changing task work.
        if handoff and handoff['pid'] != os.getpid():
            _EXECUTION.reset(token)
        else:
            close_handoff(job)
            supervisor_finished(token)


def execution_exited(job, *, deadline=None) -> None:
    info = binding(job)
    state = _execution()
    handoff = getattr(job, '_webhook_handoff', None)
    if info is None or (state is not None and not state['complete']) or not handoff:
        return
    if state is not None:
        threads = state['threads'].copy()
        if (any(thread.ident is None or thread.is_alive() for thread in threads)
                or len(threads) != len(state['threads'])):
            return  # Supervisor callbacks may outlive monitor_work_horse.
    try:
        status = _SIGNAL_STATUS.get(os.read(handoff['read'], 2)) if handoff['read'] is not None else None
        if status is None:
            return
        with _bounded_connection(job) as connection:
            # One atomic returned+exited receipt; latest RQ state was captured in
            # the workhorse transaction, and old execution tokens cannot close retries.
            construction_deadline = deadline - policy.HOOK_SECONDS / 2 if deadline is not None else None
            _record(job, info, connection, status=status, mode='exited', deadline=construction_deadline)
    except (RedisError, OSError, ValueError, TypeError):
        _failed()


def supervisor_finished(token) -> None:
    global _PROCESS_EXECUTION
    if token is not None:
        _PROCESS_EXECUTION = None
        _EXECUTION.reset(token)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    original_create = Job.create.__func__
    original_save = Job.save
    original_status = Job.set_status
    original_execute = Pipeline.execute
    original_reset = Pipeline.reset
    original_thread_start = threading.Thread.start

    def thread_start(thread, *args, **kwargs):
        state = _execution()
        if state is not None:
            # A long-lived supervisor may advance to another job while a callback
            # thread remains alive. Capture its original owner, never a later root.
            original_run = thread.run
            def run():
                token = _EXECUTION.set(state)
                try:
                    return original_run()
                finally:
                    _EXECUTION.reset(token)
            thread.run = run
            state['threads'].add(thread)
        return original_thread_start(thread, *args, **kwargs)

    def create(cls, *args, **kwargs):
        job = original_create(cls, *args, **kwargs)
        info = _ADMISSION.get()
        current = get_current_job()
        if current is None and _execution() is not None:
            current = _execution()['job']
        parent = binding(current) if current is not None else None
        if parent:
            info = {'root': parent['root'], 'parent': current.id, 'environment': parent['environment']}
        if _DETACHED.get():
            job.meta.pop(BINDING, None)
            return job
        if info:
            # Server context overwrites any supplied binding; no destination accepted.
            job.meta[BINDING] = dict(info)
            # Reserve before any publication, including caller-owned/discarded
            # pipelines and bulk Job.create. Failure prevents producer closure.
            try:
                with _bounded_connection(job) as connection:
                    if not _record(job, info, connection, published=False):
                        _failed()
            except (RedisError, OSError, ValueError, TypeError):
                _failed()
        return job

    def save(job, pipeline=None, include_meta=True, include_result=True):
        if binding(job) is None:
            return original_save(job, pipeline=pipeline, include_meta=include_meta, include_result=include_result)
        if pipeline is not None:
            _append_receipt(job, pipeline)
            return original_save(job, pipeline=pipeline, include_meta=include_meta, include_result=include_result)
        with job.connection.pipeline() as pipe:
            _append_receipt(job, pipe)
            original_save(job, pipeline=pipe, include_meta=include_meta, include_result=include_result)
            pipe.execute()

    def set_status(job, status, pipeline=None):
        if binding(job) is None:
            return original_status(job, status, pipeline=pipeline)
        if pipeline is not None:
            original_status(job, status, pipeline=pipeline)
            _append_receipt(job, pipeline)
            return
        with job.connection.pipeline() as pipe:
            original_status(job, status, pipeline=pipe)
            _append_receipt(job, pipe)
            pipe.execute()

    def execute(pipe, raise_on_error=True):
        indexes = getattr(pipe, '_webhook_command_indexes', set()).copy()
        if not indexes:
            return original_execute(pipe, raise_on_error=raise_on_error)
        results = original_execute(pipe, raise_on_error=False)
        for index, result in enumerate(results):
            if index in indexes:
                if isinstance(result, ResponseError) or not result:
                    _failed()
            elif isinstance(result, ResponseError) and raise_on_error:
                raise result
        return results

    def reset(pipe):
        pipe._webhook_command_indexes = set()
        pipe._webhook_receipts = {}
        return original_reset(pipe)

    Job.create = classmethod(create)
    Job.save = save
    Job.set_status = set_status
    Pipeline.execute = execute
    Pipeline.reset = reset
    threading.Thread.start = thread_start
    _INSTALLED = True
