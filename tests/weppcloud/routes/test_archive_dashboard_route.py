from __future__ import annotations

import pytest
from rq.exceptions import NoSuchJobError

import wepppy.weppcloud.routes.archive_dashboard.archive_dashboard as archive_dashboard_module

pytestmark = pytest.mark.routes


class _PrepStub:
    def __init__(self, archive_job_id: str | None) -> None:
        self.archive_job_id = archive_job_id
        self.clear_calls = 0

    def get_archive_job_id(self) -> str | None:
        return self.archive_job_id

    def clear_archive_job_id(self) -> None:
        self.clear_calls += 1
        self.archive_job_id = None


class _RedisStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture()
def archive_dashboard_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(archive_dashboard_module, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(archive_dashboard_module.redis, "Redis", lambda **kwargs: _RedisStub())


def test_resolve_archive_job_state_clears_stale_job_id(
    archive_dashboard_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep = _PrepStub("stale-job")
    monkeypatch.setattr(
        archive_dashboard_module.Job,
        "fetch",
        lambda *args, **kwargs: (_ for _ in ()).throw(NoSuchJobError("missing")),
    )

    in_progress, job_id = archive_dashboard_module._resolve_archive_job_state(prep)

    assert in_progress is False
    assert job_id is None
    assert prep.clear_calls == 1
    assert prep.archive_job_id is None


def test_resolve_archive_job_state_preserves_active_job_id(
    archive_dashboard_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep = _PrepStub("active-job")

    class RunningJob:
        def get_status(self, refresh: bool = False):
            return "started"

    monkeypatch.setattr(archive_dashboard_module.Job, "fetch", lambda *args, **kwargs: RunningJob())

    in_progress, job_id = archive_dashboard_module._resolve_archive_job_state(prep)

    assert in_progress is True
    assert job_id == "active-job"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "active-job"


def test_resolve_archive_job_state_preserves_job_id_on_lookup_error(
    archive_dashboard_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep = _PrepStub("active-job")
    monkeypatch.setattr(
        archive_dashboard_module.Job,
        "fetch",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    in_progress, job_id = archive_dashboard_module._resolve_archive_job_state(prep)

    assert in_progress is True
    assert job_id == "active-job"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "active-job"
