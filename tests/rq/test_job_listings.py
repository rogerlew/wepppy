from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.rq import job_listings

pytestmark = pytest.mark.unit


def test_list_active_jobs_preserves_queue_labels_states_and_read_only_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    class _Queue:
        def __init__(self, name: str, connection: object) -> None:
            self.name = name
            self.connection = connection

        def get_job_ids(self, *, offset: int, length: int) -> list[str]:
            calls.append(("queued", self.name))
            assert (offset, length) == (0, -1)
            return [f"{self.name}-queued"]

    class _StartedJobRegistry:
        def __init__(self, *, queue: _Queue) -> None:
            self.queue = queue

        def get_job_ids(self, *, start: int, end: int) -> list[str]:
            calls.append(("started", self.queue.name))
            assert (start, end) == (0, -1)
            return [f"{self.queue.name}-started"]

    class _Worker:
        @staticmethod
        def all(*, connection: object) -> list[object]:
            return []

    def _job(job_id: str) -> SimpleNamespace:
        queue_name = job_id.split("-", 1)[0]
        return SimpleNamespace(
            id=job_id,
            origin=f" {queue_name} ",
            meta={},
            args=(),
            func_name=f"tasks.{job_id}",
            description=None,
            worker_name=None,
            enqueued_at=None,
            started_at=None,
            ended_at=None,
            get_status=lambda refresh=False: "started" if job_id.endswith("started") else "queued",
        )

    class _Job:
        @staticmethod
        def fetch_many(job_ids: list[str], *, connection: object) -> list[SimpleNamespace]:
            return [_job(job_id) for job_id in job_ids]

    monkeypatch.setattr(job_listings, "Queue", _Queue)
    monkeypatch.setattr(job_listings, "StartedJobRegistry", _StartedJobRegistry)
    monkeypatch.setattr(job_listings, "Worker", _Worker)
    monkeypatch.setattr(job_listings, "Job", _Job)

    payloads = job_listings.list_active_jobs(
        object(),
        queue_names=("default", "batch"),
    )

    assert calls == [
        ("started", "default"),
        ("queued", "default"),
        ("started", "batch"),
        ("queued", "batch"),
    ]
    assert [(item["job_id"], item["queue"], item["state"]) for item in payloads] == [
        ("batch-started", "batch", "started"),
        ("default-started", "default", "started"),
        ("batch-queued", "batch", "queued"),
        ("default-queued", "default", "queued"),
    ]
