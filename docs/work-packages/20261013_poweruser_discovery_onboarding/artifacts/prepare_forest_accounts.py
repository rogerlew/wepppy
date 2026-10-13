"""Create disposable Forest-only identities; credentials stay in ignored secrets."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

from flask import session
from flask_security.utils import login_user
from wepppy.weppcloud.app import app, db, user_datastore, Run

secret = Path('/workdir/wepppy/docker/secrets/puux-browser.json')
if secret.exists():
    raise SystemExit('Existing PUUX credentials: reuse or explicitly clean up first.')
runid = 'sabbatical-stitcher'  # Disposable CBEXEC browser-created project, retained in evidence.
with app.app_context():
    run = Run.query.filter_by(runid=runid).one()
    prefix = 'puux-' + uuid4().hex[:10]
    credentials = {}
    for label, roles in [('ordinary', ['User']), ('populated', ['User']),
                         ('legacy', ['User', 'PowerUser']), ('admin', ['User', 'Admin']),
                         ('root', ['User', 'Root']), ('dev', ['User', 'Dev'])]:
        account = user_datastore.create_user(email=f'{prefix}-{label}@example.test',
                    active=True, confirmed_at=datetime.now(timezone.utc),
                    first_name='PUUX', last_name='Acceptance',
                    roles=[user_datastore.find_role(name) for name in roles])
        if label == 'populated':
            account.runs.append(run)
        db.session.commit()
        with app.test_client() as client:
            with app.test_request_context('/'):
                login_user(account, remember=False)
                payload = dict(session)
            with client.session_transaction() as cookie_session:
                cookie_session.update(payload)
                sid = cookie_session.sid
            cookie = client.get_cookie(app.config['SESSION_COOKIE_NAME'])
            credentials[label] = dict(id=account.id, email=account.email, name=cookie.key,
                                      value=cookie.value, sid=sid)
    secret.touch(mode=0o600, exist_ok=False)
    secret.write_text(json.dumps(credentials))
    print(json.dumps({'created_disposable_accounts': {k:v['id'] for k,v in credentials.items()},
                      'populated_run':runid, 'existing_account_roles_changed':False}))
