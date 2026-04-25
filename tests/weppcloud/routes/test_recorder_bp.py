from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.recorder_bp as recorder_module

pytestmark = pytest.mark.routes


class _RecorderStub:
    def __init__(self) -> None:
        self.events: list[tuple[dict, object, object]] = []

    def append_event(self, event: dict, user: object, assembler_override: object = None) -> None:
        self.events.append((event, user, assembler_override))


def _response_status(response) -> int:
    if isinstance(response, tuple):
        return int(response[1])
    return int(response.status_code)


def _response_json(response) -> dict:
    if isinstance(response, tuple):
        return response[0].get_json()
    return response.get_json()


def test_recorder_events_accepts_form_encoded_events_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    recorder = _RecorderStub()
    user = SimpleNamespace(email="agent@example.test")

    monkeypatch.setattr(recorder_module, "get_profile_recorder", lambda _app: recorder)
    monkeypatch.setattr(recorder_module.Ron, "getInstanceFromRunID", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(recorder_module, "current_user", user)

    payload = '[{"stage":"request","endpoint":"tasks/run"}]'
    with app.test_request_context(
        "/runs/demo-run/cfg/recorder/events",
        method="POST",
        data={"csrf_token": "csrf-test", "events": payload},
    ):
        response = recorder_module.recorder_events.__wrapped__("demo-run", "cfg")

    assert _response_status(response) == 204
    assert len(recorder.events) == 1
    stored_event, stored_user, assembler_override = recorder.events[0]
    assert stored_event["stage"] == "request"
    assert stored_event["endpoint"] == "tasks/run"
    assert stored_event["runId"] == "demo-run"
    assert stored_event["config"] == "cfg"
    assert stored_user is user
    assert assembler_override is None


def test_recorder_events_rejects_invalid_form_events_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    recorder = _RecorderStub()

    monkeypatch.setattr(recorder_module, "get_profile_recorder", lambda _app: recorder)
    monkeypatch.setattr(recorder_module.Ron, "getInstanceFromRunID", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(recorder_module, "current_user", SimpleNamespace(email="agent@example.test"))

    with app.test_request_context(
        "/runs/demo-run/cfg/recorder/events",
        method="POST",
        data={"csrf_token": "csrf-test", "events": "not-json"},
    ):
        response = recorder_module.recorder_events.__wrapped__("demo-run", "cfg")

    assert _response_status(response) == 400
    assert _response_json(response) == {"error": "events must be a JSON array"}
    assert recorder.events == []
