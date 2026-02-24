from __future__ import annotations

from dataclasses import dataclass

import pytest

from tools.wctl2 import rq_worker_registry_sync


pytestmark = pytest.mark.unit


@dataclass
class FakeWorker:
    queues: list[str]

    def queue_names(self) -> list[str]:
        return list(self.queues)


class FakeRedis:
    def __init__(self, scan_map: dict[str, list[str | bytes]]) -> None:
        self._scan_map = scan_map
        self.deleted_calls: list[tuple[str, ...]] = []

    def scan_iter(self, match: str):
        for item in self._scan_map.get(match, []):
            yield item

    def delete(self, *keys: str) -> int:
        self.deleted_calls.append(tuple(keys))
        return len(keys)


def test_scan_keys_normalizes_and_sorts() -> None:
    redis_conn = FakeRedis(
        {
            rq_worker_registry_sync._WORKER_KEY_PATTERN: [
                b"rq:worker:b",
                "rq:worker:a",
                b"rq:worker:b",
                b"",
            ]
        }
    )

    keys = rq_worker_registry_sync._worker_hash_keys(redis_conn)

    assert keys == ["rq:worker:a", "rq:worker:b"]


def test_rebuild_worker_registry_sets_rebuilds_from_worker_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_conn = FakeRedis(
        {
            rq_worker_registry_sync._WORKER_KEY_PATTERN: [
                "rq:worker:alpha",
                "rq:worker:beta",
                "rq:worker:missing",
            ],
            rq_worker_registry_sync._WORKER_QUEUE_KEY_PATTERN: [
                "rq:workers:default",
                b"rq:workers:batch",
            ],
        }
    )
    workers = {
        "rq:worker:alpha": FakeWorker(["default"]),
        "rq:worker:beta": FakeWorker(["batch", "default"]),
    }
    registered_workers: list[FakeWorker] = []

    monkeypatch.setattr(
        rq_worker_registry_sync.Worker,
        "find_by_key",
        classmethod(lambda cls, worker_key, connection=None: workers.get(worker_key)),
    )
    monkeypatch.setattr(
        rq_worker_registry_sync.worker_registration,
        "register",
        lambda worker: registered_workers.append(worker),
    )

    result = rq_worker_registry_sync.rebuild_worker_registry_sets(redis_conn)

    assert redis_conn.deleted_calls == [
        ("rq:workers", "rq:workers:batch", "rq:workers:default")
    ]
    assert result == rq_worker_registry_sync.RegistrySyncResult(
        worker_hashes_seen=3,
        workers_registered=2,
        queue_sets_cleared=2,
    )
    assert registered_workers == [workers["rq:worker:alpha"], workers["rq:worker:beta"]]
