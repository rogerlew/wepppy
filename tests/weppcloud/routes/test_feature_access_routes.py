"""FA-01 real PostgreSQL, Flask-Security sessions and CSRF transport tests."""
import importlib
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from flask import Flask, jsonify
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_security.utils import login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

from wepppy.weppcloud.configuration import _build_postgres_uri
from wepppy.weppcloud.feature_registry import load_feature_registry
from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal, FeatureResourceContext, evaluate_feature_access
from wepppy.weppcloud.utils.feature_access_schema import feature_access_tables, memberships, events, acceptances
from wepppy.weppcloud.utils.feature_access_store import FeatureAccessStore
from wepppy.weppcloud.utils.feature_access_web import INTERNAL_STATEMENT_VERSION

pytestmark = [pytest.mark.routes, pytest.mark.integration]
URI = _build_postgres_uri()
TEMPLATES = Path(__file__).resolve().parents[3] / 'wepppy/weppcloud/templates'
ADMIN_URL = '/admin/feature-access/memberships'
ACK_URL = '/profile/internal-access/acknowledge'
FEATURES = load_feature_registry()


@pytest.fixture
def access_client(monkeypatch):
    schema = 'feature_access_routes_' + uuid4().hex
    admin_engine = sa.create_engine(URI, hide_parameters=True)
    with admin_engine.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    app = Flask(__name__, template_folder=str(TEMPLATES))
    app.config.update(TESTING=True, SECRET_KEY=uuid4().hex, SECURITY_PASSWORD_SALT=uuid4().hex,
                      SQLALCHEMY_DATABASE_URI=URI, SECURITY_TRACKABLE=False,
                      SQLALCHEMY_ENGINE_OPTIONS={'connect_args': {'options': '-csearch_path=' + schema}},
                      SECURITY_UNAUTHORIZED_VIEW=None, SECURITY_CHANGEABLE=True, SECURITY_SEND_PASSWORD_CHANGE_EMAIL=False)
    db = SQLAlchemy(app)
    association = db.Table('roles_users', db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                           db.Column('role_id', db.Integer, db.ForeignKey('role.id')))

    class Role(db.Model, RoleMixin):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String, unique=True)
        description = db.Column(db.String)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String, unique=True)
        active = db.Column(db.Boolean, default=True)
        password = db.Column(db.String)
        fs_uniquifier = db.Column(db.String, unique=True, nullable=False)
        roles = db.relationship(Role, secondary=association)

    class OAuthAccount(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        user = db.relationship(User, backref=db.backref('oauth_accounts', lazy='dynamic'))

    feature_access_tables(db.metadata)
    datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, datastore)

    @app.get('/test-login/<int:user_id>')
    def test_login(user_id):
        logout_user()
        login_user(db.session.get(User, user_id))
        db.session.commit()
        return 'ok'

    @app.get('/test-csrf')
    def csrf():
        return generate_csrf()

    @app.get('/', endpoint='weppcloud_site.index')
    def home():
        return 'home'

    @app.get('/diagnostics', endpoint='weppcloud_site.diagnostics')
    def diagnostics():
        return 'diagnostics'

    @app.login_manager.unauthorized_handler
    def unauthorized():
        return 'unauthorized', 401

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify(error={'code': 'forbidden', 'message': 'forbidden'}), 403

    @app.errorhandler(CSRFError)
    def csrf_error(exc):
        return jsonify(error={'code': 'csrf_failed', 'message': exc.description}), 400

    app.jinja_env.globals.update(static_url=lambda path: '/static/' + path,
                                usersum_doc_link=lambda *args: args[-1])
    module = importlib.import_module('wepppy.weppcloud.app')
    monkeypatch.setattr(module, 'User', User)
    app.register_blueprint(importlib.import_module('wepppy.weppcloud.routes.admin').admin_bp)
    app.register_blueprint(importlib.import_module('wepppy.weppcloud.routes.user').user_bp)
    CSRFProtect(app)
    with app.app_context():
        db.create_all()
        role = datastore.create_role(name='Root')
        for n in [1, 2, 3]:
            datastore.create_user(id=n, email='rogerlew@gmail.com' if n == 1 else f'user{n}@example.test',
                                  fs_uniquifier=uuid4().hex, roles=[role] if n == 1 else [])
        db.session.commit()
        engine = db.engine
        store = FeatureAccessStore(engine)
        store.seed_groups(FEATURES)
    try:
        yield app, app.test_client(), engine, store
    finally:
        with app.app_context():
            db.session.remove()
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin_engine.dispose()


