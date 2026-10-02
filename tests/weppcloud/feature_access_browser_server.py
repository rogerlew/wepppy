"""Isolated full-app browser acceptance server; never serves the shared account DB.

Run via wctl exec -T weppcloud python tests/weppcloud/feature_access_browser_server.py.
Stops/cleans schema on SIGTERM. Writes disposable session cookies to an ignored,
mode-0600 file for Playwright; never print or retain those cookies in evidence.
"""
import json
import os
from pathlib import Path
import signal
from uuid import uuid4

import sqlalchemy as sa
from wepppy.weppcloud.configuration import _build_postgres_uri


def main():
    uri = _build_postgres_uri()
    schema = 'feature_access_browser_' + uuid4().hex
    admin = sa.create_engine(uri, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    os.environ.pop('POSTGRES_IDLE_IN_TX_TIMEOUT', None)
    os.environ['SQLALCHEMY_DATABASE_URI'] = sa.engine.make_url(uri).update_query_dict(
        {'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)
    os.environ['SITE_PREFIX'] = ''
    secret_file = Path('/workdir/wepppy/docker/secrets/m2-browser.json')
    sessions = []
    try:
        from flask import jsonify, session
        from flask_security import current_user, login_required
        from flask_security.utils import login_user
        from wepppy.weppcloud.app import app, db, user_datastore
        from wepppy.weppcloud.feature_registry import load_feature_registry
        from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal, FeatureResourceContext, evaluate_feature_access
        from wepppy.weppcloud.utils.feature_access_store import FeatureAccessStore
        from wepppy.weppcloud.utils.feature_access_web import INTERNAL_STATEMENT_VERSION
        from werkzeug.serving import make_server
        features = load_feature_registry()
        app.config['SERVER_NAME'] = None
        app.config['SESSION_KEY_PREFIX'] = schema + ':'
        app.session_interface.key_prefix = schema + ':'
        with app.app_context():
            db.create_all()
            root = user_datastore.create_role(name='Root')
            accounts = [user_datastore.create_user(
                email=email, active=True, roles=[root] if index == 0 else [],
                first_name='Browser', last_name='Acceptance',
            ) for index, email in enumerate(['rogerlew@gmail.com', 'collaborator@example.test'])]
            db.session.commit()
            store = FeatureAccessStore(db.engine)
            store.seed_groups(features)
            initialized = app.test_cli_runner().invoke(args=[
                'admin', 'initialize-feature-access', '--email', 'rogerlew@gmail.com',
                '--reason', 'API and compute limits; continuing designated maintainer access',
            ])
            if initialized.exit_code:
                raise RuntimeError('Isolated initializer failed') from initialized.exception
            credentials = {}
            for label, account in zip(['root', 'collaborator'], accounts):
                with app.test_client() as client:
                    with app.test_request_context('/'):
                        login_user(account, remember=False)
                        payload = dict(session)
                    with client.session_transaction() as cookie_session:
                        cookie_session.update(payload)
                        sessions.append(cookie_session.sid)
                    cookie = client.get_cookie(app.config['SESSION_COOKIE_NAME'])
                    credentials[label] = {'id': account.id, 'name': cookie.key, 'value': cookie.value}
            secret_file.touch(mode=0o600, exist_ok=False)
            secret_file.write_text(json.dumps(credentials))

        @app.get('/test-feature-access-decision')
        @login_required
        def decision():
            result = evaluate_feature_access(
                VerifiedPrincipal(kind='human', user_id=current_user.id,
                                  roles=frozenset(r.name for r in current_user.roles)),
                next(f for f in features if f.id == 'ag_fields'), 'act',
                FeatureResourceContext(existing_access_allowed=True,
                                       internal_statement_version=INTERNAL_STATEMENT_VERSION), store,
            )
            return jsonify(allowed=result.allowed, reason=result.reason)

        def stop(_signal, _frame):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        print('Isolated browser server ready on HTTPS port 8902', flush=True)
        server = make_server('0.0.0.0', 8902, app, threaded=True, ssl_context='adhoc')
        try:
            server.serve_forever()
        finally:
            server.server_close()
            for sid in sessions:
                app.config['SESSION_REDIS'].delete(schema + ':' + sid)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
    finally:
        secret_file.unlink(missing_ok=True)
        with admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin.dispose()


if __name__ == '__main__':
    main()
