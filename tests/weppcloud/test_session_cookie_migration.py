from __future__ import annotations

import pickle
from datetime import timedelta

import pytest
from flask import Flask, request
from flask_login import LoginManager, UserMixin, current_user
from flask_login.utils import encode_cookie

from wepppy.weppcloud.session_migration import (
    MAX_COOKIE_CANDIDATES,
    REVOCATION_KEY_PREFIX,
    MigratingRedisSessionInterface,
    SessionCookieBoundsError,
    cookie_values,
    revoke_presented_sessions,
)
from wepppy.weppcloud.routes._security.ui import refresh_presented_remember_cookie


pytestmark = pytest.mark.unit


class _Pipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def delete(self, key):
        self.commands.append(("delete", key))
        return self

    def setex(self, key, ttl, value):
        self.commands.append(("setex", key, ttl, value))
        return self

    def execute(self):
        for command in self.commands:
            if command[0] == "delete":
                self.redis.delete(command[1])
            else:
                self.redis.setex(command[1], command[2], command[3])


class _Redis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def exists(self, key):
        return int(key in self.values)

    def delete(self, key):
        self.values.pop(key, None)

    def setex(self, name, time, value):
        self.values[name] = value

    def pipeline(self):
        return _Pipeline(self)

    def eval(self, _script, key_count, *args):
        if key_count == 3:
            revoked_key, old_session_key, new_session_key, rev_ttl, _ttl, value = args
            if revoked_key in self.values:
                self.delete(old_session_key)
                return 0
            self.delete(old_session_key)
            self.setex(revoked_key, rev_ttl, "1")
            self.values[new_session_key] = value
            return 1
        revoked_key, session_key, _ttl, value = args
        if revoked_key in self.values:
            self.delete(session_key)
            return 0
        self.values[session_key] = value
        return 1


@pytest.fixture
def migration_app():
    app = Flask(__name__)
    app.secret_key = "migration-test-secret"
    app.config.update(
        SESSION_COOKIE_NAME="__Host-weppcloud_session",
        SESSION_COOKIE_LEGACY_NAME="session",
        SESSION_COOKIE_MIGRATION_ENABLED=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_DOMAIN=None,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_USE_SIGNER=True,
        SESSION_REFRESH_EACH_REQUEST=True,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    app.session_cookie_name = app.config["SESSION_COOKIE_NAME"]
    redis = _Redis()
    interface = MigratingRedisSessionInterface(
        redis, "session:", use_signer=True, permanent=False
    )
    app.session_interface = interface
    return app, redis, interface


def _signed(interface, app, sid):
    return interface._get_signer(app).sign(sid.encode()).decode()


def _store(redis, sid, payload):
    redis.values[f"session:{sid}"] = pickle.dumps(payload)


def test_cookie_values_preserve_duplicates_and_enforce_candidate_bound():
    assert cookie_values(["session=a; other=x; session=b"], "session") == ["a", "b"]
    raw = "; ".join(f"session={index}" for index in range(MAX_COOKIE_CANDIDATES + 1))
    with pytest.raises(SessionCookieBoundsError):
        cookie_values([raw], "session")


def test_invalid_legacy_collision_is_skipped_and_sid_payload_are_preserved(migration_app):
    app, redis, interface = migration_app
    _store(redis, "good", {"_user_id": "7", "csrf_token": "token", "cap_verified_at": 1})
    cookie = f"session=unrelated; session={_signed(interface, app, 'good')}"
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid == "good"
    assert dict(loaded) == {"_user_id": "7", "csrf_token": "token", "cap_verified_at": 1}


def test_invalid_legacy_values_do_not_consume_signed_candidate_budget(migration_app):
    app, redis, interface = migration_app
    _store(redis, "good", {"_user_id": "7", "csrf_token": "token"})
    invalid = "; ".join(f"session=invalid-{index}" for index in range(9))
    cookie = f"{invalid}; session={_signed(interface, app, 'good')}"
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid == "good"


def test_primary_presence_blocks_legacy_downgrade(migration_app):
    app, redis, interface = migration_app
    _store(redis, "legacy", {"_user_id": "7"})
    cookie = (
        "__Host-weppcloud_session=invalid; "
        f"session={_signed(interface, app, 'legacy')}"
    )
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid != "legacy"
    assert not loaded


def test_reader_first_profile_reads_owned_cookie_but_writes_legacy_name(migration_app):
    app, redis, interface = migration_app
    app.config["SESSION_COOKIE_NAME"] = "session"
    app.session_cookie_name = "session"
    app.config["SESSION_COOKIE_PRIMARY_NAME"] = "__Host-weppcloud_session"
    _store(redis, "owned", {"_user_id": "7", "csrf_token": "token"})
    cookie = f"__Host-weppcloud_session={_signed(interface, app, 'owned')}"

    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    response = app.response_class()
    interface.save_session(app, loaded, response)

    assert loaded.sid == "owned"
    assert loaded["csrf_token"] == "token"
    assert any(
        header.startswith("session=")
        for header in response.headers.getlist("Set-Cookie")
    )


def test_reader_first_rotation_expires_owned_cookie_and_writes_legacy(migration_app):
    app, redis, interface = migration_app
    app.config["SESSION_COOKIE_NAME"] = "session"
    app.session_cookie_name = "session"
    app.config["SESSION_COOKIE_PRIMARY_NAME"] = "__Host-weppcloud_session"
    _store(redis, "anonymous", {"csrf_token": "token"})
    cookie = f"__Host-weppcloud_session={_signed(interface, app, 'anonymous')}"

    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    loaded["_user_id"] = "7"
    response = app.response_class()
    interface.save_session(app, loaded, response)

    headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith("session=") and "Max-Age=0" not in header for header in headers)
    assert any(
        header.startswith("__Host-weppcloud_session=") and "Max-Age=0" in header
        for header in headers
    )


