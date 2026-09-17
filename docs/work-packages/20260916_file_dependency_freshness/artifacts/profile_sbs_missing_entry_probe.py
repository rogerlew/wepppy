"""Actual append-before-capture failure and historical multipart fallback.

No HTTP, Redis, named run, or production/test mutation. Controller discovery and
unrelated config capture are isolated; append, SBS snapshot, promotion, playback
form selection and requests multipart encoding execute their real code.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import requests

from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.profile_recorder.assembler import ProfileAssembler
from wepppy.profile_recorder.playback import PlaybackSession


def test_failure_before_event_entry_is_indistinguishable_from_legacy(tmp_path, monkeypatch):
    run = tmp_path / "source"
    source = run / "disturbed" / "sbs.tif"
    source.parent.mkdir(parents=True)
    old = b"opaque-SBS-generation-one"
    new = b"opaque-SBS-generation-three"
    source.write_bytes(old)
    monkeypatch.setattr(Disturbed, "getInstance", lambda _: SimpleNamespace(disturbed_path=str(source)))
    monkeypatch.setattr(Baer, "getInstance", lambda _: SimpleNamespace(baer_path=None))
    data_root = tmp_path / "data"
    assembler = ProfileAssembler(data_root)
    monkeypatch.setattr(assembler, "_ensure_config_seed", lambda *args: None)
    endpoint = "/rq-engine/api/runs/disposable/disturbed/tasks/upload-sbs"

    def event(event_id):
        return {"stage": "response", "id": event_id, "method": "POST", "ok": True,
                "category": "file_upload", "endpoint": endpoint}

    assembler.handle_event("disposable", "capture", event("first"), run)
    source.write_bytes(new)

    def fail_before_upload_capture(*args):
        raise PermissionError("disposable config-seed boundary failure")

    monkeypatch.setattr(assembler, "_ensure_config_seed", fail_before_upload_capture)
    assembler.handle_event("disposable", "capture", event("second"), run)
    promoted = assembler.promote_draft("disposable", "capture", slug="disposable-profile")
    capture = Path(promoted["capture_path"])
    events = [json.loads(line) for line in (capture / "events.jsonl").read_text().splitlines()]
    session = object.__new__(PlaybackSession)
    session.seed_upload_root = capture / "seed" / "uploads"
    session.run_dir = str(tmp_path / "sandbox")
    session.profile_run_root = Path(promoted["profile_root"]) / "run"
    data, files = session._build_form_request(endpoint, {"bodyType": "form-data"})
    path, mime = files["input_upload_sbs"]
    with path.open("rb") as handle:
        prepared = requests.Request("POST", "https://disposable.invalid/upload",
                                    data=data, files={"input_upload_sbs": (path.name, handle, mime)}).prepare()
    event_dir = session.seed_upload_root / "sbs" / "events" / hashlib.sha256(b"second").hexdigest()
    result = {"recorded_ids": [record["id"] for record in events],
              "second_event_entry_exists": event_dir.exists(),
              "multipart_contains_prior_bytes": old in prepared.body,
              "multipart_contains_new_bytes": new in prepared.body,
              "source_remains_new": source.read_bytes() == new,
              "promoted_events_preserved": len(events) == 2,
              "scope": "real assembler/promotion/form-selection/multipart; injected unrelated capture failure"}
    print("PROFILE_MISSING_ENTRY", json.dumps(result, sort_keys=True))
    Path(__file__).with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    assert result["recorded_ids"] == ["first", "second"]
    assert not result["second_event_entry_exists"]
    assert result["multipart_contains_prior_bytes"] and not result["multipart_contains_new_bytes"]
    assert result["source_remains_new"]
