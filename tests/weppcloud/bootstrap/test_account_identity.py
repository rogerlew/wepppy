"""Signed Bootstrap identity compatibility for shared and CILogon accounts."""
import base64
from types import SimpleNamespace
import pytest
from wepppy.weppcloud.bootstrap import api_shared as api
from wepppy.weppcloud.utils import auth_tokens

pytestmark=pytest.mark.unit


@pytest.fixture
def bootstrap_identity(monkeypatch,tmp_path):
    monkeypatch.setenv('WEPP_AUTH_JWT_SECRET','bootstrap-test-only')
    monkeypatch.setenv('WEPP_AUTH_JWT_ALGORITHM','HS256')
    monkeypatch.setattr(api,'bootstrap_wd',lambda runid:str(tmp_path))
    user=SimpleNamespace(id=7,email=None,active=True,has_role=lambda role:False)
    run=SimpleNamespace(owner_id=7,bootstrap_disabled=False,users=[])
    monkeypatch.setattr(api,'_resolve_run_record',lambda runid:run)
    monkeypatch.setattr(api,'_resolve_user_by_id',lambda uid:user if uid==7 else None)
    monkeypatch.setattr(api,'_resolve_user_by_email',lambda email:user if email=='shared@example.com' else None)
    return user,run


def context(extra,subject='user:7'):
    token=auth_tokens.issue_token(subject,audience='wepp.cloud',extra_claims={'runid':'ab-run',**extra})['token']
    header='Basic '+base64.b64encode(('7:'+token).encode()).decode()
    return api.verify_forward_auth_context(auth_header=header,forwarded_path='/git/ab/ab-run/.git/info/refs',external_host='wepp.cloud')


def test_signed_id_and_legacy_email_tokens(bootstrap_identity):
    assert context({'user_id':7}).user_id==7
    legacy=context({},'shared@example.com')
    assert legacy.user_id is None and legacy.email=='shared@example.com'
    for kwargs in ({'user_id':7},{'email':legacy.email}):
        run,user=api.ensure_bootstrap_eligibility('ab-run',require_owner=True,require_user_access=True,**kwargs)
        assert user.id==7


@pytest.mark.parametrize('invalid',[None,True,False,0,-1,'','abc','-7','7.0',[],{}])
def test_signed_invalid_id_never_falls_back_to_shared_email(bootstrap_identity,invalid):
    with pytest.raises(api.BootstrapOperationError): context({'user_id':invalid},'shared@example.com')


def test_current_active_identity_and_access_required(bootstrap_identity):
    user,run=bootstrap_identity
    with pytest.raises(api.BootstrapOperationError):
        api.ensure_bootstrap_eligibility('ab-run',require_owner=True,require_user_access=True,user_id=8,email='shared@example.com')
    user.active=False
    with pytest.raises(api.BootstrapOperationError):
        api.ensure_bootstrap_eligibility('ab-run',require_owner=True,require_user_access=True,user_id=7)
    user.active=True
    run.owner_id=8
    with pytest.raises(api.BootstrapOperationError):
        api.ensure_bootstrap_eligibility('ab-run',require_owner=True,require_user_access=True,user_id=7)


@pytest.mark.parametrize('claims,expected',[
    ({'sub':'session-id','user_id':7},200),
    ({'sub':'7'},200),
    ({'sub':'7','user_id':False},403),
    ({'sub':'service-name'},403),
])
def test_rq_mint_adapter_uses_explicit_id_and_translates_invalid_identity(bootstrap_identity,monkeypatch,claims,expected):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from wepppy.microservices.rq_engine import bootstrap_routes
    monkeypatch.setattr(bootstrap_routes,'_authorize_bootstrap_request',lambda *a,**kw:claims)
    monkeypatch.setattr(api,'ensure_bootstrap_opt_in',lambda runid:SimpleNamespace(mint_bootstrap_jwt=lambda email,uid:f'clone://user-{uid}'))
    app=FastAPI()
    app.include_router(bootstrap_routes.router)
    response=TestClient(app).post('/runs/ab-run/cfg/bootstrap/mint-token')
    assert response.status_code==expected
    if expected==200: assert response.json()['clone_url']=='clone://user-7'
