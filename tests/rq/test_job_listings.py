from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
from rq.job import JobStatus
from datetime import datetime, timedelta, timezone

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
            get_status=lambda refresh=False: JobStatus.STARTED if job_id.endswith("started") else JobStatus.QUEUED,
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
    assert all(type(item["status"]) is str for item in payloads)
    html = _render_info_details(active_jobs=payloads)
    assert "JobStatus" not in html
    assert "<code>started</code>" in html
    assert "<code>queued</code>" in html


@pytest.mark.parametrize("aware", [False, True])
@pytest.mark.parametrize("status", [JobStatus.FINISHED, JobStatus.FAILED])
def test_recent_jobs_accept_rq_utc_timestamp_generations(monkeypatch, aware, status):
    from rq.job import JobStatus

    ended = datetime.now(timezone.utc) - timedelta(seconds=5)
    if not aware:
        ended = ended.replace(tzinfo=None)
    job = SimpleNamespace(
        id="completed", origin="default", meta={}, args=(), func_name="tasks.run",
        description="run", worker_name="worker", enqueued_at=ended,
        started_at=ended, ended_at=ended, get_status=lambda refresh=False: status,
    )
    monkeypatch.setattr(job_listings, "Queue", lambda name, **kwargs: SimpleNamespace(name=name))
    monkeypatch.setattr(job_listings, "FinishedJobRegistry", lambda **kwargs: SimpleNamespace(key="finished"))
    monkeypatch.setattr(job_listings, "FailedJobRegistry", lambda **kwargs: SimpleNamespace(key="failed"))
    monkeypatch.setattr(job_listings.Job, "fetch_many", lambda *args, **kwargs: [job])
    connection = SimpleNamespace(zrevrange=lambda key, *args: [b"completed"] if key == "finished" else [])
    rows = job_listings.list_recently_completed_jobs(connection, queue_names=["default"])
    assert len(rows) == 1
    assert rows[0]["status"] == getattr(status, "value", status)
    assert type(rows[0]["status"]) is str
    html = _render_info_details(recent_jobs=rows)
    assert "JobStatus" not in html
    assert f"<code>{getattr(status, 'value', status)}</code>" in html
    assert rows[0]["ended_at"] == ended.replace(tzinfo=None).isoformat()


def _render_info_details(*, recent_jobs=(), active_jobs=()):
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

    templates = Path(__file__).resolve().parents[2] / "wepppy/weppcloud/routes/rq/info_details/templates"
    environment = Environment(loader=ChoiceLoader([
        DictLoader({"base_pure.htm": "{% block body %}{% endblock %}"}),
        FileSystemLoader(str(templates)),
    ]))
    return environment.get_template("info_details.htm").render(
        recent_jobs=recent_jobs, failed_jobs=[job for job in recent_jobs if job["status"] == "failed"],
        failed_lookback_seconds=86400,
        active_job_groups=[{"name": "batch", "jobs": active_jobs}],
        url_for_run=lambda endpoint, **kwargs: "/job",
    )
