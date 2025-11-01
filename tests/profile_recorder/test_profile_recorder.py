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
