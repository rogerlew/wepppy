"""Deactivate only PUUX disposable identities; retain acceptance/audit history."""
from pathlib import Path
from uuid import uuid4
import json
import sqlalchemy as sa

from wepppy.weppcloud.app import app, db, User
from wepppy.weppcloud.utils.feature_access_schema import acceptances

secrets = Path('/workdir/wepppy/docker/secrets')
paths = [secrets / name for name in (
    'puux-browser-attempt1.json', 'puux-browser-attempt2.json', 'puux-browser.json')]
credentials = [entry for path in paths for entry in json.loads(path.read_text()).values()]
with app.app_context():
    accounts = []
    for entry in credentials:
        account = db.session.get(User, entry['id'])
        assert account is not None and account.email == entry['email']
        assert account.email.startswith('puux-') and account.email.endswith('@example.test')
        assert all(run.runid == 'sabbatical-stitcher' for run in account.runs)
        accounts.append(account)
    assert len(accounts) == 18 and len({account.id for account in accounts}) == 18
    account_ids = sorted(account.id for account in accounts)
    acceptance_count = sa.select(sa.func.count()).select_from(acceptances).where(
        acceptances.c.user_id.in_(account_ids))
    with db.engine.connect() as connection:
        retained_before = connection.scalar(acceptance_count)
    for account in accounts:
        account.active = False
        account.fs_uniquifier = uuid4().hex
        account.runs.clear()
    db.session.commit()
    interface = app.session_interface
    for entry in credentials:
        interface.redis.delete(interface.key_prefix + entry['sid'])
    assert all(not interface.redis.exists(interface.key_prefix + entry['sid'])
               for entry in credentials)
    db.session.expire_all()
    assert all(not account.active and not account.runs for account in accounts)
    with db.engine.connect() as connection:
        retained_after = connection.scalar(acceptance_count)
    assert retained_before == retained_after
    receipt = {'deactivated_disposable_account_ids': account_ids,
               'test_run_associations_removed': True, 'recorded_sessions_deleted': True,
               'authentication_uniquifiers_rotated': True, 'acceptance_history_retained': True,
               'acceptances_before': retained_before, 'acceptances_after': retained_after,
               'existing_accounts_modified': False}
    (Path(__file__).parent / 'forest-account-cleanup.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
for path in paths:
    path.unlink()
