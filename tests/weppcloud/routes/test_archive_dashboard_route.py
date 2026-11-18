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


def test_resolve_archive_job_state_does_not_clear_stale_job_id(
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
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "stale-job"


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


@pytest.mark.parametrize(
    ("roles", "user_id", "owner_ids", "expected"),
    [
        ({"Root"}, 0, set(), True),
        ({"Admin"}, 8, {7}, False),
        ({"User"}, 7, {7}, True),
        ({"User"}, 8, {7}, False),
    ],
)
def test_private_archive_listing_is_owner_or_root_only(
    roles: set[str],
    user_id: int,
    owner_ids: set[int],
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = type("User", (), {
        "id": user_id,
        "has_role": lambda self, role: role in roles,
    })()
    monkeypatch.setattr(archive_dashboard_module, "current_user", user)
    monkeypatch.setattr(
        archive_dashboard_module,
        "get_run_owners_lazy",
        lambda _runid: [type("Owner", (), {"id": value})() for value in owner_ids],
    )
    assert archive_dashboard_module._can_list_private_archives("run-1") is expected
