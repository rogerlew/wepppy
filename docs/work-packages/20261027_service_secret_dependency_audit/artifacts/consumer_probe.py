"""Read-only local candidate probe; run inside each consumer's disposable container.

Usage: python consumer_probe.py browse|download|dtale|query-engine RUNID
Uses existing private run and database ownership, never prints credentials.
No accounts, projects, session markers, or persistent capabilities are created.
"""
import importlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

service, runid = sys.argv[1:]
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_wd
# Cold import and database lookup occur inside this service's own environment.
owners = get_run_owners_lazy(runid)
assert owners, 'Probe needs an existing owned run'
owner = next(user for user in owners if user.active)
wd = Path(get_wd(runid, prefer_active=False))
assert wd.is_dir() and not (wd / 'PUBLIC').exists(), 'Probe needs a private run'
from wepppy.weppcloud.app import app, Run, User
with app.app_context():
    config = Run.query.filter_by(runid=runid).first().config
    fs_uniquifier = owner.fs_uniquifier
    unrelated = User.query.filter(User.active.is_(True), ~User.id.in_([user.id for user in owners])).first()
    assert unrelated is not None, "Probe needs an existing unrelated account"
    unrelated_id = unrelated.id

from wepppy.microservices.rq_engine.auth import authorize_run_access, AuthError
claims = {'token_class': 'user', 'sub': str(owner.id), 'roles': [],
          'runs': [runid], 'jti': uuid.uuid4().hex, 'exp': time.time() + 120}
# No privileged role bypass: even if the local fixture owner is an admin,
# the signed probe credential carries no admin/root roles.
denied_claims = {**claims, 'sub': str(unrelated_id), 'jti': uuid.uuid4().hex}
authorize_run_access(claims, runid, operation='inspect')
try:
    authorize_run_access(denied_claims, runid, operation='inspect')
except AuthError as exc:
    assert exc.status_code == 403
else:
    raise AssertionError('Unrelated user was allowed')
results = {'service': service, 'uid': os.getuid(), 'gid': os.getgid(),
           'cold_ownership_lookup': 'passed', 'owner': 'allowed', 'unrelated_user': 'denied'}

if service in {'browse', 'download'}:
    from starlette.testclient import TestClient
    from wepppy.weppcloud.utils.auth_tokens import issue_token
    def credential(subject):
        return issue_token(subject, scopes=['rq:status'], audience='rq-engine', runs=[runid], expires_in=120,
                           extra_claims={'token_class': 'user', 'roles': [], 'jti': uuid.uuid4().hex})['token']
    mod = importlib.import_module('wepppy.microservices.' + service + ('.browse' if service == 'browse' else '.app'))
    if service == 'browse':
        path = f'/weppcloud/runs/{runid}/{config}/aria2c.spec'
    else:
        archive = next((wd / 'archives').glob('*.zip'))
        path = f'/weppcloud/runs/{runid}/{config}/download/archives/{archive.name}'
    with TestClient(mod.create_app()) as client:
        headers = {'Authorization': 'Bearer ' + credential(str(owner.id))}
        if service == 'download':
            headers['Range'] = 'bytes=0-15'
        response = client.get(path, headers=headers, follow_redirects=False)
        expected = 200 if service == 'browse' else 206
        assert response.status_code == expected, f'{service} returned {response.status_code}'
        if service == 'browse':
            assert '/download/' in response.text and len(response.text) > 0
        else:
            with archive.open('rb') as stream:
                assert response.content == stream.read(16)
        denied = client.get(path, headers={'Authorization': 'Bearer ' + credential(str(unrelated_id))}, follow_redirects=False)
        assert denied.status_code == 403, denied.status_code
        results['http_owner'] = expected
        results['http_unrelated_user'] = denied.status_code
        results['response_content'] = 'validated'
elif service == 'dtale':
    mod = importlib.import_module('wepppy.webservices.dtale.dtale')
    scope = 'run:' + runid
    for label, token_claims, expected in [('owner', claims, True), ('unrelated_user', denied_claims, False)]:
        key = uuid.uuid4().hex
        mod.VIEWER_CAPABILITIES[key] = mod.ViewerCapability(scope, runid, token_claims, None, time.time() + 120)
        try:
            with mod.app.test_request_context("/dtale/main/probe"):
                assert mod._reauthorize_private_scope(scope, key) is expected
        finally:
            mod.VIEWER_CAPABILITIES.pop(key, None)
        results['dtale_' + label] = expected
    from wepppy.microservices.rq_engine.session_routes import _resolve_user_id_from_fs_uniquifier
    with mod.app.test_request_context('/dtale/main/probe'):
        assert _resolve_user_id_from_fs_uniquifier(fs_uniquifier) == owner.id
    results['dtale_foreign_app_identity'] = 'passed'
elif service == 'query-engine':
    from wepppy.microservices.rq_engine.feature_access import verified_principal
    principal = verified_principal({'token_class': 'mcp', 'sub': fs_uniquifier})
    assert principal.user_id == owner.id
    assert verified_principal({'token_class': 'mcp', 'sub': uuid.uuid4().hex}).user_id is None
    results['legacy_mcp_identity'] = 'known resolved; unknown rejected'
else:
    raise ValueError('Unsupported probe service')
print(json.dumps(results, sort_keys=True))
