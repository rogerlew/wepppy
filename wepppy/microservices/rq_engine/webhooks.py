"""Optional callback admission. Call only after the route's normal authorization."""
from __future__ import annotations

import hashlib
import json
import functools
import logging
import os
import re
import time

import redis
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette.exceptions import HTTPException

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.webhook_http import InvalidDestination, destination
from wepppy.rq.webhook_tracking import AdmissionError, WebhookStore, bounded_root, encode
from wepppy.rq import webhook_hooks, webhook_policy
from .responses import error_response

SUPPORTED = frozenset({'run-wepp', 'run-wepp-watershed', 'prep-wepp-watershed', 'culverts-wepp-batch'})


def submission_boundary(function):
    @functools.wraps(function)
    async def wrapped(*args, **kwargs):
        request = kwargs.get('request') or next((arg for arg in args if isinstance(arg, Request)), None)
        try:
            return await function(*args, **kwargs)
        finally:
            callback = getattr(request.state, 'webhook_submission', None) if request is not None else None
            if callback is not None and callback.created and not callback.publication_attempted:
                try:
                    if callback.prepublication_cleanup is not None:
                        callback.prepublication_cleanup()
                    callback.store.prepublication_failed(callback.job_id)
                except (redis.RedisError, OSError):
                    # Preserve the original response; uncertain persistence stays
                    # pending rather than authorizing duplicate computation.
                    logging.getLogger(__name__).warning('Webhook prepublication recovery receipt unavailable')
    return wrapped


async def request_options(request, *, operation: str):
    if 'application/json' in request.headers.get('content-type', ''):
        try:
            payload = await request.json()
        except (ValueError, UnicodeError):
            return None
        return validate_option(payload, request.headers, operation=operation) if isinstance(payload, dict) else None
    payload = await request.form()
    return validate_option(payload, request.headers, operation=operation)


async def reject_unsupported(request) -> JSONResponse | None:
    """Run after the owning route's auth block, before its first mutation."""
    headers = getattr(request, 'headers', {})
    content_type = headers.get('content-type', '').split(';', 1)[0].lower()
    if not content_type and headers.get('content-length', '0') == '0':
        return None
    try:
        if content_type in {'application/json', ''}:
            payload = await request.json()
        elif content_type in {'multipart/form-data', 'application/x-www-form-urlencoded'}:
            payload = await request.form()
        else:
            return None
    except (ValueError, UnicodeError, HTTPException):
        return None  # The owning parser retains its existing malformed-body policy.
    return reject_unsupported_payload(payload)


def reject_unsupported_payload(payload) -> JSONResponse | None:
    if isinstance(payload, dict) or hasattr(payload, 'getlist'):
        if 'webhook_url' in payload:
            return response_error(AdmissionError('webhook_not_supported', 400))
    return None


def validate_option(payload, headers, *, operation: str) -> tuple[str, str] | None:
    if 'webhook_url' not in payload:
        return None
    if operation not in SUPPORTED:
        raise AdmissionError('webhook_not_supported', 400)
    values = payload.getlist('webhook_url') if hasattr(payload, 'getlist') else [payload['webhook_url']]
    if len(values) != 1:
        raise AdmissionError('invalid_webhook', 400)
    try:
        url = destination(values[0]).url
    except InvalidDestination:
        raise AdmissionError('invalid_webhook', 400) from None
    key = headers.get('Idempotency-Key', '')
    if not re.fullmatch(r'[A-Za-z0-9._-]{16,128}', key):
        raise AdmissionError('invalid_webhook', 400)
    if any(str(name).startswith('_webhook') for name in payload):
        raise AdmissionError('invalid_webhook', 400)
    return url, key


