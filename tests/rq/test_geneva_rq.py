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
            "schema_version": 1,
            "durations_minutes": data.get("durations_minutes", [30]),
            "ari_years": data.get("ari_years", [10]),
            "distribution_type": data.get("distribution_type", "neh4_type_b"),
            "rebuild": bool(data.get("rebuild", False)),
            "sources": data.get("sources"),
        }


class _GenevaStub:
    def __init__(self) -> None:
        self.frequency_panel_service = _FrequencyPanelServiceStub()
        self.started_calls = 0
        self.finished_calls = 0
        self.build_calls = 0
        self.prepare_calls = 0
        self.run_batch_calls = 0
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
        distribution_type: str = "neh4_type_b",
        rebuild: bool = False,
        sources: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.build_calls += 1
        return {
            "status": "ok",
            "durations_minutes": list(durations_minutes or []),
            "ari_years": list(ari_years or []),
            "distribution_type": distribution_type,
            "rebuild": bool(rebuild),
            "sources": sources,
        }

    def prepare_hrus(
        self,
        *,
        force_rebuild: bool = False,
        input_refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.prepare_calls += 1
        return {
            "status": "ok",
            "force_rebuild": bool(force_rebuild),
            "input_refs": input_refs,
        }

    def run_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.run_batch_calls += 1
        return {"status": "ok", "payload": dict(payload)}


@pytest.fixture()
def geneva_rq_env(monkeypatch: pytest.MonkeyPatch):
    geneva = _GenevaStub()
    clear_calls: list[tuple[str, str]] = []
    timestamp_calls: list[tuple[str, object]] = []
    setitem_calls: list[tuple[str, str, int]] = []

    def _clear_cache(runid: str, *, pup_relpath: str) -> None:
        clear_calls.append((runid, str(pup_relpath)))

    def _ensure_controller(wd: str, cfg_fn: str) -> _GenevaStub:
        assert clear_calls, "cache clear should occur before Geneva controller hydration"
        return geneva

    class _PrepStub:
        def __init__(self, wd: str) -> None:
            self._wd = wd
            self.has_sbs = False
            self._timestamps: dict[str, int] = {}

        def timestamp(self, task: object) -> None:
            timestamp_calls.append((self._wd, task))
            self._timestamps[str(task)] = int(self._timestamps.get(str(task), 0))

        def __getitem__(self, key: object) -> int | None:
            return self._timestamps.get(str(key))

        def __setitem__(self, key: str, value: int) -> None:
            self._timestamps[str(key)] = int(value)
            setitem_calls.append((self._wd, str(key), int(value)))

    monkeypatch.setattr(geneva_rq, "clear_nodb_file_cache", _clear_cache)
    monkeypatch.setattr(geneva_rq, "_ensure_geneva_controller", _ensure_controller)
    monkeypatch.setattr(geneva_rq.RedisPrep, "getInstance", lambda wd: _PrepStub(wd))
    monkeypatch.setattr(geneva_rq, "get_wd", lambda runid: f"/tmp/{runid}")
    monkeypatch.setattr(geneva_rq, "get_current_job", lambda: SimpleNamespace(id="job-123"))
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_SECONDS", 0.0)

    return geneva, clear_calls, timestamp_calls, setitem_calls


def test_build_frequency_panel_retries_started_state_lock_and_runs_job(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
) -> None:
    geneva, clear_calls, _, _ = geneva_rq_env
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
    assert clear_calls == [("run-1", "geneva.nodb")]
    assert geneva.last_started_status == "Building Geneva frequency panel..."


def test_build_frequency_panel_continues_when_started_state_lock_never_available(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva, clear_calls, _, _ = geneva_rq_env
    geneva.started_failures_remaining = 99
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_ATTEMPTS", 3)

    result = geneva_rq.run_geneva_build_frequency_panel_rq("run-1", "cfg", {})

    assert result["status"] == "ok"
    assert geneva.build_calls == 1
    assert geneva.started_calls == 3
    assert geneva.finished_calls == 1
    assert clear_calls == [("run-1", "geneva.nodb")]


def test_build_frequency_panel_continues_when_finished_state_lock_busy(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva, clear_calls, _, _ = geneva_rq_env
    geneva.finished_failures_remaining = 99
    monkeypatch.setattr(geneva_rq, "GENEVA_STATE_LOCK_RETRY_ATTEMPTS", 2)

    result = geneva_rq.run_geneva_build_frequency_panel_rq("run-1", "cfg", {})

    assert result["status"] == "ok"
    assert geneva.build_calls == 1
    assert geneva.started_calls == 1
    assert geneva.finished_calls == 2
    assert clear_calls == [("run-1", "geneva.nodb")]


def test_prepare_hrus_clears_cache_and_runs(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
) -> None:
    geneva, clear_calls, _, _ = geneva_rq_env

    result = geneva_rq.run_geneva_prepare_hrus_rq(
        "run-2",
        "cfg",
        {"force_rebuild": True, "input_refs": {"dem": "abc"}},
    )

    assert result["status"] == "ok"
    assert result["force_rebuild"] is True
    assert result["input_refs"] == {"dem": "abc"}
    assert geneva.prepare_calls == 1
    assert clear_calls == [("run-2", "geneva.nodb")]


def test_run_batch_clears_cache_and_runs(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
) -> None:
    geneva, clear_calls, timestamp_calls, _ = geneva_rq_env

    payload = {"durations_minutes": [15], "note": "batch"}
    result = geneva_rq.run_geneva_run_batch_rq("run-3", "cfg", payload)

    assert result["status"] == "ok"
    assert result["payload"] == payload
    assert geneva.run_batch_calls == 1
    assert clear_calls == [("run-3", "geneva.nodb")]
    assert timestamp_calls == [("/tmp/run-3", geneva_rq.TaskEnum.run_geneva)]


def test_run_batch_backfills_init_sbs_timestamp_for_legacy_sbs_runs(
    geneva_rq_env: tuple[_GenevaStub, list[tuple[str, str]], list[tuple[str, object]], list[tuple[str, str, int]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva, _clear_calls, timestamp_calls, setitem_calls = geneva_rq_env

    prep_holder: dict[str, Any] = {}

    class _PrepStubWithLegacy:
        def __init__(self, wd: str) -> None:
            self._wd = wd
            self.has_sbs = True
            self._timestamps = {
                str(geneva_rq.TaskEnum.landuse_map): 1234,
            }
            prep_holder["prep"] = self

        def timestamp(self, task: object) -> None:
            timestamp_calls.append((self._wd, task))

        def __getitem__(self, key: object) -> int | None:
            return self._timestamps.get(str(key))

        def __setitem__(self, key: str, value: int) -> None:
            self._timestamps[str(key)] = int(value)
            setitem_calls.append((self._wd, str(key), int(value)))

    monkeypatch.setattr(geneva_rq.RedisPrep, "getInstance", lambda wd: _PrepStubWithLegacy(wd))

    result = geneva_rq.run_geneva_run_batch_rq("run-legacy", "cfg", {"k": "v"})

    assert result["status"] == "ok"
    assert setitem_calls == [("/tmp/run-legacy", geneva_rq.TaskEnum.init_sbs_map.value, 1234)]
    assert timestamp_calls == [("/tmp/run-legacy", geneva_rq.TaskEnum.run_geneva)]
