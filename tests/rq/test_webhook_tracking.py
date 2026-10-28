from dataclasses import replace
import json
from uuid import uuid4

import pytest

from tests.rq.test_rq212_lifecycle import lifecycle
from wepppy.rq.webhook_tracking import WebhookStore, AdmissionError
from wepppy.rq.webhook_settlement import Member
from wepppy.rq.webhook_dispatcher import claim, record_attempt, inspect

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def store(lifecycle):
    return WebhookStore(lifecycle.connection, 'test-' + str(uuid4()))


def reserve(store, key='callback-request-1', digest='digest'):
    return store.reserve(principal='issuer:service:client', key=key, digest=digest, operation='run-wepp',
                         resource={'type': 'run', 'id': 'test'}, url='https://example.com/secret?key=capability',
                         job_id=str(uuid4()), now=100)


def publish(store, root):
    member = Member(root['job_id'], root['job_id'], None, 'finished', producer_closed=True, changed_at=110)
    with store.connection.pipeline() as pipe:
        pipe.hset('rq:job:' + root['job_id'], 'status', 'finished')
        store.record_member(member, pipeline=pipe)
        store.published(root['job_id'], {'job_id': root['job_id'], 'webhook': {'status': 'accepted'}}, pipeline=pipe)
        pipe.execute()
    return member


def advance_actual_generation(store, member):
    from rq.job import Job
    from wepppy.rq.webhook_hooks import save_attempt_metadata
    job = Job.create(json.loads, args=('1',), id=member.job_id, connection=store.connection)
    job._webhook_execution_id = member.execution_id
    with store.connection.pipeline() as pipe:
        save_attempt_metadata(job, pipe)
        pipe.execute()


def test_idempotent_admission_conflict_and_no_credentials(store):
    created, first = reserve(store)
    duplicate, second = reserve(store)
    assert created and not duplicate and first == second
    with pytest.raises(AdmissionError) as exc:
        reserve(store, digest='different')
    assert exc.value.status == 409
    with store.connection.pipeline() as pipe:
        with pytest.raises(ValueError):
            store.published(first['job_id'], {'browse_token': 'must-not-store'}, pipeline=pipe)


def test_missing_member_prevents_event_and_exact_event_reloaded(store):
    _, root = reserve(store)
    member = publish(store, root)
    store.record_member(replace(member, status='started', producer_closed=False))
    assert store.evaluate(root['job_id'], now=115) == 'waiting'
    store.record_member(member)
    assert store.evaluate(root['job_id'], now=120) == 'delivery_pending'
    event = json.loads(store.read(root['job_id'])['event'])
    assert event['execution_status'] == 'finished'
    assert event['event'] == 'operation.completed'
    assert 'secret' not in json.dumps(event)
    assert 'domain_status' not in event
    event_bytes = store.read(root['job_id'])['event']
    store.evaluate(root['job_id'], now=130)
    assert store.read(root['job_id'])['event'] == event_bytes


def test_claim_fencing_retry_and_url_erasure(store):
    _, root = reserve(store)
    publish(store, root)
    store.evaluate(root['job_id'], now=120)
    first = claim(store, root['job_id'], 121)
    assert first and not claim(store, root['job_id'], 122)
    assert record_attempt(store, first, {'status': 503}, 123)
    # The direct claim API is called only for due roots by the dispatcher.
    second = claim(store, root['job_id'], 154)
    assert second and second['event'] == first['event']
    assert not record_attempt(store, first, {'status': 200}, 155)
    assert record_attempt(store, second, {'status': 204}, 156)
    stored = store.read(root['job_id'])
    assert stored['state'] == 'delivered' and 'url' not in stored
    assert len(stored['audit']) == 2
    assert 'capability' not in json.dumps(inspect(store, root['job_id']))


def test_unknown_expires_to_tombstone_without_event(store):
    _, root = reserve(store)
    assert store.evaluate(root['job_id'], now=100 + 30*86400) == 'outcome_unavailable'
    assert store.read(root['job_id'])['state'] == 'admission_unavailable'
    with pytest.raises(AdmissionError) as exc:
        reserve(store)
    assert exc.value.status == 410
    assert 'url' not in store.read(root['job_id'])


def test_incomplete_tracking_does_not_create_event(store):
    _, root = reserve(store)
    publish(store, root)
    store.incomplete(root['job_id'], 'publication')
    assert store.evaluate(root['job_id'], now=120) == 'unknown'
    assert 'event' not in store.read(root['job_id'])


