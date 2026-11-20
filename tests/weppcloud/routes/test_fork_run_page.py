from __future__ import annotations

from types import SimpleNamespace

import pytest
import redis
from flask import Flask, g
from flask_login import LoginManager, UserMixin
from jinja2 import ChoiceLoader, DictLoader
from rq.job import Job, JobStatus
from rq.results import Result

from tests.rq.test_rq212_lifecycle import lifecycle
from wepppy.microservices.rq_engine import auth
from wepppy.weppcloud.routes.fork_console.fork_console import fork_bp
from wepppy.weppcloud.routes.rq.job_dashboard.routes import rq_job_dashboard_bp
from wepppy.weppcloud.routes.run_0 import fork_status
from wepppy.weppcloud.utils import feature_access_identity, helpers, query_cookie
from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal

pytestmark = pytest.mark.integration
TARGET = 'ab-fork'
SOURCE = 'ab-source'
PAGE = f'/runs/{TARGET}/cfg/'


class Viewer(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

    def has_role(self, _role):
        return False


@pytest.fixture
def fork_page(lifecycle, monkeypatch, tmp_path):
    from importlib import import_module

    page = import_module('wepppy.weppcloud.routes.run_0.run_0_bp')
    app_module = import_module('wepppy.weppcloud.app')
    conn = lifecycle.connection

    def redis_client(**_kwargs):
        return redis.StrictRedis(connection_pool=conn.connection_pool)

    monkeypatch.setattr(auth, '_AUTH_REDIS_CLIENT', redis_client)
    monkeypatch.setattr(fork_status.redis, 'Redis', redis_client)
    root = tmp_path / 'runs'
    source = root / 'ab' / SOURCE
    source.mkdir(parents=True)
    target = root / 'ab' / TARGET
    monkeypatch.setattr(helpers, 'PRIMARY_RUNS_ROOT', str(root))
    monkeypatch.setattr(helpers, 'LEGACY_RUNS_ROOT', str(tmp_path / 'legacy'))
    monkeypatch.setattr(helpers, 'redis_wd_cache_client', None)
    monkeypatch.setattr(helpers, '_PLAYBACK_USE_CLONE', False)

    owner = Viewer(42)
    source_owner = Viewer(43)
    owners = {TARGET: [owner], SOURCE: [owner]}
    monkeypatch.setattr(app_module, 'get_run_owners', lambda runid: owners[runid])
    monkeypatch.setattr(feature_access_identity, 'account_principal',
                        lambda user_id, **_kw: VerifiedPrincipal('human', user_id))

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='fork-page-test')
    LoginManager(app).user_loader(lambda _user_id: None)
    app.register_blueprint(page.run_0_bp)
    app.register_blueprint(fork_bp)
    app.register_blueprint(rq_job_dashboard_bp)
    app.after_request(query_cookie.set_page_query_cookie)
    app.jinja_loader = ChoiceLoader([DictLoader({
        'base_pure.htm': '{% block body_container %}{% endblock %}',
        'browse/not_found.htm': 'Project not found',
        'runs0_pure.htm': 'Project settings{% if fork_status %}{% include "_fork_run_notice.htm" %}{% endif %}',
    }), app.jinja_loader])
    app.jinja_env.globals['site_prefix'] = ''
    viewer = {'current': owner}

    @app.before_request
    def _owner_context():
        g._login_user = viewer['current']

    monkeypatch.setattr(page, '_build_runs0_context', lambda *_args: {})
    monkeypatch.setattr(page, '_resolve_session_id_from_request', lambda: 'test-sid')
    monkeypatch.setattr(page, '_store_session_marker', lambda *_args: None)
    monkeypatch.setattr(query_cookie.auth_tokens, 'issue_token', lambda *_a, **_k: {'token': 'test-jwt'})

    def receipt(state, *, pointer='fork-root', failed=''):
        conn.set(f'rq:fork:destination:{TARGET}', pointer)
        conn.hset(f'rq:fork:planned:{TARGET}', mapping={
            'job_id': 'fork-root', 'source_runid': SOURCE, 'target_runid': TARGET,
            'state': state, 'failed_job_id': failed,
        })

    def job(job_id, function, args, status, *, origin='default', meta=None, result=None):
        rq_job = Job.create(function, connection=conn, id=job_id, args=args, origin=origin, meta=meta)
        rq_job.set_status(status)
        rq_job.save()
        if result is not None:
            Result.create(rq_job, Result.Type.SUCCESSFUL, 60, return_value=result)
        return rq_job

    def core_files():
        target.mkdir(exist_ok=True)
        for filename in fork_status._PAGE_FILES:
            (target / filename).write_text('{}')

    yield SimpleNamespace(
        client=app.test_client(), page=page, viewer=viewer, owners=owners, source_owner=source_owner,
        target=target, receipt=receipt, job=job, core_files=core_files,
    )
    conn.delete(f'rq:fork:destination:{TARGET}', f'rq:fork:planned:{TARGET}')
    for job_id in ('fork-root', 'leaf', 'simulation'):
        conn.delete(Job.key_for(job_id), Result.get_key(job_id))