def environment() -> str:
    identity = os.environ.get('RQ_WEBHOOK_ENVIRONMENT', '')
    # An external startup setting, never an enabled bit restored from Redis.
    if not identity or os.environ.get('RQ_WEBHOOK_ADMISSION') != 'enabled':
        raise AdmissionError('webhook_unavailable', 503)
    # This gate remains closed until the package's producer/worker acceptance
    # is complete. Operators cannot accidentally opt in a mixed deployment.
    if os.environ.get('RQ_WEBHOOK_INSTRUMENTATION') != 'rq-wh-01':
        raise AdmissionError('webhook_unavailable', 503)
    return identity


def principal_key(claims: dict, principal=None) -> str:
    from .feature_access import verified_principal
    principal = principal if principal is not None else verified_principal(claims)
    issuer = claims.get('iss')
    if not isinstance(issuer, str) or not issuer:
        raise AdmissionError('webhook_principal_unsupported', 400)
    kind = claims.get('token_class')
    if principal.kind == 'human' and principal.user_id:
        identity = ['human', str(principal.user_id)]
    elif principal.kind == 'integration':
        # The existing trusted adapter has one explicitly registered integration.
        from wepppy.weppcloud.utils.feature_access_identity import principal_claim
        registered = principal_claim(principal).get('id')
        if not registered:
            raise AdmissionError('webhook_principal_unsupported', 400)
        identity = ['integration', registered]
    elif kind == 'session' and isinstance(claims.get('session_id'), str) and claims['session_id']:
        identity = ['session', claims['session_id']]
    else:
        raise AdmissionError('webhook_principal_unsupported', 400)
    return encode([issuer, *identity])


def verify_workers(connection, identity: str) -> None:
    """Read registrations without registry cleanup; every candidate must match."""
    expected_instance = os.environ.get('RQ_WEBHOOK_REDIS_RUN_ID', '')
    if not expected_instance or connection.info('server').get('run_id') != expected_instance:
        raise AdmissionError('webhook_unavailable', 503)
    covered = set()
    for worker_key in connection.smembers('rq:workers'):
        values = connection.hmget(worker_key, 'queues', 'webhook_configuration')
        if not values[0]:
            continue
        queues = set(values[0].decode().split(','))
        if not queues.intersection({'high', 'default', 'low', 'batch'}):
            continue
        try:
            configuration = json.loads(values[1]) if values[1] else {}
        except (ValueError, TypeError):
            configuration = {}
        if configuration != {'protocol': 'rq-wh-01', 'environment': identity}:
            raise AdmissionError('webhook_unavailable', 503)
        covered.update(queues)
    if not {'default', 'batch'}.issubset(covered):
        raise AdmissionError('webhook_unavailable', 503)


def response_error(exc: AdmissionError) -> JSONResponse:
    messages = {
        'invalid_webhook': 'Provide one valid HTTPS webhook_url and a 16–128 character Idempotency-Key.',
        'webhook_not_supported': 'This operation does not support callbacks.',
        'webhook_principal_unsupported': 'This credential has no supported stable callback identity.',
        'webhook_capacity_exceeded': 'Callback capacity is exhausted; retry later.',
        'webhook_unavailable': 'Callbacks are temporarily unavailable; no new operation was submitted.',
        'webhook_admission_unknown': 'Submission may be accepted; retry the same submission key.',
        'webhook_idempotency_conflict': 'The submission key is already bound to different input.',
        'webhook_admission_unavailable': 'Admission expired. Unknown publication requires operator reconciliation before new work.',
    }
    details = {'job_id': exc.job_id} if exc.job_id else None
    if exc.status == 410:
        details = {'job_id': exc.job_id, 'publication': exc.publication}
    response = error_response(messages[exc.code], status_code=exc.status, code=exc.code, details=details, log_exception=False)
    if exc.code in {'webhook_unavailable', 'webhook_capacity_exceeded'}:
        response.headers['Retry-After'] = '60'
    return response