def test_bulk_and_discarded_pipeline_membership_reservations(store, lifecycle):
    from rq import Queue
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    publish(store, root)
    queue = lifecycle.queue
    # Model the trusted worker context using RQ's own current-job stack.
    from rq.job import Job, _job_stack
    parent = Job.create(json.loads, args=('1',), connection=store.connection, id=root['job_id'])
    from wepppy.rq.webhook_hooks import BINDING
    parent.meta[BINDING] = {'root': root['job_id'], 'parent': None, 'environment': store.environment}
    _job_stack.push(parent)
    try:
        bulk = queue.enqueue_many([Queue.prepare_data(json.loads, args=('1',))])[0]
        assert store.member(root['job_id'], bulk.id).published
        with store.connection.pipeline() as pipe:
            orphan = queue.enqueue_call(json.loads, args=('2',), pipeline=pipe)
            assert not store.member(root['job_id'], orphan.id).published
        assert not store.member(root['job_id'], orphan.id).published
        assert store.evaluate(root['job_id'], now=120) == 'unknown'
    finally:
        _job_stack.pop()


def test_real_worker_closes_after_process_exit(store, lifecycle):
    from wepppy.rq.webhook_hooks import admission, install
    from tests.rq.rq212_tasks import lifecycle_job
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(lifecycle_job, kwargs={'marker': root['job_id']},
                                               job_id=root['job_id'], pipeline=pipe)
        store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
        pipe.execute()
    assert store.evaluate(root['job_id'], now=115) == 'waiting'
    with lifecycle.worker(burst=True) as process:
        assert process.wait(timeout=30) == 0
    member = store.member(root['job_id'], job.id)
    assert member.producer_closed and member.returned
    assert store.evaluate(root['job_id'], now=120) == 'delivery_pending'


def test_old_supervisor_cannot_close_new_retry_generation(store):
    _, root = reserve(store)
    member = publish(store, root)
    old = replace(member, execution_id='attempt-1', returned=True, producer_closed=False)
    store.record_member(old)
    new = replace(old, execution_id='attempt-2', status='started', returned=False)
    advance_actual_generation(store, old)
    advance_actual_generation(store, new)
    store.record_member(new, mode='start')
    assert not store.record_member(replace(old, producer_closed=True), mode='closed')
    assert not store.record_member(old, mode='returned')
    actual = store.member(root['job_id'], root['job_id'])
    assert actual.execution_id == 'attempt-2' and not actual.producer_closed and not actual.returned


@pytest.mark.parametrize('aba', [False, True])
def test_actual_rq_mutation_between_snapshot_and_commit_rejects_event(store, aba):
    _, root = reserve(store)
    publish(store, root)
    key = 'rq:job:' + root['job_id']
    store.connection.hset(key, 'status', 'finished')
    steps = store.evaluation_steps(root['job_id'], now=120)
    next(steps)  # Candidate receipt and actual job fenced before yielding.
    # Raw RQ writes model an attempt whose notification bookkeeping all failed.
    # ABA restores the same terminal status while its new producer may be alive.
    for status in (('queued', 'started', 'finished') if aba else ('queued',)):
        store.connection.hset(key, 'status', status)
    while True:
        try:
            next(steps)
        except StopIteration as done:
            assert done.value == 'conflict'
            break
    assert 'event' not in store.read(root['job_id'])


def test_active_hierarchy_does_not_watch_actual_jobs(store, monkeypatch):
    from redis.client import Pipeline
    _, root = reserve(store)
    member = publish(store, root)
    store.record_member(replace(member, status='started', producer_closed=False))
    watched = []
    original_watch = Pipeline.watch
    def watch(pipe, *keys):
        result = original_watch(pipe, *keys)
        watched.extend(keys)
        return result
    monkeypatch.setattr(Pipeline, 'watch', watch)
    assert store.evaluate(root['job_id'], now=120) == 'waiting'
    assert watched == [store.root_key(root['job_id'])]
    assert 'event' not in store.read(root['job_id'])


@pytest.mark.parametrize('old_execution', [None, 'attempt-old'])
def test_lost_bookkeeping_retry_generation_cannot_reuse_old_closure(store, old_execution):
    from wepppy.rq import webhook_policy as policy
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    _, root = reserve(store)
    member = publish(store, root)
    store.record_member(replace(member, execution_id=old_execution))
    key = 'rq:job:' + root['job_id']
    # The ordinary pre-fork write survives completely failed notification
    # bookkeeping; a new attempt can already be finished before evaluation.
    store.connection.hset(key, mapping={'status': 'finished', policy.GENERATION_FIELD: 'attempt-new'})
    old_job = Job.create(leaf, id=root['job_id'], connection=store.connection)
    old_job.set_status('finished')
    old_job.meta['directory_lock_execution_id'] = 'old-meta'
    old_job.save()
    assert store.connection.hget(key, policy.GENERATION_FIELD) == b'attempt-new'
    assert store.evaluate(root['job_id'], now=120) == 'unknown'
    assert 'event' not in store.read(root['job_id'])


