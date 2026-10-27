"""One Redis admission ledger for every catalog job on shared batch."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import time
from typing import Any

from redis.exceptions import WatchError
from rq import Queue, worker_registration
from rq.job import Job
from rq.suspension import WORKERS_SUSPENDED

LEDGER_KEY = 'query-catalog:batch-admission:v1'
PAUSE_KEY = LEDGER_KEY + ':paused'
TERMINAL = frozenset({'finished', 'failed', 'stopped', 'canceled'})
CAP = 7


class AdmissionDenied(RuntimeError):
    pass


def _text(value):
    return value.decode() if isinstance(value, bytes) else value


def _ledger(connection):
    raw = connection.get(LEDGER_KEY)
    if raw is None:
        raise AdmissionDenied('query_catalog_accounting_unavailable')
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), dict):
        raise AdmissionDenied('query_catalog_accounting_invalid')
    for jid, binding in data['jobs'].items():
        if (not isinstance(jid, str) or not isinstance(binding, dict)
                or binding.get('kind') not in {'refresh', 'inventory'}
                or not isinstance(binding.get('configuration'), dict)
                or type(binding.get('claimed')) is not bool
                or not isinstance(binding.get('reserved_at'), (int, float))):
            raise AdmissionDenied('query_catalog_accounting_invalid')
    return data


def execution_uncertain(binding: dict[str, Any], status: str | None) -> bool:
    # RQ cancel() can mark STARTED work canceled without stopping its workhorse.
    # Real finished/failed/stopped transitions retain RQ's death/timeout semantics.
    return status is None or (status == 'canceled' and binding['claimed']
                              and not binding.get('execution_exited_at'))


def execution_outstanding(binding: dict[str, Any], status: str | None) -> bool:
    return status not in TERMINAL or execution_uncertain(binding, status)


def initialize_admission(connection: Any, queue: Queue) -> None:
    """Explicit operator bootstrap; never reset an existing or uncertain ledger."""
    if queue.name != 'batch':
        raise ValueError('Catalog admission requires shared batch')
    with connection.pipeline() as pipe:
        keys = [queue.key] + ['rq:' + name + ':batch' for name in ('wip', 'deferred', 'scheduled')]
        pipe.watch(LEDGER_KEY, *keys)
        if pipe.exists(LEDGER_KEY):
            _ledger(pipe)
            return
        if next(connection.scan_iter('query-catalog:pilot:*'), None) is not None:
            raise AdmissionDenied('Lost ledger requires explicit operator recovery')
        identifiers = list(pipe.lrange(queue.key, 0, -1))
        for registry in keys[1:]:
            identifiers.extend(pipe.zrange(registry, 0, -1))
        if any((_text(jid) or '').startswith('query_catalog_refresh_') for jid in identifiers):
            raise AdmissionDenied('Existing maintenance requires explicit ledger recovery')
        pipe.multi()
        pipe.set(LEDGER_KEY, json.dumps({'jobs': {}, 'initialized_at': time.time()}))
        pipe.execute()


def ordinary_observation(connection: Any, queue: Queue, ledger: dict[str, Any]) -> dict[str, Any]:
    waiting = []
    oldest = 0.0
    unknown = False
    for raw in connection.lrange(queue.key, 0, -1):
        jid = _text(raw)
        if jid in ledger['jobs']:
            continue
        waiting.append(jid)
        value = connection.hget(Job.key_for(jid), 'enqueued_at')
        try:
            timestamp = datetime.fromisoformat(_text(value).replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            oldest = max(oldest, time.time() - timestamp.timestamp())
        except (AttributeError, TypeError, ValueError):
            unknown = True
    return dict(ordinary_waiting=len(waiting), oldest_wait_seconds=oldest,
                unknown_wait_metadata=unknown)


def _deny(queue, pilot_id, reason):
    if pilot_id:
        from ._query_catalog_pilot import pause_pilot
        pause_pilot(queue.connection, pilot_id, reason)
    raise AdmissionDenied(reason)


def prepare(pipe: Any, queue: Queue, *, job_id: str, kind: str, configuration: dict[str, Any],
            scope: dict[str, Any] | None = None, pilot_id: str | None = None,
            controller_token: str | None = None) -> dict[str, Any]:
    """Read all policy inputs under WATCH; caller enqueues and commits ticket."""
    from . import _query_catalog_pilot as pilot
    from .query_catalog_rq import WORKER_FIELD
    if queue.name != 'batch' or kind not in {'refresh', 'inventory'}:
        raise AdmissionDenied('query_catalog_queue_invalid')
    pipe.watch(LEDGER_KEY, PAUSE_KEY, queue.key, WORKERS_SUSPENDED)
    try:
        ledger = _ledger(pipe)
    except (AdmissionDenied, ValueError):
        _deny(queue, pilot_id, 'accounting_failure')
    if pipe.exists(PAUSE_KEY) or pipe.exists(WORKERS_SUSPENDED):
        _deny(queue, pilot_id, 'query_catalog_admission_paused')
    if len(ledger['jobs']) > CAP:
        _deny(queue, pilot_id, 'query_catalog_accounting_invalid')
    remaining = {}
    for jid, binding in ledger['jobs'].items():
        pipe.watch(Job.key_for(jid))
        status = _text(pipe.hget(Job.key_for(jid), 'status'))
        if execution_uncertain(binding, status):
            _deny(queue, pilot_id, 'query_catalog_accounting_uncertain')
        if execution_outstanding(binding, status):
            remaining[jid] = binding
    # Queue classification uses ledger ownership; unknown prefix-shaped jobs are
    # ordinary/uncertain work, never authority to bypass backlog priority.
    queued = [_text(jid) for jid in pipe.lrange(queue.key, 0, -1)]
    if len(queued) != len(set(queued)):
        _deny(queue, pilot_id, 'accounting_failure')
    if any(jid not in ledger['jobs'] for jid in queued):
        _deny(queue, pilot_id, 'query_catalog_ordinary_backlog')
    if any(_text(pipe.hget(Job.key_for(jid), 'status')) != 'queued' for jid in queued):
        _deny(queue, pilot_id, 'accounting_failure')
    pipe.watch('rq:workers', 'rq:workers:batch')
    registrations = list(worker_registration.get_keys(queue=queue))
    compatible = 0
    for registration in registrations:
        pipe.watch(registration)
        queues, advertised, death = pipe.hmget(registration, 'queues', WORKER_FIELD, 'death')
        if death is not None or pipe.ttl(registration) <= 0 or 'batch' not in (_text(queues) or '').split(','):
            continue
        try:
            observed = json.loads(advertised) if advertised else None
        except (ValueError, TypeError):
            observed = None
        if observed != configuration:
            _deny(queue, pilot_id, 'query_catalog_workers_unavailable')
        compatible += 1
    if pilot_id and compatible != 8:
        _deny(queue, pilot_id, 'configuration_mismatch')
    if not compatible:
        _deny(queue, pilot_id, 'query_catalog_workers_unavailable')
    if len(remaining) >= min(CAP, compatible):
        raise AdmissionDenied('query_catalog_capacity_pending')
    pilot_data = None
    if pilot_id:
        pipe.watch(pilot.key(pilot_id), pilot.key(pilot_id) + ':observer')
        pilot_data = pilot.read(pipe, pilot_id)
        try:
            pilot.require_admission(pipe, pilot_data, controller_token)
        except RuntimeError:
            _deny(queue, pilot_id, 'query_catalog_pilot_authority_unavailable')
        if pilot_data['counters'][kind] >= pilot.BUDGETS[kind]:
            raise AdmissionDenied('query_catalog_pilot_budget_exhausted')
        if kind == 'refresh':
            approved = pilot._scope(pilot_data['manifest'], scope['wd'])
            if approved['scope_id'] != scope['scope_id'] or approved['incarnation'] != scope['incarnation']:
                raise AdmissionDenied('query_catalog_pilot_scope_invalid')
    elif not configuration['enabled']:
        raise AdmissionDenied('query_catalog_refresh_disabled')
    binding = dict(kind=kind, pilot_id=pilot_id, configuration=configuration,
                   scope=scope, claimed=False, reserved_at=time.time())
    if pilot_data:
        binding['generation'] = pilot_data['manifest']['generation']
        pilot_data['counters'][kind] += 1
        pilot_data['jobs'][job_id] = binding
    remaining[job_id] = binding
    ledger['jobs'] = remaining
    return dict(ledger=ledger, pilot=pilot_data, pilot_id=pilot_id)


def commit(pipe: Any, ticket: dict[str, Any]) -> None:
    """Append policy writes to the caller's existing RQ enqueue transaction."""
    from . import _query_catalog_pilot as pilot
    pipe.set(LEDGER_KEY, json.dumps(ticket['ledger']))
    if ticket['pilot'] is not None:
        pipe.set(pilot.key(ticket['pilot_id']), json.dumps(ticket['pilot']))


