from __future__ import annotations

import io
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.vector_upload_normalization import (
    RedisScopeLeaseFactory,
    RedisRetentionLedger,
    RetentionActor,
    VectorUploadError,
    acquire_retention_maintenance_lease,
    begin_retention_rebuild_obligation,
    complete_retention_rebuild_obligation,
    prepare_vector_upload,
    reconcile_retention,
    retention_rebuild_obligation_pending,
    validate_feature_collection_geometries,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def vector_filesystem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "vector-normalizer-test")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))


@dataclass
class _Reservation:
    reservation_id: str = "reservation-test"
    committed: int | None = None
    released: bool = False
    attempt_dir: Path | None = None

    def bind_attempt(self, attempt_dir: Path) -> None:
        self.attempt_dir = attempt_dir

    def commit(self, exact_bytes: int) -> None:
        self.committed = exact_bytes

    def release_prewrite(self) -> None:
        self.released = True


class _Ledger:
    def __init__(self) -> None:
        self.reservation = _Reservation()
        self.calls: list[dict[str, Any]] = []

    def reserve(self, **kwargs: Any) -> _Reservation:
        self.calls.append(kwargs)
        return self.reservation


class _CommitFailureReservation(_Reservation):
    def commit(self, exact_bytes: int) -> None:
        raise VectorUploadError(
            "vector_retention_quota_exceeded",
            "simulated accounting failure",
            status_code=507,
        )


class _UnexpectedCommitFailureReservation(_Reservation):
    def commit(self, exact_bytes: int) -> None:
        raise RuntimeError("unexpected accounting failure")


class _Lease:
    def __init__(self) -> None:
        self.owned = True

    def assert_owned(self) -> None:
        if not self.owned:
            raise AssertionError("lease lost")

    def release(self) -> None:
        self.owned = False


def _polygon_payload() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"field_id": 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
                },
            }
        ],
    }


def _prepare_kwargs(tmp_path: Path, ledger: _Ledger) -> dict[str, object]:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    attempts = project / "vector_upload_attempts"
    return {
        "endpoint_max_bytes": 1024 * 1024,
        "attempt_root": attempts,
        "evidence_roots": (attempts,),
        "filesystem_root": tmp_path,
        "project_key": "run:test",
        "workflow": "test",
        "project_identity": "test-run",
        "actor": RetentionActor("human", 7),
        "validator": lambda _path, payload: validate_feature_collection_geometries(payload, ("Polygon", "MultiPolygon")),
        "ledger": ledger,
        "scope_lease_factory": lambda _key: _Lease(),
    }


def test_direct_geojson_retains_original_and_accepts_readback(tmp_path: Path) -> None:
    original = json.dumps(_polygon_payload(), separators=(",", ":")).encode()
    ledger = _Ledger()
    prepared = prepare_vector_upload(
        raw_filename="My Fields.geojson",
        stream=io.BytesIO(original),
        **_prepare_kwargs(tmp_path, ledger),
    )
    original_path = next((prepared.attempt_dir / "original").iterdir())
    assert original_path.name == "My_Fields.geojson.upload"
    assert original_path.read_bytes() == original
    assert stat_mode(original_path) == 0o600
    assert stat_mode(prepared.attempt_dir) == 0o700

    canonical = tmp_path / "project" / "accepted.geojson"
    result = prepared.publish(
        mutation=lambda candidate: shutil.copy2(candidate, canonical) or {"ok": True},
        canonical_path=canonical,
        canonical_relative_path="accepted.geojson",
    )
    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert result == canonical
    assert receipt["status"] == "accepted"
    assert receipt["source_sha256"] == sha256(original)
    assert receipt["canonical_sha256"] == sha256(original)
    assert receipt["actor"] == {"kind": "human", "user_id": 7}
    assert not prepared.candidate_path.exists()
    assert ledger.reservation.committed == sum(
        path.stat().st_size for path in prepared.attempt_dir.rglob("*") if path.is_file()
    )