def test_missing_actual_job_cannot_reuse_old_closure(store):
    _, root = reserve(store)
    publish(store, root)
    store.connection.delete('rq:job:' + root['job_id'])
    assert store.evaluate(root['job_id'], now=120) == 'unknown'
    assert 'event' not in store.read(root['job_id'])


def test_missed_middle_attempt_cannot_disappear_after_successful_overlap(store):
    _, root = reserve(store)
    member = publish(store, root)
    known = replace(member, execution_id='known', status='started', producer_closed=False)
    advance_actual_generation(store, known)
    assert store.record_member(known, mode='start')
    assert store.record_member(known, mode='start')  # Duplicate receipt, same generation.
    assert store.record_member(replace(known, status='finished'), mode='exited')
    missed = replace(known, execution_id='missed')
    advance_actual_generation(store, missed)  # All optional receipts fail; producer remains alive.
    later = replace(known, execution_id='later')
    advance_actual_generation(store, later)
    assert not store.record_member(later, mode='start')
    assert store.connection.hget(store.root_key(root['job_id']), 'incomplete') == b'generation_gap'
    assert not store.record_member(replace(later, status='finished'), mode='exited')
    assert store.evaluate(root['job_id'], now=120) == 'unknown'
    assert 'event' not in store.read(root['job_id'])


def test_state_receipt_cannot_adopt_an_unregistered_attempt(store):
    _, root = reserve(store)
    member = publish(store, root)
    missed = replace(member, execution_id='missed')
    advance_actual_generation(store, missed)
    assert not store.record_member(missed, mode='state')
    assert store.evaluate(root['job_id'], now=120) == 'unknown'


def test_lost_first_attempt_then_expired_job_recreation_cannot_reset_continuity(store, lifecycle):
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq import webhook_policy as policy
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(leaf, job_id=root['job_id'], pipeline=pipe)
        store.published(job.id, {'job_id': job.id}, pipeline=pipe)
        pipe.execute()
    saved = Job.fetch(job.id, connection=store.connection)
    member = store.member(job.id, job.id)
    assert store.connection.hget(job.key, policy.GENERATION_FIELD) == b'unstarted'
    advance_actual_generation(store, replace(member, execution_id='missed'))
    store.connection.delete(job.key)  # Zero TTL; every optional attempt receipt lost.
    lifecycle.queue.enqueue_job(saved)  # Public RQ path, same ID and retained object.
    assert store.connection.hget(job.key, policy.GENERATION_FIELD) is None
    later = replace(member, execution_id='later', status='started')
    advance_actual_generation(store, later)
    assert not store.record_member(later, mode='start')
    assert not store.record_member(replace(later, status='finished'), mode='exited')
    assert store.evaluate(job.id, now=120) == 'unknown'
    assert 'event' not in store.read(job.id)


def test_duplicate_creation_cannot_reset_first_publication(store):
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    publish(store, root)
    store.connection.delete('rq:job:' + root['job_id'])
    with admission(root['job_id'], store.environment):
        Job.create(leaf, id=root['job_id'], connection=store.connection)
    assert store.connection.hget(store.root_key(root['job_id']), 'incomplete') == b'republication'
    assert store.evaluate(root['job_id'], now=120) == 'unknown'


