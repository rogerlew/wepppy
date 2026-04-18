from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from wepppy.nodb.base import NoDbAlreadyLockedError
import wepppy.rq.geneva_rq as geneva_rq


pytestmark = pytest.mark.unit


class _FrequencyPanelServiceStub:
    @staticmethod
    def normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        return {
            "durations_minutes": data.get("durations_minutes", [30]),
            "ari_years": data.get("ari_years", [10]),
            "rebuild": bool(data.get("rebuild", False)),
            "sources": data.get("sources"),
        }


class _GenevaStub:
    def __init__(self) -> None:
        self.frequency_panel_service = _FrequencyPanelServiceStub()
        self.started_calls = 0
        self.finished_calls = 0
        self.build_calls = 0
        self.started_failures_remaining = 0
        self.finished_failures_remaining = 0
        self.last_started_status: str | None = None

    def mark_job_started(self, job_id: str, *, status_message: str) -> None:
        self.started_calls += 1
        self.last_started_status = status_message
        if self.started_failures_remaining > 0:
            self.started_failures_remaining -= 1
            raise NoDbAlreadyLockedError(f"start lock busy for {job_id}")

    def mark_job_finished(self, job_id: str) -> None:
        self.finished_calls += 1
        if self.finished_failures_remaining > 0:
            self.finished_failures_remaining -= 1
            raise NoDbAlreadyLockedError(f"finish lock busy for {job_id}")

    def build_frequency_panel(
        self,
        *,
        durations_minutes: list[int] | None = None,
        ari_years: list[int] | None = None,
        rebuild: bool = False,
        sources: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.build_calls += 1
        return {
            "status": "ok",
            "durations_minutes": list(durations_minutes or []),
            "ari_years": list(ari_years or []),
            "rebuild": bool(rebuild),
            "sources": sources,
        }


@pytest.fixture()
def geneva_rq_env(monkeypatch: pytest.MonkeyPatch):
    geneva = _GenevaStub()

    monkeypatch.setattr(geneva_rq, "_ensure_geneva_controller", lambda wd, cfg_fn: geneva)
    monkeypatch.setattr(geneva_rq, "get_wd", lambda runid: f"/tmp/{runid}")
    monkeypatch.setattr(geneva_rq, "get_current_job", lambda: SimpleNamespace(id="job-123"))
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_SECONDS", 0.0)

    return geneva


def test_build_frequency_panel_retries_started_state_lock_and_runs_job(
    geneva_rq_env: _GenevaStub,
) -> None:
    geneva = geneva_rq_env
    geneva.started_failures_remaining = 1

    result = geneva_rq.run_geneva_build_frequency_panel_rq(
        "run-1",
        "cfg",
        {"durations_minutes": [30], "ari_years": [10], "rebuild": True},
    )

    assert result["status"] == "ok"
    assert geneva.build_calls == 1
    assert geneva.started_calls == 2
    assert geneva.finished_calls == 1
    assert geneva.last_started_status == "Building Geneva frequency panel..."


def test_build_frequency_panel_continues_when_started_state_lock_never_available(
    geneva_rq_env: _GenevaStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva = geneva_rq_env
    geneva.started_failures_remaining = 99
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_ATTEMPTS", 3)

    result = geneva_rq.run_geneva_build_frequency_panel_rq("run-1", "cfg", {})

    assert result["status"] == "ok"
    assert geneva.build_calls == 1
    assert geneva.started_calls == 3
    assert geneva.finished_calls == 1


def test_build_frequency_panel_continues_when_finished_state_lock_busy(
    geneva_rq_env: _GenevaStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva = geneva_rq_env
    geneva.finished_failures_remaining = 99
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_ATTEMPTS", 2)

    result = geneva_rq.run_geneva_build_frequency_panel_rq("run-1", "cfg", {})

    assert result["status"] == "ok"
    assert geneva.build_calls == 1
    assert geneva.started_calls == 1
    assert geneva.finished_calls == 2
