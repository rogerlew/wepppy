from types import SimpleNamespace

import pytest
from starlette.datastructures import FormData, Headers

from tests.rq.test_rq212_lifecycle import lifecycle
from wepppy.microservices.rq_engine.webhooks import (
    AdmissionError, Submission, principal_key, validate_option, verify_workers,
)

pytestmark = pytest.mark.microservice


@pytest.mark.parametrize('value', [None, '', [], ['https://example.com'], 123, 'http://example.com', 'https://example.com/\ud800'])
def test_malformed_optional_value_rejected(value):
    with pytest.raises(AdmissionError) as exc:
        validate_option({'webhook_url': value}, Headers({'Idempotency-Key': 'submission-key-123'}), operation='run-wepp')
    assert exc.value.code == 'invalid_webhook'


def test_absence_empty_namespace_and_duplicate_form_fields():
    assert validate_option({}, Headers(), operation='unrelated') is None
    with pytest.raises(AdmissionError):
        validate_option(FormData([('webhook_url', 'https://example.com'), ('webhook_url', 'https://example.com')]),
                        Headers({'Idempotency-Key': 'submission-key-123'}), operation='run-wepp')
    with pytest.raises(AdmissionError) as exc:
        validate_option({'webhook_url': 'https://example.com'}, Headers({'Idempotency-Key': 'submission-key-123'}), operation='other')
    assert exc.value.code == 'webhook_not_supported'


def test_principal_namespace_rotation_and_issuer_isolation():
    human = SimpleNamespace(kind='human', user_id=12)
    claims = {'iss': 'issuer-one', 'token_class': 'user', 'sub': '12', 'jti': 'one'}
    first = principal_key(claims, human)
    assert principal_key({**claims, 'jti': 'two'}, human) == first
    assert principal_key({**claims, 'iss': 'issuer-two'}, human) != first
    anonymous = SimpleNamespace(kind='anonymous', user_id=None)
    assert principal_key({'iss': 'issuer-one', 'token_class': 'session', 'session_id': '12'}, anonymous) != first
    with pytest.raises(AdmissionError):
        principal_key({'iss': 'issuer-one', 'token_class': 'service', 'sub': '12'}, anonymous)


@pytest.mark.integration
def test_real_receipt_submission_and_mixed_worker_gate(lifecycle, monkeypatch):
    connection = lifecycle.connection
    identity = lifecycle.prefix
    monkeypatch.setenv('RQ_WEBHOOK_ENVIRONMENT', identity)
    monkeypatch.setenv('RQ_WEBHOOK_ADMISSION', 'enabled')
    monkeypatch.setenv('RQ_WEBHOOK_INSTRUMENTATION', 'rq-wh-01')
    monkeypatch.setenv('RQ_WEBHOOK_REDIS_RUN_ID', connection.info('server')['run_id'])
    with pytest.raises(AdmissionError):
        verify_workers(connection, identity)
    import json
    worker_key = 'rq:worker:' + identity
    connection.sadd('rq:workers', worker_key)
    connection.hset(worker_key, mapping={'queues': 'default,batch',
                                        'webhook_configuration': json.dumps({'protocol': 'rq-wh-01', 'environment': identity})})
    human = SimpleNamespace(kind='human', user_id=12)
    options = ('https://example.com/private', 'submission-key-123')
    kwargs = dict(options=options, claims={'iss': 'issuer', 'token_class': 'user'}, principal=human,
                  operation='run-wepp', resource={'type': 'run', 'id': 'test'}, payload={})
    first = Submission(connection, **kwargs)
    assert first.replay() is None
    second = Submission(connection, **kwargs)
    assert second.job_id == first.job_id and second.replay().status_code == 202
    first.enqueue(lifecycle.queue, json.loads, args=('1',))
    replay = second.replay()
    assert replay.status_code == 200 and json.loads(replay.body)['job_id'] == first.job_id
    assert lifecycle.queue.count == 1
    connection.hdel(worker_key, 'webhook_configuration')
    with pytest.raises(AdmissionError):
        verify_workers(connection, identity)


def test_submission_boundary_recovers_prepublication_cancel(tmp_path):
    import asyncio
    from starlette.requests import Request
    from wepppy.microservices.rq_engine.webhooks import submission_boundary
    calls = []
    staging = tmp_path / 'owned-staging'
    staging.mkdir()
    request = Request({'type': 'http', 'headers': []})
    callback = SimpleNamespace(created=True, publication_attempted=False, job_id='root',
                               prepublication_cleanup=lambda: staging.rmdir(),
                               store=SimpleNamespace(prepublication_failed=lambda job: calls.append(job)))
    request.state.webhook_submission = callback

    @submission_boundary
    async def route(request):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(route(request))
    assert calls == ['root'] and not staging.exists()


