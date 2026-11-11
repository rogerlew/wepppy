"""Real path/JWT boundary regressions for QE-AUTH-F1-20261110."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def boundary(monkeypatch, tmp_path):
    from wepppy.weppcloud.utils import helpers
    from wepppy.query_engine.app import server
    root = tmp_path / 'runs'
    run = root / 'ab' / 'ab-private'
    run.mkdir(parents=True)
    monkeypatch.setattr(helpers, 'PRIMARY_RUNS_ROOT', str(root))
    monkeypatch.setattr(helpers, 'LEGACY_RUNS_ROOT', str(tmp_path / 'legacy'))
    monkeypatch.setattr(helpers, 'redis_wd_cache_client', None)
    monkeypatch.setattr(helpers, '_PLAYBACK_USE_CLONE', False)
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', lambda runid: [SimpleNamespace(id=42)])
    from wepppy.query_engine import context as context_module
    original_context = context_module.resolve_run_context
    calls = []
    def context(*args, **kwargs):
        calls.append('catalog')
        return original_context(*args, **kwargs)
    monkeypatch.setattr(context_module, 'resolve_run_context', context)
    monkeypatch.setattr(server, 'activate_query_engine', lambda *a, **kw: calls.append('activate') or {})
    return TestClient(server.create_app(), raise_server_exceptions=False), run, calls


@pytest.mark.parametrize('suffix,method', [('', 'GET'), ('/schema', 'GET'), ('/query', 'GET'), ('/query', 'POST'), ('/activate', 'POST')])
@pytest.mark.parametrize('slash', ['', '/'])
@pytest.mark.parametrize('populated', [False, True])
def test_private_denial_precedes_catalog_and_logs(boundary, suffix, method, slash, populated):
    client, run, calls = boundary
    if populated:
        (run / '_query_engine').mkdir()
        (run / '_query_engine/catalog.json').write_text('catalog sentinel')
        (run / 'exceptions.log').write_text('log sentinel')
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    response = client.request(method, '/runs/ab-private/cfg' + suffix + slash, json={})
    assert response.status_code == 401
    assert calls == []
    assert {str(p.relative_to(run)): p.read_bytes() for p in run.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('method', ['GET', 'HEAD'])
def test_activation_is_post_only(boundary, method):
    client, _, calls = boundary
    assert client.request(method, '/runs/ab-private/cfg/activate').status_code == 405
    assert calls == []


@pytest.mark.parametrize('target', ['ab-private', 'ab-private/cfg/extra', '/tmp/cfg', 'ab-private/%5c', 'ab-private/%00', 'unknown;;group;;leaf/cfg'])
def test_malformed_targets_fail_before_catalog(boundary, target):
    client, _, calls = boundary
    response = client.get('/runs/' + target + '/schema')
    assert response.status_code == 400
    assert calls == []


def test_filesystem_route_cannot_select_existing_directory(boundary):
    client, run, calls = boundary
    response = client.get('/runs/' + str(run) + '/schema')
    assert response.status_code == 400
    assert calls == []


@pytest.fixture
def signed_token(monkeypatch):
    from wepppy.weppcloud.utils import auth_tokens
    import uuid
    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET', 'query-boundary-test-secret-not-production')
    auth_tokens.get_jwt_config.cache_clear()
    def issue(*, runid='ab-private', audience='query-engine', scopes=None, token_class='service', **claims):
        return auth_tokens.issue_token('42', audience=audience,
            scopes=scopes if scopes is not None else ['runs:read', 'queries:execute'],
            runs=[runid], extra_claims={'token_class': token_class, 'jti': uuid.uuid4().hex, 'runid': runid, **claims})['token']
    yield issue
    auth_tokens.get_jwt_config.cache_clear()


def _dataset(run):
    import pyarrow as pa
    import pyarrow.parquet as pq
    directory = run / 'data'
    directory.mkdir(exist_ok=True)
    pq.write_table(pa.table({'value': [3, 7]}), directory / 'sample.parquet')


def test_bound_service_query_creates_and_consumes_real_catalog(boundary, signed_token):
    client, run, _ = boundary
    _dataset(run)
    response = client.post('/runs/ab-private/cfg/query',
        headers={'Authorization': 'Bearer ' + signed_token()},
        json={'datasets': ['data/sample.parquet']})
    assert response.status_code == 200, response.text
    assert response.json()['records'] == [{'value': 3}, {'value': 7}]
    import json
    catalog = json.loads((run / '_query_engine/catalog.json').read_text())
    assert any(entry['path'] == 'data/sample.parquet' for entry in catalog['files'])


@pytest.mark.parametrize('kwargs,status', [({'audience': 'rq-engine'},401),
    ({'runid': 'other-run'},403), ({'scopes': ['runs:read']},403),
    ({'token_class': 'mcp'},403)])
def test_signed_credentials_fail_closed_without_side_effects(boundary, signed_token, kwargs, status):
    client, run, calls = boundary
    response = client.post('/runs/ab-private/cfg/query',
        headers={'Authorization': 'Bearer ' + signed_token(**kwargs)}, json={})
    assert response.status_code == status, response.text
    assert calls == []
    assert not (run / '_query_engine').exists()
    assert not (run / 'exceptions.log').exists()


def test_public_anonymous_read_and_invalid_bearer_precedence(boundary):
    client, run, _ = boundary
    (run / 'PUBLIC').touch()
    _dataset(run)
    response = client.post('/runs/ab-private/cfg/query', json={'datasets': ['data/sample.parquet']})
    assert response.status_code == 200, response.text
    response = client.get('/runs/ab-private/cfg/schema', headers={'Authorization': 'Bearer invalid'})
    assert response.status_code == 401


@pytest.mark.parametrize('origin,status', [('https://site.test', 200), ('https://evil.test',403),
    ('null',403), ('https://site.test:8443',403)])
def test_exact_origins(boundary, monkeypatch, origin, status):
    client, run, _ = boundary
    monkeypatch.setenv('QUERY_ENGINE_ALLOWED_ORIGINS', 'https://site.test')
    (run / 'PUBLIC').touch()
    response = client.get('/runs/ab-private/cfg/schema', headers={'Origin': origin})
    assert response.status_code == status, response.text


def test_scenario_symlink_never_activates_foreign_run(boundary, signed_token, tmp_path):
    client, run, _ = boundary
    foreign = tmp_path / 'foreign'
    foreign.mkdir()
    scenarios = run / '_pups/omni/scenarios'
    scenarios.mkdir(parents=True)
    (scenarios / 'escape').symlink_to(foreign, target_is_directory=True)
    response = client.post('/runs/ab-private/cfg/query',
        headers={'Authorization': 'Bearer ' + signed_token()},
        json={'scenario': 'escape', 'datasets': ['x.parquet']})
    assert response.status_code == 404, response.text
    assert list(foreign.iterdir()) == []


def test_poisoned_cache_never_probes_foreign_target(boundary, monkeypatch, tmp_path):
    from wepppy.weppcloud.utils import helpers
    from wepppy.query_engine.app.helpers import resolve_target
    _, run, _ = boundary
    sibling = run.parent / 'ab-sibling'
    sibling.mkdir()
    monkeypatch.setattr(helpers, 'redis_wd_cache_client', SimpleNamespace(get=lambda key: str(sibling)))
    with pytest.raises(FileNotFoundError):
        resolve_target('ab-private', 'cfg')


def test_symlinked_run_to_same_mount_sibling_is_rejected(boundary):
    from wepppy.query_engine.app.helpers import resolve_target
    _, run, _ = boundary
    sibling = run.parent / 'ab-sibling'
    run.rename(sibling)
    run.symlink_to(sibling, target_is_directory=True)
    with pytest.raises(FileNotFoundError):
        resolve_target('ab-private', 'cfg')


def test_omni_resolution_does_not_create_links_and_mcp_accepts_bare_id(boundary):
    from wepppy.query_engine.app.helpers import resolve_target, resolve_run_path
    _, run, _ = boundary
    (run / 'climate').mkdir()
    child = run / '_pups/omni/scenarios/test'
    child.mkdir(parents=True)
    target = resolve_target('ab-private;;omni;;test', 'cfg')
    assert target.parent_path == run
    assert target.path == child
    assert not (child / 'climate').exists()
    assert resolve_run_path('ab-private') == run


@pytest.mark.parametrize('form,env,relative', [
    ('batch;;group;;_base','BATCH_RUNNER_ROOT','group/_base'),
    ('batch;;group;;child','BATCH_RUNNER_ROOT','group/runs/child'),
    ('batch;;omni;;child','BATCH_RUNNER_ROOT','omni/runs/child'),
    ('batch;;omni-contrast;;child','BATCH_RUNNER_ROOT','omni-contrast/runs/child'),
    ('culvert;;group;;child','CULVERTS_ROOT','group/runs/child'),
    ('profile;;tmp;;child','PROFILE_PLAYBACK_RUN_ROOT','child'),
    ('profile;;fork;;child','PROFILE_PLAYBACK_FORK_ROOT','child'),
    ('profile;;archive;;child','PROFILE_PLAYBACK_ARCHIVE_ROOT','child'),
    ('batch;;group;;child;;omni-contrast;;3','BATCH_RUNNER_ROOT','group/runs/child/_pups/omni/contrasts/3'),
])
def test_composite_layouts_are_real_and_pure(boundary, monkeypatch, tmp_path, form, env, relative):
    from wepppy.query_engine.app.helpers import resolve_target
    root = tmp_path / env
    expected = root / relative
    expected.mkdir(parents=True)
    monkeypatch.setenv(env, str(root))
    assert resolve_target(form, 'cfg').path == expected


def test_legacy_and_playback_layouts(boundary, monkeypatch, tmp_path):
    from wepppy.query_engine.app.helpers import resolve_target
    from wepppy.weppcloud.utils import helpers
    legacy = tmp_path / 'legacy/old-run'
    legacy.mkdir(parents=True)
    assert resolve_target('old-run', 'cfg').path == legacy
    clone = tmp_path / 'playback/old-run'
    clone.mkdir(parents=True)
    monkeypatch.setattr(helpers, '_PLAYBACK_USE_CLONE', True)
    monkeypatch.setenv('PROFILE_PLAYBACK_RUN_ROOT', str(clone.parent))
    assert resolve_target('old-run', 'cfg').path == clone


@pytest.fixture
def session_state(monkeypatch, signed_token):
    import redis
    from wepppy.microservices.rq_engine import auth
    from wepppy.weppcloud.utils import feature_access_identity
    from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
    stores, hashes = {}, {}
    original = redis.Redis
    class SharedRedis(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.store = stores.setdefault(kwargs.get('db', 0), {})
            self.hashes = hashes.setdefault(kwargs.get('db', 0), {})
        def setex(self, key, ttl, value):
            return self.set(key, value)
    monkeypatch.setattr(redis, 'Redis', SharedRedis)
    monkeypatch.setattr(auth, '_AUTH_REDIS_CLIENT', SharedRedis)
    monkeypatch.setattr(feature_access_identity, 'account_principal',
        lambda user_id, **kw: VerifiedPrincipal('human', user_id) if user_id else VerifiedPrincipal())
    return stores, hashes


def _mark_session(resource='ab-private', sid='boundary-session'):
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    redis.Redis(**redis_connection_kwargs(RedisDB.SESSION)).set(f'auth:session:run:{resource}:{sid}', '1')


def _session_cookie(client, issue, *, resource='ab-private', config='cfg', **kwargs):
    from wepppy.weppcloud.utils.browse_cookie import query_cookie_name
    token = issue(runid=resource, token_class='session', session_id='boundary-session',
                  config=config, feature_access_principal={'version': 1, 'kind': 'human', 'id': 42}, **kwargs)
    client.cookies.set(query_cookie_name(resource, config), token)
    return token


def test_owner_cookie_and_current_owner_removal(boundary, signed_token, session_state, monkeypatch):
    from wepppy.weppcloud.utils import helpers
    client, run, _ = boundary
    _dataset(run)
    _mark_session()
    _session_cookie(client, signed_token)
    response = client.post('/runs/ab-private/cfg/query', headers={'Sec-Fetch-Site':'same-origin'},
                           json={'datasets':['data/sample.parquet']})
    assert response.status_code == 200, response.text
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', lambda _: [SimpleNamespace(id=99)])
    assert client.get('/runs/ab-private/cfg/schema').status_code == 403


def test_parent_cookie_reaches_omni_child(boundary, signed_token, session_state):
    client, run, _ = boundary
    child = run / '_pups/omni/contrasts/1'
    child.mkdir(parents=True)
    _dataset(child)
    _mark_session()
    _session_cookie(client, signed_token)
    response = client.post('/runs/ab-private;;omni-contrast;;1/cfg/query',
        headers={'Sec-Fetch-Site':'same-origin'}, json={'datasets':['data/sample.parquet']})
    assert response.status_code == 200, response.text


def test_service_cannot_gain_activation_by_cookie_transport(boundary, signed_token):
    from wepppy.weppcloud.utils.browse_cookie import query_cookie_name
    client, _, calls = boundary
    token = signed_token(config='cfg')
    client.cookies.set(query_cookie_name('ab-private','cfg'), token)
    response = client.post('/runs/ab-private/cfg/activate', headers={'Sec-Fetch-Site':'same-origin'})
    assert response.status_code == 403
    assert calls == []


@pytest.mark.parametrize('public', [False, True])
def test_revoked_cookie_uses_anonymous_read_policy(boundary, signed_token, session_state, public):
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    from wepppy.weppcloud.utils import auth_tokens
    client, run, _ = boundary
    _mark_session()
    token = _session_cookie(client, signed_token)
    claims = auth_tokens.decode_token(token, audience='query-engine')
    redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)).set('auth:jwt:revoked:' + claims['jti'], '1')
    if public:
        (run / 'PUBLIC').touch()
    assert client.get('/runs/ab-private/cfg/schema').status_code == (200 if public else 401)
    assert client.get('/runs/ab-private/cfg/schema', headers={'Authorization':'Bearer '+token}).status_code == 401


def test_fork_preparation_blocks_ownerless_admission(boundary, session_state, monkeypatch):
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    from wepppy.weppcloud.utils import helpers
    client, run, calls = boundary
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', lambda _: [])
    (run / 'ron.nodb').write_text('{"py/object":"wepppy.nodb.core.ron.Ron"}')
    redis.Redis(**redis_connection_kwargs(RedisDB.RQ)).hset('rq:fork:planned:ab-private', 'state', 'running')
    response = client.get('/runs/ab-private/cfg/schema')
    assert response.status_code == 409, response.text
    assert calls == []
    assert not (run / '_query_engine').exists()


def test_culvert_public_marker_does_not_admit_anonymous(boundary, monkeypatch, tmp_path):
    client, _, calls = boundary
    root = tmp_path / 'culverts'
    run = root / 'batch/runs/leaf'
    run.mkdir(parents=True)
    (run / 'PUBLIC').touch()
    monkeypatch.setenv('CULVERTS_ROOT', str(root))
    response = client.get('/runs/culvert;;batch;;leaf/cfg/schema')
    assert response.status_code == 401, response.text
    assert calls == []
    assert not (run / '_query_engine').exists()


def test_denied_sibling_source_has_no_schema_reads_or_writes(boundary, signed_token, monkeypatch):
    import pyarrow.parquet as pq
    client, run, _ = boundary
    sibling = run / '_pups/omni/scenarios/sibling'
    child = run / '_pups/omni/scenarios/child'
    sibling.mkdir(parents=True)
    child.mkdir(parents=True)
    _dataset(sibling)
    (child / 'landuse').mkdir()
    (child / 'landuse/landuse.parquet').symlink_to(sibling / 'data/sample.parquet')
    reads = []
    original = pq.read_schema
    def read_schema(path, *args, **kwargs):
        reads.append(str(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(pq, 'read_schema', read_schema)
    before = sorted(str(p.relative_to(run)) for p in run.rglob('*'))
    response = client.get('/runs/ab-private;;omni;;child/cfg/schema', headers={'Authorization':'Bearer '+signed_token()})
    assert response.status_code == 403, response.text
    assert reads == []
    assert sorted(str(p.relative_to(run)) for p in run.rglob('*')) == before


def test_existing_catalog_sibling_source_denied_before_read(boundary, signed_token, monkeypatch):
    import json
    import pyarrow.parquet as pq
    client, run, _ = boundary
    child = run / '_pups/omni/scenarios/child'
    sibling = run / '_pups/omni/scenarios/sibling'
    child.mkdir(parents=True)
    sibling.mkdir(parents=True)
    _dataset(sibling)
    catalog_dir = child / '_query_engine'
    catalog_dir.mkdir()
    catalog = {'root':str(child),'version':1,'files':[{'path':'secret.parquet',
        'fs_path':str(sibling/'data/sample.parquet'),'extension':'.parquet','size_bytes':0,'modified':'2026-01-01'}]}
    file = catalog_dir/'catalog.json'
    file.write_text(json.dumps(catalog))
    before = file.read_bytes()
    monkeypatch.setattr(pq, 'read_schema', lambda *a,**k: pytest.fail('foreign schema read'))
    response = client.post('/runs/ab-private;;omni;;child/cfg/query', headers={'Authorization':'Bearer '+signed_token()},json={'datasets':['secret.parquet']})
    assert response.status_code == 403, response.text
    assert file.read_bytes() == before
    assert list(catalog_dir.iterdir()) == [file]


def test_generated_contrast_metadata_links_and_external_dem_preserved(boundary, signed_token, tmp_path):
    client, run, _ = boundary
    child = run / '_pups/omni/contrasts/1'
    child.mkdir(parents=True)
    _dataset(child)
    for name in ['dem.nodb','climate.nodb','watershed.nodb','landuse.nodb','soils.nodb','unitizer.nodb','treatments.nodb']:
        (run/name).write_text('{}')
        (child/name).symlink_to(run/name)
    (run/'wepp/runs').mkdir(parents=True)
    (run/'wepp/runs/h1.slp').write_text('input')
    (child/'wepp/runs').mkdir(parents=True)
    (child/'wepp/runs/h1.slp').symlink_to(run/'wepp/runs/h1.slp')
    (child/'dem').mkdir()
    external = tmp_path/'external.tif'
    external.write_bytes(b'not a query dataset')
    (child/'dem/dem.tif').symlink_to(external)
    response = client.post('/runs/ab-private;;omni-contrast;;1/cfg/query',
        headers={'Authorization':'Bearer '+signed_token()},json={'datasets':['data/sample.parquet']})
    assert response.status_code == 200, response.text


def test_exception_log_symlink_does_not_modify_canary(boundary, tmp_path):
    from wepppy.query_engine.app.server import _log_exception_details
    from wepppy.query_engine.app.helpers import resolve_target
    _, run, _ = boundary
    canary = tmp_path/'canary'
    canary.write_text('unchanged')
    (run/'exceptions.log').symlink_to(canary)
    _log_exception_details('sensitive diagnostic', resolve_target('ab-private','cfg'))
    assert canary.read_text() == 'unchanged'


def test_auth_store_failure_is_bounded_and_never_logs_to_run(boundary, monkeypatch):
    from wepppy.weppcloud.utils import helpers
    client, run, _ = boundary
    def unavailable(_):
        raise RuntimeError('private-db-host-and-secret-path')
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', unavailable)
    response = client.get('/runs/ab-private/cfg/schema')
    assert response.status_code == 503
    assert 'private-db' not in response.text and 'stacktrace' not in response.text
    assert not (run/'exceptions.log').exists()
    assert not (run/'_query_engine').exists()


def test_scoped_relocated_parent_input_uses_only_current_root(tmp_path):
    from wepppy.query_engine.access_scope import access_scope, current_scope
    parent = tmp_path/'new'
    child = parent/'_pups/omni/scenarios/child'
    child.mkdir(parents=True)
    current = parent/'soils/a.parquet'
    with access_scope(child,parent,lambda:None):
        selected = current_scope().source_path(Path('/old/soils/a.parquet'), '/old/_pups/omni/scenarios/child')
        assert selected == current


def test_flask_issues_separate_httponly_query_credential(boundary, signed_token, session_state, monkeypatch):
    from flask import Flask, Response
    from http.cookies import SimpleCookie
    from wepppy.weppcloud.utils import query_cookie, auth_tokens
    import importlib
    bridge = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")
    from wepppy.weppcloud.utils.browse_cookie import query_cookie_name
    monkeypatch.setattr(query_cookie, 'current_user', SimpleNamespace(is_authenticated=True, is_active=True, id=42))
    monkeypatch.setattr(bridge, '_resolve_session_id_from_request', lambda: 'boundary-session')
    app = Flask(__name__)
    with app.test_request_context('/runs/ab-private/cfg/', base_url='https://site.test'):
        response = query_cookie.set_query_cookie(Response('page'), 'ab-private', 'cfg')
    cookie = SimpleCookie()
    cookie.load(response.headers['Set-Cookie'])
    credential = cookie[query_cookie_name('ab-private','cfg')]
    assert credential['httponly'] and credential['secure']
    assert credential['path'] == '/query-engine/runs/'
    assert credential['samesite'].lower() == 'lax'
    claims = auth_tokens.decode_token(credential.value,audience='query-engine')
    assert claims['scope'] == 'runs:read queries:execute'
    assert claims['runid'] == 'ab-private' and claims['config'] == 'cfg'
    assert claims['token_class'] == 'session'
    assert credential.value not in response.get_data(as_text=True)
    client, run, _ = boundary
    _dataset(run)
    client.cookies.set(query_cookie_name('ab-private','cfg'),credential.value)
    assert client.post('/runs/ab-private/cfg/query',headers={'Sec-Fetch-Site':'same-origin'},
                       json={'datasets':['data/sample.parquet']}).status_code == 200


def test_full_http_relocated_catalog_parent_input(boundary, signed_token):
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    client, run, _ = boundary
    child = run/'_pups/omni/scenarios/child'
    (child/'_query_engine').mkdir(parents=True)
    (run/'soils').mkdir()
    pq.write_table(pa.table({'value':[11]}),run/'soils/a.parquet')
    (child/'_query_engine/catalog.json').write_text(json.dumps({'version':1,
        'root':'/old/_pups/omni/scenarios/child','files':[{
        'path':'soils/a.parquet','fs_path':'/old/soils/a.parquet','extension':'.parquet',
        'size_bytes':0,'modified':'2026-01-01','schema':{'fields':[{'name':'value','type':'int64'}]}}]}))
    response=client.post('/runs/ab-private;;omni;;child/cfg/query',
        headers={'Authorization':'Bearer '+signed_token()},json={'datasets':['soils/a.parquet']})
    assert response.status_code == 200,response.text
    assert response.json()['records'] == [{'value':11}]


@pytest.mark.parametrize('transport', ['bearer','cookie'])
def test_authenticated_force_activation_writes_real_catalog(boundary, signed_token, session_state, monkeypatch, transport):
    from wepppy.query_engine.app import server
    from wepppy.query_engine.activate import activate_query_engine
    monkeypatch.setattr(server,'activate_query_engine',activate_query_engine)
    client,run,_=boundary
    _dataset(run)
    if transport == 'bearer':
        headers={'Authorization':'Bearer '+signed_token(scopes=['runs:read','runs:activate'])}
    else:
        _mark_session()
        _session_cookie(client,signed_token)
        headers={'Sec-Fetch-Site':'same-origin'}
    response=client.post('/runs/ab-private/cfg/activate',headers=headers)
    assert response.status_code==200,response.text
    assert (run/'_query_engine/catalog.json').is_file()


@pytest.mark.parametrize('headers',[{}, {'Origin':'https://evil.test'}, {'Sec-Fetch-Site':'cross-site'}])
def test_cookie_activation_origin_denial_preserves_tree(boundary,signed_token,session_state,headers):
    client,run,calls=boundary
    _mark_session()
    _session_cookie(client,signed_token)
    before=sorted(run.rglob('*'))
    response=client.post('/runs/ab-private/cfg/activate',headers=headers)
    assert response.status_code==403,response.text
    assert sorted(run.rglob('*'))==before and calls==[]


def test_child_credential_cannot_read_parent_or_sibling(boundary,signed_token):
    client,run,_=boundary
    for leaf in ['one','two']:
        (run/f'_pups/omni/contrasts/{leaf}').mkdir(parents=True)
    headers={'Authorization':'Bearer '+signed_token(runid='ab-private;;omni-contrast;;one')}
    assert client.get('/runs/ab-private/cfg/schema',headers=headers).status_code==403
    assert client.get('/runs/ab-private;;omni-contrast;;two/cfg/schema',headers=headers).status_code==403
    assert not (run/'_query_engine').exists()


def test_batch_base_cookie_alias_and_current_membership(boundary,signed_token,session_state,monkeypatch,tmp_path):
    from wepppy.weppcloud.utils import feature_access_runtime
    client,_,_=boundary
    root=tmp_path/'batch'
    base=root/'team/_base'
    child=root/'team/runs/child'
    base.mkdir(parents=True)
    child.mkdir(parents=True)
    monkeypatch.setenv('BATCH_RUNNER_ROOT',str(root))
    allowed=[True]
    class Store:
        def membership(self,*args,**kwargs):
            return allowed[0],allowed[0]
    monkeypatch.setattr(feature_access_runtime,'feature_store',Store)
    _mark_session('batch;;team;;_base')
    _session_cookie(client,signed_token,resource='batch;;team;;_base')
    response=client.get('/runs/batch;;team;;child/cfg/schema')
    assert response.status_code==200,response.text
    allowed[0]=False
    assert client.get('/runs/batch;;team;;child/cfg/schema').status_code==403


def test_culvert_bound_integration_can_query(boundary,signed_token,session_state,monkeypatch,tmp_path):
    client,_,_=boundary
    root=tmp_path/'culvert'
    child=root/'team/runs/child'
    child.mkdir(parents=True)
    _dataset(child)
    monkeypatch.setenv('CULVERTS_ROOT',str(root))
    token=signed_token(runid='team',feature_access_principal={'version':1,'kind':'integration','id':'culvert-web-app'})
    response=client.post('/runs/culvert;;team;;child/cfg/query',headers={'Authorization':'Bearer '+token},
                         json={'datasets':['data/sample.parquet']})
    assert response.status_code==200,response.text


def test_console_recheck_denial_is_not_swallowed(boundary,signed_token,session_state,monkeypatch):
    from wepppy.weppcloud.utils import helpers
    client,run,_=boundary
    _mark_session()
    _session_cookie(client,signed_token)
    lookups=[]
    def owners(_):
        lookups.append(1)
        return [SimpleNamespace(id=42 if len(lookups)==1 else 99)]
    monkeypatch.setattr(helpers,'get_run_owners_lazy',owners)
    response=client.get('/runs/ab-private/cfg/query')
    assert response.status_code==403,response.text
    assert not (run/'_query_engine').exists()


def test_cached_query_does_not_walk_entire_tree(boundary,signed_token,monkeypatch):
    from wepppy.query_engine.access_scope import AccessScope
    client,run,_=boundary
    _dataset(run)
    headers={'Authorization':'Bearer '+signed_token()}
    payload={'datasets':['data/sample.parquet']}
    assert client.post('/runs/ab-private/cfg/query',headers=headers,json=payload).status_code==200
    monkeypatch.setattr(AccessScope,'before_scan',lambda *a:pytest.fail('cached query rescanned full tree'))
    assert client.post('/runs/ab-private/cfg/query',headers=headers,json=payload).status_code==200


@pytest.mark.parametrize('populated', [False, True])
def test_recheck_backend_failure_is_bounded(boundary, signed_token, monkeypatch, populated):
    from wepppy.weppcloud.utils import helpers
    client, run, _ = boundary
    _dataset(run)
    if populated:
        assert client.get('/runs/ab-private/cfg/schema', headers={
            'Authorization': 'Bearer ' + signed_token()}).status_code == 200
        (run/'exceptions.log').write_text('existing log')
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    calls = []
    def owners(_):
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError('REVIEW_SENTINEL_AUTH_BACKEND')
        return [SimpleNamespace(id=42)]
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', owners)
    response = client.get('/runs/ab-private/cfg/schema', headers={
        'Authorization': 'Bearer ' + signed_token()})
    assert response.status_code == 503, response.text
    assert 'REVIEW_SENTINEL' not in response.text and 'stacktrace' not in response.text
    assert before == {str(p.relative_to(run)): p.read_bytes() for p in run.rglob('*') if p.is_file()}


def test_pending_refresh_preserves_external_dem_and_parent_archives(boundary, signed_token, tmp_path, monkeypatch):
    from wepppy.query_engine import catalog_refresh as refresh
    client, parent, _ = boundary
    child = parent/'_pups/omni/scenarios/child'
    child.mkdir(parents=True)
    _dataset(child)
    external = tmp_path/'external.tif'
    external.write_bytes(b'not opened by catalog scanner')
    (child/'dem').mkdir()
    (child/'dem/dem.tif').symlink_to(external)
    for name in ('climate.nodir', 'watershed.nodir'):
        (parent/name).write_bytes(b'archive sentinel')
        (child/name).symlink_to(parent/name)
    import json
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([{
        'path': str(parent.parent.parent), 'namespace': 'boundary-refresh',
        'coordination': str(tmp_path/'coordination'), 'layout': 'sharded'}]))
    monkeypatch.setenv('QUERY_CATALOG_REFRESH_ENABLED', 'false')
    endpoint = '/runs/ab-private;;omni;;child/cfg/query'
    headers = {'Authorization': 'Bearer ' + signed_token()}
    payload = {'datasets': ['data/sample.parquet']}
    assert client.post(endpoint, headers=headers, json=payload).status_code == 200
    refresh.record_catalog_refresh(child, None)
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()['records'] == [{'value': 3}, {'value': 7}]
    assert not refresh.pending_catalog_requests(child)


@pytest.mark.parametrize('role', ['Admin', 'Root', 'PortlandGroup'])
def test_current_roles_and_pcv_membership(boundary, signed_token, session_state, monkeypatch, role):
    from wepppy.weppcloud.utils import feature_access_identity, portland_collections
    from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
    client, run, _ = boundary
    _dataset(run)
    monkeypatch.setattr(feature_access_identity, 'account_principal',
        lambda *a, **k: VerifiedPrincipal('human', 99, frozenset({role})))
    monkeypatch.setattr(portland_collections, 'portland_runids', lambda: {'ab-private'})
    headers = {'Authorization': 'Bearer ' + signed_token(token_class='user', scopes=[
        'runs:read', 'queries:execute', 'runs:activate'])}
    assert client.get('/runs/ab-private/cfg/schema', headers=headers).status_code == 200
    if role == 'PortlandGroup':
        assert client.post('/runs/ab-private/cfg/activate', headers=headers).status_code == 403
        monkeypatch.setattr(portland_collections, 'portland_runids', lambda: set())
        assert client.get('/runs/ab-private/cfg/schema', headers=headers).status_code == 403
    else:
        monkeypatch.setattr(feature_access_identity, 'account_principal',
            lambda *a, **k: VerifiedPrincipal('human', 99))
        assert client.get('/runs/ab-private/cfg/schema', headers=headers).status_code == 403


def test_profile_authenticated_read(boundary, signed_token, monkeypatch, tmp_path):
    from wepppy.weppcloud.utils import helpers
    root = tmp_path/'profile'
    run = root/'child'
    run.mkdir(parents=True)
    _dataset(run)
    monkeypatch.setenv('PROFILE_PLAYBACK_RUN_ROOT', str(root))
    client, _, _ = boundary
    endpoint = '/runs/profile;;tmp;;child/cfg/schema'
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint, headers={'Authorization': 'Bearer ' + signed_token(
        runid='profile;;tmp;;child')}).status_code == 200


@pytest.mark.parametrize('valid', [True, False])
def test_ownerless_metadata_is_required_without_creating_state(boundary, monkeypatch, valid):
    import jsonpickle
    from wepppy.nodb.core import Ron
    from wepppy.weppcloud.utils import helpers
    client, run, _ = boundary
    monkeypatch.setattr(helpers, 'get_run_owners_lazy', lambda _: [])
    ron = object.__new__(Ron)
    ron.__dict__.update(wd=str(run), _name='Ownerless fixture', _scenario='')
    (run/'ron.nodb').write_text(jsonpickle.encode(ron) if valid else '{}')
    _dataset(run)
    response = client.get('/runs/ab-private/cfg/schema')
    assert response.status_code == (200 if valid else 404), response.text
    assert not (run/'VERSION').exists()
    assert not (run/'exceptions.log').exists()