def _root(fork_page, status=JobStatus.FINISHED, **kwargs):
    return fork_page.job('fork-root', fork_status._FORK_FUNCTION, (SOURCE, TARGET, True),
                         status, origin='fork-archive', **kwargs)


@pytest.mark.parametrize('destination', ['missing', 'symlink', 'copy-active'])
def test_incomplete_fork_renders_status_without_resolving_cookie(fork_page, monkeypatch, destination):
    fork_page.receipt('running')
    _root(fork_page, JobStatus.STARTED if destination == 'copy-active' else JobStatus.FINISHED)
    if destination != 'missing':
        fork_page.core_files()
    if destination == 'symlink':
        ron = fork_page.target / 'ron.nodb'
        ron.unlink()
        ron.symlink_to(fork_page.target / 'wepp.nodb')

    def unexpected(*_args, **_kwargs):
        pytest.fail('Status-only page must skip NoDb hydration and cookie target resolution')

    monkeypatch.setattr(fork_page.page, '_build_runs0_context', unexpected)
    monkeypatch.setattr(query_cookie, 'resolve_target', unexpected)
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert response.cache_control.no_store and response.cache_control.private
    assert b'This project is still being prepared.' in response.data
    assert b'/rq/job-dashboard/fork-root' in response.data
    assert 'Set-Cookie' not in response.headers


def test_failed_postprocessing_keeps_authorized_project_readable(fork_page):
    fork_page.receipt('failed', failed='leaf')
    fork_page.core_files()
    _root(fork_page, meta={'jobs:0': 'leaf', 'jobs:1': 'simulation'})
    fork_page.job('leaf', fork_status._WEPP_FUNCTION_PREFIX + '_analyze_return_periods_rq',
                  (TARGET,), JobStatus.FAILED)
    fork_page.job('simulation', fork_status._WEPP_FUNCTION_PREFIX + 'run_watershed_rq',
                  (TARGET,), JobStatus.FINISHED, result=(True, 1))

    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert response.cache_control.no_store
    assert b'Project settings' in response.data
    assert b'The project was copied, but postprocessing failed.' in response.data
    assert b'Return-period reports could not be generated.' in response.data
    assert b'The WEPP simulation finished.' in response.data
    assert b'/rq/job-dashboard/fork-root' in response.data
    assert 'Set-Cookie' not in response.headers

    fork_page.receipt('succeeded')
    ready = fork_page.client.get(f'{PAGE}?skip_migration_check=true')
    assert ready.status_code == 200
    assert ready.data == b'Project settings'
    assert query_cookie.query_cookie_name(TARGET, 'cfg') in ready.headers['Set-Cookie']


def test_source_link_requires_independent_visibility(fork_page):
    fork_page.receipt('failed')
    fork_page.core_files()
    _root(fork_page)
    fork_page.owners[SOURCE] = [fork_page.source_owner]
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert b'Project preparation failed.' in response.data
    assert b'Project settings' in response.data
    assert b'fork-root' not in response.data
    assert SOURCE.encode() not in response.data


@pytest.mark.parametrize('pointer', ['fork-root', 'foreign-root'])
def test_ownerless_destination_cannot_reveal_private_source(fork_page, pointer):
    fork_page.receipt('running', pointer=pointer)
    fork_page.owners[TARGET] = []
    fork_page.owners[SOURCE] = [fork_page.source_owner]
    response = fork_page.client.get(PAGE)
    assert response.status_code == 404
    assert b'fork-root' not in response.data
    assert SOURCE.encode() not in response.data