def test_missing_initial_publication_receipt_stays_unknown_after_recreation(store, lifecycle, monkeypatch):
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    original_record = WebhookStore.record_member
    def lose_publication(self, member, **kwargs):
        if kwargs.get('pipeline') is not None:
            raise ValueError('Injected receipt construction deadline')
        return original_record(self, member, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(WebhookStore, 'record_member', lose_publication)
        with store.connection.pipeline() as pipe:
            with admission(root['job_id'], store.environment):
                job = lifecycle.queue.enqueue_call(leaf, job_id=root['job_id'], pipeline=pipe)
            store.published(job.id, {'job_id': job.id}, pipeline=pipe)
            assert pipe.execute()[-1] == 1  # Computation remains accepted.
    assert store.read(job.id)['publication'] == 'published'
    assert store.connection.hget(store.root_key(job.id), 'incomplete') == b'initial_publication'
    saved = Job.fetch(job.id, connection=store.connection)
    member = store.member(job.id, job.id)
    assert not member.published
    advance_actual_generation(store, replace(member, execution_id='missed'))
    store.connection.delete(job.key)
    lifecycle.queue.enqueue_job(saved)
    later = replace(store.member(job.id, job.id), execution_id='later', status='started')
    advance_actual_generation(store, later)
    assert store.record_member(later, mode='start')
    assert store.record_member(replace(later, status='finished'), mode='exited')
    assert store.evaluate(job.id, now=120) == 'unknown'
    assert 'event' not in store.read(job.id)


def test_principal_retention_cleanup_preserves_other_roots(store):
    _, first = reserve(store)
    _, second = reserve(store, key='second-request-key')
    principal = store.connection.hget(store.root_key(first['job_id']), 'principal_key')
    store.finish(first['job_id'], 'admission_unavailable', now=120)
    assert store.expire(first['job_id'], 120 + 30*86400)
    assert store.connection.exists(principal)
    store.finish(second['job_id'], 'admission_unavailable', now=120)
    assert store.expire(second['job_id'], 120 + 30*86400)
    assert not store.connection.exists(principal)


def test_overlapping_retry_producers_both_must_exit(store):
    _, root = reserve(store)
    member = publish(store, root)
    first = replace(member, execution_id='first', producer_closed=False)
    second = replace(member, execution_id='second', producer_closed=False)
    advance_actual_generation(store, first)
    assert store.record_member(first, mode='start')
    advance_actual_generation(store, second)
    assert store.record_member(second, mode='start')
    assert store.record_member(replace(first, status='failed'), mode='state')
    assert store.member(root['job_id'], root['job_id']).execution_id == second.execution_id
    assert not store.connection.hexists(store.root_key(root['job_id']), 'incomplete')
    assert store.record_member(replace(second, status='finished'), mode='returned')
    assert store.record_member(second, mode='closed')
    assert not store.member(root['job_id'], root['job_id']).producer_closed
    assert store.evaluate(root['job_id'], now=120) == 'waiting'
    assert store.record_member(replace(first, status='failed'), mode='returned')
    assert store.record_member(first, mode='closed')
    result = store.member(root['job_id'], root['job_id'])
    assert result.producer_closed and result.status == 'finished' and not result.executions
    assert store.evaluate(root['job_id'], now=120) == 'delivery_pending'


def test_known_prepublication_failure_resumes_same_identity(store):
    _, first = reserve(store)
    store.prepublication_failed(first['job_id'])
    resumed, second = reserve(store)
    assert resumed and second['job_id'] == first['job_id']
    duplicate, pending = reserve(store)
    assert not duplicate and pending['state'] == 'admission_pending'
    publish(store, second)
    assert store.read(first['job_id'])['publication'] == 'published'


def test_expired_retryable_intent_cannot_resume_before_reconciliation(store):
    _, first = reserve(store)
    store.prepublication_failed(first['job_id'])
    with pytest.raises(AdmissionError) as exc:
        store.reserve(principal='issuer:service:client', key='callback-request-1', digest='digest',
                      operation='run-wepp', resource={'type': 'run', 'id': 'test'},
                      url='https://example.com', job_id=str(uuid4()), now=100 + 30*86400)
    assert exc.value.status == 410
    assert store.read(first['job_id'])['state'] == 'admission_unavailable'


@pytest.mark.parametrize('mode,outcome', [('caught', 'finished'), ('uncaught', 'failed')])
def test_real_worker_hierarchy_execution_domain_distinction(store, lifecycle, mode, outcome):
    from tests.rq.webhook_tasks import graph, callback_child
    from wepppy.rq.webhook_hooks import admission, install
    from rq import Callback
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(graph, args=(mode,), job_id=root['job_id'], pipeline=pipe,
                                               on_success=Callback(callback_child))
        store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
        pipe.execute()
    with lifecycle.worker(burst=True) as process:
        assert process.wait(timeout=45) == 0
    members = {key.decode(): json.loads(value) for key, value in store.connection.hgetall(store.members_key(job.id)).items()}
    assert len(members) == 5
    assert all(value['producer_closed'] for value in members.values())
    assert all(value['parent_id'] == job.id for key, value in members.items() if key != job.id)
    assert store.evaluate(job.id, now=120) == 'delivery_pending'
    event = json.loads(store.read(job.id)['event'])
    assert event['execution_status'] == outcome
    assert 'domain_status' not in event
    job.refresh()
    from rq.job import Job
    first = Job.fetch(job.meta['jobs:1'], connection=store.connection)
    if mode == 'caught':
        assert first.return_value()['domain_status'] == 'failed'


def test_due_page_rotation_reaches_later_principal(store, monkeypatch):
    import time
    from wepppy.rq.webhook_dispatcher import run
    for index in range(301):
        store.reserve(principal=f'principal-{index // 100}', key=f'request-key-{index:08d}', digest='digest',
                      operation='run-wepp', resource={'type': 'run', 'id': 'test'},
                      url='https://example.com', job_id=str(uuid4()), now=100 + index / 1000)
    reached = set()
    class Complete(Exception):
        pass
    started = time.monotonic()
    def evaluate(root_id, **kwargs):
        principal = store.read(root_id)['principal']
        reached.add(principal)
        if len(reached) == 4:
            raise Complete
        if time.monotonic() - started > 5:
            pytest.fail('Later principal starved behind first due page')
        yield None
        return 'waiting'
    monkeypatch.setattr(store, 'evaluation_steps', evaluate)
    with pytest.raises(Complete):
        run(store)
    assert len(reached) == 4


def test_evaluators_share_slice_and_rotate_before_repeat(store, monkeypatch):
    from types import SimpleNamespace
    from wepppy.rq import webhook_dispatcher as dispatcher
    roots = []
    for index in range(4):
        _, root = store.reserve(principal=f'slice-{index}', key='slice-request-key', digest='digest',
                               operation='run-wepp', resource={'type': 'run', 'id': 'test'},
                               url='https://example.com', job_id=str(uuid4()), now=100)
        roots.append(root['job_id'])
    elapsed = 0.0
    observed = []

    class Complete(Exception):
        pass

    def evaluate(root_id, **kwargs):
        nonlocal elapsed
        while True:
            observed.append(root_id)
            elapsed += .03  # A bounded page consumes part of the common slice.
            yield None

    def sleep(seconds):
        assert set(observed) == set(roots)
        assert len(observed) == 4
        assert elapsed < dispatcher.policy.SLICE_SECONDS + .03
        raise Complete

    monkeypatch.setattr(store, 'evaluation_steps', evaluate)
    monkeypatch.setattr(dispatcher, 'time', SimpleNamespace(
        time=lambda: 121, monotonic=lambda: elapsed, sleep=sleep))
    with pytest.raises(Complete):
        dispatcher.run(store)


def test_claim_requires_current_redis_identity(store):
    _, root = reserve(store)
    publish(store, root)
    store.evaluate(root['job_id'], now=120)
    assert claim(store, root['job_id'], 121, redis_run_id='stale-process') is None
    assert store.read(root['job_id'])['attempts'] == 0
    current = store.connection.info('server')['run_id']
    assert claim(store, root['job_id'], 121, redis_run_id=current)


@pytest.mark.parametrize('termination', ['timeout', 'stop', 'sigkill'])
def test_real_termination_requires_workhorse_completion_signal(store, lifecycle, termination):
    import os
    import signal
    from rq.command import send_stop_job_command
    from tests.rq.test_rq212_lifecycle import wait_for, state
    from tests.rq.rq212_tasks import lifecycle_job
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(lifecycle_job, kwargs={'operation': 'hold', 'marker': root['job_id']},
                                               timeout=2 if termination == 'timeout' else 30,
                                               job_id=root['job_id'], pipeline=pipe)
        store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
        pipe.execute()
    with lifecycle.worker(burst=True) as process:
        pid = int(wait_for(lambda: store.connection.get(job.id + ':started')))
        if termination == 'stop':
            send_stop_job_command(store.connection, job.id)
        elif termination == 'sigkill':
            os.kill(pid, signal.SIGKILL)
        assert process.wait(timeout=40) == 0
    assert state(job) in {'failed', 'stopped'}
    result = store.evaluate(job.id, now=120)
    if termination == 'timeout':
        assert result == 'delivery_pending'
        assert json.loads(store.read(job.id)['event'])['execution_status'] == 'failed'
    else:
        assert result in {'waiting', 'unknown'}
        assert 'event' not in store.read(job.id)


def test_real_retry_waits_for_latest_execution_exit(store, lifecycle):
    from rq import Retry
    from tests.rq.rq212_tasks import lifecycle_job
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(lifecycle_job, kwargs={'fail_attempts': 1, 'marker': root['job_id']},
                                               retry=Retry(max=1), job_id=root['job_id'], pipeline=pipe)
        store.published(job.id, {'job_id': job.id}, pipeline=pipe)
        pipe.execute()
    with lifecycle.worker(burst=True) as process:
        assert process.wait(timeout=40) == 0
    assert store.connection.get(job.id + ':attempts') == b'2'
    member = store.member(job.id, job.id)
    assert member.producer_closed and not member.executions
    assert store.evaluate(job.id, now=120) == 'delivery_pending'
    assert json.loads(store.read(job.id)['event'])['execution_status'] == 'finished'


@pytest.mark.parametrize('case', ['zero_ttl', 'surviving_producer'])
def test_exit_signal_needs_terminal_evidence_and_positive_containment(store, lifecycle, case):
    import os
    import signal
    from tests.rq.webhook_tasks import leaf, surviving_producer
    from wepppy.rq.webhook_hooks import admission, install
    install()
    _, root = reserve(store)
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(leaf if case == 'zero_ttl' else surviving_producer,
                                               result_ttl=0 if case == 'zero_ttl' else 500,
                                               job_id=root['job_id'], pipeline=pipe)
        store.published(job.id, {'job_id': job.id}, pipeline=pipe)
        pipe.execute()
    try:
        with lifecycle.worker(burst=True) as process:
            assert process.wait(timeout=40) == 0
        result = store.evaluate(job.id, now=120)
        if case == 'zero_ttl':
            assert not store.connection.exists('rq:job:' + job.id)
            assert result == 'unknown'
            assert 'event' not in store.read(job.id)
        else:
            assert result in {'waiting', 'unknown'}
            assert not store.member(job.id, job.id).producer_closed
    finally:
        pid = store.connection.get(job.id + ':surviving-producer')
        if pid:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize('race', [False, True])
def test_external_prerequisite_is_verified_and_fenced(store, monkeypatch, race):
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq.webhook_hooks import BINDING

    _, owner = reserve(store, key='external-owner-0001')
    owned = publish(store, owner)
    _, foreign = reserve(store, key='external-other-0001')
    prerequisite = publish(store, foreign)
    prerequisite = replace(prerequisite, status='failed')
    store.record_member(prerequisite)
    job = Job.create(leaf, id=prerequisite.job_id, connection=store.connection,
                     meta={BINDING: {'root': prerequisite.root_id, 'parent': None,
                                     'environment': store.environment}})
    job.set_status('failed')
    job.save()
    store.record_member(replace(owned, status='deferred', dependencies=(job.id,)))
    store.connection.hset('rq:job:' + owned.job_id, 'status', 'deferred')
    if race:
        import wepppy.rq.webhook_tracking as tracking
        original = tracking.evaluation_steps
        def mutate_after_evaluation(*args, **kwargs):
            result = yield from original(*args, **kwargs)
            job.set_status('queued')
            return result
        monkeypatch.setattr(tracking, 'evaluation_steps', mutate_after_evaluation)
    steps = store.evaluation_steps(owner['job_id'], now=120)
    for _ in range(100):
        try:
            next(steps)
        except StopIteration as done:
            assert done.value == ('conflict' if race else 'delivery_pending')
            break
    else:
        pytest.fail('External prerequisite evaluation did not terminate')
    if race:
        assert 'event' not in store.read(owner['job_id'])
        return
    event = json.loads(store.read(owner['job_id'])['event'])
    assert event['execution_status'] == 'failed'
    assert job.id.encode() not in store.connection.hkeys(store.members_key(owner['job_id']))


@pytest.mark.parametrize('case', ['joined_thread', 'after_return', 'after_return_failure', 'forked_failure'])
def test_real_helper_producer_coverage(store, lifecycle, case):
    from wepppy.rq.webhook_hooks import admission, install
    from tests.rq.webhook_tasks import threaded_child, after_return_thread, after_return_thread_failure, forked_notification_failure
    install()
    _, root = reserve(store)
    task = {'joined_thread': threaded_child, 'after_return': after_return_thread, 'after_return_failure': after_return_thread_failure,
            'forked_failure': forked_notification_failure}[case]
    with store.connection.pipeline() as pipe:
        with admission(root['job_id'], store.environment):
            job = lifecycle.queue.enqueue_call(task, job_id=root['job_id'], pipeline=pipe)
        store.published(job.id, {'job_id': job.id}, pipeline=pipe)
        pipe.execute()
    with lifecycle.worker(burst=True) as process:
        assert process.wait(timeout=30) == 0
    if case in {'joined_thread', 'after_return'}:
        assert store.connection.hlen(store.members_key(job.id)) == 2
        assert store.evaluate(job.id, now=120) == 'delivery_pending'
    else:
        assert store.evaluate(job.id, now=120) in {'waiting', 'unknown'}
        assert not store.member(job.id, job.id).producer_closed


def test_hook_serialization_deadline_precedes_large_receipt_publication(store):
    import time
    _, root = reserve(store)
    member = Member(root['job_id'], root['job_id'], None, 'deferred',
                    dependencies=tuple(str(uuid4()) for _ in range(500000)))
    started = time.monotonic()
    with pytest.raises(ValueError, match='budget exhausted'):
        store.record_member(member, deadline=started + .025)
    assert time.monotonic() - started < .05
    assert store.member(root['job_id'], root['job_id']) is None


def test_detached_context_is_explicit_and_does_not_trust_job_metadata(store):
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq.webhook_hooks import admission, binding, detached_catalog_maintenance, install
    install()
    _, root = reserve(store)
    with admission(root['job_id'], store.environment):
        ordinary = Job.create(leaf, connection=store.connection, meta={'query_catalog_maintenance': True})
        with detached_catalog_maintenance():
            detached = Job.create(leaf, connection=store.connection)
    assert binding(ordinary)['root'] == root['job_id']
    assert binding(detached) is None


def test_supervisor_thread_keeps_original_owner_after_monitor_returns(store):
    import threading
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq import webhook_hooks as hooks
    hooks.install()
    _, first = reserve(store, key='supervisor-first-0001')
    _, second = reserve(store, key='supervisor-second-001')
    def parent(root):
        return Job.create(leaf, connection=store.connection, id=root['job_id'],
            meta={hooks.BINDING: {'root': root['job_id'], 'parent': None, 'environment': store.environment}})
    release = threading.Event()
    children = []
    token = hooks.execution_started(parent(first))
    def produce():
        release.wait()
        nested = threading.Thread(target=lambda: children.append(Job.create(leaf, connection=store.connection)))
        nested.start()
        nested.join()
    thread = threading.Thread(target=produce)
    thread.start()
    hooks.supervisor_finished(token)
    later = hooks.execution_started(parent(second))
    try:
        release.set()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert hooks.binding(children[0])['root'] == first['job_id']
    finally:
        hooks.supervisor_finished(later)


def test_member_updates_preserve_bounded_reconciliation_deadline(store):
    _, root = reserve(store)
    member = publish(store, root)
    due = 150.0
    store.connection.zadd(store.due_key, {root['job_id']: due})
    store.record_member(replace(member, status='queued'))
    assert store.connection.zscore(store.due_key, root['job_id']) == due


def test_interrupted_concurrent_claims_keep_exact_event_and_fence_old_writer(store):
    from concurrent.futures import ThreadPoolExecutor
    _, root = reserve(store)
    publish(store, root)
    store.evaluate(root['job_id'], now=120)
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: claim(store, root['job_id'], 121), range(4)))
    first = next(value for value in claims if value is not None)
    assert sum(value is not None for value in claims) == 1
    # A receiver may have acknowledged; the first sender dies without persisting.
    import time
    store.connection.pexpire(store.prefix + 'claim:' + first['principal'], 1)
    time.sleep(.01)
    second = claim(store, root['job_id'], 152)
    assert second and second['event_id'] == first['event_id'] and second['event'] == first['event']
    assert second['audit'][0]['result'] == 'interrupted'
    assert not record_attempt(store, first, {'status': 204}, 153)
    assert record_attempt(store, second, {'status': 204}, 154)
    assert store.read(root['job_id'])['state'] == 'delivered'