def test_accounting_failure_never_downgrades_accepted_workflow(tmp_path: Path) -> None:
    original = json.dumps(_polygon_payload(), separators=(",", ":")).encode()
    ledger = _Ledger()
    ledger.reservation = _CommitFailureReservation()
    prepared = prepare_vector_upload(
        raw_filename="accepted.geojson",
        stream=io.BytesIO(original),
        **_prepare_kwargs(tmp_path, ledger),
    )
    canonical = tmp_path / "project" / "accepted.geojson"

    with pytest.raises(VectorUploadError, match="accounting failure"):
        prepared.publish(
            mutation=lambda candidate: shutil.copy2(candidate, canonical),
            canonical_path=canonical,
            canonical_relative_path="accepted.geojson",
        )

    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert canonical.read_bytes() == original
    assert receipt["status"] == "accepted"
    assert receipt["accounting_status"] == "pending"
    assert prepared.is_terminal


@pytest.mark.parametrize("terminal", ["reject", "incomplete"])
def test_unexpected_terminal_accounting_failure_releases_scope_lease(
    tmp_path: Path,
    terminal: str,
) -> None:
    ledger = _Ledger()
    ledger.reservation = _UnexpectedCommitFailureReservation()
    lease = _Lease()
    kwargs = _prepare_kwargs(tmp_path, ledger)
    kwargs["scope_lease_factory"] = lambda _key: lease
    prepared = prepare_vector_upload(
        raw_filename="failure.geojson",
        stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
        **kwargs,
    )

    with pytest.raises(RuntimeError, match="unexpected accounting failure"):
        if terminal == "reject":
            prepared.reject("test_failure")
        else:
            prepared.mark_incomplete_after_mutation("test_failure")

    assert prepared.is_terminal
    assert lease.owned is False


def test_terminal_receipt_write_failure_releases_scope_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.microservices import vector_upload_normalization as normalization

    ledger = _Ledger()
    lease = _Lease()
    kwargs = _prepare_kwargs(tmp_path, ledger)
    kwargs["scope_lease_factory"] = lambda _key: lease
    prepared = prepare_vector_upload(
        raw_filename="failure.geojson",
        stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
        **kwargs,
    )
    monkeypatch.setattr(
        normalization,
        "_atomic_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("receipt write failed")),
    )

    with pytest.raises(OSError, match="receipt write failed"):
        prepared.reject("test_failure")

    assert prepared.is_terminal
    assert lease.owned is False


def test_partial_mutation_is_recorded_incomplete_not_rejected(tmp_path: Path) -> None:
    original = json.dumps(_polygon_payload(), separators=(",", ":")).encode()
    ledger = _Ledger()
    prepared = prepare_vector_upload(
        raw_filename="uncertain.geojson",
        stream=io.BytesIO(original),
        **_prepare_kwargs(tmp_path, ledger),
    )
    canonical = tmp_path / "project" / "accepted.geojson"

    def partial_mutation(candidate: Path) -> None:
        shutil.copy2(candidate, canonical)
        raise RuntimeError("simulated post-replacement failure")

    with pytest.raises(RuntimeError, match="post-replacement"):
        prepared.publish(mutation=partial_mutation, canonical_path=canonical)

    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert receipt["status"] == "incomplete"
    assert receipt["outcome"] == "quarantined"


