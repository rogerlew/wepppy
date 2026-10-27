"""Trusted operator pilot authority; no public control or implicit registration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from redis.exceptions import WatchError
from rq import Queue
from rq.job import Job

MARKER = '.query-catalog-pilot-owner.json'
OBSERVATION_SECONDS = 10
LEASE_SECONDS = 60
WINDOW_SECONDS = 1800
BUDGETS = {'refresh': 25, 'inventory': 2}


def key(pilot_id: str) -> str:
    if not isinstance(pilot_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,63}', pilot_id):
        raise ValueError('Invalid pilot identifier')
    return 'query-catalog:pilot:' + pilot_id


def text(value: Any) -> str | None:
    return value.decode() if isinstance(value, bytes) else value


def read(connection: Any, pilot_id: str) -> dict[str, Any]:
    raw = connection.get(key(pilot_id))
    if raw is None:
        raise ValueError('Pilot authority is absent; operator recovery required')
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get('manifest'), dict) or not isinstance(data.get('jobs'), dict):
        raise ValueError('Malformed pilot authority')
    if (data['manifest'].get('pilot_id') != pilot_id or not isinstance(data.get('counters'), dict)
            or data['counters'].keys() != BUDGETS.keys()):
        raise ValueError('Malformed pilot accounting')
    if any(type(data['counters'][kind]) is not int or not 0 <= data['counters'][kind] <= limit for kind, limit in BUDGETS.items()):
        raise ValueError('Malformed pilot counters')
    manifest = data['manifest']
    if (manifest.get('protocol') != 1 or manifest.get('budgets') != BUDGETS
            or manifest.get('queue') != 'batch'):
        raise ValueError('Malformed pilot manifest protocol or budgets')
    counts = dict.fromkeys(BUDGETS, 0)
    for binding in data['jobs'].values():
        if (not isinstance(binding, dict) or binding.get('kind') not in BUDGETS
                or binding.get('pilot_id') != pilot_id
                or binding.get('generation') != manifest.get('generation')):
            raise ValueError('Malformed pilot job accounting')
        counts[binding['kind']] += 1
    if counts != data['counters']:
        raise ValueError('Pilot counters disagree with retained job bindings')
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    if digest != data.get('manifest_sha256'):
        raise ValueError('Immutable pilot manifest changed')
    return data


def _directory_identity(path: Path) -> dict[str, int]:
    # NFS mount device numbers differ across hosts. Namespace, incarnation and
    # owned marker bind the shared scope; its inode detects directory replacement.
    return {'inode': path.stat().st_ino}


def _scope(manifest: dict[str, Any], path: str) -> dict[str, Any]:
    from wepppy.query_engine.catalog_refresh import configured_roots, resolve_scope
    from ._query_catalog_inventory import validated_scope_path
    approved = next((s for s in manifest['scopes'] if s['path'] == str(path)), None)
    if approved is None:
        raise ValueError('Scope is not approved by pilot')
    base = validated_scope_path(configured_roots(), str(path))
    if str(base) != approved['path']:
        raise ValueError('Pilot scope locator changed')
    marker = base / MARKER
    if marker.is_symlink() or json.loads(marker.read_text()) != {'pilot_id': manifest['pilot_id']}:
        raise ValueError('Pilot fixture ownership changed')
    scope = resolve_scope(base, create=False)
    identity = _directory_identity(base)
    if (not scope.managed or scope.scope_id != approved['scope_id'] or
            scope.incarnation != approved['incarnation'] or scope.namespace != approved['namespace'] or
            identity != approved['directory_identity']):
        raise ValueError('Pilot scope identity changed')
    return approved


def register_pilot(connection: Any, pilot_id: str, paths: list[str]) -> dict[str, Any]:
    from wepppy.query_engine.catalog_refresh import configured_roots, resolve_scope
    from ._query_catalog_inventory import validated_scope_path
    from .query_catalog_rq import catalog_worker_configuration
    from ._query_catalog_admission import initialize_admission
    destination = key(pilot_id)
    if connection.exists(destination):
        raise ValueError('Pilot identifier already registered; budgets cannot reset')
    if not paths or len(paths) > 25 or len(set(map(str, paths))) != len(paths):
        raise ValueError('Pilot requires one to 25 distinct owned scopes')
    configuration = catalog_worker_configuration()
    if configuration['enabled']:
        raise ValueError('Owned pilot requires general admission disabled')
    scopes = []
    for path in paths:
        base = validated_scope_path(configured_roots(), str(path))
        marker = base / MARKER
        if marker.is_symlink() or json.loads(marker.read_text()) != {'pilot_id': pilot_id}:
            raise ValueError('Pilot fixture ownership marker required')
        scope = resolve_scope(base, create=False)
        if not scope.managed or not scope.incarnation:
            raise ValueError('Operator must initialize owned fixture identity before registration')
        scopes.append(dict(path=str(base), scope_id=scope.scope_id, incarnation=scope.incarnation,
                           namespace=scope.namespace, directory_identity=_directory_identity(base)))
    now = time.time()
    manifest = dict(protocol=1, pilot_id=pilot_id, generation=uuid4().hex, scopes=scopes,
                    configuration=configuration, started_at=now, deadline=now + WINDOW_SECONDS,
                    budgets=dict(BUDGETS), queue='batch')
    data = dict(manifest=manifest, manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), state='paused', counters=dict(refresh=0, inventory=0),
                jobs={}, failures=[], phases={}, observation={}, pause_reason='registered')
    initialize_admission(connection, Queue('batch', connection=connection))
    if not connection.set(destination, json.dumps(data), nx=True):
        raise ValueError('Pilot identifier already registered; budgets cannot reset')
    return manifest


def acquire_controller(connection: Any, pilot_id: str) -> str:
    read(connection, pilot_id)
    token = uuid4().hex
    if not connection.set(key(pilot_id) + ':observer', token, nx=True, ex=LEASE_SECONDS):
        raise RuntimeError('Pilot observer already owned')
    return token


def require_owner(connection: Any, pilot_id: str, token: str | None) -> None:
    if not token or text(connection.get(key(pilot_id) + ':observer')) != token:
        raise RuntimeError('Pilot observation ownership lost')


def require_admission(connection: Any, data: dict[str, Any], token: str | None) -> None:
    from .query_catalog_rq import catalog_worker_configuration
    manifest = data['manifest']
    require_owner(connection, manifest['pilot_id'], token)
    if data['state'] != 'active' or time.time() >= manifest['deadline']:
        raise RuntimeError('Pilot is paused, expired or exhausted')
    if time.time() - data.get('observation', {}).get('at', 0) >= LEASE_SECONDS:
        raise RuntimeError('Pilot observation is stale')
    if manifest['configuration'] != catalog_worker_configuration():
        raise RuntimeError('Pilot configuration changed')


def _mutate_once(connection: Any, pilot_id: str, change: Any, *, token: str | None = None) -> dict[str, Any]:
    with connection.pipeline() as pipe:
        pipe.watch(key(pilot_id), key(pilot_id) + ':observer')
        data = read(pipe, pilot_id)
        if token is not None:
            require_owner(pipe, pilot_id, token)
        change(data)
        pipe.multi()
        pipe.set(key(pilot_id), json.dumps(data))
        pipe.execute()
    return pilot_status(connection, pilot_id)


def _mutate(connection: Any, pilot_id: str, change: Any, *, token: str | None = None) -> dict[str, Any]:
    # Concurrent claims/observations are expected; reread authority on every CAS.
    for attempt in range(8):
        try:
            return _mutate_once(connection, pilot_id, change, token=token)
        except WatchError:
            if attempt == 7:
                raise


def pause_pilot(connection: Any, pilot_id: str, reason: str) -> dict[str, Any]:
    def change(data):
        data['state'] = 'paused'
        data['pause_reason'] = str(reason)
        if reason in {'artifact_failure', 'controller_observation_failure', 'controller_monitor_bound', 'query_catalog_pilot_authority_unavailable', 'accounting_failure', 'configuration_mismatch', 'ordinary_wait_limit'}:
            if not any(f.get('reason') == reason for f in data['failures']):
                data['failures'].append(dict(reason=reason, at=time.time()))
    return _mutate(connection, pilot_id, change)


def resume_pilot(connection: Any, pilot_id: str, token: str) -> dict[str, Any]:
    def change(data):
        if time.time() >= data['manifest']['deadline']:
            raise RuntimeError('Original pilot admission window expired')
        if time.time() - data.get('observation', {}).get('at', 0) >= LEASE_SECONDS:
            raise RuntimeError('Successful observation required before resume')
        if data['observation'].get('ordinary_waiting'):
            raise RuntimeError('Ordinary batch backlog prevents resume')
        data['state'] = 'active'
        data['pause_reason'] = None
    return _mutate(connection, pilot_id, change, token=token)


def _observe_once(connection: Any, pilot_id: str, token: str) -> dict[str, Any]:
    from ._query_catalog_admission import ordinary_observation, LEDGER_KEY, _ledger, execution_uncertain
    with connection.pipeline() as pipe:
        pipe.watch(key(pilot_id), key(pilot_id) + ':observer', LEDGER_KEY)
        data = read(pipe, pilot_id)
        require_owner(pipe, pilot_id, token)
        ledger_raw = pipe.get(LEDGER_KEY)
        if ledger_raw is None:
            raise RuntimeError('Admission ledger lost; operator recovery required')
        ledger = _ledger(pipe)
        observed = ordinary_observation(connection, Queue('batch', connection=connection), ledger)
        if any(execution_uncertain(binding, text(connection.hget(Job.key_for(jid), 'status')))
               for jid, binding in ledger['jobs'].items()):
            data['state'] = 'paused'
            data['pause_reason'] = 'uncertain_accounting'
            if not any(f.get('reason') == 'uncertain_accounting' for f in data['failures']):
                data['failures'].append(dict(reason='uncertain_accounting', at=time.time()))
        known = {f.get('job_id') for f in data['failures'] if isinstance(f, dict)}
        for jid in data['jobs']:
            status = text(connection.hget(Job.key_for(jid), 'status'))
            if status in {'failed', 'stopped', 'canceled'} and jid not in known:
                data['failures'].append(dict(job_id=jid, state=status, at=time.time()))
                data['state'] = 'paused'
                data['pause_reason'] = 'job_failure'
        if observed['ordinary_waiting']:
            data['state'] = 'paused'
            data['pause_reason'] = 'ordinary_backlog'
        if observed.get('oldest_wait_seconds', 0) >= 300 and not any(f.get('reason') == 'ordinary_wait_limit' for f in data['failures']):
            data['failures'].append(dict(reason='ordinary_wait_limit', at=time.time()))
        data['observation'] = dict(observed, at=time.time())
        pipe.multi()
        pipe.set(key(pilot_id), json.dumps(data))
        pipe.expire(key(pilot_id) + ':observer', LEASE_SECONDS)
        pipe.execute()
    return pilot_status(connection, pilot_id)


def observe_pilot(connection: Any, pilot_id: str, token: str) -> dict[str, Any]:
    for attempt in range(8):
        try:
            return _observe_once(connection, pilot_id, token)
        except WatchError:
            if attempt == 7:
                raise


def pilot_status(connection: Any, pilot_id: str) -> dict[str, Any]:
    data = read(connection, pilot_id)
    jobs = {}
    for jid, binding in data['jobs'].items():
        jobs[jid] = dict(binding, status=text(connection.hget(Job.key_for(jid), 'status')) or 'unknown')
    result = dict(data, jobs=jobs, deadline=data['manifest']['deadline'])
    from ._query_catalog_admission import _ledger, AdmissionDenied, execution_outstanding, execution_uncertain
    result['outstanding'] = sum(execution_outstanding(j, None if j['status'] == 'unknown' else j['status']) for j in jobs.values())
    try:
        ledger = _ledger(connection)
        statuses = [text(connection.hget(Job.key_for(jid), 'status')) for jid in ledger['jobs']]
        result['global_job_ids'] = list(ledger['jobs'])
        result['global_outstanding'] = sum(execution_outstanding(binding, status) for binding, status in zip(ledger['jobs'].values(), statuses))
        result['global_uncertain'] = sum(execution_uncertain(binding, status) for binding, status in zip(ledger['jobs'].values(), statuses))
    except (AdmissionDenied, ValueError) as exc:
        result['global_job_ids'] = []
        result['global_outstanding'] = None
        result['global_uncertain'] = True
        result['accounting_error'] = type(exc).__name__
    if time.time() >= result['deadline']:
        result['state'] = 'expired'
    elif all(data['counters'][kind] >= maximum for kind, maximum in BUDGETS.items()):
        result['state'] = 'exhausted'
    return result


def authorize_receipt(connection: Any, pilot_id: str, path: str, controller_token: str) -> dict[str, Any]:
    data = read(connection, pilot_id)
    require_admission(connection, data, controller_token)
    return dict(_scope(data['manifest'], str(path)))


def record_phase(connection: Any, pilot_id: str, controller_token: str, phase: str, value: Any) -> dict[str, Any]:
    def change(data):
        if phase in data['phases'] and data['phases'][phase] != value:
            raise ValueError('Pilot phase is already recorded differently')
        data['phases'][phase] = value
    return _mutate(connection, pilot_id, change, token=controller_token)
