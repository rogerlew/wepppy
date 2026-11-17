from __future__ import annotations

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER

from wepppy.query_engine.catalog_refresh import (
    catalog_lifecycle_guard, invalidate_catalog_incarnation,
)

from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle

import errno
import hashlib
import json
import logging
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, ContextManager, Mapping, Sequence

from wepppy.microservices.vector_upload_normalization import (
    RedisRetentionLedger,
    RedisScopeLeaseFactory,
    RetentionActor,
    assert_project_retention_capacity,
    begin_retention_rebuild_obligation,
    complete_retention_rebuild_obligation,
    reconcile_retention,
)

_ARCHIVE_DISK_HEADROOM_RATIO = 0.02
_ARCHIVE_MIN_HEADROOM_BYTES = 64 * 1024 * 1024
_ARCHIVE_PER_FILE_OVERHEAD_BYTES = 1024
_ARCHIVE_EXCLUDE_PREFIXES: tuple[str, ...] = ("archives",)
_PROJECT_CONFIG_TRANSACTION_FILES = frozenset({
    ".config-amendment.lock",
    "roads.lifecycle.lock",
    ".config-amendment.pending.json",
})


@dataclass(frozen=True)
class ArchiveRuntime:
    get_current_job: Callable[[], Any]
    get_wd: Callable[[str], str]
    get_prep_from_runid: Callable[[str], Any]
    lock_statuses: Callable[[str], Mapping[str, Any]]
    clear_nodb_file_cache: Callable[[str], Sequence[Any]]
    publish_status: Callable[[str, str], None]
    disk_usage: Callable[[str | os.PathLike[str]], Any]
    zip_file_cls: type[zipfile.ZipFile]
    project_config_lifecycle_guard: Callable[[str | Path], ContextManager[None]]
    project_config_authority_wd: Callable[[str], str]


def _normalize_relpath(relpath: str) -> str:
    rel = relpath.replace("\\", "/")
    if rel == ".":
        return ""
    while rel.startswith("./"):
        rel = rel[2:]
    return rel.rstrip("/")


def _is_archive_excluded_relpath(relpath: str) -> bool:
    rel = _normalize_relpath(relpath)
    if not rel:
        return False
    if "/" not in rel and rel in _PROJECT_CONFIG_TRANSACTION_FILES:
        return True
    return any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in _ARCHIVE_EXCLUDE_PREFIXES)


def _estimate_archive_required_bytes(payload_bytes: int, file_count: int) -> int:
    headroom = max(
        _ARCHIVE_MIN_HEADROOM_BYTES,
        int(payload_bytes * _ARCHIVE_DISK_HEADROOM_RATIO),
        file_count * _ARCHIVE_PER_FILE_OVERHEAD_BYTES,
    )
    return max(payload_bytes, 0) + headroom


def _assert_sufficient_disk_space(
    base_path: Path,
    *,
    required_bytes: int,
    purpose: str,
    reclaimable_bytes: int = 0,
    disk_usage: Callable[[str | os.PathLike[str]], Any] = shutil.disk_usage,
) -> None:
    usage = disk_usage(base_path)
    available_bytes = int(getattr(usage, "free", 0)) + max(int(reclaimable_bytes), 0)
    if available_bytes < int(required_bytes):
        raise OSError(
            errno.ENOSPC,
            (
                f"Insufficient disk space to {purpose}: "
                f"required={int(required_bytes)}B available={available_bytes}B "
                f"(includes reclaimable={max(int(reclaimable_bytes), 0)}B)"
            ),
        )


def _calculate_run_payload_bytes(wd: Path) -> tuple[int, int]:
    total_bytes = 0
    file_count = 0

    for root, dirs, files in os.walk(wd):
        if any((Path(root) / name).is_symlink() for name in (*dirs, *files)):
            raise ValueError("Project archives cannot include symbolic links")
        rel_root = os.path.relpath(root, wd)
        if rel_root == ".":
            rel_root = ""

        if _is_archive_excluded_relpath(rel_root):
            dirs[:] = []
            continue

        dirs[:] = [
            d
            for d in dirs
            if not _is_archive_excluded_relpath(os.path.relpath(os.path.join(root, d), wd))
        ]

        for filename in files:
            abs_path = Path(root) / filename
            rel_path = os.path.relpath(abs_path, wd)
            if _is_archive_excluded_relpath(rel_path):
                continue
            try:
                total_bytes += abs_path.stat().st_size
                file_count += 1
            except FileNotFoundError:
                continue

    return total_bytes, file_count


