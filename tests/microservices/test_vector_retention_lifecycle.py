from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid
from types import SimpleNamespace

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as n
from wepppy.microservices import vector_retention_lifecycle as lifecycle

pytestmark = pytest.mark.integration


@pytest.fixture
def environment(tmp_path, monkeypatch):
    identity = f"copy-lifecycle-{uuid.uuid4().hex}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", identity)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    secret = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if secret.exists():
        kwargs["password"] = secret.read_text().strip()
    conn = redis.client.Redis(**kwargs)
    monkeypatch.setattr(n.redis, "Redis", lambda **_kw: conn)
    prefix = f"vector-upload-retention:{identity}"
    conn.hset(prefix + ":totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    env = SimpleNamespace(root=tmp_path, conn=conn, prefix=prefix)
    yield env
    keys = list(conn.scan_iter(match=prefix + ":*"))
    if keys:
        conn.delete(*keys)


def evidence(project, relative="roads/vector_upload_attempts", status="accepted"):
    attempt = project / relative / "fixed-id"
    attempt.mkdir(parents=True)
    original = b"opaque complete original"
    (attempt / "original.upload").write_bytes(original)
    (attempt / "normalization.json").write_text(json.dumps({
        "schema": "vector-normalization-v1", "status": status,
        "actor": {"kind": "human", "user_id": 7}, "attempt_id": "fixed-id",
        "project_identity": "source", "source_sha256": hashlib.sha256(original).hexdigest(),
    }))
    return attempt


def total(env):
    return int(env.conn.hget(env.prefix + ":totals", "committed"))


def principal(env, user):
    key = hashlib.sha256(f"human:{user}".encode()).hexdigest()
    return int(env.conn.hget(env.prefix + ":principal:" + key, "committed") or 0)


def operation(env, source, destination, **kw):
    return lifecycle.retained_tree_operation(
        destination, source=source,
        project_keys=[f"run:copy-source-{env.root.name}", f"run:{destination.name}-{env.root.name}"],
        actor=n.RetentionActor("human", 8), operation="test_copy", **kw,
    )


@pytest.mark.parametrize("status", ["accepted", "rejected", "incomplete"])
def test_copy_keeps_source_provenance_and_charges_copying_actor(environment, status):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    original = evidence(source, status=status)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    initial = total(env)
    original_receipt = (original / "normalization.json").read_bytes()
    with operation(env, source, target):
        shutil.copytree(source, target)
    copied = target / original.relative_to(source)
    receipt = json.loads((copied / "normalization.json").read_text())
    assert receipt["actor"] == {"kind": "human", "user_id": 7}
    assert receipt["retention_actor"] == {"kind": "human", "user_id": 8}
    assert receipt["copied_from"]["receipt_sha256"] == hashlib.sha256(original_receipt).hexdigest()
    assert (copied / "copy-source-receipt.json").read_bytes() == original_receipt
    assert (copied / "original.upload").read_bytes() == (original / "original.upload").read_bytes()
    assert (original / "normalization.json").read_bytes() == original_receipt
    copied_size = n._regular_tree_size(copied)
    assert principal(env, 7) == initial
    assert principal(env, 8) == copied_size
    assert total(env) == initial + copied_size
    second = env.root / "second"
    with operation(env, target, second):
        shutil.copytree(target, second)
    second_receipt = json.loads((second / original.relative_to(source) / "normalization.json").read_text())
    assert second_receipt["actor"] == receipt["actor"]
    assert set(second_receipt["copied_from"]) == {"receipt_sha256", "project_identity", "attempt_id"}
    assert total(env) == sum(n._regular_tree_size(p) for p in [original, copied, second / original.relative_to(source)])


def test_copy_quota_rejects_before_destination_mutation(environment, monkeypatch):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    evidence(source)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    monkeypatch.setattr(n, "_PRINCIPAL_LIMIT", 1)
    with pytest.raises(n.VectorUploadError, match="retention quota"):
        with operation(env, source, target):
            pytest.fail("copy was admitted")
    assert not target.exists()
    assert not env.conn.smembers(env.prefix + ":rebuild-pending")


def test_partial_copy_retry_and_ordinary_model_symlink(environment):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    original = evidence(source)
    (source / "climate-link").symlink_to(env.root / "unrelated", target_is_directory=True)
    (env.root / "unrelated").mkdir()
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    with pytest.raises(OSError, match="injected"):
        with operation(env, source, target):
            partial = target / original.relative_to(source)
            partial.mkdir(parents=True)
            (partial / "original.upload").write_bytes(b"partial")
            raise OSError("injected interrupted copy")
    assert lifecycle.retained_tree_repair_pending(target, "test_copy")
    with operation(env, source, target) as state:
        assert state.repair_pending
        shutil.rmtree(target)
        shutil.copytree(source, target, symlinks=True)
    assert not lifecycle.retained_tree_repair_pending(target, "test_copy")
    assert (target / "climate-link").is_symlink()


def test_copy_rejects_evidence_symlink(environment):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    source.mkdir()
    (source / "roads").mkdir()
    (source / "roads/vector_upload_attempts").symlink_to(env.root / "outside", target_is_directory=True)
    with pytest.raises(n.VectorUploadError, match="symbolic"):
        with operation(env, source, target):
            pytest.fail("symlink admitted")
    assert not target.exists()


def test_borrowed_scope_and_active_reservation_survive_cleanup(environment):
    env = environment
    source = env.root / "parent"
    evidence(source)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    reservation = n.RedisRetentionLedger(env.conn).reserve(
        project_key="run:unrelated", actor=n.RetentionActor("human", 9),
        worst_case_bytes=20, filesystem_root=env.root,
    )
    key = f"run:parent-{env.root.name}"
    lease = n.RedisScopeLeaseFactory()(key)
    try:
        with lifecycle.borrow_retention_scope(key, lease):
            with lifecycle.retained_tree_operation(source, project_keys=[key], operation="test_cleanup"):
                shutil.rmtree(source)
        lease.assert_owned()
        assert total(env) == 0
        assert int(env.conn.hget(env.prefix + ":totals", "reserved")) == 20
    finally:
        lease.release()
        reservation.release_prewrite()


def test_linked_model_subtree_cannot_materialize_uncharged_evidence(environment):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    source.mkdir()
    other = env.root / "other"
    evidence(other)
    (source / "model-alias").symlink_to(other, target_is_directory=True)
    with pytest.raises(n.VectorUploadError, match="symbolic"):
        with operation(env, source, target):
            shutil.copytree(source, target)
    assert not target.exists()


def test_explicit_export_inside_root_requires_identity(environment, monkeypatch):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    evidence(source)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID")
    with pytest.raises(n.VectorUploadError, match="identity"):
        with operation(env, source, target, managed_export=True):
            pytest.fail("in-root export admitted without identity")


def test_successful_callback_with_missing_receipt_leaves_repair_obligation(environment):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    original = evidence(source)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    with pytest.raises(n.VectorUploadError, match="missing its receipt"):
        with operation(env, source, target):
            partial = target / original.relative_to(source)
            partial.mkdir(parents=True)
            (partial / "original.upload").write_bytes(b"copied but no receipt")
    assert lifecycle.retained_tree_repair_pending(target, "test_copy")


def test_release_failure_still_releases_all_owned_leases(environment, monkeypatch):
    env = environment
    released = []
    class Lease:
        def __init__(self, key):
            self.key = key
            self.connection = env.conn
        def assert_owned(self):
            pass
        def release(self):
            released.append(self.key)
            if self.key == "run:b":
                raise OSError("injected release failure")
    monkeypatch.setattr(n, "acquire_retention_maintenance_lease", lambda: Lease("global"))
    monkeypatch.setattr(n, "RedisScopeLeaseFactory", lambda: lambda key: Lease(key))
    with pytest.raises(OSError, match="release failure"):
        with lifecycle.retained_tree_operation(env.root / "empty", project_keys=["run:a", "run:b"]):
            pass
    assert released == ["run:b", "run:a", "global"]


def test_replacement_requires_headroom_for_old_bytes_and_reservations(environment, monkeypatch):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    evidence(source)
    evidence(target)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    monkeypatch.setattr(n, "_GLOBAL_LIMIT", total(env) + 1)
    with pytest.raises(n.VectorUploadError, match="retention quota"):
        with operation(env, source, target):
            pytest.fail("invalid reclaim admitted")
    assert (target / "roads/vector_upload_attempts/fixed-id/original.upload").exists()


@pytest.mark.parametrize("relative_target", [False, True])
def test_copy_syncs_evidence_ancestors_before_clearing_marker(environment, monkeypatch, relative_target):
    env = environment
    source, target = env.root / "source", env.root / "new-shard/projects/copy"
    evidence(source)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    if relative_target:
        monkeypatch.chdir(env.root)
        target = target.relative_to(env.root)
    synced = []
    real_sync = n._fsync_directory
    def sync(path):
        synced.append(Path(path).resolve())
        real_sync(path)
    monkeypatch.setattr(n, "_fsync_directory", sync)
    with operation(env, source, target):
        shutil.copytree(source, target)
    target = target.resolve()
    assert target / "roads" in synced
    assert target in synced
    assert target.parent in synced
    assert target.parent.parent in synced
    assert env.root in synced
    assert synced.index(target / "roads") < synced.index(target) < synced.index(target.parent)
    assert synced.index(target.parent) < synced.index(target.parent.parent)


def test_copy_free_space_admission_includes_live_reservations(environment, monkeypatch):
    env = environment
    source, target = env.root / "source", env.root / "copy"
    evidence(source)
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True)
    env.conn.hset(env.prefix + ":totals", "reserved", 100000)
    monkeypatch.setattr(n.shutil, "disk_usage", lambda _path: SimpleNamespace(free=n._FREE_SPACE_RESERVE + 10000))
    with pytest.raises(n.VectorUploadError, match="filesystem reserve"):
        with operation(env, source, target):
            pytest.fail("outstanding reservations ignored")
    assert not target.exists()


