from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.rq.batch_rq as batch_rq


pytestmark = pytest.mark.unit


class DummyJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.meta: dict[str, str] = {}

    def save(self) -> None:
        return None


def test_delete_batch_rq_removes_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    batch_name = "demo"
    batch_wd = tmp_path / batch_name
    (batch_wd / "_base").mkdir(parents=True)
    (batch_wd / "runs" / "r001").mkdir(parents=True)
    (batch_wd / "runs" / "r002").mkdir(parents=True)

    runner = type("Runner", (), {"wd": str(batch_wd)})()
    cleaned_runids: list[str] = []
    cleaned_wds: list[str] = []
    published: list[str] = []

    monkeypatch.setattr(batch_rq, "get_current_job", lambda: DummyJob("job-del-1"))
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda name: runner,
    )
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "cleanup_run_instances",
        lambda wd: 0,
    )
    monkeypatch.setattr(
        batch_rq,
        "_cleanup_batch_run_cache_and_locks",
        lambda runid: cleaned_runids.append(runid),
    )
    monkeypatch.setattr(
        batch_rq.NoDbBase,
        "cleanup_run_instances",
        lambda wd: cleaned_wds.append(wd) or 0,
    )
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )
    monkeypatch.setattr(batch_rq, "_active_batch_job_summaries", lambda *args, **kwargs: [])

    result = batch_rq.delete_batch_rq(batch_name)

    assert result == {"batch_name": batch_name, "deleted": True}
    assert not batch_wd.exists()
    assert set(cleaned_runids) == {
        "batch;;demo;;_base",
        "batch;;demo;;r001",
        "batch;;demo;;r002",
    }
    assert str(batch_wd) in cleaned_wds
    assert any("TRIGGER batch BATCH_DELETE_COMPLETED" in message for message in published)


def test_delete_batch_rq_handles_missing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[str] = []

    monkeypatch.setattr(batch_rq, "get_current_job", lambda: DummyJob("job-del-2"))
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda name: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )
    monkeypatch.setattr(batch_rq, "_active_batch_job_summaries", lambda *args, **kwargs: [])

    result = batch_rq.delete_batch_rq("missing")

    assert result == {"batch_name": "missing", "deleted": False, "already_missing": True}
    assert any("TRIGGER batch BATCH_DELETE_COMPLETED" in message for message in published)


def test_delete_batch_rq_raises_when_batch_jobs_active(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    batch_name = "demo"
    batch_wd = tmp_path / batch_name
    batch_wd.mkdir(parents=True)

    runner = type("Runner", (), {"wd": str(batch_wd)})()
    published: list[str] = []

    monkeypatch.setattr(batch_rq, "get_current_job", lambda: DummyJob("job-del-3"))
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda name: runner,
    )
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "cleanup_run_instances",
        lambda wd: 0,
    )
    monkeypatch.setattr(
        batch_rq.NoDbBase,
        "cleanup_run_instances",
        lambda wd: 0,
    )
    monkeypatch.setattr(
        batch_rq,
        "_active_batch_job_summaries",
        lambda *args, **kwargs: ["job-99:started:run_batch_watershed_rq"],
    )
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )

    with pytest.raises(RuntimeError, match="jobs are active"):
        batch_rq.delete_batch_rq(batch_name)

    assert batch_wd.exists()
    assert any("TRIGGER batch BATCH_DELETE_FAILED" in message for message in published)
