from __future__ import annotations

import importlib
import io
import logging
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask, Response, session
from flask_security import signals as fs_signals

pytestmark = pytest.mark.routes


def test_user_authenticated_signal_caches_role_names_in_session() -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    app = Flask(__name__)
    app.config.update(SECRET_KEY="security-log-test")
    module._connect_security_signals(app)

    user = SimpleNamespace(
        id=11,
        roles=[
            SimpleNamespace(name="User"),
            SimpleNamespace(name="Root"),
            "user",  # Duplicate role label with different case should be deduped.
        ],
    )

    with app.test_request_context("/security/login?next=/weppcloud/runs/ab1234/cfg/browse/"):
        fs_signals.user_authenticated.send(app, user=user)
        assert session["_roles_mask"] == ["User", "Root"]
        assert session["_roles"] == ["User", "Root"]


def test_user_unauthenticated_signal_clears_cached_role_names() -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    app = Flask(__name__)
    app.config.update(SECRET_KEY="security-log-test")
    module._connect_security_signals(app)

    with app.test_request_context("/security/logout"):
        session["_roles_mask"] = ["Admin"]
        session["_roles"] = ["Admin"]
        fs_signals.user_unauthenticated.send(app, user=None)

        assert "_roles_mask" not in session
        assert "_roles" not in session


def test_security_log_sanitizers_allowlist_safe_fields() -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    form = SimpleNamespace(data={
        "email": "user@example.test",
        "remember": True,
        "password": "PASSWORD_SENTINEL",
        "csrf_token": "CSRF_SENTINEL",
        "cap-token": "CAP_SENTINEL",
    })

    assert module._sanitize_form(form) == {"remember_selected": True}
    assert module._sanitize_extra({
        "OAuth-Token": "OAUTH_SENTINEL",
        "nested": {"Authorization": "BEARER_SENTINEL"},
    }) == ["OAuth-Token", "nested"]


def test_security_file_handler_uses_restricted_append_only_path(tmp_path) -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    app = Flask(__name__)
    log_path = tmp_path / "security" / "security.log"
    app.config["SECURITY_LOG_FILE"] = str(log_path)

    configured = module._configure_security_file_logging(app)
    assert configured == log_path
    assert log_path.stat().st_mode & 0o777 == 0o600
    assert log_path.parent.stat().st_mode & 0o777 == 0o700

    logger = logging.getLogger(module._SECURITY_LOGGER_NAME)
    matching = [
        handler for handler in logger.handlers
        if getattr(handler, "_security_log_path", None) == log_path
    ]
    assert len(matching) == 1
    module._configure_security_file_logging(app)
    assert len([
        handler for handler in logger.handlers
        if getattr(handler, "_security_log_path", None) == log_path
    ]) == 1

    logger.warning("append-only-test")
    matching[0].flush()
    assert "append-only-test" in log_path.read_text(encoding="utf-8")


def test_final_security_records_exclude_untrusted_sentinels() -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    app = Flask(__name__)
    app.config.update(SECRET_KEY="security-log-test")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger(module._SECURITY_LOGGER_NAME)
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    form = SimpleNamespace(data={
        "email": "FORM_SENTINEL",
        "password": "PASSWORD_SENTINEL",
        "remember": "REMEMBER_SENTINEL",
        "cap_token": "CAP_SENTINEL",
    })
    try:
        app.add_url_rule("/login", endpoint="security.login", view_func=lambda: "ok", methods=["POST"])
        with app.test_request_context(
            "/login?next=NEXT_SENTINEL",
            method="POST",
            data={
                "email": "FORM_SENTINEL",
                "password": "PASSWORD_SENTINEL",
                "remember": "REMEMBER_SENTINEL",
                "cap_token": "CAP_SENTINEL",
            },
            headers={
                "Referer": "https://example.test/?token=REFERRER_SENTINEL",
                "Authorization": "Bearer AUTH_SENTINEL",
                "User-Agent": "UA_SENTINEL",
            },
        ):
            module._log_event(
                "test",
                login_form=form,
                extra={"oauth_token": "OAUTH_SENTINEL"},
            )
            module._log_login_request()
            module._log_login_response(
                Response(status=302, headers={"Location": "/?token=LOCATION_SENTINEL"})
            )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    emitted = stream.getvalue()
    assert "Security test" in emitted
    assert "Security login POST received" in emitted
    assert "Security login response" in emitted
    for sentinel in (
        "FORM_SENTINEL", "PASSWORD_SENTINEL", "REMEMBER_SENTINEL",
        "CAP_SENTINEL", "NEXT_SENTINEL", "REFERRER_SENTINEL",
        "AUTH_SENTINEL", "UA_SENTINEL", "OAUTH_SENTINEL", "LOCATION_SENTINEL",
    ):
        assert sentinel not in emitted


def test_watched_handler_reopens_after_external_rotation(tmp_path) -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    app = Flask(__name__)
    log_path = tmp_path / "security" / "security.log"
    app.config["SECURITY_LOG_FILE"] = str(log_path)
    module._configure_security_file_logging(app)
    logger = logging.getLogger(module._SECURITY_LOGGER_NAME)
    logger.warning("before-rotation")
    rotated = log_path.with_suffix(".log.1")
    log_path.rename(rotated)
    log_path.touch(mode=0o600)
    logger.warning("after-rotation")
    for handler in logger.handlers:
        if getattr(handler, "_security_log_path", None) == log_path:
            handler.flush()
    assert "before-rotation" in rotated.read_text(encoding="utf-8")
    assert "after-rotation" in log_path.read_text(encoding="utf-8")


def test_watched_handler_reports_write_failure(monkeypatch, tmp_path) -> None:
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes._security.logging"))
    handler = module._VisibleWatchedFileHandler(tmp_path / "security.log")
    calls = []
    service_logger = logging.getLogger("gunicorn.error")
    monkeypatch.setattr(service_logger, "error", lambda *args, **kwargs: calls.append((args, kwargs)))
    try:
        raise OSError("WRITE_SENTINEL")
    except OSError:
        handler.handleError(logging.LogRecord("test", logging.INFO, __file__, 1, "msg", (), None))
    assert calls
    assert calls[0][1]["exc_info"] is True