@pytest.mark.slow
def test_parent_cleanup_preserves_active_child_upload(environment):
    import io
    from wepppy.nodb.mods.omni.omni_state_contrast_mixin import OmniStateContrastMixin

    env = environment
    parent = env.root / 'parent'
    child = parent / '_pups/omni/contrasts/1'
    child.mkdir(parents=True)
    parent_id = f'parent-{uuid.uuid4().hex}'
    child_id = f'{parent_id};;omni-contrast;;1'
    payload = json.dumps({'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'properties': {'field_id': 1}, 'geometry': {
            'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        },
    }]}).encode()
    attempt_root = child / 'ag_fields/vector_upload_attempts'
    attempt_root.parent.mkdir()
    prepared = n.prepare_vector_upload(
        raw_filename='fields.geojson', stream=io.BytesIO(payload), endpoint_max_bytes=1048576,
        attempt_root=attempt_root, evidence_roots=(attempt_root,), filesystem_root=child,
        project_key=f'run:{child_id}', workflow='ag_fields', project_identity=child_id,
        actor=n.RetentionActor('human', 42), validator=lambda *_: {'valid': True},
        ledger=n.RedisRetentionLedger(env.conn),
    )
    original = prepared.attempt_dir / prepared.receipt['source_path']
    controller = SimpleNamespace(wd=str(parent), runid=parent_id,
                                 _contrast_sidecar_dir=lambda: str(parent / 'omni/contrasts'))
    try:
        with pytest.raises(n.VectorUploadError):
            OmniStateContrastMixin._clean_stale_contrast_runs(controller, [])
        prepared.lease.assert_owned()
        assert original.read_bytes() == payload
        assert not env.conn.smembers(env.prefix + ':rebuild-pending')
    finally:
        prepared.reject('test_cleanup')


