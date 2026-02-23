from __future__ import annotations

import errno
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_ARCHIVE_DISK_HEADROOM_RATIO = 0.02
_ARCHIVE_MIN_HEADROOM_BYTES = 64 * 1024 * 1024
_ARCHIVE_PER_FILE_OVERHEAD_BYTES = 1024
_ARCHIVE_EXCLUDE_PREFIXES: tuple[str, ...] = ("archives", ".nodir/cache")


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


def archive_rq(runid: str, comment: str | None, *, runtime: ArchiveRuntime) -> None:
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "archive_rq"
    status_channel = f"{runid}:archive"
    runtime.publish_status(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    prep = None
    archive_path_tmp: str | None = None
    try:
        prep = runtime.get_prep_from_runid(runid)
        wd = runtime.get_wd(runid)
        wd_path = Path(wd)

        locked = [name for name, state in runtime.lock_statuses(runid).items() if name.endswith(".nodb") and state]
        if locked:
            raise RuntimeError("Cannot archive while files are locked: " + ", ".join(locked))

        payload_bytes, payload_file_count = _calculate_run_payload_bytes(wd_path)
        required_bytes = _estimate_archive_required_bytes(payload_bytes, payload_file_count)
        _assert_sufficient_disk_space(
            wd_path,
            required_bytes=required_bytes,
            purpose=f"create archive for {runid}",
            disk_usage=runtime.disk_usage,
        )

        archives_dir = os.path.join(wd, "archives")
        os.makedirs(archives_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        archive_name = f"{runid}.{timestamp}.zip"
        archive_path = os.path.join(archives_dir, archive_name)
        archive_path_tmp = archive_path + ".tmp"

        for candidate in (archive_path, archive_path_tmp):
            if os.path.exists(candidate):
                os.remove(candidate)

        runtime.publish_status(status_channel, f"Creating archive {archive_name}")

        comment_bytes = (comment or "").encode("utf-8")

        with runtime.zip_file_cls(archive_path_tmp, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(wd):
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
                    abs_path = os.path.join(root, filename)
                    arcname = os.path.relpath(abs_path, wd)
                    if _is_archive_excluded_relpath(arcname):
                        continue

                    runtime.publish_status(status_channel, f"Adding {arcname}")
                    zf.write(abs_path, arcname)

            if comment_bytes:
                zf.comment = comment_bytes

        os.replace(archive_path_tmp, archive_path)
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

        _clear_archive_job_id(runtime, prep, runid)


def restore_archive_rq(runid: str, archive_name: str, *, runtime: ArchiveRuntime) -> None:
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "restore_archive_rq"
    status_channel = f"{runid}:archive"
    runtime.publish_status(status_channel, f"rq:{job_id} STARTED {func_name}({runid}, {archive_name})")

    prep = None
    try:
        prep = runtime.get_prep_from_runid(runid)
        wd = Path(runtime.get_wd(runid)).resolve()

        archives_dir = wd / "archives"
        archive_path = (archives_dir / archive_name).resolve()

        if not archive_path.exists() or not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found: {archive_name}")

        # Ensure the archive resides inside the archives directory.
        if archives_dir not in archive_path.parents:
            raise ValueError("Invalid archive path")

        runtime.publish_status(status_channel, f"Preparing to restore from {archive_name}")

        with runtime.zip_file_cls(archive_path, mode="r") as zf:
            failed_member = zf.testzip()
            if failed_member:
                raise zipfile.BadZipFile(
                    f"Archive integrity check failed for member: {failed_member}"
                )

            restore_members, restore_bytes, restore_file_count = _collect_restore_members(zf, wd)
            reclaimable_bytes, _ = _calculate_run_payload_bytes(wd)
            required_bytes = _estimate_archive_required_bytes(restore_bytes, restore_file_count)
            _assert_sufficient_disk_space(
                wd,
                required_bytes=required_bytes,
                reclaimable_bytes=reclaimable_bytes,
                purpose=f"restore archive {archive_name}",
                disk_usage=runtime.disk_usage,
            )

            for entry in sorted(wd.iterdir()):
                if entry.name == "archives":
                    continue

                try:
                    if entry.is_dir() and not entry.is_symlink():
                        runtime.publish_status(status_channel, f"Removing directory {entry.relative_to(wd)}")
                        shutil.rmtree(entry)
                    else:
                        runtime.publish_status(status_channel, f"Removing file {entry.relative_to(wd)}")
                        entry.unlink()
                except FileNotFoundError:
                    continue

            for member, target_path, relative_target in restore_members:
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    runtime.publish_status(status_channel, f"Restored directory {relative_target}")
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                perm = member.external_attr >> 16
                if perm:
                    try:
                        os.chmod(target_path, perm)
                    except OSError:
                        pass

                runtime.publish_status(status_channel, f"Restored file {relative_target}")

        try:
            cleared_entries = runtime.clear_nodb_file_cache(runid)
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_archive.py:325", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            runtime.publish_status(status_channel, f"Failed to clear NoDb cache after restore ({exc})")
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
        _clear_archive_job_id(runtime, prep, runid)
