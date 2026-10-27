"""Exercise the real Flask/SQLAlchemy app boundary without production accounts."""
from contextlib import nullcontext
import sys
from types import ModuleType

import pytest
from flask import Flask, current_app, has_app_context
from flask_sqlalchemy import SQLAlchemy

pytestmark = pytest.mark.microservice


@pytest.fixture
def account_app(monkeypatch):
    app = Flask('account-app')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db = SQLAlchemy(app)

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        fs_uniquifier = db.Column(db.String, nullable=False)

        roles = db.relationship('Role')

    class Role(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        name = db.Column(db.String, nullable=False)

    with app.app_context():
        db.create_all()
        db.session.add(User(id=42, fs_uniquifier='26f2d8c2055e413ba64392db32bc7c10',
                            roles=[Role(name='User')]))
        db.session.commit()

    # Replace only the heavyweight app bootstrap. The context, ORM session and
    # query boundary stay real. Expose every attribute these helpers consume.
    module = ModuleType('wepppy.weppcloud.app')
    module.app = app
    module.User = User
    module.Run = object()
    module.user_datastore = object()
    module.get_run_owners = lambda runid: User.query.filter_by(id=42).all() if runid == 'owned' else []
    monkeypatch.setitem(sys.modules, 'wepppy.weppcloud.app', module)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.mark.parametrize('context_kind', ['none', 'account', 'foreign'])
def test_shared_lookups_use_account_app_and_restore_caller(account_app, context_kind):
    from wepppy.weppcloud.utils.helpers import get_run_owners_lazy
    from wepppy.microservices.rq_engine.session_routes import (
        _resolve_user_id_from_fs_uniquifier, _resolve_roles_for_user_id,
    )
    foreign = Flask('dtale-like-app')
    outer = {'none': nullcontext(), 'account': account_app.app_context(),
             'foreign': foreign.test_request_context('/private-data')}[context_kind]
    with outer:
        before = current_app._get_current_object() if context_kind != 'none' else None
        assert [user.id for user in get_run_owners_lazy('owned')] == [42]
        assert get_run_owners_lazy('absent') == []
        assert _resolve_user_id_from_fs_uniquifier('26f2d8c2055e413ba64392db32bc7c10') == 42
        assert _resolve_user_id_from_fs_uniquifier('00000000000000000000000000000000') is None
        assert _resolve_roles_for_user_id(42) == ['User']
        assert _resolve_roles_for_user_id(99) == []
        if before is not None:
            assert current_app._get_current_object() is before
        else:
            assert not has_app_context()
