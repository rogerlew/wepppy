"""Real authorization, real saved bundles and bounded report transport."""
from types import SimpleNamespace
import re

import pytest

pytest.importorskip('flask')
from flask import Flask, g
from flask_login import LoginManager, UserMixin

from wepppy.nodb.mods.postfire_debris_flow import report
from wepppy.weppcloud.routes.nodb_api import postfire_report_bp as routes
from tests.nodb.mods.test_postfire_debris_flow_report import saved, IDENTITY

pytestmark = pytest.mark.routes
ROOT = '/runs/fixture/config'
QUERY = ROOT + '/query/postfire_debris_flow/'


@pytest.fixture
def client(saved, monkeypatch):
    root, _, _ = saved
    from wepppy.weppcloud import app as app_module
    from wepppy.weppcloud.utils import helpers
    class User(UserMixin):
        id = '123'
        def has_role(self, role):
            return False
    owner = User()
    policy = dict(owners=[owner], public=False, user=owner)
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='testing-only', SITE_PREFIX='/weppcloud')
    login = LoginManager(app)
    login.user_loader(lambda identity: owner)
    @app.before_request
    def identity():
        g._login_user = policy['user']
    app.register_blueprint(routes.postfire_report_bp)
    app.add_url_rule('/runs/<runid>/<config>/', endpoint='run_0.runs0', view_func=lambda **kw: '')
    monkeypatch.setattr(app_module, 'get_run_owners', lambda runid: policy['owners'])
    monkeypatch.setattr(helpers, 'get_wd', lambda *a, **kw: str(root))
    monkeypatch.setattr(routes.Ron, 'ispublic', lambda wd: policy['public'])
    monkeypatch.setattr(routes, 'load_run_context', lambda *a, **kw: SimpleNamespace(active_root=root))
    # Do not replace authorize: every transport exercises the shared owner/public rules.
    with app.test_client() as value:
        yield value, root, policy


def test_query_exact_payload_and_prefix(client):
    client, root, _ = client
    response = client.get(QUERY, query_string=dict(attempt_id=IDENTITY, limit=1))
    assert response.status_code == 200, response.data
    assert response.headers['Cache-Control'] == 'no-store'
    payload = response.get_json()
    assert set(payload) == {'schema_version', 'status', 'attempt_id', 'summary', 'design', 'inverse', 'events', 'query', 'urls', 'response_curve'}
    assert len(payload['events']['rows']) == 1
    assert payload['events']['total'] == payload['events']['unfiltered_total'] == 3
    assert all(url.startswith('/weppcloud/runs/') for key, url in payload['urls'].items() if key != 'artifacts')
    assert str(root) not in response.text


@pytest.mark.parametrize('parameters', [dict(duration_minutes=16), dict(duration_minutes='15.0'),
    dict(limit=1001), dict(offset=200001), dict(sort='date'), dict(descending='1'),
    dict(min_probability='nan'), dict(min_probability='1.1'), dict(year='1.5'),
    dict(sql='SELECT'), dict(attempt_id='A' * 32), dict(attempt_id='')])
def test_malformed_query_is_sanitized(client, parameters):
    client, _, _ = client
    response = client.get(QUERY, query_string={'attempt_id': IDENTITY, **parameters})
    assert response.status_code == 400
    assert response.get_json() == {'error': {'code': 'invalid_input', 'message': 'Invalid report request.'}}
    assert response.headers['Cache-Control'] == 'no-store'


def test_repeated_unknown_and_optional_blank_filters(client):
    client, _, _ = client
    repeated = client.get(QUERY, query_string=[('attempt_id', IDENTITY), ('limit', '1'), ('limit', '2')])
    assert repeated.status_code == 400
    response = client.get(QUERY, query_string=dict(attempt_id=IDENTITY, year='', min_probability=''))
    assert response.status_code == 200
    assert response.json['query']['year'] is None
    assert client.post(QUERY).status_code == 405


def test_detail_not_found_and_replacement(client):
    client, _, _ = client
    payload = client.get(QUERY, query_string=dict(attempt_id=IDENTITY)).json
    event_id = payload['events']['rows'][0]['event_id']
    detail = client.get(QUERY + 'event', query_string=dict(attempt_id=IDENTITY, event_id=event_id))
    assert detail.status_code == 200 and len(detail.json['rows']) == 3
    assert client.get(QUERY + 'event', query_string=dict(attempt_id=IDENTITY, event_id='0' * 64 + ':0')).status_code == 404
    replaced = client.get(QUERY, query_string=dict(attempt_id='e' * 32))
    assert replaced.status_code == 409 and replaced.json['error']['code'] == 'assessment_replaced'


@pytest.mark.parametrize('path', [QUERY, QUERY + 'event', ROOT + '/report/postfire_debris_flow/',
    ROOT + '/report/postfire_debris_flow/files/manifest.json'])