def test_failed_workflow_validation_quarantines_complete_original_and_candidate(tmp_path: Path) -> None:
    payload = _polygon_payload()
    payload["features"][0]["geometry"] = {"type": "Point", "coordinates": [0.0, 0.0]}  # type: ignore[index]
    original = json.dumps(payload).encode()
    ledger = _Ledger()
    with pytest.raises(VectorUploadError, match="geometry must be") as raised:
        prepare_vector_upload(
            raw_filename="wrong.geojson",
            stream=io.BytesIO(original),
            **_prepare_kwargs(tmp_path, ledger),
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.status_code == 400
    assert receipt["status"] == "rejected"
    assert receipt["outcome"] == "quarantined"
    assert receipt["source_sha256"] == sha256(original)
    assert (attempt / "candidate.geojson").read_bytes() == original
    assert ledger.reservation.committed is not None


def test_deep_geometry_is_stably_rejected_and_quarantined(tmp_path: Path) -> None:
    payload = _polygon_payload()
    coordinates: object = [0.0, 0.0]
    for _ in range(20):
        coordinates = [coordinates]
    payload["features"][0]["geometry"] = {  # type: ignore[index]
        "type": "Polygon",
        "coordinates": coordinates,
    }
    original = json.dumps(payload).encode()
    ledger = _Ledger()

    with pytest.raises(VectorUploadError, match="nesting exceeds") as raised:
        prepare_vector_upload(
            raw_filename="deep.geojson",
            stream=io.BytesIO(original),
            **_prepare_kwargs(tmp_path, ledger),
        )

    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.code == "invalid_vector"
    assert receipt["status"] == "rejected"
    assert receipt["source_sha256"] == sha256(original)
    assert ledger.reservation.committed is not None


def test_json_parser_recursion_is_stably_rejected_and_quarantined(tmp_path: Path) -> None:
    nested = ("[" * 1200) + "0" + ("]" * 1200)
    original = (
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        f'"properties":{{"nested":{nested}}},'
        '"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[0,0]]]}}]}'
    ).encode()
    ledger = _Ledger()

    with pytest.raises(VectorUploadError) as raised:
        prepare_vector_upload(
            raw_filename="recursive.geojson",
            stream=io.BytesIO(original),
            **_prepare_kwargs(tmp_path, ledger),
        )

    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.code == "invalid_vector"
    assert receipt["status"] == "rejected"
    assert receipt["source_sha256"] == sha256(original)
    assert ledger.reservation.committed is not None


def test_real_redis_reconciliation_releases_eight_abandoned_prewrite_reservations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    filesystem_id = f"pytest-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path("/run/secrets/redis_password")
    if not password_path.exists():
        password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/nonexistent"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        existing = list(connection.scan_iter(match=f"{prefix}:*"))
        if existing:
            connection.delete(*existing)
        connection.hset(f"{prefix}:totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
        ledger = RedisRetentionLedger(connection)
        connection.set(f"{prefix}:reconcile", "operator", ex=30)
        with pytest.raises(VectorUploadError):
            ledger.reserve(
                project_key="run:blocked-by-rebuild",
                actor=RetentionActor("human", 1),
                worst_case_bytes=1,
                filesystem_root=tmp_path,
            )
        connection.delete(f"{prefix}:reconcile")
        for index in range(8):
            ledger.reserve(
                project_key="run:abandoned",
                actor=RetentionActor("human", index + 1),
                worst_case_bytes=1,
                filesystem_root=tmp_path,
            )
        with pytest.raises(VectorUploadError):
            ledger.reserve(
                project_key="run:blocked",
                actor=RetentionActor("human", 99),
                worst_case_bytes=1,
                filesystem_root=tmp_path,
            )

        report = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            now=int(__import__("time").time()) + 601,
        )
        assert len(report["actions"]) == 8
        assert {action["action"] for action in report["actions"]} == {"release_prewrite"}
        recovered = ledger.reserve(
            project_key="run:recovered",
            actor=RetentionActor("human", 99),
            worst_case_bytes=1,
            filesystem_root=tmp_path,
        )
        recovered.release_prewrite()
        totals = connection.hgetall(f"{prefix}:totals")
        assert int(totals.get("inflight", 0)) == 0
        assert int(totals.get("reserved", 0)) == 0

        project_root = tmp_path / "project"
        project_root.mkdir()
        prepared = prepare_vector_upload(
            raw_filename="bound.geojson",
            stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
            endpoint_max_bytes=1024 * 1024,
            attempt_root=tmp_path / "project" / "vector_upload_attempts",
            evidence_roots=(tmp_path / "project" / "vector_upload_attempts",),
            filesystem_root=project_root,
            project_key="run:bound-crash",
            workflow="test",
            project_identity="bound-crash",
            actor=RetentionActor("human", 42),
            validator=lambda _path, _payload: {"valid": True},
            ledger=ledger,
            scope_lease_factory=lambda _key: _Lease(),
        )
        recovered_bound = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            now=int(__import__("time").time()) + 601,
        )
        assert any(
            action["reservation"] == prepared.reservation.reservation_id
            and action["action"] == "incomplete"
            for action in recovered_bound["actions"]
        )
        bound_receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
        assert bound_receipt["status"] == "incomplete"

        retained = tmp_path / "run" / "vector_upload_attempts" / "attempt-1"
        retained.mkdir(parents=True)
        (retained / "original.upload").write_bytes(b"retained evidence")
        (retained / "normalization.json").write_text(json.dumps({
            "schema": "vector-normalization-v1",
            "status": "rejected",
            "actor": {"kind": "human", "user_id": 42},
        }))
        connection.hset(f"{prefix}:totals", mapping={"committed": 1})
        rebuilt = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            rebuild_ledger=True,
        )
        expected = sum(
            item.stat().st_size
            for evidence_root in (retained, prepared.attempt_dir)
            for item in evidence_root.rglob("*")
            if item.is_file()
        )
        assert rebuilt["ledger_audit"]["computed_committed"] == expected
        assert rebuilt["ledger_audit"]["rebuilt"] is True
        totals = connection.hgetall(f"{prefix}:totals")
        assert int(totals["committed"]) == expected
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_rebuild_obligation_blocks_new_reservations_until_durably_cleared(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    filesystem_id = f"pytest-obligation-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        existing = list(connection.scan_iter(match=f"{prefix}:*"))
        if existing:
            connection.delete(*existing)
        connection.hset(
            f"{prefix}:totals",
            mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0},
        )
        for index in range(16):
            assert not retention_rebuild_obligation_pending(
                tmp_path,
                operation="private_archive_delete",
                target=f"run/archives/private/missing-{index}",
                connection=connection,
            )
        assert connection.scard(f"{prefix}:rebuild-pending") == 0
        assert not (tmp_path / ".vector-upload-rebuild-pending").exists()
        obligation = begin_retention_rebuild_obligation(
            tmp_path,
            operation="delete-project",
            target="run:test",
            connection=connection,
        )
        pending_key = f"{prefix}:rebuild-pending"
        assert retention_rebuild_obligation_pending(
            tmp_path,
            operation="delete-project",
            target="run:test",
            connection=connection,
        )
        assert connection.smembers(pending_key) == {obligation.stem}
        assert obligation.is_file()
        project_root = tmp_path / "runs" / "project-1"
        project_root.mkdir(parents=True)
        connection.delete(pending_key)
        assert connection.scard(pending_key) == 0
        ledger = RedisRetentionLedger(connection)
        with pytest.raises(VectorUploadError) as lost_namespace:
            ledger.reserve(
                project_key="run:blocked-by-filesystem-marker",
                actor=RetentionActor("human", 7),
                worst_case_bytes=1,
                filesystem_root=project_root,
            )
        assert lost_namespace.value.code == "vector_retention_quota_exceeded"
        assert connection.smembers(pending_key) == {obligation.stem}
        connection.delete(pending_key)
        reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            rebuild_ledger=True,
            stale_seconds=0,
            committed_only=True,
        )
        assert connection.smembers(pending_key) == {obligation.stem}

        maintenance = acquire_retention_maintenance_lease(connection)
        try:
            with pytest.raises(VectorUploadError):
                acquire_retention_maintenance_lease(connection)
        finally:
            maintenance.release()

        with pytest.raises(VectorUploadError) as raised:
            ledger.reserve(
                project_key="run:blocked-pending-rebuild",
                actor=RetentionActor("human", 7),
                worst_case_bytes=1,
                filesystem_root=tmp_path,
            )
        assert raised.value.code == "vector_retention_quota_exceeded"

        complete_retention_rebuild_obligation(obligation, connection=connection)
        assert not obligation.exists()
        assert connection.scard(pending_key) == 0
        assert not retention_rebuild_obligation_pending(
            tmp_path,
            operation="delete-project",
            target="run:test",
            connection=connection,
        )
        reservation = ledger.reserve(
            project_key="run:unblocked-after-rebuild",
            actor=RetentionActor("human", 7),
            worst_case_bytes=1,
            filesystem_root=tmp_path,
        )
        reservation.release_prewrite()
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_real_redis_reconciliation_stops_before_mutation_after_lock_loss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.microservices.vector_upload_normalization as normalization

    filesystem_id = f"pytest-lock-loss-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        connection.hset(
            f"{prefix}:totals",
            mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0},
        )
        project = tmp_path / "project"
        project.mkdir()
        prepared = prepare_vector_upload(
            raw_filename="accepted.geojson",
            stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
            endpoint_max_bytes=1024 * 1024,
            attempt_root=project / "vector_upload_attempts",
            evidence_roots=(project / "vector_upload_attempts",),
            filesystem_root=project,
            project_key="run:lock-loss",
            workflow="test",
            project_identity="lock-loss",
            actor=RetentionActor("human", 42),
            validator=lambda _path, _payload: {"valid": True},
            ledger=RedisRetentionLedger(connection),
            scope_lease_factory=lambda _key: _Lease(),
        )
        canonical = project / "accepted.geojson"
        prepared.publish(
            mutation=lambda candidate: canonical.write_bytes(candidate.read_bytes()),
            canonical_path=canonical,
            canonical_relative_path="accepted.geojson",
        )
        receipt_path = prepared.attempt_dir / "normalization.json"
        before_receipt = receipt_path.read_bytes()
        before_totals = connection.hgetall(f"{prefix}:totals")
        original_hash = normalization._hash_regular
        stolen = False

        def steal_reconcile_lock(path: Path):
            nonlocal stolen
            result = original_hash(path)
            if not stolen:
                connection.set(f"{prefix}:reconcile", "new-owner", ex=600)
                stolen = True
            return result

        monkeypatch.setattr(normalization, "_hash_regular", steal_reconcile_lock)
        with pytest.raises(VectorUploadError, match="lock ownership was lost"):
            reconcile_retention(
                tmp_path,
                apply=True,
                connection=connection,
                now=int(__import__("time").time()) + 601,
            )

        assert receipt_path.read_bytes() == before_receipt
        assert connection.hgetall(f"{prefix}:totals") == before_totals
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_real_redis_reconciliation_skips_active_project_scope_then_recovers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    filesystem_id = f"pytest-active-scope-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        connection.hset(
            f"{prefix}:totals",
            mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0},
        )
        project = tmp_path / "project"
        project.mkdir()
        prepared = prepare_vector_upload(
            raw_filename="active.geojson",
            stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
            endpoint_max_bytes=1024 * 1024,
            attempt_root=project / "vector_upload_attempts",
            evidence_roots=(project / "vector_upload_attempts",),
            filesystem_root=project,
            project_key="run:active-reconcile",
            workflow="test",
            project_identity="active-reconcile",
            actor=RetentionActor("human", 42),
            validator=lambda _path, _payload: {"valid": True},
            ledger=RedisRetentionLedger(connection),
            scope_lease_factory=RedisScopeLeaseFactory(connection),
        )
        receipt_path = prepared.attempt_dir / "normalization.json"
        reservation_key = f"{prefix}:reservation:{prepared.reservation.reservation_id}"
        before_receipt = receipt_path.read_bytes()
        before_reservation = connection.hgetall(reservation_key)
        before_totals = connection.hgetall(f"{prefix}:totals")
        future = int(__import__("time").time()) + 601

        active_report = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            now=future,
        )

        assert active_report["actions"] == [{
            "reservation": prepared.reservation.reservation_id,
            "action": "active_scope_skipped",
        }]
        assert receipt_path.read_bytes() == before_receipt
        assert connection.hgetall(reservation_key) == before_reservation
        assert connection.hgetall(f"{prefix}:totals") == before_totals

        prepared.lease.release()
        recovered_report = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            now=future,
        )
        assert recovered_report["actions"] == [{
            "reservation": prepared.reservation.reservation_id,
            "action": "incomplete",
        }]
        assert json.loads(receipt_path.read_text())["status"] == "incomplete"
        assert not connection.exists(reservation_key)
        totals = connection.hgetall(f"{prefix}:totals")
        assert int(totals["inflight"]) == 0
        assert int(totals["reserved"]) == 0
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_reconciliation_rejects_descendant_root_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    filesystem_id = f"pytest-descendant-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    child = tmp_path / "runs"
    child.mkdir()
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    totals_key = f"{prefix}:totals"
    try:
        connection.hset(
            totals_key,
            mapping={"initialized": 1, "committed": 17, "reserved": 0, "inflight": 0},
        )
        before = connection.hgetall(totals_key)
        for apply in (False, True):
            with pytest.raises(VectorUploadError, match="identity cannot be verified"):
                reconcile_retention(
                    child,
                    apply=apply,
                    rebuild_ledger=True,
                    connection=connection,
                )
            assert connection.hgetall(totals_key) == before
            assert not connection.exists(f"{prefix}:reconcile")
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_reconciliation_blocks_in_root_attempt_symlink_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    filesystem_id = f"pytest-symlink-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        connection.hset(
            f"{prefix}:totals",
            mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0},
        )
        reservation = RedisRetentionLedger(connection).reserve(
            project_key="run:symlink",
            actor=RetentionActor("human", 9),
            worst_case_bytes=123,
            filesystem_root=tmp_path,
        )
        alias = tmp_path / "project" / "vector_upload_attempts" / "alias"
        alias.mkdir(parents=True)
        reservation.bind_attempt(alias)
        alias.rmdir()
        target = tmp_path / "other" / "vector_upload_attempts" / "target"
        target.mkdir(parents=True)
        receipt_path = target / "normalization.json"
        receipt_path.write_text(json.dumps({
            "schema": "vector-normalization-v1",
            "status": "rejected",
            "reservation_id": "other",
        }))
        alias.symlink_to(target, target_is_directory=True)
        reservation_key = f"{prefix}:reservation:{reservation.reservation_id}"
        before_receipt = receipt_path.read_bytes()
        before_reservation = connection.hgetall(reservation_key)
        before_totals = connection.hgetall(f"{prefix}:totals")

        report = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            now=int(__import__("time").time()) + 601,
        )

        assert report["actions"] == [{
            "reservation": reservation.reservation_id,
            "action": "blocked_symlink_evidence",
        }]
        assert receipt_path.read_bytes() == before_receipt
        assert connection.hgetall(reservation_key) == before_reservation
        assert connection.hgetall(f"{prefix}:totals") == before_totals
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_rebuild_preserves_terminal_receipt_reservation_until_normal_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.microservices.vector_upload_normalization as normalization

    filesystem_id = f"pytest-rebuild-active-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    connection_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        connection_kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**connection_kwargs)
    prefix = f"vector-upload-retention:{filesystem_id}"
    try:
        connection.hset(
            f"{prefix}:totals",
            mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0},
        )
        project = tmp_path / "project"
        project.mkdir()
        prepared = prepare_vector_upload(
            raw_filename="pending.geojson",
            stream=io.BytesIO(json.dumps(_polygon_payload()).encode()),
            endpoint_max_bytes=1024 * 1024,
            attempt_root=project / "vector_upload_attempts",
            evidence_roots=(project / "vector_upload_attempts",),
            filesystem_root=project,
            project_key="run:pending-commit",
            workflow="test",
            project_identity="pending-commit",
            actor=RetentionActor("human", 42),
            validator=lambda _path, _payload: {"valid": True},
            ledger=RedisRetentionLedger(connection),
            scope_lease_factory=RedisScopeLeaseFactory(connection),
        )
        prepared.receipt.update(
            status="rejected",
            outcome="quarantined",
            accounting_status="pending",
        )
        normalization._atomic_json(
            prepared.attempt_dir / "normalization.json",
            prepared.receipt,
        )
        exact = normalization._regular_tree_size(prepared.attempt_dir)

        report = reconcile_retention(
            tmp_path,
            apply=True,
            connection=connection,
            rebuild_ledger=True,
            stale_seconds=0,
            committed_only=True,
        )
        assert any(action["action"] == "active_receipt_reserved" for action in report["actions"])
        totals = connection.hgetall(f"{prefix}:totals")
        assert int(totals["committed"]) == 0
        assert int(totals["reserved"]) > 0
        assert int(totals["inflight"]) == 1

        prepared.reservation.commit(exact)
        prepared.lease.release()
        totals = connection.hgetall(f"{prefix}:totals")
        assert int(totals["committed"]) == exact
        assert int(totals["reserved"]) == 0
        assert int(totals["inflight"]) == 0
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)