def _authorize_job_once(connection: Any, job: Job, *, kind: str, pilot_id: str | None,
                  scope_id: str | None = None, wd: str | None = None) -> dict[str, Any] | None:
    from . import _query_catalog_pilot as pilot
    from .query_catalog_rq import catalog_worker_configuration
    with connection.pipeline() as pipe:
        pipe.watch(LEDGER_KEY, Job.key_for(job.id))
        ledger = _ledger(pipe)
        binding = ledger['jobs'].get(job.id)
        if (not binding or binding['kind'] != kind or binding.get('pilot_id') != pilot_id or
                binding['configuration'] != catalog_worker_configuration() or binding.get('claimed')):
            raise ValueError('Catalog job has no unused admitted execution authority')
        if job.origin != 'batch' or _text(pipe.hget(Job.key_for(job.id), 'status')) != 'started':
            raise ValueError('Catalog job is not started')
        if kind == 'refresh' and (binding['scope']['scope_id'] != scope_id or binding['scope']['wd'] != str(wd)):
            raise ValueError('Catalog scope argument changed')
        data = None
        if pilot_id:
            pipe.watch(pilot.key(pilot_id))
            data = pilot.read(pipe, pilot_id)
            approved = data['jobs'].get(job.id)
            if approved != binding or data['manifest']['generation'] != binding['generation']:
                raise ValueError('Pilot job binding changed')
            if kind == 'refresh':
                if binding['scope']['scope_id'] != scope_id:
                    raise ValueError('Pilot scope argument changed')
                pilot._scope(data['manifest'], binding['scope']['wd'])
        binding['claimed'] = True
        binding['claimed_at'] = time.time()
        pipe.multi()
        pipe.set(LEDGER_KEY, json.dumps(ledger))
        if data:
            data['jobs'][job.id] = binding
            pipe.set(pilot.key(pilot_id), json.dumps(data))
        pipe.execute()
    return data['manifest'] if data else None


