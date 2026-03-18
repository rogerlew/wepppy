from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from wepppy.weppcloud.utils import run_ttl


pytestmark = pytest.mark.unit


def test_read_ttl_state_defaults_missing_expires_at(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    (wd / run_ttl.TTL_FILENAME).write_text(
        json.dumps(
            {
                "version": 1,
                "ttl_days": 90,
                "policy": run_ttl.POLICY_DISABLED,
                "user_disabled": False,
                "disabled_reason": run_ttl.DISABLED_REASON_READONLY,
                "delete_state": run_ttl.DELETE_STATE_ACTIVE,
                "db_cleared": False,
            }
        ),
        encoding="utf-8",
    )

    state = run_ttl.read_ttl_state(str(wd))

    assert state is not None
    assert "expires_at" in state
    assert state["expires_at"] is None


def test_read_ttl_state_preserves_existing_expires_at(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    (wd / run_ttl.TTL_FILENAME).write_text(
        json.dumps(
            {
                "version": 1,
                "ttl_days": 90,
                "policy": run_ttl.POLICY_ROLLING,
                "expires_at": "2026-12-31T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    state = run_ttl.read_ttl_state(str(wd))

    assert state is not None
    assert state["expires_at"] == "2026-12-31T00:00:00Z"


def test_ensure_ttl_state_creates_missing_ttl(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir()

    state = run_ttl.ensure_ttl_state(str(wd), touched_by="context")

    assert state is not None
    assert (wd / run_ttl.TTL_FILENAME).exists()
    assert state["version"] == run_ttl.TTL_VERSION
    assert state["last_touched_by"] == "context"
    assert state["policy"] in {
        run_ttl.POLICY_ROLLING,
        run_ttl.POLICY_DISABLED,
        run_ttl.POLICY_EXCLUDED,
    }


def test_ensure_ttl_state_repairs_partial_payload(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    (wd / "READONLY").touch()
    ttl_file = wd / run_ttl.TTL_FILENAME
    ttl_file.write_text(
        json.dumps(
            {
                "version": 1,
                "ttl_days": 90,
                "policy": run_ttl.POLICY_DISABLED,
                "user_disabled": False,
                "disabled_reason": run_ttl.DISABLED_REASON_READONLY,
                "delete_state": run_ttl.DELETE_STATE_ACTIVE,
                "db_cleared": False,
            }
        ),
        encoding="utf-8",
    )

    repaired = run_ttl.ensure_ttl_state(str(wd), touched_by="context")

    assert repaired is not None
    assert repaired["expires_at"] is None
    persisted = json.loads(ttl_file.read_text(encoding="utf-8"))
    assert persisted["expires_at"] is None
    assert persisted["last_touched_by"] == "context"
    assert persisted["updated_at"]


def test_ensure_ttl_state_does_not_rewrite_healthy_payload(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    initial_time = datetime(2026, 3, 18, 19, 0, tzinfo=timezone.utc)
    run_ttl.initialize_ttl(str(wd), now=initial_time, touched_by="create")
    ttl_file = wd / run_ttl.TTL_FILENAME
    before = json.loads(ttl_file.read_text(encoding="utf-8"))

    later = datetime(2026, 3, 18, 21, 0, tzinfo=timezone.utc)
    ensured = run_ttl.ensure_ttl_state(str(wd), now=later, touched_by="context")
    after = json.loads(ttl_file.read_text(encoding="utf-8"))

    assert ensured is not None
    assert after == before
