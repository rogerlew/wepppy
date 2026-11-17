"""Real ledger recovery for destructive run and Batch deletion boundaries."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as normalization
from wepppy.rq import batch_rq, project_rq_delete

pytestmark = pytest.mark.integration


@pytest.fixture
def deletion_environment(tmp_path, monkeypatch):
    identity = f"deletion-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", identity)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    monkeypatch.setenv("BATCH_RUNNER_ROOT", str(tmp_path))
    kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    secret = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if secret.exists():
        kwargs["password"] = secret.read_text().strip()
    connection = redis.client.Redis(**kwargs)
    prefix = f"vector-upload-retention:{identity}"
    connection.hset(f"{prefix}:totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    scopes = []
    def factory():
        def acquire(key):
            lease = normalization.RedisScopeLeaseFactory(connection)(key)
            scopes.append(lease.key)
            return lease
        return acquire
    for module in (batch_rq, project_rq_delete):
        monkeypatch.setattr(module, "RedisScopeLeaseFactory", factory)
        monkeypatch.setattr(module, "acquire_retention_maintenance_lease", lambda: normalization.acquire_retention_maintenance_lease(connection))
        monkeypatch.setattr(module, "begin_retention_rebuild_obligation", lambda root, **kw: normalization.begin_retention_rebuild_obligation(root, connection=connection, **kw))
        monkeypatch.setattr(module, "complete_retention_rebuild_obligation", lambda path: normalization.complete_retention_rebuild_obligation(path, connection=connection))
        monkeypatch.setattr(module, "reconcile_retention", lambda root, **kw: normalization.reconcile_retention(root, connection=connection, **kw))
    mutations = []
    monkeypatch.setattr(project_rq_delete, "_try_mark_delete_state", lambda **kw: mutations.append("ttl") or True)
    monkeypatch.setattr(project_rq_delete, "_delete_db_record", lambda *_: mutations.append("db"))
    import flask
    monkeypatch.setattr(flask, "has_app_context", lambda: True)
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: None)
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda *_: None)
    monkeypatch.setattr(batch_rq, "_active_batch_job_summaries", lambda *a, **kw: [])
    monkeypatch.setattr(batch_rq, "_cleanup_batch_run_cache_and_locks", lambda *_: mutations.append("cache"))
    monkeypatch.setattr(batch_rq.BatchRunner, "cleanup_run_instances", lambda *_: None)
    monkeypatch.setattr(batch_rq.NoDbBase, "cleanup_run_instances", lambda *_: None)
    def runner(name):
        target = tmp_path / name
        if not target.exists():
            raise FileNotFoundError(name)
        return SimpleNamespace(wd=str(target))
    monkeypatch.setattr(batch_rq.BatchRunner, "getInstanceFromBatchName", runner)
    def invoke(kind, target, remove=None):
        if kind == "batch":
            if remove:
                with monkeypatch.context() as patch:
                    patch.setattr(batch_rq.shutil, "rmtree", remove)
                    return batch_rq.delete_batch_rq(target.name)
            return batch_rq.delete_batch_rq(target.name)
        runtime = project_rq_delete.DeleteRuntime(
            get_current_job=lambda: None, get_wd=lambda _: str(target),
            publish_status=lambda *_: None,
            clear_nodb_file_cache=lambda *_: mutations.append("cache"),
            clear_locks=lambda *_: None, rmtree=remove or shutil.rmtree,
            sleep=lambda *_: None, logger=logging.getLogger(__name__),
        )
        return project_rq_delete.delete_run_rq(target.name, str(target), delete_files=True, runtime=runtime)
    yield SimpleNamespace(root=tmp_path, conn=connection, prefix=prefix, scopes=scopes, mutations=mutations, invoke=invoke)
    keys = list(connection.scan_iter(match=f"{prefix}:*")) + scopes
    if keys:
        connection.delete(*keys)


def retained(target, user_id):
    attempt = target / "resources" / "vector_upload_attempts" / "one"
    attempt.mkdir(parents=True)
    (attempt / "original.upload").write_bytes(b"retained-complete-source")
    (attempt / "normalization.json").write_text(json.dumps({
        "schema": "vector-normalization-v1", "status": "rejected",
        "actor": {"kind": "human", "user_id": user_id},
    }))
    return sum(p.stat().st_size for p in attempt.iterdir())


@pytest.mark.parametrize("kind", ["run", "batch"])
@pytest.mark.parametrize("fault", ["none", "partial", "removed", "fsync", "global_loss", "scope_loss", "rebuild"])
def test_deletion_retries_preserve_obligations_and_exact_ledger(deletion_environment, monkeypatch, kind, fault):
    env = deletion_environment
    target = env.root / f"target-{kind}"
    retained(target, 7)
    unrelated = env.root / "unrelated"
    unrelated_bytes = retained(unrelated, 8)
    normalization.reconcile_retention(env.root, apply=True, rebuild_ledger=True, connection=env.conn)
    reservation = normalization.RedisRetentionLedger(env.conn).reserve(
        project_key=f"run:unrelated-{env.root.name}", actor=normalization.RetentionActor("human", 9),
        worst_case_bytes=123, filesystem_root=unrelated,
    )
    remove = shutil.rmtree
    fsync = os.fsync
    fired = False
    def fault_remove(path):
        nonlocal fired
        if fault == "partial" and not fired:
            fired = True
            next(path.rglob("original.upload")).unlink()
            raise OSError(5, "injected partial deletion")
        remove(path)
        fired = True
        if fault == "removed":
            raise OSError(5, "injected after deletion")
        if fault == "global_loss":
            env.conn.delete(f"{env.prefix}:reconcile")
        if fault == "scope_loss":
            env.conn.delete(env.scopes[0])
    def fault_fsync(fd):
        if fired:
            raise OSError(5, "injected parent fsync")
        return fsync(fd)
    with monkeypatch.context() as patch:
        if fault == "fsync":
            patch.setattr(os, "fsync", fault_fsync)
        if fault == "rebuild":
            module = batch_rq if kind == "batch" else project_rq_delete
            patch.setattr(module, "reconcile_retention", lambda *_a, **_k: (_ for _ in ()).throw(OSError("injected rebuild")))
        if fault in {"none", "partial", "removed"} and kind == "run":
            env.invoke(kind, target, fault_remove)
        elif fault == "none":
            env.invoke(kind, target, fault_remove)
        else:
            with pytest.raises((OSError, normalization.VectorUploadError)):
                env.invoke(kind, target, fault_remove)
    if fault != "none" and (target.exists() or fault not in {"removed"} or kind == "batch"):
        assert env.conn.scard(f"{env.prefix}:rebuild-pending") == 1
        assert len(list((env.root / ".vector-upload-rebuild-pending").glob("*.json"))) == 1
    env.invoke(kind, target)
    assert not target.exists()
    assert env.conn.scard(f"{env.prefix}:rebuild-pending") == 0
    assert not list((env.root / ".vector-upload-rebuild-pending").glob("*.json"))
    totals = env.conn.hgetall(f"{env.prefix}:totals")
    assert int(totals["committed"]) == unrelated_bytes
    assert int(totals["reserved"]) == 123
    assert int(totals["inflight"]) == 1
    deleted_bucket = hashlib.sha256(b"human:7").hexdigest()
    assert int(env.conn.hget(f"{env.prefix}:principal:{deleted_bucket}", "committed") or 0) == 0
    active_bucket = hashlib.sha256(b"human:9").hexdigest()
    active_totals = env.conn.hgetall(f"{env.prefix}:principal:{active_bucket}")
    assert int(active_totals["reserved"]) == 123
    assert int(active_totals["committed"]) == 0
    bucket = hashlib.sha256(b"human:8").hexdigest()
    assert int(env.conn.hget(f"{env.prefix}:principal:{bucket}", "committed")) == unrelated_bytes
    assert next(unrelated.rglob("original.upload")).read_bytes() == b"retained-complete-source"
    reservation.release_prewrite()


@pytest.mark.parametrize("kind", ["run", "batch"])
@pytest.mark.parametrize("fault", ["missing_id", "missing_root", "wrong_root", "symlink"])
def test_invalid_deletion_identity_causes_no_filesystem_or_workflow_mutation(deletion_environment, monkeypatch, kind, fault):
    env = deletion_environment
    target = env.root / "target"
    retained(target, 7)
    if fault == "missing_id":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID")
    elif fault == "missing_root":
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT")
    elif fault == "wrong_root":
        wrong = env.root / "wrong"
        wrong.mkdir()
        monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(wrong))
    else:
        alias = env.root / "alias"
        alias.symlink_to(target, target_is_directory=True)
        target = alias
    before = {str(p.relative_to(env.root)): p.read_bytes() for p in env.root.rglob("*") if p.is_file()}
    with pytest.raises((RuntimeError, ValueError)):
        env.invoke(kind, target)
    after = {str(p.relative_to(env.root)): p.read_bytes() for p in env.root.rglob("*") if p.is_file()}
    assert after == before
    assert not env.mutations
    assert env.conn.scard(f"{env.prefix}:rebuild-pending") == 0


@pytest.mark.parametrize("dangling", [False, True])
def test_obligation_directory_symlink_rejected_without_touching_referent(deletion_environment, dangling):
    env = deletion_environment
    referent = env.root / "other"
    if not dangling:
        referent.mkdir(mode=0o755)
    marker = env.root / ".vector-upload-rebuild-pending"
    marker.symlink_to(referent, target_is_directory=True)
    with pytest.raises(normalization.VectorUploadError):
        normalization.begin_retention_rebuild_obligation(env.root, operation="test", target="target", connection=env.conn)
    assert not referent.exists() if dangling else (referent.stat().st_mode & 0o777) == 0o755
    assert env.conn.scard(f"{env.prefix}:rebuild-pending") == 0


def test_obligation_fsync_failure_preserves_redis_and_replaced_file(deletion_environment, monkeypatch):
    env = deletion_environment
    original = normalization._atomic_json
    def write_then_fail(path, value):
        original(path, value)
        raise OSError("injected post-replace directory fsync")
    monkeypatch.setattr(normalization, "_atomic_json", write_then_fail)
    with pytest.raises(OSError):
        normalization.begin_retention_rebuild_obligation(env.root, operation="test", target="target", connection=env.conn)
    paths = list((env.root / ".vector-upload-rebuild-pending").glob("*.json"))
    assert len(paths) == 1
    assert env.conn.smembers(f"{env.prefix}:rebuild-pending") == {paths[0].stem}


@pytest.mark.parametrize("child", ["_base", "runs/child"])
def test_batch_deletion_fences_active_child_upload(deletion_environment, child):
    env = deletion_environment
    target = env.root / "batch-with-child"
    retained(target, 7)
    retained(target / child, 8)
    leaf = Path(child).name
    lease = normalization.RedisScopeLeaseFactory(env.conn)(f"run:batch;;{target.name};;{leaf}")
    try:
        with pytest.raises(normalization.VectorUploadError, match="Another vector evidence"):
            env.invoke("batch", target)
        assert next((target / child).rglob("original.upload")).read_bytes() == b"retained-complete-source"
        assert not env.mutations
        assert env.conn.scard(f"{env.prefix}:rebuild-pending") == 0
    finally:
        lease.release()
    env.invoke("batch", target)
    assert not target.exists()
