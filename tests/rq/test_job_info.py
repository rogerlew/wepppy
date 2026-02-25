from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from wepppy.rq.job_info import recursive_get_job_details


pytestmark = pytest.mark.unit


@dataclass
class _FakeJob:
    id: str = "job-1"
    meta: dict[str, Any] = field(default_factory=dict)
    status: str = "failed"
    result: Any = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    description: str = "fake job"
    exc_info: str | None = None

    def get_status(self) -> str:
        return self.status


def test_recursive_job_details_prefers_exc_string_meta() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1", "exc_string": "traceback from meta"}, exc_info="traceback from rq")

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["status"] == "failed"
    assert payload["exc_info"] == "traceback from meta"


def test_recursive_job_details_falls_back_to_rq_exc_info() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1"}, exc_info="traceback from rq")

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["exc_info"] == "traceback from rq"


def test_recursive_job_details_exc_info_none_when_missing() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1"})

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["exc_info"] is None