def authorize_job(connection: Any, job: Job, *, kind: str, pilot_id: str | None,
                  scope_id: str | None = None, wd: str | None = None) -> dict[str, Any] | None:
    # Up to seven workers claim concurrently against the shared ledger. A CAS
    # retry rereads all authority; it never replays a committed execution claim.
    for attempt in range(16):
        try:
            return _authorize_job_once(connection, job, kind=kind, pilot_id=pilot_id,
                                       scope_id=scope_id, wd=wd)
        except WatchError:
            if attempt == 15:
                raise


def execution_exited(connection: Any, job: Job, pilot_id: str | None) -> None:
    """Durable proof that admitted scope work has left its worker boundary."""
    from . import _query_catalog_pilot as pilot
    for attempt in range(16):
        try:
            with connection.pipeline() as pipe:
                pipe.watch(LEDGER_KEY)
                ledger = _ledger(pipe)
                binding = ledger['jobs'].get(job.id)
                if not binding or not binding['claimed'] or binding.get('pilot_id') != pilot_id:
                    raise ValueError('Execution exit has no admitted claim')
                data = None
                if pilot_id:
                    pipe.watch(pilot.key(pilot_id))
                    data = pilot.read(pipe, pilot_id)
                    if data['jobs'].get(job.id) != binding:
                        raise ValueError('Execution exit binding changed')
                binding['execution_exited_at'] = time.time()
                pipe.multi()
                pipe.set(LEDGER_KEY, json.dumps(ledger))
                if data is not None:
                    data['jobs'][job.id] = binding
                    pipe.set(pilot.key(pilot_id), json.dumps(data))
                pipe.execute()
            return
        except WatchError:
            if attempt == 15:
                raise