def test_reader_first_rejected_primary_is_expired(migration_app):
    app, _redis, interface = migration_app
    app.config["SESSION_COOKIE_NAME"] = "session"
    app.session_cookie_name = "session"
    app.config["SESSION_COOKIE_PRIMARY_NAME"] = "__Host-weppcloud_session"

    with app.test_request_context(
        "/", headers={"Cookie": "__Host-weppcloud_session=invalid"}
    ):
        loaded = interface.open_session(app, request)
    response = app.response_class()
    interface.save_session(app, loaded, response)

    assert any(
        header.startswith("__Host-weppcloud_session=") and "Max-Age=0" in header
        for header in response.headers.getlist("Set-Cookie")
    )


def test_reader_first_rejected_primary_with_new_csrf_state_is_expired(migration_app):
    app, _redis, interface = migration_app
    app.config["SESSION_COOKIE_NAME"] = "session"
    app.session_cookie_name = "session"
    app.config["SESSION_COOKIE_PRIMARY_NAME"] = "__Host-weppcloud_session"

    with app.test_request_context(
        "/", headers={"Cookie": "__Host-weppcloud_session=invalid"}
    ):
        loaded = interface.open_session(app, request)
    loaded["csrf_token"] = "rendered-token"
    response = app.response_class()
    interface.save_session(app, loaded, response)

    headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith("session=") and "Max-Age=0" not in header for header in headers)
    assert any(
        header.startswith("__Host-weppcloud_session=")
        and "Path=/" in header
        and "Secure" in header
        and "Max-Age=0" in header
        for header in headers
    )


def test_missing_authoritative_sid_does_not_scan_to_later_live_sid(migration_app):
    app, redis, interface = migration_app
    _store(redis, "later", {"_user_id": "7"})
    cookie = (
        f"session={_signed(interface, app, 'missing')}; "
        f"session={_signed(interface, app, 'later')}"
    )
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid not in {"missing", "later"}


def test_cross_principal_candidates_fail_closed(migration_app):
    app, redis, interface = migration_app
    _store(redis, "first", {"_user_id": "7"})
    _store(redis, "second", {"_user_id": "8"})
    cookie = (
        f"session={_signed(interface, app, 'first')}; "
        f"session={_signed(interface, app, 'second')}"
    )
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid not in {"first", "second"}
    assert loaded["_session_migration_conflict"] is True
    assert loaded["_remember"] == "clear"


def test_repeated_same_anonymous_sid_is_one_session(migration_app):
    app, redis, interface = migration_app
    _store(redis, "anonymous", {"csrf_token": "token", "cap_verified_at": 1})
    signed = _signed(interface, app, "anonymous")
    with app.test_request_context(
        "/", headers={"Cookie": f"session={signed}; session={signed}"}
    ):
        loaded = interface.open_session(app, request)
    assert loaded.sid == "anonymous"
    assert loaded["csrf_token"] == "token"


def test_over_bound_signed_candidates_suppress_remember_and_logout_revokes_all(
    migration_app,
):
    app, redis, interface = migration_app
    signed = []
    for index in range(9):
        sid = f"candidate-{index}"
        _store(redis, sid, {"_user_id": "7"})
        signed.append(f"session={_signed(interface, app, sid)}")
    cookie = "; ".join(signed)

    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded["_session_migration_conflict"] is True
    assert loaded["_remember"] == "clear"

    with app.test_request_context("/logout", headers={"Cookie": cookie}):
        assert revoke_presented_sessions(app, request) == 9
    for index in range(9):
        sid = f"candidate-{index}"
        assert f"session:{sid}" not in redis.values
        assert REVOCATION_KEY_PREFIX + sid in redis.values