def test_real_principal_quota_releases_without_canceling_computation(store):
    from wepppy.rq import webhook_policy as policy
    roots = [reserve(store, key=f'quota-request-{index:04}')[1] for index in range(policy.PRINCIPAL_ROOTS)]
    with pytest.raises(AdmissionError) as denied:
        reserve(store, key='quota-over-limit-001')
    assert denied.value.status == 429
    store.finish(roots[0]['job_id'], 'outcome_unavailable', now=120)
    created, _ = reserve(store, key='quota-after-release-1')
    assert created
    assert all(store.read(root['job_id'])['state'] == 'admission_pending' for root in roots[1:])


@pytest.mark.parametrize('publication', ['not_published', 'unknown'])
def test_expired_admission_http_body_preserves_publication_evidence(store, publication):
    from wepppy.microservices.rq_engine.webhooks import response_error
    from wepppy.rq import webhook_policy as policy
    _, root = reserve(store)
    if publication == 'not_published':
        store.prepublication_failed(root['job_id'])
    else:
        store.evaluate(root['job_id'], now=100+policy.TRACKING_SECONDS)
    with pytest.raises(AdmissionError) as expired:
        store.reserve(principal='issuer:service:client', key='callback-request-1', digest='digest',
            operation='run-wepp', resource={'type':'run','id':'test'}, url='https://example.com/unused',
            job_id=str(uuid4()), now=100+policy.TRACKING_SECONDS)
    response = response_error(expired.value)
    assert response.status_code == 410
    body = json.loads(response.body)
    assert len(body.pop('error_id')) == 32
    assert body == {'error': {
        'message': 'Admission expired. Unknown publication requires operator reconciliation before new work.',
        'code': 'webhook_admission_unavailable',
        'details': {'job_id': root['job_id'], 'publication': publication}}}