def _contains_vector_upload_attempts(wd: Path) -> bool:
    for root, dirs, files in os.walk(wd):
        if any((Path(root) / name).is_symlink() for name in (*dirs, *files)):
            raise ValueError("Project archives cannot include symbolic links")
        relative = os.path.relpath(root, wd)
        if _is_archive_excluded_relpath(relative):
            dirs[:] = []
            continue
        if "vector_upload_attempts" in dirs:
            return True
        dirs[:] = [name for name in dirs if name != "archives"]
    return False


def _write_private_archive_sidecar(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    temp = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        temp.unlink(missing_ok=True)


def _verify_private_archive(archive_path: Path, wd: Path) -> None:
    try:
        relative = archive_path.relative_to(wd)
    except ValueError as exc:
        raise ValueError("Invalid private archive path") from exc
    if relative.parts[:2] != ("archives", "private"):
        return
    sidecar_path = archive_path.with_suffix(".zip.sensitive.json")
    receipt_path = archive_path.parent / "normalization.json"
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        size = archive_path.stat().st_size
        digest = hashlib.sha256()
        with archive_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Private archive provenance is invalid") from exc
    archive_digest = digest.hexdigest()
    if (
        sidecar.get("schema") != "vector-upload-private-archive-v1"
        or sidecar.get("archive") != archive_path.name
        or sidecar.get("archive_size") != size
        or sidecar.get("archive_sha256") != archive_digest
        or sidecar.get("contains_vector_upload_attempts") is not True
        or receipt.get("schema") != "vector-normalization-v1"
        or receipt.get("status") not in {"accepted", "accepted_recovered"}
        or receipt.get("canonical_path") != relative.as_posix()
        or receipt.get("canonical_size") != size
        or receipt.get("canonical_sha256") != archive_digest
    ):
        raise ValueError("Private archive provenance is invalid")
def _collect_restore_members(
    zf: zipfile.ZipFile,
    wd: Path,
) -> tuple[list[tuple[zipfile.ZipInfo, Path, Path]], int, int]:
    members: list[tuple[zipfile.ZipInfo, Path, Path]] = []
    total_bytes = 0
    file_count = 0

    for member in zf.infolist():
        arcname = member.filename
        if not arcname:
            continue

        # Normalize name to avoid traversal attempts.
        target_path = (wd / arcname).resolve()
        if wd not in target_path.parents and target_path != wd:
            raise ValueError(f"Unsafe archive member path: {arcname}")

        try:
            relative_target = target_path.relative_to(wd)
        except ValueError as exc:
            raise ValueError(f"Unsafe archive member path: {arcname}") from exc

        # Skip archive outputs and ephemeral NoDir cache paths.
        if _is_archive_excluded_relpath(relative_target.as_posix()):
            continue

        if not member.is_dir():
            total_bytes += int(member.file_size)
            file_count += 1

        members.append((member, target_path, relative_target))

    return members, total_bytes, file_count


def _restore_directory_modes(members, wd):
    """Validate explicit UNIX directory modes before destructive restoration."""
    modes = {}
    file_targets = {target for member, target, _ in members if not member.is_dir()}
    for member, target, _ in members:
        mode = member.external_attr >> 16
        if (target == wd or not member.is_dir() or member.create_system != 3
                or not stat.S_ISDIR(mode)):
            continue
        permissions = stat.S_IMODE(mode)
        if target in modes and modes[target] != permissions:
            raise ValueError(f'Conflicting archive directory modes: {member.filename}')
        if target in file_targets or any(parent in file_targets for parent in target.parents if parent != wd):
            raise ValueError(f'Archive directory conflicts with a file: {member.filename}')
        modes[target] = permissions
    return modes


def _grant_owner_cleanup_perms(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, OSError):
        return

    if stat.S_ISLNK(mode):
        return

    desired_mode = mode | stat.S_IRUSR | stat.S_IWUSR
    if stat.S_ISDIR(mode):
        desired_mode |= stat.S_IXUSR

    if desired_mode == mode:
        return

    try:
        os.chmod(path, desired_mode)
    except OSError:
        return


def _prepare_cleanup_retry(path: Path) -> None:
    _grant_owner_cleanup_perms(path.parent)

    try:
        is_dir = path.is_dir()
        is_symlink = path.is_symlink()
    except OSError:
        return

    if is_symlink or not is_dir:
        _grant_owner_cleanup_perms(path)
        return

    for root, dirs, files in os.walk(path, topdown=False, followlinks=False):
        root_path = Path(root)
        _grant_owner_cleanup_perms(root_path)

        for filename in files:
            _grant_owner_cleanup_perms(root_path / filename)

        for dirname in dirs:
            child = root_path / dirname
            try:
                if child.is_symlink():
                    continue
            except OSError:
                continue
            _grant_owner_cleanup_perms(child)

    _grant_owner_cleanup_perms(path)


def _remove_restore_directory(path: Path) -> None:
    try:
        shutil.rmtree(path)
        return
    except FileNotFoundError:
        return
    except PermissionError:
        _prepare_cleanup_retry(path)

    shutil.rmtree(path)


def _remove_restore_file(path: Path) -> None:
    try:
        path.unlink()
        return
    except FileNotFoundError:
        return
    except PermissionError:
        _prepare_cleanup_retry(path)

    path.unlink()


def _clear_archive_job_id(runtime: ArchiveRuntime, prep: Any | None, runid: str) -> None:
    if prep is None:
        try:
            prep = runtime.get_prep_from_runid(runid)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:149", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            prep = None

    if prep is not None:
        try:
            prep.clear_archive_job_id()
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:155", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            pass


def archive_rq(
    runid: str,
    comment: str | None,
    retention_actor: Mapping[str, Any] | None = None,
    *,
    runtime: ArchiveRuntime,
) -> None:
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "archive_rq"
    status_channel = f"{runid}:archive"
    runtime.publish_status(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    prep = None
    archive_path: str | None = None
    archive_path_tmp: str | None = None
    retention_reservation = None
    retention_lease = None
    try:
        prep = runtime.get_prep_from_runid(runid)
        wd = runtime.get_wd(runid)
        wd_path = Path(wd)

        authority_wd = runtime.project_config_authority_wd(runid)
        roads_guard = roads_lifecycle.operation(wd_path, shared=True, create=True)
        with catalog_lifecycle_guard(wd_path), runtime.project_config_lifecycle_guard(authority_wd), roads_guard:
            from wepppy.declarative.policy import require_settled
            require_settled(wd_path)
            locked = [name for name, state in runtime.lock_statuses(runid).items() if name.endswith(".nodb") and state]
            if locked:
                raise RuntimeError("Cannot archive while files are locked: " + ", ".join(locked))

            # Hold the same project-scoped lease used by vector uploads before
            # inspecting or walking the tree. Otherwise an upload can create a
            # retained attempt after the sensitivity check and leak it into a
            # public archive.
            retention_configured = bool(
                os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip()
                and os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", "").strip()
            )
            if retention_configured:
                retention_lease = RedisScopeLeaseFactory()(f"run:{runid}")
                retention_lease.assert_owned()

            payload_bytes, payload_file_count = _calculate_run_payload_bytes(wd_path)
            required_bytes = _estimate_archive_required_bytes(payload_bytes, payload_file_count)
            contains_sensitive = _contains_vector_upload_attempts(wd_path)
            _assert_sufficient_disk_space(
                wd_path,
                required_bytes=required_bytes,
                purpose=f"create archive for {runid}",
                disk_usage=runtime.disk_usage,
            )

            archives_dir = Path(wd) / "archives"
            archives_dir.mkdir(exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            archive_name = f"{runid}.{timestamp}.zip"
            if contains_sensitive:
                bundle_dir = archives_dir / "private" / f"{runid}.{timestamp}"
                bundle_dir.mkdir(parents=True, mode=0o700)
                os.chmod(bundle_dir.parent, 0o700)
                os.chmod(bundle_dir, 0o700)
                archive_path_obj = bundle_dir / archive_name
                archive_name = archive_path_obj.relative_to(archives_dir).as_posix()
                assert_project_retention_capacity(
                    (
                        wd_path / "roads" / "vector_upload_attempts",
                        wd_path / "ag_fields" / "vector_upload_attempts",
                        wd_path / "_pups" / "omni" / "contrasts" / "vector_upload_attempts",
                        archives_dir / "private",
                    ),
                    worst_case_bytes=required_bytes + 1024 * 1024,
                )
                actor_payload = retention_actor if isinstance(retention_actor, Mapping) else {}
                actor = RetentionActor(
                    str(actor_payload.get("kind") or "unattributed"),
                    actor_payload.get("identifier"),
                )
                retention_reservation = RedisRetentionLedger().reserve(
                    project_key=f"run:{runid}",
                    actor=actor,
                    worst_case_bytes=required_bytes + 1024 * 1024,
                    filesystem_root=wd_path,
                )
                retention_reservation.bind_attempt(bundle_dir)
            else:
                archive_path_obj = archives_dir / archive_name
            archive_path = os.fspath(archive_path_obj)
            archive_path_tmp = archive_path + ".tmp"

            for candidate in (archive_path, archive_path_tmp):
                if os.path.exists(candidate):
                    os.remove(candidate)

            runtime.publish_status(status_channel, f"Creating archive {archive_name}")

            comment_bytes = (comment or "").encode("utf-8")

            with runtime.zip_file_cls(archive_path_tmp, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for root, dirs, files in os.walk(wd):
                    if retention_lease is not None:
                        retention_lease.assert_owned()
                    if any(os.path.islink(os.path.join(root, name)) for name in (*dirs, *files)):
                        raise ValueError("Project archives cannot include symbolic links")
                    rel_root = os.path.relpath(root, wd)
                    if rel_root == ".":
                        rel_root = ""

                    if _is_archive_excluded_relpath(rel_root):
                        dirs[:] = []
                        continue

                    dirs[:] = [
                        d
                        for d in dirs
                        if not _is_archive_excluded_relpath(os.path.relpath(os.path.join(root, d), wd))
                    ]

                    if rel_root:
                        # os.walk does not traverse symlink directories. Retain
                        # ordinary directory metadata, including empty folders.
                        zf.write(root, rel_root + "/")

                    for filename in files:
                        if retention_lease is not None:
                            retention_lease.assert_owned()
                        abs_path = os.path.join(root, filename)
                        arcname = os.path.relpath(abs_path, wd)
                        if _is_archive_excluded_relpath(arcname):
                            continue

                        runtime.publish_status(status_channel, f"Adding {arcname}")
                        zf.write(abs_path, arcname)

                if comment_bytes:
                    zf.comment = comment_bytes

            if retention_lease is not None:
                retention_lease.assert_owned()
            os.replace(archive_path_tmp, archive_path)
            if contains_sensitive:
                archive_size = archive_path_obj.stat().st_size
                archive_digest = hashlib.sha256()
                with archive_path_obj.open("rb") as archive_stream:
                    for chunk in iter(lambda: archive_stream.read(1024 * 1024), b""):
                        archive_digest.update(chunk)
                archive_sha256 = archive_digest.hexdigest()
                os.chmod(archive_path_obj, 0o600)
                sidecar = archive_path_obj.with_suffix(archive_path_obj.suffix + ".sensitive.json")
                sidecar_payload = {
                    "schema": "vector-upload-private-archive-v1",
                    "archive": archive_path_obj.name,
                    "archive_size": archive_size,
                    "archive_sha256": archive_sha256,
                    "contains_vector_upload_attempts": True,
                }
                _write_private_archive_sidecar(sidecar, sidecar_payload)
                _write_private_archive_sidecar(
                    archive_path_obj.parent / "normalization.json",
                    {
                        "schema": "vector-normalization-v1",
                        "attempt_id": archive_path_obj.parent.name,
                        "status": "accepted",
                        "outcome": "retained",
                        "enforcement_stage": "private_archive",
                        "accounting_status": "committed",
                        "actor": actor.receipt_value(),
                        "reservation_id": retention_reservation.reservation_id,
                        "project_root": wd_path.resolve(strict=True).relative_to(
                            Path(os.environ["VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT"]).resolve(strict=True)
                        ).as_posix(),
                        "canonical_path": (Path("archives") / archive_name).as_posix(),
                        "canonical_size": archive_size,
                        "canonical_sha256": archive_sha256,
                    },
                )
                retained_bytes = sum(
                    item.stat().st_size for item in archive_path_obj.parent.iterdir() if item.is_file()
                )
                retention_reservation.commit(retained_bytes)
                retention_lease.release()
        runtime.publish_status(status_channel, f"Archive ready: {archive_name}")
        runtime.publish_status(status_channel, f"rq:{job_id} COMPLETED {func_name}({runid})")
        runtime.publish_status(status_channel, f"rq:{job_id} TRIGGER   archive ARCHIVE_COMPLETE")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:234", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        runtime.publish_status(status_channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")
        runtime.publish_status(status_channel, f"rq:{job_id} TRIGGER   archive ARCHIVE_FAILED")
        raise
    finally:
        if archive_path_tmp and os.path.exists(archive_path_tmp):
            try:
                os.remove(archive_path_tmp)
            except OSError:
                pass

        if retention_reservation is not None and (archive_path is None or not os.path.exists(archive_path)):
            retention_reservation.release_prewrite()
        if retention_lease is not None:
            try:
                retention_lease.release()
            except ValueError:
                logging.getLogger(__name__).warning("Private archive retention lock release deferred", exc_info=True)

        _clear_archive_job_id(runtime, prep, runid)


def _clear_restore_query_engine(path: Path) -> None:
    """Remove incoming-replaced metadata without unlinking held lifecycle fences."""
    for entry in sorted(path.iterdir()):
        if entry.name == 'refresh' and entry.is_dir() and not entry.is_symlink():
            for child in sorted(entry.iterdir()):
                if child.name in {'incarnation.json', 'publication.lock', 'redisprep.lock'}:
                    continue
                if child.is_dir() and not child.is_symlink():
                    _remove_restore_directory(child)
                else:
                    _remove_restore_file(child)
        elif entry.is_dir() and not entry.is_symlink():
            _remove_restore_directory(entry)
        else:
            _remove_restore_file(entry)


def restore_archive_rq(runid: str, archive_name: str, *, runtime: ArchiveRuntime) -> None:
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "restore_archive_rq"
    status_channel = f"{runid}:archive"
    runtime.publish_status(status_channel, f"rq:{job_id} STARTED {func_name}({runid}, {archive_name})")

    prep = None
    restore_started = False
    restore_completed = False
    retention_lease = None
    rebuild_obligation = None
    try:
        prep = runtime.get_prep_from_runid(runid)
        notification_wd = runtime.get_wd(runid)
        wd = Path(notification_wd).resolve()
        retention_lease = RedisScopeLeaseFactory()(f"run:{runid}")
        retention_lease.assert_owned()

        archives_dir = wd / "archives"
        archive_path = (archives_dir / archive_name).resolve()

        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found: {archive_name}")

        # Ensure the archive resides inside the archives directory.
        if archives_dir not in archive_path.parents:
            raise ValueError("Invalid archive path")
        _verify_private_archive(archive_path, wd)

        runtime.publish_status(status_channel, f"Preparing to restore from {archive_name}")

        authority_wd = runtime.project_config_authority_wd(runid)
        with catalog_lifecycle_guard(wd), runtime.project_config_lifecycle_guard(authority_wd), runtime.zip_file_cls(archive_path, mode="r") as zf:
            failed_member = zf.testzip()
            if failed_member:
                raise zipfile.BadZipFile(
                    f"Archive integrity check failed for member: {failed_member}"
                )

            restore_members, restore_bytes, restore_file_count = _collect_restore_members(zf, wd)
            retention_lease.assert_owned()
            from wepppy.declarative.archive import validate_restore
            preserve_declarative = validate_restore(wd, zf, restore_members)
            directory_modes = _restore_directory_modes(restore_members, wd)
            if preserve_declarative:
                directory_modes = {path: mode for path, mode in directory_modes.items()
                                   if path.relative_to(wd).parts[0] != "provenance"}
            reclaimable_bytes, _ = _calculate_run_payload_bytes(wd)
            required_bytes = _estimate_archive_required_bytes(restore_bytes, restore_file_count)
            _assert_sufficient_disk_space(
                wd,
                required_bytes=required_bytes,
                reclaimable_bytes=reclaimable_bytes,
                purpose=f"restore archive {archive_name}",
                disk_usage=runtime.disk_usage,
            )

            locked = [
                name
                for name, state in runtime.lock_statuses(runid).items()
                if name.endswith(".nodb") and state
            ]
            if locked:
                raise RuntimeError(
                    "Cannot restore while NoDb files are locked: "
                    + ", ".join(locked)
                )

            # Validate every incoming recovery snapshot before deleting project data.
            from wepppy.nodb._redis_prep_snapshot import validate_snapshot, publish_snapshot
            from wepppy.nodb.redis_prep import RedisPrep
            import json
            snapshots = {}
            for member, target_path, _ in restore_members:
                if not member.is_dir() and target_path.name == 'redisprep.dump':
                    snapshots[target_path.parent] = validate_snapshot(json.loads(zf.read(member)))

            roads_guard = roads_lifecycle.restore_operation(wd)
            with roads_guard:
                filesystem_root = None
                if os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip():
                    filesystem_root = Path(os.environ["VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT"]).resolve(strict=True)
                    rebuild_obligation = begin_retention_rebuild_obligation(
                        filesystem_root,
                        operation="private_archive_restore",
                        target=wd.relative_to(filesystem_root).as_posix(),
                    )
                # Commit the replacement fence BEFORE destruction; a killed
                # restorer must not later masquerade as first initialization.
                invalidate_catalog_incarnation(wd)
                restore_started = True
                try:
                    for entry in sorted(wd.iterdir()):
                        retention_lease.assert_owned()
                        if preserve_declarative and entry.name in {"provenance", "READONLY"}:
                            continue
                        if entry.name in {"archives", ".config-amendment.lock", "roads.lifecycle.lock", "redisprep.dump"}:
                            continue

                        try:
                            if entry.name == '_query_engine' and entry.is_dir() and not entry.is_symlink():
                                _clear_restore_query_engine(entry)
                                continue
                            if entry.is_dir() and not entry.is_symlink():
                                runtime.publish_status(status_channel, f"Removing directory {entry.relative_to(wd)}")
                                _remove_restore_directory(entry)
                            else:
                                runtime.publish_status(status_channel, f"Removing file {entry.relative_to(wd)}")
                                _remove_restore_file(entry)
                        except FileNotFoundError:
                            continue

                    # ZIP ordering cannot expose a private payload before its ancestry
                    # is restricted. Owner access is temporary for readonly directories.
                    for directory, mode in sorted(directory_modes.items(), key=lambda item: len(item[0].parts)):
                        retention_lease.assert_owned()
                        directory.mkdir(mode=mode | 0o700, parents=True, exist_ok=True)
                        os.chmod(directory, mode | 0o700)

                    for member, target_path, relative_target in restore_members:
                        retention_lease.assert_owned()
                        if preserve_declarative and relative_target.parts[0] in {"provenance", "READONLY"}:
                            continue
                        if member.is_dir():
                            target_path.mkdir(parents=True, exist_ok=True)
                            runtime.publish_status(status_channel, f"Restored directory {relative_target}")
                            continue

                        if relative_target.as_posix() in {
                            '_query_engine/refresh/incarnation.json',
                            '_query_engine/refresh/publication.lock',
                            '_query_engine/refresh/redisprep.lock',
                        }:
                            continue
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        if target_path.name == 'redisprep.dump':
                            directory_fd = os.open(target_path.parent, os.O_RDONLY | os.O_DIRECTORY)
                            try:
                                publish_snapshot(directory_fd, snapshots[target_path.parent],
                                                 target_mode=(member.external_attr >> 16) & 0o7777
                                                 if member.external_attr >> 16 else None)
                            finally:
                                os.close(directory_fd)
                        else:
                            with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                                shutil.copyfileobj(src, dst)

                        perm = member.external_attr >> 16
                        if perm and target_path.name != 'redisprep.dump':
                            try:
                                os.chmod(target_path, perm)
                            except OSError:
                                pass

                        runtime.publish_status(status_channel, f"Restored file {relative_target}")

                finally:
                    # The pre-destructive fence survives failures and SIGKILL.
                    # Do not use the old wrapper for receipt cleanup.
                    prep = None

                # Retire copied requests and nested catalog identities as before.
                # The pre-destructive root fence remains safe if this fails.
                invalidate_catalog_incarnation(wd)

                # Incoming metadata replaces prior receipts atomically, preserving
                # independently owned live mirrors. No per-field loaded window.
                # Nested snapshots can be retained provenance or repeated scenario
                # leaf names. Only the archive's root has proven live-run authority.
                RedisPrep(str(wd)).restore_snapshot(snapshots.get(wd, {}))
                prep = runtime.get_prep_from_runid(runid)
                restore_completed = True

                for directory, mode in sorted(directory_modes.items(), key=lambda item: len(item[0].parts), reverse=True):
                    os.chmod(directory, mode)
                if preserve_declarative:
                    from wepppy.declarative.records import verify_protected
                    verify_protected(wd)

        if filesystem_root is not None:
            retention_lease.assert_owned()
            reconcile_retention(
                filesystem_root,
                apply=True,
                rebuild_ledger=True,
                stale_seconds=0,
                committed_only=True,
            )
            if rebuild_obligation is not None:
                complete_retention_rebuild_obligation(rebuild_obligation)

        from wepppy.nodb.persistence_events import notify_committed
        notify_committed(str(notification_wd), runid, "lifecycle")
        try:
            cleared_entries = runtime.clear_nodb_file_cache(runid)
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:325", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            runtime.publish_status(status_channel, safe_text(f"Failed to clear NoDb cache after restore ({exc})", source_profile=current_profile(WORKER)))
            raise
        runtime.publish_status(
            status_channel,
            f"Cleared NoDb cache entries after restore ({len(cleared_entries)})",
        )

        runtime.publish_status(status_channel, f"Restore complete: {archive_name}")
        runtime.publish_status(status_channel, f"rq:{job_id} COMPLETED {func_name}({runid})")
        runtime.publish_status(status_channel, f"rq:{job_id} TRIGGER   archive RESTORE_COMPLETE")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:336", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        runtime.publish_status(status_channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")
        runtime.publish_status(status_channel, f"rq:{job_id} TRIGGER   archive RESTORE_FAILED")
        raise
    finally:
        if retention_lease is not None:
            try:
                retention_lease.release()
            except ValueError:
                logging.getLogger(__name__).warning(
                    "Restore vector retention lock release deferred", exc_info=True,
                )
        if not restore_started or restore_completed:
            _clear_archive_job_id(runtime, prep, runid)
        else:
            # Old live metadata is not reconciled with committed incoming bytes.
            # Receipt cleanup must not publish that old hash over recovery evidence.
            logging.getLogger(__name__).warning(
                'Restore failed after replacement began; retaining RedisPrep snapshot and receipt for reconciliation',
                extra={'runid': runid},
            )
