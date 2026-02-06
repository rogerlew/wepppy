from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

import wepppy.rq.project_rq as project_rq

pytestmark = pytest.mark.unit


def _stub_user_models(monkeypatch: pytest.MonkeyPatch, runid: str):
    class DummyRun:
        runid = "runid"

        def __init__(self, runid_value: str) -> None:
            self.runid = runid_value

    dummy_run = DummyRun(runid)

    class DummyQuery:
        def __init__(self, run: DummyRun) -> None:
            self._run = run

        def filter(self, *args, **kwargs) -> "DummyQuery":
            return self

        def first(self) -> DummyRun:
            return self._run

    DummyRun.query = DummyQuery(dummy_run)

    class DummyUserDatastore:
        def __init__(self) -> None:
            self.deleted: list[DummyRun] = []

        def delete_run(self, run: DummyRun) -> None:
            self.deleted.append(run)

    user_datastore = DummyUserDatastore()

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["get_user_models"])
    monkeypatch.setattr(helpers, "get_user_models", lambda: (DummyRun, None, user_datastore))

    return user_datastore, dummy_run


def _stub_delete_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runid: str,
    job_id: str,
    errno_value: int,
) -> tuple[list[str], list[dict[str, object]], object]:
    job = SimpleNamespace(id=job_id)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: job)

    published: list[str] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append(message),
    )

    def fake_rmtree(_path: Path) -> None:
        raise OSError(errno_value, "busy")

    monkeypatch.setattr(project_rq.shutil, "rmtree", fake_rmtree)
    monkeypatch.setattr(project_rq.time, "sleep", lambda _seconds: None)

    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda _runid: [])
    monkeypatch.setattr(project_rq, "clear_locks", lambda _runid: None)
    import flask

    monkeypatch.setattr(flask, "has_app_context", lambda: True)

    mark_calls: list[dict[str, object]] = []

    def fake_mark_delete_state(
        wd: str,
        state: str,
        *,
        db_cleared: bool | None = None,
        touched_by: str = "delete",
    ) -> None:
        mark_calls.append({
            "wd": wd,
            "state": state,
            "db_cleared": db_cleared,
            "touched_by": touched_by,
        })

    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["mark_delete_state"])
    monkeypatch.setattr(ttl_module, "mark_delete_state", fake_mark_delete_state)

    user_datastore, _dummy_run = _stub_user_models(monkeypatch, runid)
    return published, mark_calls, user_datastore


def test_delete_run_rq_marks_ttl_when_rmtree_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "test-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True)
    (run_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    published, mark_calls, user_datastore = _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="job-1",
        errno_value=project_rq.errno.EBUSY,
    )

    project_rq.delete_run_rq(runid, wd=str(run_dir), delete_files=True)

    assert len(user_datastore.deleted) == 1
    assert run_dir.exists()
    assert any(call["state"] == "queued" for call in mark_calls)
    assert any(call["db_cleared"] is True for call in mark_calls)
    assert not any("delete deferred" in message for message in published)
    assert not any("delete retry" in message for message in published)
    assert not any("delete failed" in message for message in published)


def test_gc_runs_rq_deferred_delete_suppresses_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "gc-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True)
    (run_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    published, mark_calls, user_datastore = _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="job-2",
        errno_value=project_rq.errno.EBUSY,
    )
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["collect_gc_candidates"])
    monkeypatch.setattr(
        ttl_module,
        "collect_gc_candidates",
        lambda *args, **kwargs: [
            {
                "runid": runid,
                "wd": str(run_dir),
                "reason": "queued",
            }
        ],
    )

    result = project_rq.gc_runs_rq(root=str(tmp_path), limit=10, dry_run=False)

    assert result["deleted"] == 0
    assert result["deferred"] == 1
    assert result["errors"] == []
    assert len(user_datastore.deleted) == 1
    assert run_dir.exists()
    assert any(call["state"] == "queued" for call in mark_calls)
    assert any(call["db_cleared"] is True for call in mark_calls)
    assert not any("delete deferred" in message for message in published)
    assert not any("delete retry" in message for message in published)
    assert not any("delete failed" in message for message in published)
