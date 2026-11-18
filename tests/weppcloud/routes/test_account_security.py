"""Real Flask-Security, SQLAlchemy, CSRF and signed mailbox lifecycle coverage."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from flask import Flask, g
from flask_security import Security
from flask_security.utils import hash_password, verify_password
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

from wepppy.weppcloud import account_security as accounts
from wepppy.weppcloud.auth_forms import ExtendedLoginForm
from wepppy.weppcloud.routes._security import oauth

pytestmark = pytest.mark.routes


@pytest.fixture
def account_app(monkeypatch):
    from wepppy.weppcloud.app import db, User, Role, Run, WeppCloudUserDatastore
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[3] / 'wepppy/weppcloud/templates'))
    app.config.update(TESTING=True, SECRET_KEY='test-only', SQLALCHEMY_DATABASE_URI='sqlite://',
        SECURITY_PASSWORD_SALT='test-only', SECURITY_PASSWORD_HASH='bcrypt',
        SECURITY_REGISTERABLE=True, SECURITY_CONFIRMABLE=True, SECURITY_RECOVERABLE=True,
        SECURITY_CHANGEABLE=True, SECURITY_LOGIN_WITHOUT_CONFIRMATION=True,
        SECURITY_SEND_REGISTER_EMAIL=False, SECURITY_SEND_PASSWORD_RESET_NOTICE_EMAIL=False,
        SECURITY_SEND_PASSWORD_CHANGE_EMAIL=False, WTF_CSRF_ENABLED=True)
    db.init_app(app)
    datastore = WeppCloudUserDatastore(db, User, Role, Run)
    CSRFProtect(app)
    Security(app, datastore, login_form=ExtendedLoginForm)
    accounts.init_account_security(app, datastore)
    app.url_build_error_handlers.append(lambda error, endpoint, values: '/mock/' + endpoint)
    app.jinja_env.globals.update(static_url=lambda filename: '/static/' + filename, site_prefix='')
    app.add_url_rule('/test-csrf', view_func=lambda: generate_csrf())
    @app.teardown_request
    def clear_request_identity(error):
        # Tests retain a DB app context; real HTTP requests have a fresh g each time.
        g.pop('_login_user', None)

    mails = []
    monkeypatch.setattr(accounts, 'send_mail', lambda *a, **kw: mails.append((a, kw)))
    monkeypatch.setattr('wepppy.weppcloud.auth_forms.verify_cap_token', lambda token: {'success': True})
    with app.app_context():
        tables = [db.metadata.tables[name] for name in
                  ('user', 'role', 'roles_users', 'run', 'runs_users', 'oauth_account', 'user_preferences')]
        db.metadata.create_all(db.engine, tables=tables)
        yield app, datastore, mails
        db.session.remove()
        db.metadata.drop_all(db.engine, tables=list(reversed(tables)))


def post(client, path, **data):
    csrf = client.get('/test-csrf').text
    return client.post(path, data=dict(csrf_token=csrf, **data))


def signup(client, email='owner@example.com'):
    return post(client, '/register', first_name='Test', last_name='Owner', email=email, cap_token='test')


def link(mails):
    return urlsplit(mails[-1][1]['verification_link']).path


def create(datastore, **kwargs):
    user = datastore.create_user(email='owner@example.com', active=True, **kwargs)
    datastore.commit()
    return user


def test_email_first_signup_requires_mailbox_post_before_password_and_access(account_app):
    app, ds, mails = account_app
    client = app.test_client()
    assert client.post('/register', data={'email':'owner@example.com'}).status_code == 400
    response = signup(client)
    assert response.status_code == 302
    user = ds.find_user(email='owner@example.com')
    assert user.password is None and user.local_credential_state == 'pending'
    with client.session_transaction() as session:
        assert '_user_id' not in session
    path = link(mails)
    assert client.get(path).status_code == 200
    assert user.password is None
    assert client.post(path, data={'password': 'password'}).status_code == 400
    assert post(client, path, password='a-good-mailbox-password', password_confirm='a-good-mailbox-password').status_code == 302
    ds.db.session.expire_all()
    assert user.local_credential_state == 'enabled'
    assert accounts.mailbox_verified(user)
    assert verify_password('a-good-mailbox-password', user.password)
    old_hash = user.password
    post(client, path, password='replacement-password', password_confirm='replacement-password')
    ds.db.session.expire_all()
    assert user.password == old_hash
    with client.session_transaction() as session:
        assert '_user_id' not in session
    response = post(client, '/login', email=user.email, password='a-good-mailbox-password', cap_token='test')
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['_user_id'] == user.fs_uniquifier


def test_public_signup_never_replaces_existing_password(account_app):
    app, ds, mails = account_app
    user = create(ds, password=hash_password('existing-password'))
    before = user.password
    client = app.test_client()
    signup(client)
    assert not mails[-1][1]['setup_password']
    post(client, link(mails), password='attacker-password', password_confirm='attacker-password')
    ds.db.session.expire_all()
    assert user.password == before and accounts.mailbox_verified(user)
    assert user.local_credential_state == 'legacy'


def test_cilogon_contacts_never_merge_and_cannot_setup_local_password(account_app):
    app, ds, mails = account_app
    shared = create(ds, password=hash_password('existing-password'))
    first = accounts.resolve_federated_account(ds,'cilogon','subject-1',shared.email,True,{}, {})
    second = accounts.resolve_federated_account(ds,'cilogon','subject-2',shared.email,True,{}, {})
    absent = accounts.resolve_federated_account(ds,'cilogon','subject-3',None,False,{}, {})
    assert len({shared.id,first.id,second.id,absent.id}) == 4
    assert first.email is None and first.password is None and absent.contact_email is None
    again = accounts.resolve_federated_account(ds,'cilogon','subject-1','changed@example.com',True,{}, {})
    assert again.id == first.id and again.contact_email == shared.email
    with app.test_request_context():
        assert accounts._send_instructions(first,'setup') == 'unavailable'
        assert accounts._send_instructions(first,'verify') == 'sent'
    post(app.test_client(), link(mails))
    ds.db.session.expire_all()
    assert accounts.mailbox_verified(first) and first.password is None and first.email is None
    assert not accounts.mailbox_verified(shared)


@pytest.mark.parametrize('provider', ['google','github'])
def test_verified_shared_matching_then_stable_identity_drift(account_app, provider):
    app, ds, mails = account_app
    shared = create(ds, password=hash_password('existing-password'))
    with pytest.raises(ValueError):
        accounts.resolve_federated_account(ds,provider,'subject',shared.email,False,{}, {})
    user = accounts.resolve_federated_account(ds,provider,'subject',shared.email,True,{}, {})
    assert user.id == shared.id and user.local_credential_state == 'legacy'
    again = accounts.resolve_federated_account(ds,provider,'subject','other@example.com',False,{}, {})
    assert again.id == shared.id and again.email == 'owner@example.com'
    assert not accounts.mailbox_verified(again)


def test_address_change_invalidates_proof_token_and_security_identity(account_app):
    app, ds, mails = account_app
    user = create(ds, password=None, local_credential_state='pending')
    with app.test_request_context():
        assert accounts._send_instructions(user,'setup') == 'sent'
    path = link(mails)
    identity = user.fs_uniquifier
    user.email='changed@example.com'
    ds.commit()
    assert user.fs_uniquifier != identity
    post(app.test_client(),path,password='new-password-here',password_confirm='new-password-here')
    ds.db.session.expire_all()
    assert user.password is None and not accounts.mailbox_verified(user)


def test_resend_is_bounded_and_supersedes_previous_token(account_app):
    app, ds, mails = account_app
    client = app.test_client()
    signup(client)
    original = link(mails)
    signup(client)
    assert len(mails)==1
    user = ds.find_user(email='owner@example.com')
    user.verification_sent_at = None
    ds.commit()
    signup(client)
    assert len(mails)==2
    post(client,original,password='new-password-here',password_confirm='new-password-here')
    ds.db.session.expire_all()
    assert user.password is None


@pytest.mark.parametrize('flag', [False, None, 'true', 'false', 1])
def test_google_requires_boolean_email_assurance(flag):
    assert oauth._fetch_primary_verified_email(None,{'name':'Google'},{'email':'a@example.com','email_verified':flag}) == ('a@example.com',False)


def test_github_never_falls_back_to_profile_assurance():
    class Client:
        def get(self, endpoint):
            return type('Response', (), {'ok':False})()
    assert oauth._fetch_primary_verified_email(Client(),{'name':'GitHub'},{'email':'a@example.com','verified':True}) == (None,False)


def test_json_registration_ignores_preverification_password_and_recovery_uses_setup(account_app):
    app, ds, mails=account_app
    client=app.test_client()
    csrf=client.get('/test-csrf').text
    response=client.post('/register',json=dict(email='owner@example.com',first_name='Test',last_name='Owner',cap_token='test',password='attacker-password',password_confirm='attacker-password'),headers={'X-CSRFToken':csrf})
    assert response.status_code==200
    assert 'authentication_token' not in response.text
    user=ds.find_user(email='owner@example.com')
    assert user.password is None
    user.verification_sent_at=None
    ds.commit()
    post(client,'/reset',email='owner@example.com')
    assert mails[-1][1]['setup_password'] is True
    assert '/account/email/confirm/' in link(mails)
    with client.session_transaction() as session: assert '_user_id' not in session


def test_pending_oauth_session_cannot_use_stock_password_or_confirmation_paths(account_app):
    from flask_security.recoverable import generate_reset_password_token
    from flask_security.confirmable import generate_confirmation_token
    app, ds, mails=account_app
    user=create(ds,password=None,local_credential_state='pending')
    client=app.test_client()
    with app.test_request_context():
        reset=generate_reset_password_token(user)
        confirmation=generate_confirmation_token(user)
    for path in ('/reset/'+reset, '/confirm/'+confirmation):
        post(client,path,password='bypass-password',password_confirm='bypass-password')
        ds.db.session.expire_all()
        assert user.password is None
    with client.session_transaction() as session:
        session['_user_id']=user.fs_uniquifier
        session['_fresh']=True
    response=post(client,'/change',password='',new_password='bypass-password',new_password_confirm='bypass-password')
    assert response.status_code==302
    ds.db.session.expire_all()
    assert user.password is None


def test_wrong_account_expiry_and_mail_failure_do_not_verify(account_app,monkeypatch):
    from smtplib import SMTPException
    app,ds,mails=account_app
    client=app.test_client()
    signup(client)
    user=ds.find_user(email='owner@example.com')
    path=link(mails)
    other=ds.create_user(email='other@example.com',password=None,active=True)
    ds.commit()
    with client.session_transaction() as session: session['_user_id']=other.fs_uniquifier
    post(client,path,password='mailbox-password',password_confirm='mailbox-password')
    ds.db.session.expire_all()
    assert user.password is None
    client=app.test_client()
    monkeypatch.setattr(accounts,'get_within_delta',lambda key:__import__('datetime').timedelta(seconds=-1))
    post(client,path,password='mailbox-password',password_confirm='mailbox-password')
    assert user.password is None
    def fail(*a,**kw): raise SMTPException('private transport detail')
    monkeypatch.setattr(accounts,'send_mail',fail)
    user.verification_sent_at=None
    ds.commit()
    with app.test_request_context(): assert accounts._send_instructions(user,'setup')=='failed'
    assert not accounts.mailbox_verified(user)


def test_normalized_email_unique_and_role_run_identity_preserved(account_app):
    from sqlalchemy.exc import IntegrityError
    app,ds,mails=account_app
    user=create(ds,password=hash_password('existing-password'))
    run=ds.create_run('ab-test','cfg',user)
    original_hash=user.password
    with pytest.raises(IntegrityError):
        ds.create_user(email=' OWNER@example.com ',password=None)
        ds.commit()
    ds.db.session.rollback()
    linked=accounts.resolve_federated_account(ds,'google','stable',user.email,True,{}, {})
    cilogon=accounts.resolve_federated_account(ds,'cilogon','stable',user.email,True,{}, {})
    assert linked.id==user.id and linked.password==original_hash
    assert run in linked.runs and run not in cilogon.runs


def test_real_mail_facility_renders_and_redeems_setup_link(account_app,monkeypatch):
    import re
    from flask_mail import Mail
    from flask_security.utils import send_mail
    app,ds,_=account_app
    app.config.update(MAIL_SUPPRESS_SEND=True,MAIL_DEFAULT_SENDER='test@example.com')
    mail=Mail(app)
    monkeypatch.setattr(accounts,'send_mail',send_mail)
    client=app.test_client()
    with mail.record_messages() as outbox:
        signup(client)
    assert len(outbox)==1 and outbox[0].recipients==['owner@example.com']
    address=re.search(r'http://localhost/account/email/confirm/[^\s<]+',outbox[0].body).group()
    post(client,urlsplit(address).path,password='mail-sink-password',password_confirm='mail-sink-password')
    ds.db.session.expire_all()
    user=ds.find_user(email='owner@example.com')
    assert accounts.mailbox_verified(user) and verify_password('mail-sink-password',user.password)


def test_bootstrap_real_detached_roles_and_membership_with_no_email(account_app,monkeypatch,tmp_path):
    import importlib
    from wepppy.weppcloud.bootstrap import api_shared as api
    app,ds,_=account_app
    monkeypatch.setattr(importlib.import_module('wepppy.weppcloud.app'),'app',app)
    monkeypatch.setattr(api,'bootstrap_wd',lambda runid:str(tmp_path))
    owner=create(ds,password=None)
    run=ds.create_run('ab-identity','cfg',owner)
    collaborator=accounts.resolve_federated_account(ds,'cilogon','collaborator',None,False,{}, {})
    ds.add_run_to_user(collaborator,run)
    admin=accounts.resolve_federated_account(ds,'cilogon','admin',None,False,{}, {})
    role=ds.create_role(name='Admin')
    ds.add_role_to_user(admin,role)
    ds.commit()
    for uid in (owner.id,collaborator.id,admin.id):
        detached_run,detached_user=api.ensure_bootstrap_eligibility('ab-identity',require_owner=True,require_user_access=True,user_id=uid)
        assert detached_user.id==uid
    ds.remove_run_to_user(collaborator,run)
    with pytest.raises(api.BootstrapOperationError):
        api.ensure_bootstrap_eligibility('ab-identity',require_owner=True,require_user_access=True,user_id=collaborator.id)


@pytest.mark.parametrize('payload',[[1],'text',None])
def test_nonobject_json_is_bad_request(account_app,payload):
    import json
    app,ds,mails=account_app
    client=app.test_client()
    csrf=client.get('/test-csrf').text
    response=client.post('/register',data=json.dumps(payload),content_type='application/json',headers={'X-CSRFToken':csrf})
    assert response.status_code==400 and not mails


def test_cilogon_run_owner_display_is_not_anonymous(account_app):
    from wepppy.weppcloud.routes.user import _owner_email_map
    app,ds,mails=account_app
    user=accounts.resolve_federated_account(ds,'cilogon','owner-display',None,False,{}, {})
    run=ds.create_run('ab-display','cfg',user)
    assert _owner_email_map([run])[str(user.id)]==f'User {user.id}'
    assert run.owner==f'User {user.id}'
