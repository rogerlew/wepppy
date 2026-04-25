from __future__ import annotations

import re

import pytest

pytest.importorskip("flask")
from flask import Flask

from wepppy.weppcloud.utils import helpers


pytestmark = pytest.mark.unit


def test_exception_factory_5xx_includes_error_id() -> None:
    app = Flask(__name__)

    with app.test_request_context("/"):
        response = helpers.exception_factory(
            msg="server failed",
            status_code=500,
            stacktrace="Traceback (most recent call last):\nRuntimeError: boom",
            details="Traceback (most recent call last):\nRuntimeError: boom",
        )

    payload = response.get_json()
    assert response.status_code == 500
    assert payload["error"]["message"] == "server failed"
    assert re.fullmatch(r"[0-9a-f]{32}", payload["error_id"])


def test_error_factory_5xx_includes_error_id() -> None:
    app = Flask(__name__)

    with app.test_request_context("/"):
        response = helpers.error_factory(
            msg="server failed",
            status_code=500,
        )

    payload = response.get_json()
    assert response.status_code == 500
    assert payload["error"]["message"] == "server failed"
    assert re.fullmatch(r"[0-9a-f]{32}", payload["error_id"])


def test_error_factory_4xx_does_not_force_error_id() -> None:
    app = Flask(__name__)

    with app.test_request_context("/"):
        response = helpers.error_factory(
            msg="validation failed",
            status_code=400,
        )

    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"]["message"] == "validation failed"
    assert "error_id" not in payload


def test_exception_factory_4xx_does_not_force_error_id() -> None:
    app = Flask(__name__)

    with app.test_request_context("/"):
        response = helpers.exception_factory(
            msg="validation failed",
            status_code=400,
            stacktrace="traceback-not-required",
            details="missing field",
        )

    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"]["message"] == "validation failed"
    assert payload["error"]["details"] == "missing field"
    assert "error_id" not in payload


def test_exception_factory_run_log_records_error_id(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    app = Flask(__name__)
    run_root = tmp_path / "run-1"
    run_root.mkdir()
    monkeypatch.setattr(helpers, "get_wd", lambda _runid: str(run_root))

    stacktrace = "Traceback (most recent call last):\nRuntimeError: boom"
    with app.test_request_context("/"):
        response = helpers.exception_factory(
            msg="server failed",
            runid="run-1",
            status_code=500,
            stacktrace=stacktrace,
            details=stacktrace,
        )

    payload = response.get_json()
    error_id = payload["error_id"]

    exception_log = (run_root / "exception_factory.log").read_text()
    assert f"error_id={error_id}" in exception_log
    assert stacktrace in exception_log
