"""Read-only observations for the Admin/Root RQ snapshot."""
from collections import Counter
from hashlib import sha256
from datetime import datetime, timezone
import json
import logging
import time

from redis.exceptions import RedisError
from rq import Queue

from . import _query_catalog_admission as admission
from . import query_catalog_rq as catalog

_LOG = logging.getLogger(__name__)
_READ_ERRORS = (RedisError, ValueError, TypeError, KeyError, OverflowError, OSError, RecursionError)
_OBSERVER = b'production-cutover-20261106:general-observation'


def _timestamp(value):
    if value is None:
        return 'None recorded'
    if type(value) not in (int, float):
        raise ValueError('Invalid timestamp')
    return datetime.fromtimestamp(value, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def _admission(connection, panel):
    rows, messages = panel['rows'], panel['messages']
    # Read owner and expiry in the same Redis transaction. Do not expose arbitrary values.
    with connection.pipeline() as pipe:
        pipe.getrange(admission.PAUSE_KEY, 0, len(_OBSERVER))
        pipe.ttl(admission.PAUSE_KEY)
        owner, ttl = pipe.execute()
    if ttl != -2:
        messages.append('Catalog admission is paused.')
        label = 'Production cutover observer' if owner == _OBSERVER else 'Unrecognized owner'
        rows.extend([('Pause owner', label), ('Pause expires', 'No expiry' if ttl == -1 else f'In {ttl} seconds')])
    else:
        rows.append(('Catalog pause', 'Clear'))

    settings = catalog.QueryCatalogSettings.from_environ()
    rows.append(('Asynchronous refresh', 'Enabled' if settings.enabled else 'Disabled'))
    if not settings.enabled:
        messages.append('Asynchronous refresh is disabled.')

    queue = Queue('default', connection=connection)
    workers = catalog.consumer_status(queue)
    compatible = workers['compatible']
    rows.append(('Default workers', f"{compatible} compatible, {len(workers['incompatible'])} incompatible"))
    if workers['suspended']:
        messages.append('RQ workers are suspended.')
    if not compatible or workers['incompatible']:
        messages.append('Worker compatibility blocks admission.')

    try:
        raw = connection.getrange(admission.LEDGER_KEY, 0, 262144)
        if len(raw) > 262144:
            raise ValueError('Ledger exceeds monitoring read limit')
        jobs = admission._parse_ledger(raw or None)['jobs']
    except admission.AdmissionDenied:
        messages.append('Admission ledger is missing or invalid.')
        return
    if len(jobs) > admission.CAP:
        messages.append('Admission ledger exceeds the permit limit.')
        return
    with connection.pipeline() as pipe:
        for jid in jobs:
            pipe.hget('rq:job:' + jid, 'status')
        pipe.llen(queue.key)
        pipe.lrange(queue.key, 0, admission.CAP - 1)
        *statuses, length, head = pipe.execute()
    namespace, invalid = admission.owner_policy(connection, catalog.catalog_worker_configuration())
    if invalid:
        messages.append('Batch owner policy does not select a unique batch namespace. The owner cap is inactive.')
    rows.append(('Batch owner cap', f'{admission.OWNER_CAP} in {namespace}' if namespace else ('Invalid' if invalid else 'Disabled')))
    owners = Counter()
    outstanding = uncertain = 0
    for binding, raw in zip(jobs.values(), statuses):
        state = raw.decode() if raw else None
        if state is not None and state not in admission.TERMINAL | catalog.ACTIVE_STATES:
            raise ValueError('Unknown job status')
        outstanding += admission.execution_outstanding(binding, state)
        if binding['kind'] == 'refresh' and admission.execution_outstanding(binding, state):
            try:
                owner = admission.batch_owner(binding.get('scope'), namespace)
            except admission.AdmissionDenied:
                messages.append('Outstanding refresh has invalid owner accounting.')
                return
            if owner:
                owners[owner] += 1
        uncertain += admission.execution_uncertain(binding, state)
    for owner, count in sorted(owners.items()):
        label = sha256(owner.encode()).hexdigest()[:12]
        rows.append((f'Batch owner {label}', f'{count} of {admission.OWNER_CAP}'))
    rows.extend([('Outstanding permits', f'{outstanding} of {admission.CAP}'),
                 ('Uncertain reservations', uncertain)])
    if uncertain:
        messages.append('Reservation execution is uncertain. Reconcile retained job evidence.')
    if compatible and outstanding >= min(compatible, admission.CAP):
        messages.append('Catalog capacity is full.')
    queued = [jid.decode() for jid in head]
    status_by_job = dict(zip(jobs, statuses))
    if len(set(queued)) != len(queued) or any(
        jid in jobs and status_by_job[jid] != b'queued' for jid in queued
    ):
        messages.append('Queue and reservation records disagree.')
    ordinary = sum(jid not in jobs for jid in queued)
    if length > len(head):
        backlog = f'At least {ordinary} (first {len(head)} inspected)'
        if not ordinary:
            messages.append('Default queue exceeds the catalog cap. Check queue accounting and ordinary backlog.')
    else:
        backlog = ordinary
    rows.append(('Ordinary default jobs waiting', backlog))
    if ordinary:
        messages.append('Ordinary jobs have queue priority.')
    if not messages:
        messages.append('No observed admission blocker.')


def _health(connection, panel):
    identity = catalog._configuration_id()
    key = 'query-catalog:inventory:' + identity
    with connection.pipeline() as pipe:
        pipe.scard('query-catalog:dirty:' + identity)
        pipe.getrange(key + ':health', 0, 4096)
        dirty, raw = pipe.execute()
    panel['rows'].append(('Known dirty locators', dirty))
    if not raw:
        panel['messages'].append('No scheduler summary recorded for this configuration.')
        return
    if len(raw) > 4096:
        raise ValueError('Scheduler summary exceeds monitoring read limit')
    summary = json.loads(raw)
    fields = [('visited', 'Inventory directories visited'), ('pending', 'Pending locators'),
              ('admitted', 'Jobs reported admitted at last tick'), ('failures', 'Reconciliation errors'),
              ('unavailable', 'Unavailable namespaces')]
    if not isinstance(summary, dict) or any(type(summary[k]) is not int or summary[k] < 0 for k, _ in fields):
        raise ValueError('Invalid scheduler counters')
    if type(summary['discovery_unavailable']) is not bool or summary['tick'] is None:
        raise ValueError('Invalid scheduler state')
    rows = [('Last committed scheduler tick', _timestamp(summary['tick'])),
            ('Time since scheduler tick', f"{round(time.time() - summary['tick'])} seconds"),
            ('Cycle started', _timestamp(summary['started'])), ('Cycle completed', _timestamp(summary['completed']))]
    panel['rows'].extend(rows + [(label, summary[k]) for k, label in fields])
    if 'owner_deferrals' in summary:
        if type(summary['owner_deferrals']) is not int or summary['owner_deferrals'] < 0:
            raise ValueError('Invalid owner deferral count')
        panel['rows'].append(('Owner capacity deferrals at last tick', summary['owner_deferrals']))
    if summary['failures'] or summary['unavailable'] or summary['discovery_unavailable']:
        panel['messages'].append('Reconciliation reported a problem at the last tick.')
    elif summary['completed'] is not None:
        panel['messages'].append('Cycle complete at the last tick.')
    elif summary['started'] is not None:
        panel['messages'].append('Cycle in progress at the last tick.')
    else:
        panel['messages'].append('Waiting for a discovery cycle at the last tick.')


def catalog_panels(connection):
    panels = []
    for title, read in [('Catalog admission', _admission), ('Catalog health', _health)]:
        panel = {'rows': [], 'messages': []}
        try:
            read(connection, panel)
        except _READ_ERRORS:
            _LOG.warning('Unable to read %s telemetry', title, exc_info=True)
            panel['messages'].append('Monitoring data unavailable.')
        panels.append((title, panel))
    return panels
