"""Stream claims, session boundary and ordinary/operation authority regressions."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from wepppy.microservices.rq_engine import stream_routes as stream
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.microservice
_CANONICAL_ACCESS = stream.sessions._session_user_authorized_for_run


@pytest.fixture
def harness(monkeypatch, tmp_path):
    key = tmp_path / 'signing'
    key.write_text('test-stream-key')
    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET_FILE', str(key))
    monkeypatch.delenv('WEPP_AUTH_JWT_SECRETS_FILE', raising=False)
    monkeypatch.delenv('WEPP_AUTH_JWT_SECRETS', raising=False)
    monkeypatch.setenv('WEPP_AUTH_JWT_DEFAULT_AUDIENCE', 'rq-engine')
    auth_tokens.get_jwt_config.cache_clear()
    monkeypatch.setattr(stream, '_restore_identity', lambda run: None)
    monkeypatch.setattr(stream, '_resolve_config', lambda run, config: 'test-project')
    monkeypatch.setattr(stream.sessions, '_session_user_authorized_for_run', lambda *args: True)
    monkeypatch.setattr(stream, 'require_workflow_access', lambda *args, **kw: None)
    markers = []
    monkeypatch.setattr(stream, '_store_marker', lambda run, sid: markers.append((run, sid)))
    app = FastAPI()
    app.include_router(stream.router, prefix='/api')
    with TestClient(app, base_url='https://testserver') as client:
        yield client, markers
    auth_tokens.get_jwt_config.cache_clear()


def post(client, payload=None, **kw):
    return client.post('/api/runs/example/cfg/stream-token',
                       json=payload or {'service': 'status'},
                       headers={'Origin': 'https://testserver', **kw})


def test_exact_service_claims_no_general_audience_or_cookie(harness):
    client, markers = harness
    response = post(client)
    assert response.status_code == 200
    body = response.json()
    claims = auth_tokens.decode_jwt(body['token'], secret='test-stream-key', algorithms=['HS256'],
                                    audience=['wepp-status'], issuer='weppcloud-stream')
    assert claims['aud'] == 'wepp-status'
    assert claims['scope'] == 'status:read'
    assert claims['config'] == 'test-project'
    assert claims['runid'] == 'example'
    assert claims['nbf'] == claims['iat']
    assert claims['exp'] - claims['iat'] == 300
    assert claims['session_id'] == claims['sub'] == markers[0][1]
    assert response.headers['cache-control'] == 'no-store'
    assert 'set-cookie' not in response.headers


@pytest.mark.parametrize('payload', [dict(service='other'), dict(service='status', extra=1),
                                      dict(service='preflight', job_id='job'), dict(service=['status'])])
def test_invalid_payload(harness, payload):
    assert post(harness[0], payload).status_code == 400


def test_private_denial_and_origin(harness, monkeypatch):
    client, markers = harness
    monkeypatch.setattr(stream.sessions, '_session_user_authorized_for_run', lambda *args: False)
    assert post(client).status_code == 403
    assert post(client, Origin='https://hostile.example').status_code == 403
    assert post(client, Authorization='Bearer invalid').status_code == 400
    assert markers == []


def test_invalid_cookie_never_public_fallback(harness, monkeypatch):
    def invalid(*args):
        raise stream.AuthError('Invalid session', status_code=401)
    monkeypatch.setattr(stream.sessions, '_resolve_session_from_cookie', invalid)
    assert post(harness[0], Cookie='session=invalid').status_code == 401
    assert harness[1] == []


@pytest.mark.parametrize('roles', [['Root'], ['Admin']])
def test_run_sync_current_privileged_role_and_bound_arguments(monkeypatch, roles):
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(stream.redis, 'Redis', lambda **kw: Conn())
    job = SimpleNamespace(func_name='wepppy.rq.run_sync_rq.run_sync_rq', origin='default',
                          args=('example', 'host', 'owner', 'root', 'cfg'))
    monkeypatch.setattr(stream.Job, 'fetch', lambda *args, **kw: job)
    assert stream._run_sync_config('job', 'example', 'cfg', roles) == 'cfg'
    for field, value in [('origin', 'other'), ('func_name', 'other')]:
        original = getattr(job, field)
        setattr(job, field, value)
        with pytest.raises(stream.AuthError):
            stream._run_sync_config('job', 'example', 'cfg', roles)
        setattr(job, field, original)
    with pytest.raises(stream.AuthError):
        stream._run_sync_config('job', 'other', 'cfg', roles)
    with pytest.raises(stream.AuthError):
        stream._run_sync_config('job', 'example', 'other', roles)
    with pytest.raises(stream.AuthError):
        stream._run_sync_config('job', 'example', 'cfg', ['User'])


def test_resolve_config_requires_real_identity_and_matches(monkeypatch, tmp_path):
    monkeypatch.setattr(stream.sessions, 'get_wd', lambda *args, **kw: str(tmp_path))
    with pytest.raises(stream.AuthError):
        stream._resolve_config('example', 'cfg')
    (tmp_path / 'ron.nodb').write_text('{}')
    monkeypatch.setattr(stream.Ron, 'load_detached', lambda *args: SimpleNamespace(config_stem='project'))
    assert stream._resolve_config('example', 'cfg') == 'project'
    assert stream._resolve_config('example', 'project') == 'project'
    with pytest.raises(stream.AuthError):
        stream._resolve_config('example', 'wrong')


@pytest.mark.integration
def test_atomic_marker_preserves_ttl_and_revocation_with_real_redis(monkeypatch):
    import redis
    import uuid
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    conn = redis.StrictRedis(**redis_connection_kwargs(RedisDB.SESSION))
    run, sid = 'stream-auth-test-' + uuid.uuid4().hex, uuid.uuid4().hex
    marker, fence = f'auth:session:run:{run}:{sid}', f'auth:session:revoked:{sid}'
    monkeypatch.setattr(stream.redis, 'Redis', redis.StrictRedis)
    try:
        stream._store_marker(run, sid)
        assert 298 <= conn.ttl(marker) <= 300
        conn.setex(marker, 10, '1')
        stream._store_marker(run, sid)
        assert 298 <= conn.ttl(marker) <= 300
        conn.setex(marker, 4 * 86400, '1')
        stream._store_marker(run, sid)
        assert conn.ttl(marker) > 3 * 86400
        conn.setex(fence, 300, '1')
        with pytest.raises(stream.AuthError):
            stream._store_marker(run, sid)
        conn.delete(marker)
        with pytest.raises(stream.AuthError):
            stream._store_marker(run, sid)
        assert not conn.exists(marker)
    finally:
        conn.delete(marker, fence)
        conn.close()


@pytest.mark.parametrize('public,owners,user,roles,expected', [
    (False, [7], 7, [], 200), (False, [7, 8], 8, [], 200),
    (False, [7], 9, [], 403), (False, [7], None, [], 403),
    (False, [7], 9, ['Admin'], 200), (False, [7], 9, ['Root'], 200),
    (True, [7], None, [], 200), (False, [], None, [], 200),
])
def test_canonical_run_policy_matrix(harness, monkeypatch, public, owners, user, roles, expected):
    monkeypatch.setattr(stream.sessions, '_session_user_authorized_for_run', _CANONICAL_ACCESS)
    monkeypatch.setattr(stream.sessions, '_run_is_public', lambda run: public)
    monkeypatch.setattr(stream.sessions, 'get_run_owners_lazy', lambda run: [SimpleNamespace(id=n) for n in owners])
    monkeypatch.setattr(stream.sessions, '_resolve_session_from_cookie', lambda request: ('sid', {}))
    monkeypatch.setattr(stream.sessions, '_identity_from_session_payload', lambda payload: (user, roles))
    monkeypatch.setattr(stream, '_check_session_revocation', lambda sid: None)
    headers = {'Cookie': 'session=fixture'} if user is not None else {}
    assert post(harness[0], **headers).status_code == expected


def test_revoked_cookie_denies_public_and_feature_gate_denies(harness, monkeypatch):
    monkeypatch.setattr(stream.sessions, '_resolve_session_from_cookie', lambda request: ('sid', {}))
    def deny(*args, **kwargs):
        raise stream.AuthError('Denied', status_code=403)
    monkeypatch.setattr(stream, '_check_session_revocation', deny)
    assert post(harness[0], Cookie='session=fixture').status_code == 403
    monkeypatch.setattr(stream, 'require_workflow_access', deny)
    assert post(harness[0]).status_code == 403
    assert harness[1] == []


def test_omni_uses_parent_owners(monkeypatch):
    seen = []
    monkeypatch.setattr(stream.sessions, '_run_is_public', lambda run: False)
    monkeypatch.setattr(stream.sessions, 'get_run_owners_lazy', lambda run: seen.append(run) or [SimpleNamespace(id=7)])
    assert _CANONICAL_ACCESS('example;;omni;;scenario', 7, [])
    assert seen == ['example']


def test_restore_identity_reads_bound_zip_during_missing_or_partial_ron(monkeypatch, tmp_path):
    import zipfile
    import json
    (tmp_path / 'archives').mkdir()
    target = tmp_path / 'archives' / 'example.zip'
    with zipfile.ZipFile(target, 'w') as archive:
        archive.writestr('ron.nodb', json.dumps({'py/object': 'wepppy.nodb.core.ron.Ron', 'py/state': {'_config': 'project.cfg?section:option=value'}}))
        archive.writestr('PUBLIC', '')
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def hget(self, *args): return 'restore-job'
    monkeypatch.setattr(stream.redis, 'Redis', lambda **kw: Conn())
    monkeypatch.setattr(stream.sessions, 'get_wd', lambda *args, **kw: str(tmp_path))
    job = SimpleNamespace(func_name='wepppy.rq.project_rq.restore_archive_rq', origin='fork-archive',
                          args=('example', 'example.zip'), get_status=lambda **kw: 'started')
    monkeypatch.setattr(stream.Job, 'fetch', lambda *args, **kw: job)
    assert stream._restore_identity('example') == ('project', True)
    (tmp_path / 'ron.nodb').write_text('{partial')
    assert stream._restore_identity('example') == ('project', True)
    job.args = ('other', 'example.zip')
    with pytest.raises(stream.AuthError):
        stream._restore_identity('example')


def test_missing_signing_file_is_redacted_unavailable(harness, monkeypatch, tmp_path, caplog):
    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET_FILE', str(tmp_path / 'missing'))
    auth_tokens.get_jwt_config.cache_clear()
    response = post(harness[0])
    assert response.status_code == 503
    assert str(tmp_path) not in response.text
    assert str(tmp_path) not in caplog.text


@pytest.mark.parametrize('child_bound', [False, True])
def test_restore_child_identity_uses_bound_archive_not_live_discovery(monkeypatch, tmp_path, child_bound):
    import json
    import zipfile
    child = 'example;;omni;;scenario'
    bound = child if child_bound else 'example'
    member = 'ron.nodb' if child_bound else '_pups/omni/scenarios/scenario/ron.nodb'
    (tmp_path / 'archives').mkdir()
    with zipfile.ZipFile(tmp_path / 'archives' / 'snapshot.zip', 'w') as archive:
        archive.writestr(member, json.dumps({'py/state': {'_config': 'project.cfg'}}))
        archive.writestr('PUBLIC', '')
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def hget(self, run, key): return 'restore-job' if run == bound else None
    monkeypatch.setattr(stream.redis, 'Redis', lambda **kw: Conn())
    def wd(run, **kwargs):
        assert run == bound  # A missing legacy child must never fall through to another root.
        return str(tmp_path)
    monkeypatch.setattr(stream.sessions, 'get_wd', wd)
    job = SimpleNamespace(func_name='wepppy.rq.project_rq.restore_archive_rq', origin='fork-archive',
                          args=(bound, 'snapshot.zip'), get_status=lambda **kw: 'started')
    monkeypatch.setattr(stream.Job, 'fetch', lambda *args, **kw: job)
    assert stream._restore_identity(child) == ('project', not child_bound)


def test_bridge_authorization_rejection_through_application_middleware(harness):
    from wepppy.microservices.rq_engine import app
    with TestClient(app, base_url='https://testserver') as client:
        assert post(client, Authorization='Bearer invalid').status_code == 400
