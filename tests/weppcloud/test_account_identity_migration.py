"""Additive account migration preserves old credentials and refuses unsafe rollback."""
import importlib
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

pytestmark=pytest.mark.unit
migration=importlib.import_module('wepppy.weppcloud.migrations.versions.a7c1106e42b9_account_identity')


def test_populated_upgrade_uniqueness_and_rollback_guard():
    engine=sa.create_engine('sqlite://')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE "user" (id INTEGER PRIMARY KEY, email VARCHAR(255) UNIQUE, password TEXT, confirmed_at TEXT)')
        conn.exec_driver_sql("INSERT INTO user VALUES (7, 'Owner@example.com', 'legacy-hash', '2025-01-01')")
        conn.exec_driver_sql('CREATE TABLE runs_users (run_id INTEGER, user_id INTEGER)')
        conn.exec_driver_sql('INSERT INTO runs_users VALUES (11,7)')
        with Operations.context(MigrationContext.configure(conn)): migration.upgrade()
        row=conn.execute(sa.text('SELECT * FROM user WHERE id=7')).mappings().one()
        assert row['password']=='legacy-hash' and row['account_kind']=='shared' and row['local_credential_state']=='legacy'
        assert row['mailbox_verified_at'] is None
        assert conn.exec_driver_sql('SELECT user_id FROM runs_users WHERE run_id=11').scalar()==7
        with pytest.raises(sa.exc.IntegrityError):
            conn.exec_driver_sql("INSERT INTO user (email) VALUES (' owner@example.com ')")
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            migration.upgrade()
        conn.exec_driver_sql("INSERT INTO user (account_kind,local_credential_state) VALUES ('cilogon','none')")
        with Operations.context(MigrationContext.configure(conn)), pytest.raises(RuntimeError,match='compatible rollback'):
            migration.downgrade()


def test_duplicate_preflight_does_not_add_columns():
    engine=sa.create_engine('sqlite://')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE user (id INTEGER PRIMARY KEY, email TEXT UNIQUE)')
        conn.exec_driver_sql("INSERT INTO user(email) VALUES ('owner@example.com'),(' OWNER@example.com ')")
        with Operations.context(MigrationContext.configure(conn)), pytest.raises(RuntimeError,match='Duplicate normalized'):
            migration.upgrade()
        assert {c['name'] for c in sa.inspect(conn).get_columns('user')}=={'id','email'}