def login(fixture, user_id=1):
    assert fixture[1].get(f'/test-login/{user_id}').status_code == 200


def post(fixture, url=ADMIN_URL, payload=None, *, csrf=True, content_type='application/json'):
    token = fixture[1].get('/test-csrf').text if csrf else 'forged'
    return fixture[1].post(url, json=payload, headers={'X-CSRFToken': token}, content_type=content_type)


def grant(**extra):
    return dict(operation='add', user_id=2, group_key='openet_ts', reason='Approved limited collaboration', **extra)


def counts(fixture):
    with fixture[2].connect() as connection:
        return tuple(connection.scalar(sa.select(sa.func.count()).select_from(t)) for t in (memberships, events, acceptances))


def decision(fixture):
    return evaluate_feature_access(
        VerifiedPrincipal(kind='human', user_id=2), next(f for f in FEATURES if f.id == 'openet_ts'), 'act',
        FeatureResourceContext(existing_access_allowed=True, backend='wepp',
                               internal_statement_version=INTERNAL_STATEMENT_VERSION), fixture[3],
    )


def test_grant_ack_remove_real_transport_and_admission(access_client):
    login(access_client)
    assert access_client[1].get('/admin/feature-access').status_code == 200
    assert not decision(access_client).allowed
    response = post(access_client, payload=grant())
    assert response.status_code == 200
    assert response.json['result'] == dict(user_id=2, group_key='openet_ts', member=True, changed=True)
    assert post(access_client, payload=grant()).json['result']['changed'] is False
    assert not decision(access_client).allowed
    login(access_client, 2)
    profile = access_client[1].get('/profile')
    assert profile.status_code == 200
    assert 'actions await acknowledgment' in profile.text
    assert 'Approved limited collaboration' not in profile.text
    payload = dict(accepts_training=True, statement_version=INTERNAL_STATEMENT_VERSION)
    assert post(access_client, ACK_URL, payload).json['result']['changed'] is True
    assert post(access_client, ACK_URL, payload).json['result']['changed'] is False
    assert decision(access_client).allowed
    login(access_client)
    assert post(access_client, payload={**grant(), 'operation': 'remove'}).json['result']['member'] is False
    assert not decision(access_client).allowed
    assert counts(access_client) == (0, 2, 1)
    history = access_client[1].get('/admin/feature-access').text
    assert 'Approved limited collaboration' in history
    assert 'openet_ts' in history


@pytest.mark.parametrize('patch', [
    {'user_id': True}, {'user_id': '2'}, {'user_id': 999}, {'user_id': -1},
    {'group_key': 'no-such-group'}, {'group_key': []}, {'operation': []},
    {'reason': ''}, {'reason': '   '}, {'reason': None}, {'actor_id': 3},
    {'role': 'Root'}, {'expires_at': '2020-01-01T00:00:00Z'},
    {'expires_at': '2030-01-01'}, {'review_at': '2030-01-01T12:00:00+02:00'},
    {'operation': 'remove', 'expires_at': None},
])
def test_invalid_membership_no_partial_write(access_client, patch):
    login(access_client)
    response = post(access_client, payload={**grant(), **patch})
    assert response.status_code == 400
    assert response.json['error']['code'] == 'validation_error'
    assert counts(access_client) == (0, 0, 0)


@pytest.mark.parametrize('patch,code', [
    ({'user_id': 1}, 400), ({'role': 'Root'}, 400), ({'accepts_training': 'true'}, 400),
    ({'accepts_training': False}, 400), ({'statement_version': 'old'}, 409),
])
def test_acknowledgment_cannot_target_another_account(access_client, patch, code):
    login(access_client, 2)
    response = post(access_client, ACK_URL, dict(accepts_training=True, statement_version=INTERNAL_STATEMENT_VERSION) | patch)
    assert response.status_code == code
    assert counts(access_client) == (0, 0, 0)


def test_authentication_authorization_csrf_and_content_type(access_client):
    assert post(access_client, payload=grant()).status_code == 401
    login(access_client, 2)
    assert post(access_client, payload=grant()).status_code == 403
    assert access_client[1].get('/admin/feature-access').status_code == 403
    login(access_client)
    assert post(access_client, payload=grant(), csrf=False).status_code == 400
    assert post(access_client, payload=grant(), content_type='text/plain').status_code == 400
    assert counts(access_client) == (0, 0, 0)


def test_acknowledgment_is_own_and_profile_is_private(access_client):
    login(access_client, 2)
    post(access_client, ACK_URL, dict(accepts_training=True, statement_version=INTERNAL_STATEMENT_VERSION))
    with access_client[2].connect() as connection:
        assert connection.execute(sa.select(acceptances.c.user_id)).scalars().all() == [2]
    login(access_client, 3)
    assert 'You have accepted this version.' not in access_client[1].get('/profile').text


