"""Actual fork/reset copies, retained-byte accounting, and absent-target repair.

Run preparation after the developer clone is outside this suite. Redis leases,
repair authorities, fork rsync, receipt readback and accounting are real.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import uuid
import zipfile

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as retention
from wepppy.microservices.rq_engine import fork_archive_routes as routes
from wepppy.rq import project_rq as project
from wepppy.rq import project_rq_fork as fork_helpers

pytestmark = pytest.mark.integration


def _evidence(run: Path, *, private: bool = False) -> Path:
    relative = "archives/private/snapshot" if private else "roads/vector_upload_attempts/shared-attempt"
    attempt = run / relative
    attempt.mkdir(parents=True)
    payload = b"private source snapshot" if private else b"opaque retained shapefile upload"
    if private:
        with zipfile.ZipFile(attempt / "snapshot.zip", "w") as archive:
            archive.writestr("roads/vector_upload_attempts/original/payload.upload", payload)
        payload = (attempt / "snapshot.zip").read_bytes()
        (attempt / "snapshot.zip.sensitive.json").write_text(json.dumps({
            "schema": "vector-upload-private-archive-v1", "archive": "snapshot.zip",
            "archive_size": len(payload), "archive_sha256": hashlib.sha256(payload).hexdigest(),
            "contains_vector_upload_attempts": True,
        }))
    else:
        (attempt / "payload.upload").write_bytes(payload)
    (attempt / "normalization.json").write_text(json.dumps({
        "schema": "vector-normalization-v1", "status": "rejected",
        "actor": {"kind": "human", "user_id": 42},
        "project_identity": "run:original", "attempt_id": "shared-attempt",
        "source_size": len(payload), "source_sha256": hashlib.sha256(payload).hexdigest(),
    }))
    return attempt


def _size(path: Path) -> int:
    return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())


@pytest.fixture
def fork_retention(monkeypatch, tmp_path, runtime_redis_credentials):
    identity = "fork-retention-" + uuid.uuid4().hex
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", identity)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    connection = redis.client.Redis(**redis_connection_kwargs(RedisDB.LOCK, decode_responses=True))
    connection.ping()
    monkeypatch.setattr(retention.redis, "Redis", lambda **_kwargs: connection)
    prefix = f"vector-upload-retention:{identity}"
    connection.hset(prefix + ":totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    real_maintenance = retention.acquire_retention_maintenance_lease
    real_reconcile = retention.reconcile_retention
    real_scope_factory = retention.RedisScopeLeaseFactory(connection)
    monkeypatch.setattr(retention, "acquire_retention_maintenance_lease", lambda: real_maintenance(connection))
    monkeypatch.setattr(retention, "RedisScopeLeaseFactory", lambda: real_scope_factory)
    monkeypatch.setattr(retention, "reconcile_retention", lambda root, **kw: real_reconcile(root, connection=connection, **kw))
    monkeypatch.setattr(retention.shutil, "disk_usage", lambda _path: SimpleNamespace(
        total=30_000_000_000, used=1_000_000_000, free=29_000_000_000))

    def principal(bucket):
        return prefix + ":principal:" + hashlib.sha256(bucket.encode()).hexdigest()

    def rebuild(root=tmp_path):
        return retention.reconcile_retention(root, apply=True, rebuild_ledger=True)

    try:
        yield SimpleNamespace(connection=connection, prefix=prefix, principal=principal, rebuild=rebuild,
                              source_id=identity + "-source", target_id=identity + "-target")
    finally:
        keys = list(connection.scan_iter(match=prefix + ":*"))
        if keys:
            connection.delete(*keys)
        connection.close()


def _prepare(source, target, env, actor):
    return fork_helpers.prepare_fork_run(
        env.source_id, env.target_id, undisturbify=False,
        status_channel="test:fork", publish_status=lambda *_args: None,
        get_wd=lambda _runid: str(source), get_primary_wd=lambda _runid: str(target),
        wait_for_paths=lambda *_args, **_kw: None, ron_cls=None, disturbed_cls=None,
        landuse_cls=None, soils_cls=None, initialize_ttl=None, retention_actor=actor,
    )


@pytest.mark.parametrize("actor", [retention.RetentionActor("human", 77), None])
def test_fork_copies_originals_and_private_archives_with_copy_charge(
    tmp_path, monkeypatch, fork_retention, actor,
):
    env = fork_retention
    source, target = tmp_path / "source", tmp_path / "target"
    attempts = [_evidence(source), _evidence(source, private=True)]
    originals = {attempt.relative_to(source): (attempt / "normalization.json").read_bytes() for attempt in attempts}
    env.rebuild()
    # An exhausted uploader budget must not prevent another principal's copy.
    env.connection.hset(env.principal("human:42"), "committed", retention._PRINCIPAL_LIMIT)
    result = _prepare(source, target, env, actor)
    assert result == str(target)
    charged_actor = actor or retention.RetentionActor("unattributed", None)
    source_size = sum(_size(attempt) for attempt in attempts)
    copied_size = 0
    for relative, original in originals.items():
        copied = target / relative
        receipt = json.loads((copied / "normalization.json").read_bytes())
        assert (source / relative / "normalization.json").read_bytes() == original
        for original_file in (source / relative).iterdir():
            if original_file.name != "normalization.json":
                assert (copied / original_file.name).read_bytes() == original_file.read_bytes()
        assert receipt["actor"] == {"kind": "human", "user_id": 42}
        assert receipt["retention_actor"] == charged_actor.receipt_value()
        assert receipt["attempt_id"] == "shared-attempt"
        assert receipt["copied_from"]["receipt_sha256"] == hashlib.sha256(original).hexdigest()
        assert (copied / "copy-source-receipt.json").read_bytes() == original
        copied_size += _size(copied)
    assert int(env.connection.hget(env.prefix + ":totals", "committed")) == source_size + copied_size
    assert int(env.connection.hget(env.principal("human:42"), "committed")) == source_size
    assert int(env.connection.hget(env.principal(charged_actor.ledger_bucket), "committed")) == copied_size
    assert not env.connection.smembers(env.prefix + ":rebuild-pending")


def test_fork_copy_rejects_recipient_quota_before_copy(tmp_path, fork_retention):
    env = fork_retention
    source, target = tmp_path / "source", tmp_path / "target"
    attempt = _evidence(source)
    before = (attempt / "normalization.json").read_bytes()
    env.rebuild()
    env.connection.hset(env.principal("human:77"), "committed", retention._PRINCIPAL_LIMIT)
    with pytest.raises(retention.VectorUploadError, match="quota"):
        _prepare(source, target, env, retention.RetentionActor("human", 77))
    assert not target.exists()
    assert (attempt / "normalization.json").read_bytes() == before
    assert not env.connection.smembers(env.prefix + ":rebuild-pending")


@pytest.mark.parametrize("authority", ["both", "filesystem", "redis"])
@pytest.mark.parametrize("failure", ["rmtree", "rebuild"])
def test_fork_replacement_repairs_absent_target_and_previous_tombstone(
    tmp_path, monkeypatch, fork_retention, authority, failure,
):
    env = fork_retention
    target = tmp_path / "target"
    _evidence(target)
    env.rebuild()
    actual_remove = shutil.rmtree
    actual_rebuild = retention.reconcile_retention

    def fail_remove(path, *args, **kwargs):
        if Path(path).name == ".target.replacing-retained":
            raise OSError("interrupted tombstone deletion")
        return actual_remove(path, *args, **kwargs)

    def fail_rebuild(*args, **kwargs):
        raise OSError("interrupted accounting rebuild")

    if failure == "rmtree":
        monkeypatch.setattr(routes.shutil, "rmtree", fail_remove)
    else:
        monkeypatch.setattr(retention, "reconcile_retention", fail_rebuild)
    with pytest.raises(OSError, match="interrupted"):
        routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    assert not target.exists()
    marker, = (tmp_path / ".vector-upload-rebuild-pending").glob("*.json")
    if authority == "filesystem":
        env.connection.delete(env.prefix + ":rebuild-pending")
    elif authority == "redis":
        marker.unlink()
    # Admission may allocate another job id before another interrupted retry.
    with pytest.raises(OSError, match="interrupted"):
        routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    monkeypatch.setattr(routes.shutil, "rmtree", actual_remove)
    monkeypatch.setattr(retention, "reconcile_retention", actual_rebuild)
    routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    assert not target.exists()
    assert not (tmp_path / ".target.replacing-retained").exists()
    assert int(env.connection.hget(env.prefix + ":totals", "committed")) == 0
    assert not env.connection.smembers(env.prefix + ":rebuild-pending")
    assert not list((tmp_path / ".vector-upload-rebuild-pending").glob("*.json"))


@pytest.mark.parametrize("missing_configuration", [
    "VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT",
])
def test_absent_fork_target_preserves_retained_tombstone_without_configuration(
    tmp_path, monkeypatch, fork_retention, missing_configuration,
):
    env = fork_retention
    target = tmp_path / "target"
    _evidence(target)
    env.rebuild()
    actual_remove = shutil.rmtree

    def interrupted_remove(*_args, **_kwargs):
        raise OSError("interrupted tombstone deletion")

    monkeypatch.setattr(routes.shutil, "rmtree", interrupted_remove)
    with pytest.raises(OSError, match="interrupted"):
        routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    tombstone = tmp_path / ".target.replacing-retained"
    original = tombstone / "roads/vector_upload_attempts/shared-attempt/payload.upload"
    expected = original.read_bytes()
    monkeypatch.setattr(routes.shutil, "rmtree", actual_remove)
    monkeypatch.delenv(missing_configuration)
    with pytest.raises(retention.VectorUploadError, match="configured"):
        routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    assert not target.exists()
    assert original.read_bytes() == expected
    assert env.connection.smembers(env.prefix + ":rebuild-pending")


@pytest.mark.parametrize("old_target", [False, True])
def test_developer_test_run_replaces_and_accounts_before_pipeline(
    tmp_path, monkeypatch, fork_retention, old_target,
):
    env = fork_retention
    source, target = tmp_path / "source", tmp_path / "target"
    source_attempt = _evidence(source)
    if old_target:
        _evidence(target, private=True)
    env.rebuild()
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="developer-test"))
    monkeypatch.setattr(project, "get_wd", lambda _runid: str(source))
    monkeypatch.setattr(project, "get_primary_wd", lambda _runid: str(target))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(project, "clear_nodb_file_cache", lambda *_args: None)
    monkeypatch.setattr(project, "clear_locks", lambda *_args: [])

    def stop_before_pipeline(_wd):
        raise RuntimeError("stop before pipeline")

    monkeypatch.setattr(project.RedisPrep, "getInstance", stop_before_pipeline)
    with pytest.raises(RuntimeError, match="stop before pipeline"):
        project.test_run_rq(env.source_id)
    copied = target / source_attempt.relative_to(source)
    receipt = json.loads((copied / "normalization.json").read_text())
    assert receipt["actor"] == {"kind": "human", "user_id": 42}
    assert receipt["retention_actor"] == {"kind": "unattributed"}
    assert (copied / "payload.upload").read_bytes() == (source_attempt / "payload.upload").read_bytes()
    assert not (target / "archives").exists()
    assert int(env.connection.hget(env.prefix + ":totals", "committed")) == _size(source_attempt) + _size(copied)
    assert int(env.connection.hget(env.principal("unattributed"), "committed")) == _size(copied)


@pytest.mark.parametrize("metadata", [None, {}, {"vector_retention_actor": {"kind": "human", "identifier": 77}}])
def test_worker_passes_admission_actor_to_fork_copy(tmp_path, monkeypatch, metadata):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    seen = []
    job = SimpleNamespace(id="fork", connection=SimpleNamespace(eval=lambda *_args: 1))
    if metadata is not None:
        job.meta = metadata
    monkeypatch.setattr(project, "get_current_job", lambda: job)
    monkeypatch.setattr(project, "get_wd", lambda _runid: str(source))
    monkeypatch.setattr(project, "get_primary_wd", lambda _runid: str(target))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(project, "_reset_forked_run_job_markers", lambda *_args: None)

    def prepare(*_args, **kwargs):
        seen.append(kwargs["retention_actor"].receipt_value())
        return str(target)

    monkeypatch.setattr(project._fork_helpers, "prepare_fork_run", prepare)
    project.fork_rq("source", "target")
    assert seen == ([{"kind": "human", "user_id": 77}] if metadata else [{"kind": "unattributed"}])


def _profile_worker(monkeypatch, env, source, profile_root):
    """Exercise the real profile path resolver and exclusive worker claim."""
    target = profile_root / env.target_id
    profile_root.mkdir(parents=True)
    profile_id = f"profile;;fork;;{env.target_id}"

    def resolve(runid, prefer_active=True):
        if runid == env.source_id:
            return str(source)
        if runid == profile_id:
            return str(target)
        if runid == "profile;;fork;;__root_probe__":
            return str(profile_root / "__root_probe__")
        raise AssertionError(f"Unexpected run resolution: {runid}")

    monkeypatch.setattr(project, "get_wd", resolve)
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(
        id="profile-copy", connection=SimpleNamespace(eval=lambda *_args: 1),
        meta={"vector_retention_actor": {"kind": "human", "identifier": 77}},
    ))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(project, "_reset_forked_run_job_markers", lambda *_args: None)
    Path(project._profile_fork_claim_path(str(target))).write_text("profile-copy")
    return target, profile_id


@pytest.mark.parametrize("profile_inside_managed_root", [False, True])
def test_profile_fork_and_reset_respect_configured_filesystem_boundary(
    tmp_path, monkeypatch, fork_retention, profile_inside_managed_root,
):
    env = fork_retention
    managed = tmp_path / "runs"
    source = managed / "source"
    source_attempt = _evidence(source)
    profile_root = (managed if profile_inside_managed_root else tmp_path) / "profiles" / "fork"
    target, profile_id = _profile_worker(monkeypatch, env, source, profile_root)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(managed))
    env.rebuild(managed)
    original = (source_attempt / "normalization.json").read_bytes()
    source_size = _size(source_attempt)

    project.fork_rq(env.source_id, profile_id)

    copied = target / source_attempt.relative_to(source)
    assert (copied / "payload.upload").read_bytes() == (source_attempt / "payload.upload").read_bytes()
    assert (source_attempt / "normalization.json").read_bytes() == original
    assert not Path(project._profile_fork_claim_path(str(target))).exists()
    if profile_inside_managed_root:
        assert json.loads((copied / "normalization.json").read_bytes())["retention_actor"] == {
            "kind": "human", "user_id": 77,
        }
        assert int(env.connection.hget(env.prefix + ":totals", "committed")) == source_size + _size(copied)
        assert int(env.connection.hget(env.principal("human:77"), "committed")) == _size(copied)
    else:
        assert (copied / "normalization.json").read_bytes() == original
        assert int(env.connection.hget(env.prefix + ":totals", "committed")) == source_size
        assert not env.connection.exists(env.principal("human:77"))

    routes._delete_fork_replacement_tree(str(target), profile_id, lambda: None)
    assert not target.exists()
    assert int(env.connection.hget(env.prefix + ":totals", "committed")) == source_size
    assert not env.connection.smembers(env.prefix + ":rebuild-pending")
    assert (source_attempt / "normalization.json").read_bytes() == original


@pytest.mark.parametrize("missing_configuration", [
    "VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT",
])
def test_profile_fork_and_reset_require_configuration_for_retained_evidence(
    tmp_path, monkeypatch, fork_retention, missing_configuration,
):
    env = fork_retention
    managed = tmp_path / "runs"
    source = managed / "source"
    source_attempt = _evidence(source)
    target, profile_id = _profile_worker(monkeypatch, env, source, tmp_path / "profiles" / "fork")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(managed))
    env.rebuild(managed)
    source_bytes = (source_attempt / "payload.upload").read_bytes()
    monkeypatch.delenv(missing_configuration)

    with pytest.raises(retention.VectorUploadError, match="configured"):
        project.fork_rq(env.source_id, profile_id)
    assert not target.exists()
    assert (source_attempt / "payload.upload").read_bytes() == source_bytes

    retained_target = _evidence(target)
    target_bytes = (retained_target / "payload.upload").read_bytes()
    with pytest.raises(retention.VectorUploadError, match="configured"):
        routes._delete_fork_replacement_tree(str(target), profile_id, lambda: None)
    assert (retained_target / "payload.upload").read_bytes() == target_bytes


def test_authorized_replacement_recovers_interrupted_worker_copy(tmp_path, monkeypatch, fork_retention):
    env = fork_retention
    source, target = tmp_path / "source", tmp_path / "target"
    original = _evidence(source)
    env.rebuild()
    source_total = int(env.connection.hget(env.prefix + ":totals", "committed"))
    real_rsync = fork_helpers._run_rsync_with_bounded_output
    def interrupted(**kwargs):
        real_rsync(**kwargs)
        raise OSError("interrupted worker copy")
    with monkeypatch.context() as patch:
        patch.setattr(fork_helpers, "_run_rsync_with_bounded_output", interrupted)
        with pytest.raises(OSError, match="interrupted worker copy"):
            _prepare(source, target, env, retention.RetentionActor("human", 77))
    assert routes.retained_tree_repair_pending(target, "fork_copy")
    routes._delete_fork_replacement_tree(str(target), env.target_id, lambda: None)
    assert not target.exists()
    assert not env.connection.smembers(env.prefix + ":rebuild-pending")
    assert int(env.connection.hget(env.prefix + ":totals", "committed")) == source_total
    assert (original / "payload.upload").exists()
    _prepare(source, target, env, retention.RetentionActor("human", 77))
    assert int(env.connection.hget(env.principal("human:77"), "committed")) == _size(target / original.relative_to(source))
