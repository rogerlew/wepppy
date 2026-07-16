from __future__ import annotations

from typing import Any

import pytest
from rq.exceptions import InvalidJobOperation

from wepppy.rq import cancel_job


pytestmark = pytest.mark.unit


class _FakeJob:
    def __init__(self, job_id: str, status: str, meta: dict[str, str] | None = None) -> None:
        self.id = job_id
        self._status = status
        self.meta = dict(meta or {})
        self.cancel_calls = 0

    def get_status(self) -> str:
        return self._status

    def cancel(self) -> None:
        self.cancel_calls += 1
        if self._status == "finished":
            raise InvalidJobOperation

    def save_meta(self) -> None:
        pass


def test_cancel_finished_dispatch_parent_still_cancels_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _FakeJob("child", "queued")
    parent = _FakeJob("parent", "finished", {"jobs:0,scheme:concept_1": "child"})
    monkeypatch.setattr(
        cancel_job.Job,
        "fetch",
        lambda job_id, connection: child if job_id == "child" else parent,
    )

    cancel_job._cancel_job_recursive(parent, object())  # type: ignore[arg-type]

    assert parent.cancel_calls == 1
    assert child.cancel_calls == 1


def test_cancel_dispatch_parent_marks_request_under_shared_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str]] = []

    class _Lock:
        def __enter__(self):
            events.append(("lock", "enter"))

        def __exit__(self, exc_type, exc, tb):
            events.append(("lock", "exit"))
            return False

    class _Redis:
        def lock(self, key, *, timeout, blocking_timeout):
            assert key == "agfields:suite_dispatch:parent"
            assert (timeout, blocking_timeout) == (30, 30)
            return _Lock()

    child = _FakeJob("child", "queued")
    parent = _FakeJob(
        "parent",
        "finished",
        {
            "child_dispatch_lock_key": "agfields:suite_dispatch:parent",
            "jobs:0,scheme:concept_1": "child",
        },
    )

    def save_parent_meta() -> None:
        events.append(("parent", "saved"))

    parent.save_meta = save_parent_meta  # type: ignore[method-assign]
    monkeypatch.setattr(
        cancel_job.Job,
        "fetch",
        lambda job_id, connection: child if job_id == "child" else parent,
    )

    cancel_job._cancel_job_recursive(parent, _Redis())  # type: ignore[arg-type]

    assert parent.meta["cancel_requested"] is True
    assert events == [("lock", "enter"), ("parent", "saved"), ("lock", "exit")]
    assert child.cancel_calls == 1
