"""Pytest-facing helper fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

import pytest

from .redis import make_redis_client, make_redis_prep
from .rq import RQRecorder, make_queue, make_redis_conn


@dataclass
class RQEnvironment:
    recorder: RQRecorder
    redis_prep_class: Type[Any]

    def redis_conn_factory(self, *, label: str = "redis-conn") -> Callable[[], Any]:
        return lambda: make_redis_conn(self.recorder, label)

    def queue_class(self, *, default_job_id: str = "job-123") -> Type[Any]:
        return make_queue(self.recorder, default_job_id=default_job_id)

    def redis_client_class(self) -> Type[Any]:
        return make_redis_client(self.recorder)

    def patch_module(
        self,
        monkeypatch: pytest.MonkeyPatch,
        module: Any,
        *,
        redis_prep_attr: str = "RedisPrep",
        redis_conn_attr: str = "_redis_conn",
        queue_attr: str = "Queue",
        default_job_id: str = "job-123",
        redis_label: str = "redis-conn",
    ) -> None:
        monkeypatch.setattr(module, redis_prep_attr, self.redis_prep_class)
        monkeypatch.setattr(module, redis_conn_attr, self.redis_conn_factory(label=redis_label))
        monkeypatch.setattr(module, queue_attr, self.queue_class(default_job_id=default_job_id))


@pytest.fixture
def rq_recorder() -> RQRecorder:
    return RQRecorder()


@pytest.fixture
def rq_environment(rq_recorder: RQRecorder) -> RQEnvironment:
    redis_prep_cls = make_redis_prep(rq_recorder)
    return RQEnvironment(recorder=rq_recorder, redis_prep_class=redis_prep_cls)