def test_stale_dispatcher_cannot_shorten_new_retry_deadline(store, monkeypatch):
    from wepppy.rq import webhook_dispatcher as dispatcher
    _, root = reserve(store)
    publish(store, root)
    store.evaluate(root['job_id'], now=120)
    monkeypatch.setattr(dispatcher.time, 'time', lambda: 121)
    def concurrent_attempt(*args, **kwargs):
        store.connection.zadd(store.due_key, {root['job_id']: 421})
        return None
    monkeypatch.setattr(dispatcher, 'claim', concurrent_attempt)
    dispatcher.run(store, dispatch=True, once=True, redis_run_id=store.connection.info('server')['run_id'])
    assert store.connection.zscore(store.due_key, root['job_id']) == 421


def test_stale_terminal_due_does_not_starve_same_principal_delivery(store, monkeypatch):
    from types import SimpleNamespace
    from wepppy.rq import webhook_dispatcher as dispatcher
    _, old = reserve(store)
    publish(store, old)
    store.finish(old['job_id'], 'exhausted', now=120)
    store.connection.zadd(store.due_key, {old['job_id']: 120})
    _, new = reserve(store, key='new-delivery-request')
    publish(store, new)
    store.evaluate(new['job_id'], now=121)
    clock = [122]
    monkeypatch.setattr(dispatcher, 'time', SimpleNamespace(
        time=lambda: clock[0], monotonic=lambda: 0, sleep=lambda _: None))
    dispatcher.run(store, once=True)
    assert store.connection.zscore(store.due_key, old['job_id']) == 120 + dispatcher.policy.AUDIT_SECONDS
    seen = []
    monkeypatch.setattr(dispatcher, 'attempt', lambda store, claimed, arm: seen.append(claimed['job_id']))
    clock[0] = 153
    dispatcher.run(store, once=True, dispatch=True, redis_run_id=store.connection.info('server')['run_id'])
    assert seen == [new['job_id']]


