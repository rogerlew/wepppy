"""Profile copies preserve evidence; executable reentry uses runFS accounting."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as normalization
from wepppy.profile_recorder.assembler import ProfileAssembler
from wepppy.profile_recorder.playback import PlaybackSession
from services.profile_playback import app as playback_app

pytestmark = pytest.mark.integration


def _retained_record(run: Path, *, archived=False) -> Path:
    attempt = run / ("archives/private/bundle" if archived else "roads/vector_upload_attempts/attempt")
    attempt.mkdir(parents=True)
    original = attempt / "original" / "upload.zip.upload"
    original.parent.mkdir(mode=0o700)
    original.write_bytes(b"retained original bytes")
    original.chmod(0o600)
    receipt = {
        "schema": "vector-normalization-v1", "status": "rejected",
        "actor": {"kind": "human", "user_id": 42},
        "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "project": "run:source", "attempt_id": "attempt",
    }
    (attempt / "normalization.json").write_text(json.dumps(receipt))
    return attempt


def _read_tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def runfs(monkeypatch, tmp_path):
    root = tmp_path / "managed"
    root.mkdir()
    filesystem_id = f"profile-retention-{tmp_path.name}"
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(root))
    kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_file = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_file.exists():
        kwargs["password"] = password_file.read_text().strip()
    connection = redis.client.Redis(**kwargs)
    connection.ping()
    monkeypatch.setattr(redis, "Redis", lambda **_kw: connection)
    monkeypatch.setattr(normalization.shutil, "disk_usage", lambda _path: SimpleNamespace(
        total=30_000_000_000, used=1_000_000_000, free=29_000_000_000))
    prefix = f"vector-upload-retention:{filesystem_id}"
    connection.hset(f"{prefix}:totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    monkeypatch.setattr(playback_app, "PLAYBACK_RUN_ROOT", root / "playback")
    monkeypatch.setattr(playback_app, "uuid4", lambda: SimpleNamespace(hex="repeatable-sandbox"))
    try:
        yield root, connection, prefix
    finally:
        keys = list(connection.scan_iter(match=f"{prefix}:*"))
        if keys:
            connection.delete(*keys)
        connection.close()


def test_offline_promotion_preserves_complete_retained_records_without_runfs_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    source = tmp_path / "source"
    _retained_record(source)
    _retained_record(source, archived=True)
    data_repo = tmp_path / "profile-data"
    draft = data_repo / "profiles/_drafts/source/stream"
    draft.mkdir(parents=True)
    (draft / "run_dir.txt").write_text(str(source))
    (draft / "events.jsonl").write_text('{"stage":"request"}\n')
    before = _read_tree(source)
    result = ProfileAssembler(data_repo).promote_draft("source", slug="promoted")
    copied = Path(result["profile_root"]) / "run"
    assert _read_tree(copied) == before
    assert _read_tree(source) == before
    assert (copied / "roads/vector_upload_attempts/attempt/original/upload.zip.upload").stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.rglob(".vector-upload-rebuild-pending"))


@pytest.mark.parametrize("prepare", ["_prepare_sandbox_clone", "_prepare_sandbox_run"])
def test_managed_profile_reentry_preserves_provenance_and_charges_copy(prepare, runfs, tmp_path):
    root, connection, prefix = runfs
    profile = tmp_path / "profiles/test-profile"
    source_attempt = _retained_record(profile / "run")
    original_receipt = json.loads((source_attempt / "normalization.json").read_text())
    _uuid, target = getattr(playback_app, prepare)(profile, "source")
    copied_attempt = target / "roads/vector_upload_attempts/attempt"
    receipt = json.loads((copied_attempt / "normalization.json").read_text())
    assert receipt["actor"] == original_receipt["actor"]
    assert receipt["source_sha256"] == original_receipt["source_sha256"]
    assert receipt["attempt_id"] == original_receipt["attempt_id"]
    assert receipt["retention_actor"] == {"kind": "unattributed"}
    assert (copied_attempt / "original/upload.zip.upload").read_bytes() == b"retained original bytes"
    expected = sum(len(data) for data in _read_tree(copied_attempt).values())
    assert int(connection.hget(f"{prefix}:totals", "committed")) == expected
    bucket = hashlib.sha256(b"unattributed").hexdigest()
    assert int(connection.hget(f"{prefix}:principal:{bucket}", "committed")) == expected
    assert json.loads((source_attempt / "normalization.json").read_text()) == original_receipt
    assert not connection.smembers(f"{prefix}:rebuild-pending")


@pytest.mark.parametrize("prepare", ["_prepare_sandbox_clone", "_prepare_sandbox_run"])
@pytest.mark.parametrize("missing", ["id", "root", "both"])
def test_evidence_reentry_does_not_classify_missing_configuration_as_offline_export(monkeypatch, tmp_path, prepare, missing):
    profile = tmp_path / "profiles/test-profile"
    _retained_record(profile / "run")
    sandbox_root = tmp_path / "playback"
    monkeypatch.setattr(playback_app, "PLAYBACK_RUN_ROOT", sandbox_root)
    monkeypatch.setattr(playback_app, "uuid4", lambda: SimpleNamespace(hex="sandbox"))
    managed = tmp_path / "managed"
    managed.mkdir()
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "configured-runfs")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(managed))
    if missing in {"id", "both"}:
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    if missing in {"root", "both"}:
        monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    with pytest.raises(normalization.VectorUploadError):
        getattr(playback_app, prepare)(profile, "source")
    assert not (sandbox_root / "sandbox").exists()


def test_deterministic_playback_reset_releases_old_retained_charge(runfs, monkeypatch, tmp_path):
    root, connection, prefix = runfs
    target = root / "playback/source"
    _retained_record(target)
    normalization.reconcile_retention(root, connection=connection, apply=True, rebuild_ledger=True)
    assert int(connection.hget(f"{prefix}:totals", "committed")) > 0
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(target.parent))
    session = PlaybackSession.__new__(PlaybackSession)
    session.seed_root = tmp_path / "absent-seeds"
    session.playback_run_id = "profile;;tmp;;source"
    actual = session._prepare_run_directory(tmp_path / "profile", "source")
    assert actual == target
    assert list(target.iterdir()) == []
    assert int(connection.hget(f"{prefix}:totals", "committed")) == 0
    assert not connection.smembers(f"{prefix}:rebuild-pending")


@pytest.mark.parametrize("failure_stage", ["partial_copy", "after_copy"])
def test_interrupted_profile_clone_retains_repair_and_retry_converges(runfs, monkeypatch, tmp_path, failure_stage):
    root, connection, prefix = runfs
    profile = tmp_path / "profiles/test-profile"
    _retained_record(profile / "run")
    copytree = shutil.copytree

    def interrupted(source, target, *args, **kwargs):
        if Path(source) == profile / "run" and failure_stage == "partial_copy":
            relative = Path("roads/vector_upload_attempts/attempt/original")
            copytree(Path(source) / relative, Path(target) / relative)
            raise OSError("injected clone interruption during copy")
        result = copytree(source, target, *args, **kwargs)
        if Path(source) == profile / "run":
            raise OSError("injected clone interruption after copy")
        return result

    with monkeypatch.context() as failure:
        failure.setattr(playback_app.shutil, "copytree", interrupted)
        with pytest.raises(playback_app.ProfileOperationError, match="injected clone interruption"):
            playback_app._prepare_sandbox_clone(profile, "source")
    assert connection.smembers(f"{prefix}:rebuild-pending")
    assert list((root / ".vector-upload-rebuild-pending").glob("*.json"))
    _uuid, target = playback_app._prepare_sandbox_clone(profile, "source")
    assert not connection.smembers(f"{prefix}:rebuild-pending")
    assert not list((root / ".vector-upload-rebuild-pending").glob("*.json"))
    attempt = target / "roads/vector_upload_attempts/attempt"
    assert (attempt / "original/upload.zip.upload").read_bytes() == b"retained original bytes"
    expected = sum(len(data) for data in _read_tree(attempt).values())
    assert int(connection.hget(f"{prefix}:totals", "committed")) == expected


def test_config_seed_playback_does_not_expand_into_full_snapshot_copy(monkeypatch, tmp_path):
    profile = tmp_path / "profiles/test-profile"
    _retained_record(profile / "run")
    config = profile / "capture/seed/config"
    config.mkdir(parents=True)
    (config / "demo.cfg").write_text("[general]\n")
    monkeypatch.setattr(playback_app, "PLAYBACK_RUN_ROOT", tmp_path / "sandbox")
    monkeypatch.setattr(playback_app, "Ron", lambda *_a, **_kw: None)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    _uuid, target = playback_app._prepare_sandbox_run(profile, "source")
    assert (target / "demo.cfg").read_text() == "[general]\n"
    assert not (target / "roads").exists()


def test_archive_export_copies_all_records_outside_runfs_without_charging_export(runfs, monkeypatch, tmp_path):
    root, connection, prefix = runfs
    profiles = tmp_path / "profiles"
    profile = profiles / "test-profile"
    attempt = _retained_record(profile / "run", archived=True)
    (profile / "run/active_config.txt").write_text("demo")
    monkeypatch.setattr(playback_app, "PROFILE_ROOT", profiles)
    monkeypatch.setattr(playback_app, "PLAYBACK_ARCHIVE_ROOT", tmp_path / "offline-archive")
    monkeypatch.setattr(playback_app, "_detect_profile_run_id", lambda _: "source")
    monkeypatch.setattr(playback_app, "_clear_sandbox_locks", lambda *_a, **_kw: None)
    monkeypatch.setattr(playback_app, "_poll_job_completion", lambda *_a, **_kw: {"status": "finished"})
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"Success": True, "job_id": "test-job"})
    monkeypatch.setattr(playback_app, "_ensure_session", lambda *_a, **_kw: SimpleNamespace(post=lambda *_a, **_kw: response))
    result = playback_app.archive_profile("test-profile", playback_app.ProfileArchiveRequest())
    copied = Path(result.archive_dir) / "private/bundle"
    sandbox = Path(result.run_dir) / "archives/private/bundle"
    assert _read_tree(copied) == _read_tree(sandbox)
    assert (copied / "original/upload.zip.upload").read_bytes() == (attempt / "original/upload.zip.upload").read_bytes()
    expected = sum(len(data) for data in _read_tree(sandbox).values())
    assert int(connection.hget(f"{prefix}:totals", "committed")) == expected


def test_deterministic_playback_reset_without_identity_preserves_existing_evidence(monkeypatch, tmp_path):
    target = tmp_path / "playback/source"
    _retained_record(target)
    before = _read_tree(target)
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(target.parent))
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    session = PlaybackSession.__new__(PlaybackSession)
    session.seed_root = tmp_path / "absent-seeds"
    session.playback_run_id = "profile;;tmp;;source"
    with pytest.raises(normalization.VectorUploadError):
        session._prepare_run_directory(tmp_path / "profile", "source")
    assert _read_tree(target) == before


@pytest.mark.parametrize("prepare", ["_prepare_sandbox_clone", "_prepare_sandbox_run"])
def test_default_split_root_profile_copy_preserves_records_without_runfs_charge(
    runfs, monkeypatch, tmp_path, prepare,
):
    _managed, connection, prefix = runfs
    # Match deployment topology: /wc1 and /workdir/data are separate roots.
    managed = tmp_path / "wc1"
    managed.mkdir()
    data_repo = tmp_path / "workdir/wepppy-test-engine-data"
    profile = data_repo / "profiles/test-profile"
    _retained_record(profile / "run")
    _retained_record(profile / "run", archived=True)
    source_bytes = _read_tree(profile / "run")
    playback_root = data_repo / "playback/runs"
    existing = playback_root / "repeatable-sandbox"
    _retained_record(existing)
    (existing / "previous-run.txt").write_bytes(b"old workspace")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(managed))
    monkeypatch.setattr(playback_app, "PLAYBACK_RUN_ROOT", playback_root)
    ledger_before = connection.hgetall(f"{prefix}:totals")

    _uuid, target = getattr(playback_app, prepare)(profile, "source")

    assert target == existing
    assert _read_tree(target) == source_bytes
    assert _read_tree(profile / "run") == source_bytes
    assert connection.hgetall(f"{prefix}:totals") == ledger_before
    assert not list(connection.scan_iter(match=f"{prefix}:principal:*"))
    assert not connection.smembers(f"{prefix}:rebuild-pending")
    assert not list(tmp_path.rglob(".vector-upload-rebuild-pending"))


def test_default_split_root_deterministic_reset_preserves_seed_bytes_without_runfs_charge(
    runfs, monkeypatch, tmp_path,
):
    _managed, connection, prefix = runfs
    managed = tmp_path / "wc1"
    managed.mkdir()
    data_repo = tmp_path / "workdir/wepppy-test-engine-data"
    profile = data_repo / "profiles/test-profile"
    config_seed = profile / "capture/seed/config"
    config_seed.mkdir(parents=True)
    (config_seed / "demo.cfg").write_bytes(b"[general]\nname = source\n")
    target = data_repo / "playback/runs/source"
    _retained_record(target)
    source_bytes = _read_tree(config_seed)
    ledger_before = connection.hgetall(f"{prefix}:totals")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(managed))
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(target.parent))
    session = PlaybackSession.__new__(PlaybackSession)
    session.seed_root = config_seed.parent
    session.seed_config_stem = None
    session.playback_run_id = "profile;;tmp;;source"

    result = session._prepare_run_directory(profile, "source")

    assert result == target
    assert _read_tree(target) == source_bytes
    assert _read_tree(config_seed) == source_bytes
    assert connection.hgetall(f"{prefix}:totals") == ledger_before
    assert not connection.smembers(f"{prefix}:rebuild-pending")
    assert not list(tmp_path.rglob(".vector-upload-rebuild-pending"))


def test_managed_mapped_private_archive_reset_with_empty_source_releases_charge(
    runfs, monkeypatch, tmp_path,
):
    root, connection, prefix = runfs
    sandbox = root / "playback/repeatable-sandbox"
    sandbox.mkdir(parents=True)
    (sandbox / "active_config.txt").write_text("demo")
    profile_root = tmp_path / "profiles/test-profile"
    profile_root.mkdir(parents=True)
    archive_root = root / "profile-archives"
    target = archive_root / "repeatable-sandbox"
    # The export maps source archives/private/bundle to destination private/bundle.
    staged = tmp_path / "export-source"
    source_attempt = _retained_record(staged, archived=True)
    mapped = target / "private/bundle"
    shutil.copytree(source_attempt, mapped)
    normalization.reconcile_retention(root, connection=connection, apply=True, rebuild_ledger=True)
    original_charge = sum(len(data) for data in _read_tree(mapped).values())
    assert int(connection.hget(f"{prefix}:totals", "committed")) == original_charge
    monkeypatch.setattr(playback_app, "PROFILE_ROOT", profile_root.parent)
    monkeypatch.setattr(playback_app, "PLAYBACK_ARCHIVE_ROOT", archive_root)
    monkeypatch.setattr(playback_app, "_detect_profile_run_id", lambda _: "source")
    # Isolate archive export from setup; this sandbox has no new archive output.
    monkeypatch.setattr(playback_app, "_prepare_sandbox_clone", lambda *_a: ("repeatable-sandbox", sandbox))
    monkeypatch.setattr(playback_app, "_clear_sandbox_locks", lambda *_a, **_kw: None)
    monkeypatch.setattr(playback_app, "_poll_job_completion", lambda *_a, **_kw: {"status": "finished"})
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"Success": True, "job_id": "test-job"})
    monkeypatch.setattr(playback_app, "_ensure_session", lambda *_a, **_kw: SimpleNamespace(post=lambda *_a, **_kw: response))

    result = playback_app.archive_profile("test-profile", playback_app.ProfileArchiveRequest())

    assert Path(result.archive_dir) == target
    assert list(target.iterdir()) == []
    assert int(connection.hget(f"{prefix}:totals", "committed")) == 0
    assert not connection.smembers(f"{prefix}:rebuild-pending")
    assert not list((root / ".vector-upload-rebuild-pending").glob("*.json"))