class Submission:
    """Credential-free receipt bound before mutation; root publication is atomic."""
    def __init__(self, connection, *, options, claims, operation, resource, payload, principal=None):
        self.store = WebhookStore(connection, environment())
        verify_workers(connection, self.store.environment)
        self.connection = connection
        self.options = options
        self.redis_run_id = os.environ.get('RQ_WEBHOOK_REDIS_RUN_ID')
        self.publication_attempted = False
        self.prepublication_cleanup = None
        binding = {'type': 'culvert_batch'} if operation == 'culverts-wepp-batch' else resource
        digest = hashlib.sha256(encode([operation, binding, payload, options[0]]).encode()).hexdigest()
        self.created, self.root = self.store.reserve(
            principal=principal_key(claims, principal), key=options[1], digest=digest,
            operation=operation, resource=resource, url=options[0], job_id=new_rq_job_id(),
            redis_run_id=os.environ.get('RQ_WEBHOOK_REDIS_RUN_ID'))

    @property
    def job_id(self):
        return self.root['job_id']

    def replay(self) -> JSONResponse | None:
        if self.created:
            return None
        root = self.store.read(self.job_id)
        if root is None:
            raise AdmissionError('webhook_admission_unknown', 503, self.job_id)
        if root['state'] in {'admission_pending', 'admission_retryable'}:
            return JSONResponse({'job_id': self.job_id, 'webhook': {'status': 'admission_pending'}}, status_code=202)
        if root['state'] == 'admission_unavailable':
            raise AdmissionError('webhook_admission_unavailable', 410, self.job_id,
                                 publication=root.get('publication', 'unknown'))
        return JSONResponse(root['response'])

    def enqueue(self, queue, func, *, args, response: dict | None = None, **kwargs):
        webhook_hooks.install()
        response = dict(response or {'job_id': self.job_id})
        response['webhook'] = {'status': 'accepted'}
        try:
            # RQ 2.12 sets explicit MULTI while preparing enqueue commands.
            # Capture that buffered transaction without executing it, then commit
            # through a fresh WATCH pipeline. This preserves enqueue_call actor
            # hooks and reserves root membership before watching its revision.
            with self.connection.pipeline() as prepared:
                with webhook_hooks.admission(self.job_id, self.store.environment):
                    job = queue.enqueue_call(func, args=args, job_id=self.job_id, pipeline=prepared, **kwargs)
                self.store.published(self.job_id, response, pipeline=prepared)
                commands = list(prepared.command_stack)
                indexes = getattr(prepared, '_webhook_command_indexes', set()).copy()
            with self.connection.pipeline() as pipe:
                pipe.watch(self.store.root_key(self.job_id))
                raw = pipe.hget(self.store.root_key(self.job_id), 'data')
                root = json.loads(raw) if raw else None
                if (root is None or root['state'] != 'admission_pending'
                        or root['digest'] != self.root['digest']
                        or pipe.info('server').get('run_id') != self.redis_run_id
                        or pipe.hget(self.store.root_key(self.job_id), 'incomplete')):
                    raise AdmissionError('webhook_admission_unknown', 503, self.job_id)
                if time.time() >= root['created_at'] + webhook_policy.TRACKING_SECONDS:
                    raise AdmissionError('webhook_admission_unavailable', 410, self.job_id,
                                         publication=root.get('publication', 'unknown'))
                bounded_root({**root, 'state': 'tracking', 'publication': 'published', 'response': response},
                             int(pipe.hget(self.store.root_key(self.job_id), 'bytes')))
                pipe.multi()
                pipe.command_stack.extend(commands)
                pipe._webhook_command_indexes = indexes
                self.publication_attempted = True
                results = pipe.execute()
                if results[-1] != 1:
                    raise AdmissionError('webhook_admission_unknown', 503, self.job_id)
        except redis.RedisError:
            # Verify the notification publication receipt, not merely a job hash.
            # Do not issue a fresh operation or let postcommit errors delete inputs.
            try:
                root = self.store.read(self.job_id)
            except redis.RedisError:
                raise AdmissionError('webhook_admission_unknown', 503, self.job_id) from None
            if root is None or root['publication'] != 'published':
                raise AdmissionError('webhook_admission_unknown', 503, self.job_id) from None
            return self.job_id
        return job.id
