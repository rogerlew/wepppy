from __future__ import annotations

import json

import pytest

from wepppy.microservices.rq_engine.creation_idempotency import (
    CREATION_IDEMPOTENCY_TTL_SECONDS,
    CreationIdempotencyError,
    build_creation_fingerprint,
    complete_creation,
    release_creation,
    reserve_creation,
)

pytestmark = pytest.mark.microservice


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        xx: bool = False,
        ex: int,
    ) -> bool:
        if nx and key in self.values:
            return False
        if xx and key not in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        self.ttls.pop(key, None)
        return int(existed)


def _fingerprint(dem: str = "ned1/2024") -> str:
    return build_creation_fingerprint(
        mode="preset",
        preset_id="disturbed9002",
        normalized_overrides={"general.dem_db": dem},
        registry_revision="revision-1",
    )


def test_reserve_complete_replay_and_ttl_contract() -> None:
    client = FakeRedis()
    acquired = reserve_creation(
        client,
        idempotency_key="12345678-1234-4234-9234-123456789abc",
        actor_scope="user:42",
        fingerprint=_fingerprint(),
    )
    assert acquired.status == "acquired"
    assert client.ttls[acquired.redis_key] == CREATION_IDEMPOTENCY_TTL_SECONDS
    assert "12345678-1234" not in acquired.redis_key

    concurrent = reserve_creation(
        client,
        idempotency_key="12345678-1234-4234-9234-123456789abc",
        actor_scope="user:42",
        fingerprint=_fingerprint(),
    )
    assert concurrent.status == "in_progress"

    complete_creation(client, acquired, run_id="safe-run", location="/runs/safe-run/disturbed9002")
    replay = reserve_creation(
        client,
        idempotency_key="12345678-1234-4234-9234-123456789abc",
        actor_scope="user:42",
        fingerprint=_fingerprint(),
    )
    assert (replay.status, replay.run_id, replay.location) == (
        "replay",
        "safe-run",
        "/runs/safe-run/disturbed9002",
    )
    assert "token" not in json.loads(client.get(acquired.redis_key) or "{}")


def test_conflict_actor_scope_and_release_contract() -> None:
    client = FakeRedis()
    key = "abcdef12-1234-4234-9234-123456789abc"
    first = reserve_creation(client, idempotency_key=key, actor_scope="user:42", fingerprint=_fingerprint())
    conflict = reserve_creation(
        client,
        idempotency_key=key,
        actor_scope="user:42",
        fingerprint=_fingerprint("ned1/2016"),
    )
    other_actor = reserve_creation(
        client,
        idempotency_key=key,
        actor_scope="user:43",
        fingerprint=_fingerprint(),
    )

    assert conflict.status == "conflict"
    assert other_actor.status == "acquired"
    assert other_actor.redis_key != first.redis_key
    release_creation(client, first)
    retry = reserve_creation(client, idempotency_key=key, actor_scope="user:42", fingerprint=_fingerprint())
    assert retry.status == "acquired"


@pytest.mark.parametrize("key", ["short", "x" * 201, "invalid key with spaces"])
def test_invalid_client_keys_fail_before_redis_write(key: str) -> None:
    client = FakeRedis()
    with pytest.raises(CreationIdempotencyError):
        reserve_creation(client, idempotency_key=key, actor_scope=None, fingerprint=_fingerprint())
    assert client.values == {}
