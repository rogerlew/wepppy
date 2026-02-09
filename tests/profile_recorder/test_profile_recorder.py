from __future__ import annotations

from types import SimpleNamespace

import json

import pytest

from wepppy.profile_recorder.config import RecorderConfig
from wepppy.profile_recorder.profile_recorder import ProfileRecorder


@pytest.mark.unit
def test_append_event_writes_audit_and_draft(tmp_path, monkeypatch):
    run_dir = tmp_path / "demo-run"
    run_dir.mkdir()

    data_repo = tmp_path / "data"
    recorder = ProfileRecorder(config=RecorderConfig(data_repo_root=data_repo, assembler_enabled=True))

    monkeypatch.setattr(
        "wepppy.profile_recorder.profile_recorder.get_wd",
        lambda runid: run_dir,
    )

    event = {
        "runId": "demo-run",
        "id": "evt-1",
        "stage": "request",
        "method": "POST",
        "endpoint": "/tasks/run",
    }

    recorder.append_event(event, user=SimpleNamespace(is_authenticated=False))

    audit_file = run_dir / "_logs" / "profile.events.jsonl"
    assert audit_file.exists()
    content = audit_file.read_text(encoding="utf-8").strip()
    assert content
    parsed = json.loads(content)
    assert parsed["runId"] == "demo-run"
    assert parsed["id"] == "evt-1"

    draft_path = data_repo / "profiles" / "_drafts" / "demo-run" / "stream" / "events.jsonl"
    assert draft_path.exists()
    draft_content = draft_path.read_text(encoding="utf-8").strip()
    assert draft_content


@pytest.mark.unit
def test_append_event_authenticated_user_excludes_email(tmp_path, monkeypatch):
    run_dir = tmp_path / "demo-run"
    run_dir.mkdir()

    data_repo = tmp_path / "data"
    recorder = ProfileRecorder(config=RecorderConfig(data_repo_root=data_repo, assembler_enabled=True))

    monkeypatch.setattr(
        "wepppy.profile_recorder.profile_recorder.get_wd",
        lambda runid: run_dir,
    )

    event = {
        "runId": "demo-run",
        "id": "evt-2",
        "stage": "request",
        "method": "GET",
        "endpoint": "/tasks/run",
    }
    user = SimpleNamespace(is_authenticated=True, id=7, email="user@example.com")

    recorder.append_event(event, user=user)

    audit_file = run_dir / "_logs" / "profile.events.jsonl"
    parsed_audit = json.loads(audit_file.read_text(encoding="utf-8").strip())
    assert parsed_audit["user"] == {"id": 7}
    assert "email" not in parsed_audit["user"]

    draft_path = data_repo / "profiles" / "_drafts" / "demo-run" / "stream" / "events.jsonl"
    parsed_draft = json.loads(draft_path.read_text(encoding="utf-8").strip())
    assert parsed_draft["user"] == {"id": 7}
    assert "email" not in parsed_draft["user"]


@pytest.mark.unit
def test_append_event_strips_raw_request_bodies_by_default(tmp_path, monkeypatch):
    run_dir = tmp_path / "demo-run"
    run_dir.mkdir()

    data_repo = tmp_path / "data"
    recorder = ProfileRecorder(config=RecorderConfig(data_repo_root=data_repo, assembler_enabled=True))

    monkeypatch.setattr(
        "wepppy.profile_recorder.profile_recorder.get_wd",
        lambda runid: run_dir,
    )

    event = {
        "runId": "demo-run",
        "id": "evt-3",
        "stage": "request",
        "method": "POST",
        "endpoint": "/tasks/run",
        "requestMeta": {
            "bodyType": "json",
            "jsonPayload": json.dumps({
                "email": "user@example.com",
                "token": "abc123",
                "slope": 5,
            }),
            "formValues": {
                "email": "user@example.com",
                "note": "keep-key-only",
            },
            "bodyPreview": "{\"email\":\"user@example.com\"}",
        },
    }

    recorder.append_event(event, user=SimpleNamespace(is_authenticated=False))

    audit_file = run_dir / "_logs" / "profile.events.jsonl"
    parsed = json.loads(audit_file.read_text(encoding="utf-8").strip())
    meta = parsed["requestMeta"]
    assert "jsonPayload" not in meta
    assert "formValues" not in meta
    assert "bodyPreview" not in meta
    assert meta["jsonKeys"] == ["email", "token", "slope"]
    assert meta["formKeys"] == ["email", "note"]

    draft_path = data_repo / "profiles" / "_drafts" / "demo-run" / "stream" / "events.jsonl"
    parsed_draft = json.loads(draft_path.read_text(encoding="utf-8").strip())
    draft_meta = parsed_draft["requestMeta"]
    assert "jsonPayload" not in draft_meta
    assert "formValues" not in draft_meta
    assert "bodyPreview" not in draft_meta
    assert draft_meta["jsonKeys"] == ["email", "token", "slope"]
    assert draft_meta["formKeys"] == ["email", "note"]


@pytest.mark.unit
def test_append_event_allow_body_values_redacts_sensitive_fields(tmp_path, monkeypatch):
    run_dir = tmp_path / "demo-run"
    run_dir.mkdir()

    data_repo = tmp_path / "data"
    recorder = ProfileRecorder(
        config=RecorderConfig(
            data_repo_root=data_repo,
            assembler_enabled=True,
            allow_body_values=True,
        )
    )

    monkeypatch.setattr(
        "wepppy.profile_recorder.profile_recorder.get_wd",
        lambda runid: run_dir,
    )

    event = {
        "runId": "demo-run",
        "id": "evt-4",
        "stage": "request",
        "method": "POST",
        "endpoint": "/tasks/run",
        "requestMeta": {
            "bodyType": "json",
            "jsonPayload": json.dumps({
                "email": "user@example.com",
                "token": "abc123",
                "slope": 5,
            }),
            "formValues": {
                "email": "user@example.com",
                "token": "abc123",
                "note": "safe",
            },
            "bodyPreview": "preview-value",
        },
    }

    recorder.append_event(event, user=SimpleNamespace(is_authenticated=False))

    audit_file = run_dir / "_logs" / "profile.events.jsonl"
    parsed = json.loads(audit_file.read_text(encoding="utf-8").strip())
    meta = parsed["requestMeta"]
    assert json.loads(meta["jsonPayload"]) == {
        "email": "[redacted]",
        "token": "[redacted]",
        "slope": 5,
    }
    assert meta["formValues"] == {
        "email": "[redacted]",
        "token": "[redacted]",
        "note": "safe",
    }
    assert meta["bodyPreview"] == "preview-value"
