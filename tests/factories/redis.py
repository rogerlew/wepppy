"""Redis-related testing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from .rq import RQRecorder


@dataclass
class RedisPrepState:
    removed: List[Any] = field(default_factory=list)
    job_history: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def job_ids(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for key, job_id in self.job_history:
            mapping[key] = job_id
        return mapping


def make_redis_prep(
    recorder: Optional[RQRecorder] = None,
    *,
    initial_job_ids: Optional[Iterable[Tuple[str, str]]] = None,
) -> Type["RedisPrepStub"]:
    """Create a RedisPrep stub class bound to an optional recorder."""

    class RedisPrepStub:
        _instances: Dict[str, "RedisPrepStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.state = RedisPrepState()
            if initial_job_ids:
                self.state.job_history.extend(initial_job_ids)

        @classmethod
        def getInstance(cls, wd: str) -> "RedisPrepStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @classmethod
        def reset_instances(cls) -> None:
            cls._instances.clear()

        def remove_timestamp(self, task) -> None:  # noqa: ANN001 - signature parity
            self.state.removed.append(task)
            if recorder is not None:
                recorder.redis_entries.append(f"remove:{task}")

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            entry = (key, job_id)
            self.state.job_history.append(entry)
            if recorder is not None:
                recorder.redis_entries.append(f"job:{key}:{job_id}")

        # Convenience mirror to minimise test churn
        @property
        def removed(self) -> List[Any]:
            return self.state.removed

        @property
        def job_ids(self) -> Dict[str, str]:
            return self.state.job_ids

        @property
        def job_history(self) -> List[Tuple[str, str]]:
            return self.state.job_history

    return RedisPrepStub


def make_redis_client(recorder: Optional[RQRecorder] = None):
    """Factory for a context-managed redis client stub."""

    class RedisClientStub:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            if recorder is not None:
                recorder.redis_entries.append(("client", kwargs))

        def __enter__(self) -> "RedisClientStub":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            return None

    return RedisClientStub

