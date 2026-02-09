from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask, session
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