@pytest.mark.integration
def test_restore_between_reservation_and_publication_never_enqueues(lifecycle, monkeypatch):
    import json
    from wepppy.microservices.rq_engine import webhooks
    identity = lifecycle.prefix
    monkeypatch.setenv('RQ_WEBHOOK_ENVIRONMENT', identity)
    monkeypatch.setenv('RQ_WEBHOOK_ADMISSION', 'enabled')
    monkeypatch.setenv('RQ_WEBHOOK_INSTRUMENTATION', 'rq-wh-01')
    monkeypatch.setenv('RQ_WEBHOOK_REDIS_RUN_ID', lifecycle.connection.info('server')['run_id'])
    monkeypatch.setattr(webhooks, 'verify_workers', lambda *args: None)
    submission = Submission(lifecycle.connection, options=('https://example.com', 'submission-key-123'),
                            claims={'iss': 'issuer', 'token_class': 'user'},
                            principal=SimpleNamespace(kind='human', user_id=12), operation='run-wepp',
                            resource={'type': 'run', 'id': 'test'}, payload={})
    lifecycle.connection.unlink(submission.store.root_key(submission.job_id))
    with pytest.raises(AdmissionError):
        submission.enqueue(lifecycle.queue, json.loads, args=('1',))
    assert lifecycle.queue.count == 0
    assert not lifecycle.connection.exists('rq:job:' + submission.job_id)


@pytest.mark.integration
def test_culvert_api_replay_recovers_browse_mint_without_second_enqueue(lifecycle, monkeypatch, tmp_path):
    import json
    from fastapi.testclient import TestClient
    import wepppy.microservices.rq_engine as rq_engine
    from wepppy.microservices.rq_engine import culvert_routes, webhooks
    from tests.microservices.test_rq_engine_culverts import _auth_headers, _resolve_payload_zip
    identity = lifecycle.prefix
    monkeypatch.setenv('CULVERTS_ROOT', str(tmp_path / 'culverts'))
    monkeypatch.setenv('RQ_WEBHOOK_ENVIRONMENT', identity)
    monkeypatch.setenv('RQ_WEBHOOK_ADMISSION', 'enabled')
    monkeypatch.setenv('RQ_WEBHOOK_INSTRUMENTATION', 'rq-wh-01')
    monkeypatch.setenv('RQ_WEBHOOK_REDIS_RUN_ID', lifecycle.connection.info('server')['run_id'])
    monkeypatch.setattr(webhooks, 'verify_workers', lambda *args: None)
    monkeypatch.setattr(culvert_routes.redis, 'Redis', type(lifecycle.connection))
    monkeypatch.setattr(culvert_routes, 'redis_connection_kwargs', lambda *args: {
        'unix_socket_path': lifecycle.connection.connection_pool.connection_kwargs['path'], 'db': 2})
    monkeypatch.setattr(culvert_routes, 'require_feature_access', lambda *args: SimpleNamespace(kind='human', user_id=12))
    def enqueue(batch_uuid, *, callback):
        return callback.enqueue(lifecycle.queue, json.loads, args=('1',), response={
            'job_id': callback.job_id, 'culvert_batch_uuid': batch_uuid,
            'status_url': '/rq-engine/api/jobstatus/' + callback.job_id})
    monkeypatch.setattr(culvert_routes, '_enqueue_culvert_batch_job', enqueue)
    mint_calls = []
    def mint(*args, **kwargs):
        mint_calls.append(1)
        if len(mint_calls) == 1:
            raise RuntimeError('Controlled issuer outage')
        return {'token': 'fresh-browse-credential', 'claims': {'exp': 123}}
    monkeypatch.setattr(culvert_routes, '_mint_culvert_browse_token', mint)
    monkeypatch.setenv('WEPP_AUTH_JWT_ISSUER', 'webhook-test-issuer')
    headers = {**_auth_headers(monkeypatch), 'Idempotency-Key': 'culvert-request-123'}
    archive = _resolve_payload_zip().read_bytes()
    with TestClient(rq_engine.app) as client:
        def submit():
            return client.post('/api/culverts-wepp-batch/', headers=headers,
                files={'payload.zip': ('payload.zip', archive, 'application/zip')},
                data={'webhook_url': 'https://example.com/private-capability'})
        first = submit()
        assert first.status_code == 202, first.text
        second = submit()
        assert second.status_code == 200, second.text
    assert first.json()['job_id'] == second.json()['job_id']
    assert second.json()['browse_token'] == 'fresh-browse-credential'
    assert lifecycle.queue.count == 1
    from wepppy.rq.webhook_tracking import WebhookStore
    stored = WebhookStore(lifecycle.connection, identity).read(first.json()['job_id'])
    assert 'credential' not in json.dumps(stored['response'])


def test_culvert_postcommit_receipt_read_failure_preserves_same_key_recovery(monkeypatch):
    import json
    import redis
    from contextlib import nullcontext
    from wepppy.microservices.rq_engine import culvert_routes
    def unavailable(_):
        raise redis.ConnectionError('Injected receipt read failure')
    callback = SimpleNamespace(job_id='accepted-root', store=SimpleNamespace(read=unavailable))
    monkeypatch.setattr(culvert_routes.redis, 'Redis', lambda **kwargs: nullcontext(object()))
    response = culvert_routes._callback_browse_response(callback, {}, None)
    assert response.status_code == 503
    body = json.loads(response.body)
    assert len(body.pop('error_id')) == 32
    assert body == {'error': {
        'message': 'Submission may be accepted; retry the same submission key.',
        'code': 'webhook_admission_unknown', 'details': {'job_id': 'accepted-root'}}}


def test_replay_racing_prepublication_failure_remains_pending():
    import json
    root = {'job_id': 'planned-root', 'state': 'admission_retryable', 'response': {}}
    submission = object.__new__(Submission)
    submission.created = False
    submission.root = root
    submission.store = SimpleNamespace(read=lambda _: root)
    response = submission.replay()
    assert response.status_code == 202
    assert json.loads(response.body) == {'job_id': 'planned-root', 'webhook': {'status': 'admission_pending'}}
