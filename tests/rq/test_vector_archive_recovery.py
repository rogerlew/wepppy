"""Destructive archive recovery using real retention authorities and byte readback."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import zipfile
import uuid

import pytest
import redis

from tests.rq.test_project_rq_archive import archive_rq_environment
from tests.microservices.test_rq_engine_fork_archive_routes import _private_archive_fixture
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb._redis_prep_snapshot import RedisPrepSnapshotError
from wepppy.microservices import vector_upload_normalization as retention
from wepppy.microservices.rq_engine import fork_archive_routes as routes
from wepppy.rq import project_rq_archive as archive

pytestmark = pytest.mark.integration


def _evidence(root: Path, payload: bytes = b"original evidence") -> Path:
    attempt = root / "roads/vector_upload_attempts/attempt"
    attempt.mkdir(parents=True)
    (attempt / "payload.upload").write_bytes(payload)
    (attempt / "normalization.json").write_text(json.dumps({
        "schema": "vector-normalization-v1", "status": "rejected",
        "actor": {"kind": "human", "user_id": 42},
    }))
    return attempt


def _tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


@pytest.fixture
def real_archive_retention(monkeypatch, tmp_path):
    """Real Lua/markers, namespaced keys, and no test-owned accounting shortcuts."""
    filesystem_id = f"archive-recovery-{uuid.uuid4().hex}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_file = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_file.exists():
        kwargs["password"] = password_file.read_text().strip()
    connection = redis.client.Redis(**kwargs)
    connection.ping()
    prefix = f"vector-upload-retention:{filesystem_id}"
    leases = []
    real_scope_factory = retention.RedisScopeLeaseFactory(connection)

    def scope_factory(scope):
        lease = real_scope_factory(scope)
        leases.append(lease)
        return lease

    for module in (archive, routes):
        monkeypatch.setattr(module, "RedisScopeLeaseFactory", lambda: scope_factory)
        monkeypatch.setattr(module, "acquire_retention_maintenance_lease",
                            lambda: retention.acquire_retention_maintenance_lease(connection))
        monkeypatch.setattr(module, "begin_retention_rebuild_obligation",
                            lambda root, **kw: retention.begin_retention_rebuild_obligation(root, connection=connection, **kw))
        monkeypatch.setattr(module, "complete_retention_rebuild_obligation",
                            lambda path: retention.complete_retention_rebuild_obligation(path, connection=connection))
        monkeypatch.setattr(module, "reconcile_retention",
                            lambda root, **kw: retention.reconcile_retention(root, connection=connection, **kw))
    monkeypatch.setattr(routes, "retention_rebuild_obligation_pending",
                        lambda root, **kw: retention.retention_rebuild_obligation_pending(root, connection=connection, **kw))
    monkeypatch.setattr(retention.shutil, "disk_usage", lambda _path: SimpleNamespace(
        total=30_000_000_000, used=1_000_000_000, free=29_000_000_000))
    connection.hset(f"{prefix}:totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    try:
        yield SimpleNamespace(connection=connection, prefix=prefix, leases=leases)
    finally:
        for lease in leases:
            # Only our exact acquired keys; no database-wide cleanup.
            connection.eval(retention._LOCK_RELEASE_LUA, 1, lease.key, lease.token)
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)
        connection.close()


def _assert_pending(root, env):
    markers = list((root / ".vector-upload-rebuild-pending").glob("*.json"))
    assert len(markers) == 1
    assert env.connection.smembers(f"{env.prefix}:rebuild-pending") == {markers[0].stem}
    return markers[0]


def _assert_rebuilt(root, env, expected, actor_bytes):
    assert not list((root / ".vector-upload-rebuild-pending").glob("*.json"))
    assert not env.connection.smembers(f"{env.prefix}:rebuild-pending")
    totals = env.connection.hgetall(f"{env.prefix}:totals")
    assert int(totals["committed"]) == expected
    principal = hashlib.sha256(b"human:42").hexdigest()
    assert int(env.connection.hget(f"{env.prefix}:principal:{principal}", "committed")) == actor_bytes


@pytest.mark.parametrize("source", ["live", "incoming"])
@pytest.mark.parametrize("configuration", ["missing_id", "missing_root", "wrong_root"])
def test_sensitive_restore_identity_failure_has_no_project_mutation(
    archive_rq_environment, monkeypatch, source, configuration,
):
    project, root, _published, prep = archive_rq_environment
    run = root / "demo"
    archives = run / "archives"
    archives.mkdir(parents=True)
    (run / "keep.txt").write_bytes(b"accepted project")
    if source == "live":
        _evidence(run)
    incoming = archives / "incoming.zip"
    with zipfile.ZipFile(incoming, "w") as zipped:
        zipped.writestr("roads/vector_upload_attempts/attempt/payload.upload" if source == "incoming" else "keep.txt", b"replacement")
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "configured")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(root))
    if configuration == "missing_id":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID")
    elif configuration == "missing_root":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT")
    else:
        unrelated = root / "different-filesystem"
        unrelated.mkdir()
        monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(unrelated))
    with pytest.raises((RuntimeError, ValueError)):
        project.restore_archive_rq("demo", incoming.name)
    assert {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()} == before
    assert not prep
    assert not (root / ".vector-upload-rebuild-pending").exists()


@pytest.mark.parametrize("fault", ["partial_remove", "directory_fsync", "lost_scope", "rebuild"])
def test_private_delete_fault_retains_dual_obligation_and_retry_rebuilds(
    monkeypatch, tmp_path, real_archive_retention, fault,
):
    env = real_archive_retention
    run = tmp_path / "demo"
    _name, archive_path = _private_archive_fixture(run)
    unrelated = _evidence(tmp_path / "unrelated")
    expected = _tree_bytes(unrelated)
    retention.reconcile_retention(tmp_path, connection=env.connection, apply=True, rebuild_ledger=True)
    reserved = retention.RedisRetentionLedger(env.connection).reserve(
        project_key="run:other-active", actor=retention.RetentionActor("human", 42),
        worst_case_bytes=4096, filesystem_root=tmp_path)
    kwargs = dict(wd=str(run), runid="demo", archive_path=str(archive_path),
                  relative_archive=archive_path.relative_to(run), remove_bundle=True)
    original_remove = shutil.rmtree
    original_fsync = os.fsync

    def fail_remove(path, *args, **kwargs):
        if Path(path) == archive_path.parent:
            if fault == "partial_remove":
                archive_path.unlink()
                raise OSError("injected partial removal")
            original_remove(path, *args, **kwargs)
            env.connection.delete(env.leases[-1].key)
            return
        return original_remove(path, *args, **kwargs)

    def fail_fsync(fd):
        if Path(os.readlink(f"/proc/self/fd/{fd}")) == archive_path.parent.parent:
            raise OSError("injected directory fsync")
        return original_fsync(fd)

    with monkeypatch.context() as injected:
        if fault in {"partial_remove", "lost_scope"}:
            injected.setattr(routes.shutil, "rmtree", fail_remove)
        elif fault == "directory_fsync":
            injected.setattr(routes.os, "fsync", fail_fsync)
        else:
            injected.setattr(routes, "reconcile_retention", lambda *_a, **_k: (_ for _ in ()).throw(OSError("injected rebuild")))
        with pytest.raises((OSError, retention.VectorUploadError)):
            routes._repair_private_archive_deletion(**kwargs)
    marker = _assert_pending(tmp_path, env)
    before_retry_totals = env.connection.hgetall(f"{env.prefix}:totals")
    assert int(before_retry_totals["committed"]) > expected
    assert (unrelated / "payload.upload").read_bytes() == b"original evidence"
    # Simulate loss of the Redis half; the durable identity still authorizes repair.
    env.connection.delete(f"{env.prefix}:rebuild-pending")
    synced = []
    with monkeypatch.context() as observe:
        def record_fsync(fd):
            synced.append(Path(os.readlink(f"/proc/self/fd/{fd}")))
            return original_fsync(fd)
        observe.setattr(routes.os, "fsync", record_fsync)
        routes._repair_private_archive_deletion(**{**kwargs, "remove_bundle": False})
    assert archive_path.parent.parent in synced
    assert not archive_path.parent.exists()
    assert not marker.exists()
    _assert_rebuilt(tmp_path, env, expected, expected)
    totals = env.connection.hgetall(f"{env.prefix}:totals")
    assert (int(totals["reserved"]), int(totals["inflight"])) == (4096, 1)
    reserved.release_prewrite()


def test_pending_private_delete_revalidates_symlink_ancestry(
    monkeypatch, tmp_path, real_archive_retention,
):
    env = real_archive_retention
    run = tmp_path / "demo"
    _name, archive_path = _private_archive_fixture(run)
    marker = retention.begin_retention_rebuild_obligation(tmp_path,
        operation="private_archive_delete", target=archive_path.parent.relative_to(tmp_path).as_posix(),
        connection=env.connection)
    moved = tmp_path / "outside"
    archive_path.parent.rename(moved)
    archive_path.parent.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match="Invalid archive_name"):
        routes._repair_private_archive_deletion(wd=str(run), runid="demo", archive_path=str(archive_path),
            relative_archive=archive_path.relative_to(run), remove_bundle=False)
    assert (moved / archive_path.name).is_file()
    assert marker.is_file()
    _assert_pending(tmp_path, env)
    archive_path.parent.unlink()
    moved.rename(archive_path.parent)
    routes._repair_private_archive_deletion(wd=str(run), runid="demo", archive_path=str(archive_path),
        relative_archive=archive_path.relative_to(run), remove_bundle=False)
    assert not marker.exists()


@pytest.mark.parametrize("fault", ["partial_remove", "file_fsync", "directory_fsync", "lost_scope"])
def test_sensitive_restore_fault_retains_dual_obligation_until_retry(
    archive_rq_environment, real_archive_retention, monkeypatch, fault,
):
    project, root, _published, _prep = archive_rq_environment
    env = real_archive_retention
    run = root / "demo"
    live = _evidence(run, b"old accepted evidence")
    unrelated = _evidence(root / "unrelated")
    archives = run / "archives"
    archives.mkdir()
    incoming = archives / "incoming.zip"
    with zipfile.ZipFile(incoming, "w") as zipped:
        zipped.writestr("roads/vector_upload_attempts/attempt/payload.upload", b"incoming evidence")
        zipped.writestr("roads/vector_upload_attempts/attempt/normalization.json", (live / "normalization.json").read_bytes())
    retention.reconcile_retention(root, connection=env.connection, apply=True, rebuild_ledger=True)
    original_remove = archive._remove_restore_directory
    original_fsync = os.fsync

    def fail_remove(path):
        result = original_remove(path)
        if Path(path) == run / "roads":
            if fault == "lost_scope":
                env.connection.delete(env.leases[-1].key)
            else:
                raise OSError("injected partial removal")
        return result

    def fail_fsync(fd):
        path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if (fault == "file_fsync" and path == live / "payload.upload") or (
            fault == "directory_fsync" and path == run and (live / "payload.upload").exists()
            and (live / "payload.upload").read_bytes() == b"incoming evidence"
        ):
            raise OSError("injected restore fsync")
        return original_fsync(fd)

    with monkeypatch.context() as injected:
        if fault in {"partial_remove", "lost_scope"}:
            injected.setattr(archive, "_remove_restore_directory", fail_remove)
        else:
            injected.setattr(archive.os, "fsync", fail_fsync)
        with pytest.raises((OSError, retention.VectorUploadError, RedisPrepSnapshotError)):
            project.restore_archive_rq("demo", incoming.name)
    _assert_pending(root, env)
    assert (unrelated / "payload.upload").read_bytes() == b"original evidence"
    project.restore_archive_rq("demo", incoming.name)
    assert (live / "payload.upload").read_bytes() == b"incoming evidence"
    expected = _tree_bytes(live) + _tree_bytes(unrelated)
    _assert_rebuilt(root, env, expected, expected)


def test_restore_rejects_archive_symlink_without_consuming_target(archive_rq_environment):
    project, root, _published, _prep = archive_rq_environment
    run = root / "demo"
    archives = run / "archives"
    archives.mkdir(parents=True)
    outside = root / "outside.zip"
    with zipfile.ZipFile(outside, "w") as zipped:
        zipped.writestr("payload.txt", b"must not restore")
    (archives / "aliased.zip").symlink_to(outside)
    with pytest.raises(ValueError):
        project.restore_archive_rq("demo", "aliased.zip")
    assert not (run / "payload.txt").exists()
    assert outside.is_file()


@pytest.mark.parametrize('phase', ['reserved', 'prepared'])
def test_parent_restore_preserves_active_descendant_upload(
    archive_rq_environment, real_archive_retention, phase,
):
    project, root, _published, _prep = archive_rq_environment
    env = real_archive_retention
    runid = f'parent-{uuid.uuid4().hex}'
    run = root / runid
    archives = run / 'archives'
    archives.mkdir(parents=True)
    (run / 'keep.txt').write_bytes(b'accepted project')
    incoming = archives / 'incoming.zip'
    with zipfile.ZipFile(incoming, 'w') as zipped:
        zipped.writestr('keep.txt', b'restored project')
    scope = f'run:{runid};;omni-contrast;;1'
    child = run / '_pups/omni/contrasts/1'
    ledger = retention.RedisRetentionLedger(env.connection)
    prepared = None
    if phase == 'prepared':
        (child / 'roads').mkdir(parents=True)
        attempt_root = child / 'roads/vector_upload_attempts'
        prepared = retention.prepare_vector_upload(
            raw_filename='child.geojson', stream=io.BytesIO(b'{"type":"FeatureCollection","features":[]}'),
            endpoint_max_bytes=1024, attempt_root=attempt_root, evidence_roots=(attempt_root,),
            filesystem_root=child, project_key=scope, workflow='roads', project_identity=scope[4:],
            actor=retention.RetentionActor('human', 9), validator=lambda *_: {'valid': True},
            ledger=ledger, scope_lease_factory=retention.RedisScopeLeaseFactory(env.connection),
        )
        lease = prepared.lease
        original = prepared.attempt_dir / prepared.receipt['source_path']
        original_bytes = original.read_bytes()
    else:
        reservation = ledger.reserve(project_key=scope, actor=retention.RetentionActor('human', 9),
                                     worst_case_bytes=123, filesystem_root=run)
        lease = retention.RedisScopeLeaseFactory(env.connection)(scope)
        assert not child.exists()
    before = env.connection.hgetall(f'{env.prefix}:totals')
    try:
        with pytest.raises(retention.VectorUploadError, match='Another vector evidence'):
            project.restore_archive_rq(runid, incoming.name)
        lease.assert_owned()
        assert (run / 'keep.txt').read_bytes() == b'accepted project'
        if prepared is not None:
            assert original.read_bytes() == original_bytes
            assert json.loads((prepared.attempt_dir / 'normalization.json').read_text())['status'] == 'prepared'
        assert env.connection.hgetall(f'{env.prefix}:totals') == before
        assert not env.connection.smembers(f'{env.prefix}:rebuild-pending')
        assert not list((root / '.vector-upload-rebuild-pending').glob('*.json'))
    finally:
        if prepared is not None:
            prepared.reject('test-complete')
        else:
            lease.release()
            reservation.release_prewrite()
    project.restore_archive_rq(runid, incoming.name)
    assert (run / 'keep.txt').read_bytes() == b'restored project'
    assert not child.exists()
    assert int(env.connection.hget(f'{env.prefix}:totals', 'committed')) == 0


@pytest.mark.parametrize("configuration", ["missing_id", "missing_root", "wrong_root"])
def test_private_delete_identity_failure_does_not_mutate_evidence(
    monkeypatch, tmp_path, real_archive_retention, configuration,
):
    env = real_archive_retention
    run = tmp_path / "demo"
    _name, archive_path = _private_archive_fixture(run)
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    if configuration == "missing_id":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID")
    elif configuration == "missing_root":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT")
    else:
        wrong = tmp_path / "wrong"
        wrong.mkdir()
        monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(wrong))
    with pytest.raises((retention.VectorUploadError, ValueError)):
        routes._repair_private_archive_deletion(wd=str(run), runid="demo", archive_path=str(archive_path),
            relative_archive=archive_path.relative_to(run), remove_bundle=True)
    assert {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()} == before
    assert not env.connection.smembers(f"{env.prefix}:rebuild-pending")
    assert not (tmp_path / ".vector-upload-rebuild-pending").exists()
