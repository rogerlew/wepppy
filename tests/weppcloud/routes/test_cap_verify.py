from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.utils.cap_verify as cap_verify_module
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp
from wepppy.weppcloud.utils.cap_guard import CAP_SESSION_KEY

pytestmark = pytest.mark.routes


def test_cap_verify_marks_session_and_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")

    monkeypatch.setattr(cap_verify_module, "verify_cap_token", lambda token: {"success": True})

    with app.test_client() as client:
        response = client.post("/weppcloud/cap/verify", data={"cap_token": "good-token"})

        assert response.status_code == 200
        assert response.get_json() == {}

        with client.session_transaction() as session:
            assert CAP_SESSION_KEY in session