def test_immediate_watch_preserves_rq_save_and_ordinary_pipeline_errors(store):
    import redis
    from rq.job import Job
    from tests.rq.webhook_tasks import leaf
    from wepppy.rq.webhook_hooks import BINDING, install
    install()
    _, root = reserve(store)
    publish(store, root)
    job = Job.create(leaf, id=root['job_id'], connection=store.connection,
        meta={BINDING: {'root': root['job_id'], 'parent': None, 'environment': store.environment}})
    with store.connection.pipeline() as pipe:
        pipe.watch('unrelated-watch-guard')
        job.save(pipeline=pipe)
        job.save(pipeline=pipe)
        job.set_status('finished', pipeline=pipe)
        assert not pipe.command_stack
        assert not getattr(pipe, '_webhook_command_indexes', set())
        assert store.connection.hget(store.root_key(job.id), 'incomplete') == b'nontransactional_watch'
        assert store.evaluate(job.id, now=120) == 'unknown'
        store.connection.set('ordinary-error-key', 'not-a-list')
        pipe.multi()
        pipe.lpush('ordinary-error-key', 'value')
        with pytest.raises(redis.ResponseError):
            pipe.execute()


def test_immediate_member_lua_result_is_not_misreported_as_buffered(store):
    member = Member('missing', 'missing', None, 'queued')
    with store.connection.pipeline() as pipe:
        pipe.watch('unrelated-watch-guard')
        assert store.record_member(member, pipeline=pipe) is False
        assert not pipe.command_stack