def test_oversize_records_no_original_hash_or_partial(tmp_path: Path) -> None:
    ledger = _Ledger()
    kwargs = _prepare_kwargs(tmp_path, ledger)
    kwargs["endpoint_max_bytes"] = 8
    with pytest.raises(VectorUploadError) as raised:
        prepare_vector_upload(
            raw_filename="large.geojson",
            stream=io.BytesIO(b"{" + b"x" * 20),
            **kwargs,
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.status_code == 413
    assert receipt["outcome"] == "oversize_not_retained"
    assert receipt["source_complete"] is False
    assert "source_sha256" not in receipt
    assert not list((attempt / "original").iterdir())


def test_binary_converter_digest_is_reconciled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    source = b"PAR1bounded-fixturePAR1"
    canonical = json.dumps(_polygon_payload(), separators=(",", ":")).encode()

    class Response:
        status_code = 200
        headers: dict[str, str] = {}

        def iter_content(self, **_kwargs: Any):
            yield json.dumps({
                "request_id": "converter-request",
                "geojson": _polygon_payload(),
                "metadata": {
                    "source_size": len(source),
                    "source_sha256": sha256(source),
                    "canonical_size": len(canonical),
                    "canonical_sha256": sha256(canonical),
                    "parser_provenance": {
                        "binary_name": "geoparquet_parser_cli",
                        "binary_version": "0.0.0",
                        "binary_sha256": "1" * 64,
                        "cargo_lock_sha256": "2" * 64,
                        "source_revision": "3" * 40,
                    },
                },
            }).encode()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "wepppy.microservices.vector_upload_normalization.requests.post",
        lambda *_args, **_kwargs: Response(),
    )
    ledger = _Ledger()
    prepared = prepare_vector_upload(
        raw_filename="fields.parquet",
        stream=io.BytesIO(source),
        converter_url="http://shape-converter/v1/convert",
        **_prepare_kwargs(tmp_path, ledger),
    )
    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert receipt["status"] == "prepared"
    assert receipt["converter_request_id"] == "converter-request"
    assert receipt["parser_provenance"]["binary_name"] == "geoparquet_parser_cli"
    prepared.reject("test_cleanup")