@pytest.mark.slow
def test_unbound_child_reservation_scope_is_fenced(environment):
    env = environment
    parent = f'run:parent-{uuid.uuid4().hex}'
    child = parent + ';;omni-contrast;;1'
    reservation = n.RedisRetentionLedger(env.conn).reserve(
        project_key=child, actor=n.RetentionActor('human', 42),
        worst_case_bytes=20, filesystem_root=env.root,
    )
    lease = n.RedisScopeLeaseFactory()(child)
    try:
        with pytest.raises(n.VectorUploadError):
            with lifecycle.retained_tree_operation(env.root / 'parent', project_keys=[parent]):
                pytest.fail('unbound child scope was not fenced')
        lease.assert_owned()
    finally:
        lease.release()
        reservation.release_prewrite()


@pytest.mark.parametrize('receipt_accounting', ['pending', 'committed'])
def test_copy_requires_source_reservation_reconciliation(environment, receipt_accounting):
    env = environment
    source, target = env.root / 'source', env.root / 'copy'
    attempt = evidence(source, status='incomplete')
    reservation = n.RedisRetentionLedger(env.conn).reserve(
        project_key=f'run:source-{uuid.uuid4().hex}', actor=n.RetentionActor('human', 7),
        worst_case_bytes=10000, filesystem_root=env.root,
    )
    reservation.bind_attempt(attempt)
    receipt_path = attempt / 'normalization.json'
    receipt = json.loads(receipt_path.read_text())
    receipt.update(reservation_id=reservation.reservation_id, accounting_status=receipt_accounting)
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(n.VectorUploadError, match='[Rr]econcil'):
        with operation(env, source, target):
            shutil.copytree(source, target)
    assert not target.exists()
    assert principal(env, 8) == 0
    assert not env.conn.smembers(env.prefix + ':rebuild-pending')
    n.reconcile_retention(env.root, apply=True, rebuild_ledger=True, stale_seconds=0)
    original_bytes = total(env)
    with operation(env, source, target):
        shutil.copytree(source, target)
    copied_bytes = n._regular_tree_size(target / attempt.relative_to(source))
    assert principal(env, 7) == original_bytes
    assert principal(env, 8) == copied_bytes
    assert total(env) == original_bytes + copied_bytes