def test_database_failure_is_correlated_and_rolls_back(access_client, caplog):
    login(access_client)
    with access_client[2].begin() as connection:
        connection.execute(sa.text("ALTER TABLE feature_access_event ADD CONSTRAINT reject_test_event CHECK (reason = 'never')"))
    response = post(access_client, payload=grant())
    assert response.status_code == 503
    assert response.json['error_id'] in caplog.text
    assert 'CHECK' not in response.text and 'Traceback' not in response.text
    assert counts(access_client) == (0, 0, 0)


def test_dates_conflict_and_expired_profile(access_client):
    login(access_client)
    payload = grant(review_at='2025-01-01T00:00:00Z', expires_at='2099-01-01T00:00:00Z')
    assert post(access_client, payload=payload).status_code == 200
    assert post(access_client, payload=grant()).status_code == 409
    with access_client[2].begin() as connection:
        connection.execute(memberships.update().values(expires_at=sa.text("now() - interval '1 day'")))
    login(access_client, 2)
    assert 'membership expired' in access_client[1].get('/profile').text


def test_initialization_cli_audits_and_is_idempotent(access_client):
    runner = access_client[0].test_cli_runner()
    args = ['admin', 'initialize-feature-access', '--email', 'rogerlew@gmail.com', '--reason', 'API and compute limits; continuing maintainer access']
    result = runner.invoke(args=args)
    assert result.exit_code == 0, result.output
    assert counts(access_client) == (2, 2, 0)
    assert runner.invoke(args=args).exit_code == 0
    assert counts(access_client) == (2, 2, 0)
    with access_client[2].connect() as connection:
        assert set(connection.execute(sa.select(memberships.c.user_id)).scalars()) == {1}
        assert set(connection.execute(sa.select(events.c.actor_id)).scalars()) == {1}


def test_initializer_conflict_has_no_partial_grant(access_client):
    login(access_client)
    assert post(access_client, payload=grant()).status_code == 200
    with pytest.raises(ValueError, match='sole maintainer'):
        access_client[3].initialize_maintainer(1, features=FEATURES, reason='initial setup')
    assert counts(access_client) == (1, 1, 0)


@pytest.mark.parametrize('session_kind', ['none', 'stale', 'inactive'])
@pytest.mark.parametrize('url', [ADMIN_URL, ACK_URL])
def test_token_cannot_substitute_for_browser_session(access_client, session_kind, url):
    app, client, engine, _store = access_client
    with app.app_context():
        datastore = app.extensions['security'].datastore
        token = datastore.find_user(id=1).get_auth_token()
        inactive = datastore.find_user(id=3)
        inactive.active = False
        inactive_id = inactive.fs_uniquifier
        datastore.commit()
    csrf = client.get('/test-csrf').text
    with client.session_transaction() as cookie_session:
        if session_kind != 'none':
            cookie_session['_user_id'] = inactive_id if session_kind == 'inactive' else 'deleted-account'
    payload = grant() if url == ADMIN_URL else dict(accepts_training=True, statement_version=INTERNAL_STATEMENT_VERSION)
    response = client.post(url, json=payload, headers={'X-CSRFToken': csrf, 'Authentication-Token': token})
    assert response.status_code == 401
    assert response.json['error']['code'] == 'unauthorized'
    assert counts(access_client) == (0, 0, 0)


def test_inactive_account_can_be_pregranted_but_is_not_effective(access_client):
    login(access_client)
    with access_client[2].begin() as connection:
        connection.execute(sa.text('UPDATE "user" SET active = false WHERE id = 2'))
    response = post(access_client, payload=grant())
    assert response.status_code == 200
    assert response.json['result'] == dict(user_id=2, group_key='openet_ts', changed=True, member=False)
    assert access_client[3].membership(2, 'openet_ts') == (False, False)
    assert 'Inactive account' in access_client[1].get('/admin/feature-access').text


def test_initializer_second_event_failure_rolls_back_both_groups(access_client):
    with access_client[2].begin() as connection:
        connection.execute(sa.text("ALTER TABLE feature_access_event ADD CONSTRAINT reject_second_event CHECK (group_key <> 'openet_ts')"))
    with pytest.raises(sa.exc.IntegrityError):
        access_client[3].initialize_maintainer(1, features=FEATURES, reason='initial setup')
    assert counts(access_client) == (0, 0, 0)