def test_real_authorization_denies_every_private_transport_repeatedly(client, path):
    client, _, policy = client
    policy['owners'] = [object()]
    for _ in range(2):
        response = client.get(path, query_string=dict(attempt_id=IDENTITY))
        assert response.status_code == 403
        assert response.headers['Cache-Control'] == 'no-store'
        assert 'snapshot' not in response.text and IDENTITY not in response.text


@pytest.mark.parametrize('policy_key,value', [('public', True), ('owners', [])])
def test_real_public_and_ownerless_rules_allow_reads(client, policy_key, value):
    client, _, policy = client
    policy['owners'] = [object()]
    policy[policy_key] = value
    assert client.get(QUERY, query_string=dict(attempt_id=IDENTITY)).status_code == 200


def test_download_and_close_on_early_disconnect(client, monkeypatch):
    client, root, _ = client
    actual = report.open_attachment
    opened = []
    def capture(*args):
        stream = actual(*args)
        opened.append(stream)
        return stream
    monkeypatch.setattr(report, 'open_attachment', capture)
    response = client.get(ROOT + '/report/postfire_debris_flow/files/events.parquet',
                          query_string=dict(attempt_id=IDENTITY), buffered=False)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'attachment' in response.headers['Content-Disposition']
    response.close()
    assert opened[-1].closed
    bad = client.get(ROOT + '/report/postfire_debris_flow/files/secret', query_string=dict(attempt_id=IDENTITY))
    assert bad.status_code == 404


def test_unexpected_and_infrastructure_failures_are_sanitized(client, monkeypatch):
    client, _, _ = client
    def broken(*args, **kwargs):
        raise RuntimeError('/private/path token=secret')
    monkeypatch.setattr(routes, 'authorize', broken)
    response = client.get(QUERY)
    assert response.status_code == 500
    assert '/private' not in response.text and 'secret' not in response.text
    assert response.headers['Cache-Control'] == 'no-store'
    def outage(*args, **kwargs):
        raise ConnectionError('private connection details')
    monkeypatch.setattr(routes, 'authorize', outage)
    assert client.get(QUERY).status_code == 503


def test_missing_shell_state_never_creates_files_and_has_readable_reload(client):
    client, root, _ = client
    assert not (root / 'unitizer.nodb').exists()
    response = client.get(ROOT + '/report/postfire_debris_flow/')
    assert response.status_code == 503 and 'Reload report' in response.text
    assert not (root / 'unitizer.nodb').exists()


def test_pup_query_key_and_urls_are_preserved(client, monkeypatch):
    client, _, _ = client
    actual = routes._context
    def context(*args):
        wd = actual(*args)
        g.pup_relpath = 'retained'
        return wd
    monkeypatch.setattr(routes, '_context', context)
    response = client.get(QUERY, query_string=dict(attempt_id=IDENTITY, pup='retained'))
    assert response.status_code == 200
    assert 'pup=retained' in response.json['urls']['query']
    assert all('pup=retained' in url for url in response.json['urls']['artifacts'].values())


def test_rendered_report_inheritance_suppresses_only_postfire_passive_unitizer_bootstrap():
    from tests.weppcloud.routes.test_pure_controls_render import jinja_env

    # Reuse the shared shell fixture, rendering the real parent, child and includes.
    # This is deliberately not a source-text or replaced-parent-template assertion.
    environment = jinja_env.__wrapped__()
    context = dict(unitizer_nodb=SimpleNamespace(is_english=True, preferences={'precipitation': 'in'}),
                   precisions={'precipitation': {'mm': 2, 'in': 2}},
                   postfire_report_seed={**report.view(None), 'urls': {}}, postfire_report_error=None)
    ordinary = environment.get_template('reports/_base_report.htm').render(**context)
    postfire = environment.get_template('reports/postfire_debris_flow/report.htm').render(**context)
    initial_call = r'\btriggerUnitChange\(\);'
    assert len(re.findall(initial_call, ordinary)) == 1
    assert not re.search(initial_call, postfire)
    for rendered in (ordinary, postfire):
        # Keep the Project instance, explicit unit-change method and modal hooks.
        assert 'window.Project.getInstance()' in rendered
        assert 'project.unitChangeEvent();' in rendered
        assert 'function triggerUnitChange()' in rendered
        assert 'id="unitizerModal"' in rendered
        assert 'data-project-unitizer="global"' in rendered
        assert 'data-project-unitizer="category"' in rendered
        assert re.search(r'value="in"\s+checked', rendered)
    assert 'id="postfire-report-seed"' in postfire
    assert 'data-pfr-field="duration"' in postfire
    assert '<option value="15" selected>15 minutes</option>' in postfire