def test_logout_revokes_all_presented_signed_sids_and_fences_late_save(migration_app):
    app, redis, interface = migration_app
    _store(redis, "primary", {"_user_id": "7"})
    _store(redis, "legacy", {"_user_id": "7"})
    cookie = (
        f"__Host-weppcloud_session={_signed(interface, app, 'primary')}; "
        f"session={_signed(interface, app, 'legacy')}"
    )
    with app.test_request_context("/logout", headers={"Cookie": cookie}):
        assert revoke_presented_sessions(app, request) == 2
    assert f"session:primary" not in redis.values
    assert f"session:legacy" not in redis.values
    assert REVOCATION_KEY_PREFIX + "primary" in redis.values
    assert REVOCATION_KEY_PREFIX + "legacy" in redis.values

    late_session = interface.session_class({"_user_id": "7"}, sid="primary")
    response = app.response_class()
    interface.save_session(app, late_session, response)
    assert "session:primary" not in redis.values
    assert "Max-Age=0" in response.headers.get("Set-Cookie", "")
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith("remember_token=") for header in set_cookie_headers)


def test_revoked_session_suppresses_remember_restoration(migration_app):
    app, redis, interface = migration_app
    redis.values[REVOCATION_KEY_PREFIX + "revoked"] = b"1"
    cookie = f"session={_signed(interface, app, 'revoked')}"
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    assert loaded.sid != "revoked"
    assert loaded["_session_migration_conflict"] is True
    assert loaded["_remember"] == "clear"


def test_anonymous_to_authenticated_transition_rotates_sid_and_preserves_payload(
    migration_app,
):
    app, redis, interface = migration_app
    _store(redis, "anonymous", {"csrf_token": "token", "oauth_state": "state"})
    cookie = f"session={_signed(interface, app, 'anonymous')}"
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    loaded["_user_id"] = "7"
    response = app.response_class()

    interface.save_session(app, loaded, response)

    assert loaded.sid != "anonymous"
    assert "session:anonymous" not in redis.values
    assert REVOCATION_KEY_PREFIX + "anonymous" in redis.values
    saved = pickle.loads(redis.values[f"session:{loaded.sid}"])
    assert saved["csrf_token"] == "token"
    assert saved["oauth_state"] == "state"
    assert saved["_user_id"] == "7"


def test_logout_winning_anonymous_auth_rotation_clears_cookies_without_new_session(
    migration_app,
):
    app, redis, interface = migration_app
    _store(redis, "anonymous", {"csrf_token": "token"})
    cookie = f"session={_signed(interface, app, 'anonymous')}"
    with app.test_request_context("/", headers={"Cookie": cookie}):
        loaded = interface.open_session(app, request)
    loaded["_user_id"] = "7"
    redis.values[REVOCATION_KEY_PREFIX + "anonymous"] = b"1"
    response = app.response_class()

    interface.save_session(app, loaded, response)

    assert "session:anonymous" not in redis.values
    assert not any(
        key.startswith("session:") and key != "session:anonymous"
        for key in redis.values
    )
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(
        header.startswith("__Host-weppcloud_session=") and "Max-Age=0" in header
        for header in set_cookie_headers
    )
    assert any(
        header.startswith("remember_token=") and "Max-Age=0" in header
        for header in set_cookie_headers
    )


def test_cross_principal_conflict_stays_anonymous_through_flask_login(migration_app):
    app, redis, interface = migration_app
    login_manager = LoginManager(app)

    class _User(UserMixin):
        def __init__(self, user_id):
            self.id = user_id

    login_manager.user_loader(lambda user_id: _User(user_id))
    app.before_request(refresh_presented_remember_cookie)
    app.add_url_rule(
        "/identity",
        "identity",
        lambda: "authenticated" if current_user.is_authenticated else "anonymous",
    )
    _store(redis, "first", {"_user_id": "7"})
    _store(redis, "second", {"_user_id": "8"})
    remember = encode_cookie("7", key=app.secret_key)
    cookie = (
        f"session={_signed(interface, app, 'first')}; "
        f"session={_signed(interface, app, 'second')}; remember_token={remember}"
    )

    with app.test_client(use_cookies=False) as client:
        response = client.get("/identity", headers={"Cookie": cookie})

    assert response.data == b"anonymous"
    assert any(
        header.startswith("remember_token=") and "Max-Age=0" in header
        for header in response.headers.getlist("Set-Cookie")
    )
