from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Flask

try:
    from wepppy.weppcloud.routes.upload_bp import upload_bp
except ImportError:
    pytest.skip("Upload blueprint dependencies missing", allow_module_level=True)

pytestmark = pytest.mark.routes


def test_upload_health_endpoint() -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(upload_bp)

    with app.test_client() as client:
        response = client.get("/upload/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["scope"] == "upload"
    assert payload["message"] == "upload health endpoint"
    assert payload["prefix"] == "/upload"