def test_replacement_discards_rendered_project(fork_page, monkeypatch):
    fork_page.receipt('failed')
    fork_page.core_files()
    _root(fork_page)

    def replace_receipt(*_args):
        fork_page.receipt('running', pointer='replacement')
        return {}

    monkeypatch.setattr(fork_page.page, '_build_runs0_context', replace_receipt)
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert b'Project preparation changed.' in response.data
    assert b'Project settings' not in response.data
    assert b'fork-root' not in response.data
    assert 'Set-Cookie' not in response.headers


def test_unusable_pup_and_protected_roads_selection_show_status(fork_page, monkeypatch):
    fork_page.receipt('failed')
    _root(fork_page)
    fork_page.core_files()
    pup = fork_page.target / '_pups' / 'selected'
    pup.mkdir(parents=True)
    (pup / 'ron.nodb').symlink_to(fork_page.target / 'ron.nodb')

    def unexpected(*_args):
        pytest.fail('A protected alternate root or results scope must stay status-only')

    monkeypatch.setattr(fork_page.page, '_build_runs0_context', unexpected)
    for suffix in ('?pup=selected', '?output_scope=roads'):
        response = fork_page.client.get(PAGE + suffix)
        assert response.status_code == 200
        assert b'Project preparation failed.' in response.data
        assert 'Set-Cookie' not in response.headers


def test_wrong_record_type_shows_generic_status_only_to_owner(fork_page, lifecycle):
    lifecycle.connection.set(f'rq:fork:planned:{TARGET}', 'invalid-type')
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert b'Project preparation status is unavailable.' in response.data
    fork_page.owners[TARGET] = []
    assert fork_page.client.get(PAGE).status_code == 404


def test_stopped_root_has_terminal_status_even_if_receipt_is_running(fork_page):
    fork_page.receipt('running')
    _root(fork_page, JobStatus.STOPPED)
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert b'Project preparation failed.' in response.data
    assert b'This project is still being prepared.' not in response.data


def test_reservation_during_normal_render_discards_redirect(fork_page, monkeypatch):
    fork_page.core_files()

    def create_reservation(*_args):
        fork_page.receipt('running')
        return {'redirect': '/url-from-stale-project/'}

    monkeypatch.setattr(fork_page.page, '_build_runs0_context', create_reservation)
    response = fork_page.client.get(f'{PAGE}?skip_migration_check=true')
    assert response.status_code == 200
    assert b'Project preparation changed.' in response.data
    assert 'Location' not in response.headers
    assert 'Set-Cookie' not in response.headers


def test_new_owner_is_rechecked_after_observing_reservation(fork_page, monkeypatch):
    from importlib import import_module
    from itertools import count

    app_module = import_module('wepppy.weppcloud.app')
    lookups = count()
    fork_page.receipt('running')

    def owners(runid):
        if runid == TARGET:
            return [] if next(lookups) == 0 else [fork_page.source_owner]
        return fork_page.owners[runid]

    monkeypatch.setattr(app_module, 'get_run_owners', owners)
    response = fork_page.client.get(PAGE)
    # The run blueprint intentionally returns a non-disclosing 404 for 403.
    assert response.status_code == 404
    assert b'This project is still being prepared.' not in response.data


def test_completed_legacy_pointer_keeps_normal_project_entry(fork_page, lifecycle):
    fork_page.core_files()
    _root(fork_page)
    lifecycle.connection.set(f'rq:fork:destination:{TARGET}', 'fork-root')
    response = fork_page.client.get(f'{PAGE}?skip_migration_check=true')
    assert response.status_code == 200
    assert response.data == b'Project settings'
    assert 'Set-Cookie' in response.headers


def test_failed_receipt_without_retained_root_stays_status_only(fork_page, monkeypatch):
    fork_page.receipt('failed', failed='prior-child')
    fork_page.core_files()
    monkeypatch.setattr(fork_page.page, '_build_runs0_context',
                        lambda *_args: pytest.fail('A child ID alone cannot prove the current copy'))
    response = fork_page.client.get(PAGE)
    assert response.status_code == 200
    assert b'Project preparation failed.' in response.data
    assert b'View fork details' not in response.data
    assert 'Set-Cookie' not in response.headers
