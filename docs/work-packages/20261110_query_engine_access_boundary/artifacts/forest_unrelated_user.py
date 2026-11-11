"""Create/remove only one disposable ordinary account for the denial browser gate."""
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from flask_security.utils import hash_password
from wepppy.weppcloud.app import app, db, User, user_datastore

record = Path('/tmp/qe-boundary-unrelated.json')
with app.app_context():
    if '--cleanup' in sys.argv:
        values = json.loads(record.read_text())
        assert values['DEV_AGENT_EMAIL'].startswith('qe-boundary-')
        user = User.query.filter_by(email=values['DEV_AGENT_EMAIL']).one()
        assert not user.runs and not user.roles
        db.session.delete(user)
        db.session.commit()
        record.unlink()
        print('Removed disposable unrelated account and credential file')
    else:
        assert not record.exists()
        values = {'DEV_AGENT_EMAIL': 'qe-boundary-' + secrets.token_hex(8) + '@example.com',
                  'DEV_AGENT_PASSWORD': secrets.token_urlsafe(32)}
        with os.fdopen(os.open(record, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as stream:
            json.dump(values, stream)
        user_datastore.create_user(email=values['DEV_AGENT_EMAIL'], active=True,
            first_name='Query boundary', last_name='Disposable', confirmed_at=datetime.now(),
            password=hash_password(values['DEV_AGENT_PASSWORD']))
        db.session.commit()
        print('Created disposable unrelated account without roles or runs')