def test_converter_source_digest_mismatch_is_quarantined(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    source = b"PAR1bounded-fixturePAR1"

    class Response:
        status_code = 200
        headers: dict[str, str] = {}

        def iter_content(self, **_kwargs: Any):
            yield json.dumps({
                "request_id": "converter-request",
                "geojson": _polygon_payload(),
                "metadata": {
                    "source_size": len(source),
                    "source_sha256": "0" * 64,
                    "canonical_size": 1,
                    "canonical_sha256": "0" * 64,
                },
            }).encode()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "wepppy.microservices.vector_upload_normalization.requests.post",
        lambda *_args, **_kwargs: Response(),
    )
    ledger = _Ledger()
    with pytest.raises(VectorUploadError) as raised:
        prepare_vector_upload(
            raw_filename="fields.parquet",
            stream=io.BytesIO(source),
            converter_url="http://shape-converter/v1/convert",
            **_prepare_kwargs(tmp_path, ledger),
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.code == "vector_source_integrity_error"
    assert receipt["status"] == "rejected"
    assert receipt["outcome"] == "quarantined"
    assert receipt["source_sha256"] == sha256(source)


def test_default_ledger_fails_closed_without_filesystem_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    with pytest.raises(VectorUploadError) as raised:
        RedisRetentionLedger().reserve(
            project_key="run:test",
            actor=RetentionActor("human", 7),
            worst_case_bytes=1024,
            filesystem_root=tmp_path,
        )
    assert raised.value.code == "vector_retention_quota_exceeded"
    assert raised.value.status_code == 507


def sha256(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777
