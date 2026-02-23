"""NoDir materialization helpers for FS-boundary endpoints.

This module extracts archive-backed NoDir entries into an internal cache under
``WD/.nodir/cache`` when a downstream tool requires a real filesystem path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import posixpath
import random
import shutil
import stat as statmod
import uuid
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep
from typing import Callable
from zipfile import ZipFile, ZipInfo

from .errors import NoDirError, nodir_invalid_archive, nodir_limit_exceeded, nodir_locked
from .fs import ResolvedNoDirPath, _get_zip_index, resolve
from .paths import normalize_relpath
from .state import is_transitioning_locked

__all__ = [
    "materialize_file",
    "materialize_path_if_archive",
]

_LOGGER = logging.getLogger(__name__)

_DEFAULT_MAX_FILE_BYTES = 16 * 1024**3
_DEFAULT_MAX_REQUEST_BYTES = 20 * 1024**3
_DEFAULT_MAX_REQUEST_FILES = 32
_DEFAULT_LOCK_TTL_SECONDS = 300
_DEFAULT_LOCK_WAIT_SECONDS = 1.0
_DEFAULT_RATIO_MIN_BYTES = 64 * 1024**2
_DEFAULT_RATIO_MAX = 200.0
_LOCK_RENEWAL_INTERVAL_SECONDS = 30.0

_SHP_REQUIRED_SIDECARS = (".shx", ".dbf")
_SHP_OPTIONAL_SIDECARS = (
    ".prj",
    ".cpg",
    ".qix",
    ".sbn",
    ".sbx",
    ".fix",
)

# Test harnesses monkeypatch this module attribute directly.
_REDIS_LOCK_CLIENT_UNSET = object()
redis_lock_client = _REDIS_LOCK_CLIENT_UNSET


@dataclass(frozen=True, slots=True)
class _MaterializePlan:
    inner_path: str
    basename: str
    info: ZipInfo


def _env_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _env_positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _lock_ttl_seconds() -> int:
    return _env_positive_int("NODIR_MATERIALIZE_LOCK_TTL_SECONDS", _DEFAULT_LOCK_TTL_SECONDS)


def _lock_wait_seconds() -> float:
    return _env_positive_float("NODIR_MATERIALIZE_LOCK_WAIT_SECONDS", _DEFAULT_LOCK_WAIT_SECONDS)


def _max_file_bytes() -> int:
    return _env_positive_int("NODIR_MATERIALIZE_MAX_FILE_BYTES", _DEFAULT_MAX_FILE_BYTES)


def _max_request_bytes() -> int:
    return _env_positive_int("NODIR_MATERIALIZE_MAX_REQUEST_BYTES", _DEFAULT_MAX_REQUEST_BYTES)


def _max_request_files() -> int:
    return _env_positive_int("NODIR_MATERIALIZE_MAX_REQUEST_FILES", _DEFAULT_MAX_REQUEST_FILES)


def _ratio_min_bytes() -> int:
    return _env_positive_int("NODIR_MATERIALIZE_RATIO_MIN_BYTES", _DEFAULT_RATIO_MIN_BYTES)


def _ratio_max() -> float:
    return _env_positive_float("NODIR_MATERIALIZE_RATIO_MAX", _DEFAULT_RATIO_MAX)


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _runid_from_wd(wd_path: Path) -> str:
    return wd_path.name


def _entry_id(inner_path: str) -> str:
    return hashlib.sha256(inner_path.encode("utf-8")).hexdigest()[:32]


def _archive_fp_string(archive_fp: tuple[int, int] | None) -> str:
    if archive_fp is None:
        raise nodir_invalid_archive("archive fingerprint unavailable")
    return f"{int(archive_fp[0])}-{int(archive_fp[1])}"


def _entry_fingerprint(info: ZipInfo) -> dict[str, int | str]:
    return {
        "crc32": int(info.CRC),
        "file_size": int(info.file_size),
        "compress_size": int(info.compress_size),
        "method": int(info.compress_type),
    }


def _build_meta(target: ResolvedNoDirPath, plans: list[_MaterializePlan], *, purpose: str) -> dict:
    assert target.archive_fp is not None
    files: list[dict] = []
    for plan in plans:
        files.append(
            {
                "inner_path": plan.inner_path,
                "basename": plan.basename,
                "zip": _entry_fingerprint(plan.info),
                "extracted": {"size_bytes": int(plan.info.file_size)},
            }
        )

    return {
        "schema_version": 1,
        "root": target.root,
        "inner_path": target.inner_path,
        "purpose": purpose,
        "archive_fingerprint": {
            "mtime_ns": int(target.archive_fp[0]),
            "size_bytes": int(target.archive_fp[1]),
        },
        "updated_at": _now_iso_utc(),
        "files": files,
    }


def _load_meta(meta_path: Path) -> dict | None:
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _meta_archive_matches(meta: dict, target: ResolvedNoDirPath) -> bool:
    if target.archive_fp is None:
        return False
    archive_fp = meta.get("archive_fingerprint")
    if not isinstance(archive_fp, dict):
        return False
    return (
        int(archive_fp.get("mtime_ns", -1)) == int(target.archive_fp[0])
        and int(archive_fp.get("size_bytes", -1)) == int(target.archive_fp[1])
    )


def _cache_hit(entry_dir: Path, target: ResolvedNoDirPath, plans: list[_MaterializePlan]) -> bool:
    meta_path = entry_dir / "meta.json"
    meta = _load_meta(meta_path)
    if meta is None:
        return False

    if int(meta.get("schema_version", 0)) != 1:
        return False
    if meta.get("inner_path") != target.inner_path:
        return False
    if not _meta_archive_matches(meta, target):
        return False

    files_meta = meta.get("files")
    if not isinstance(files_meta, list):
        return False
    if len(files_meta) != len(plans):
        return False

    by_inner: dict[str, dict] = {}
    for item in files_meta:
        if not isinstance(item, dict):
            return False
        inner_path = item.get("inner_path")
        if not isinstance(inner_path, str):
            return False
        by_inner[inner_path] = item

    for plan in plans:
        item = by_inner.get(plan.inner_path)
        if item is None:
            return False

        if item.get("basename") != plan.basename:
            return False

        item_zip = item.get("zip")
        if not isinstance(item_zip, dict):
            return False
        expected_zip = _entry_fingerprint(plan.info)
        for key, value in expected_zip.items():
            if int(item_zip.get(key, -1)) != int(value):
                return False

        extracted = item.get("extracted")
        if not isinstance(extracted, dict):
            return False
        expected_size = int(extracted.get("size_bytes", -1))
        file_path = entry_dir / plan.basename
        try:
            st = file_path.stat()
        except FileNotFoundError:
            return False
        except OSError:
            return False
        if not statmod.S_ISREG(st.st_mode):
            return False
        if int(st.st_size) != expected_size:
            return False

    return True


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return
    except OSError:
        return


def _path_in_cache(wd_path: Path, materialized_path: Path) -> str:
    try:
        rel = materialized_path.relative_to(wd_path)
    except ValueError as exc:
        raise nodir_invalid_archive("materialized path escaped run root") from exc
    rel_posix = rel.as_posix()
    if rel_posix.startswith("../") or rel_posix == "..":
        raise nodir_invalid_archive("materialized path escaped run root")
    return rel_posix


def _extract_file(
    zf: ZipFile,
    info: ZipInfo,
    dst_path: Path,
    *,
    max_file_bytes: int,
    max_request_bytes: int,
    running_total: int,
    renew_lock: Callable[[], None] | None = None,
) -> int:
    if int(info.file_size) > max_file_bytes:
        raise nodir_limit_exceeded(
            f"archive entry exceeds per-file materialization limit ({int(info.file_size)} > {max_file_bytes})"
        )

    temp_name = f"{dst_path.name}.tmp.{os.getpid()}.{random.randint(0, 1_000_000)}"
    temp_path = dst_path.with_name(temp_name)

    bytes_written = 0
    crc32_value = 0
    next_renewal = monotonic() + _LOCK_RENEWAL_INTERVAL_SECONDS
    try:
        with zf.open(info, "r") as src, temp_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                bytes_written += len(chunk)
                running_total += len(chunk)
                crc32_value = zlib.crc32(chunk, crc32_value)

                if bytes_written > max_file_bytes:
                    raise nodir_limit_exceeded(
                        f"archive entry exceeds per-file materialization limit ({bytes_written} > {max_file_bytes})"
                    )
                if running_total > max_request_bytes:
                    raise nodir_limit_exceeded(
                        f"materialization request exceeded total byte limit ({running_total} > {max_request_bytes})"
                    )

                if renew_lock is not None and monotonic() >= next_renewal:
                    renew_lock()
                    next_renewal = monotonic() + _LOCK_RENEWAL_INTERVAL_SECONDS

        if bytes_written != int(info.file_size):
            raise nodir_invalid_archive(
                f"zip entry size mismatch for {info.filename} ({bytes_written} != {int(info.file_size)})"
            )

        if int(crc32_value & 0xFFFFFFFF) != int(info.CRC):
            raise nodir_invalid_archive(f"zip entry CRC mismatch for {info.filename}")

        os.replace(temp_path, dst_path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    return bytes_written


def _enforce_plan_limits(plans: list[_MaterializePlan]) -> None:
    max_files = _max_request_files()
    max_file = _max_file_bytes()
    max_total = _max_request_bytes()
    ratio_min = _ratio_min_bytes()
    ratio_max = _ratio_max()

    if len(plans) > max_files:
        raise nodir_limit_exceeded(
            f"materialization request exceeded file limit ({len(plans)} > {max_files})"
        )

    total_bytes = 0
    for plan in plans:
        size = int(plan.info.file_size)
        comp_size = int(plan.info.compress_size)
        total_bytes += size

        if size > max_file:
            raise nodir_limit_exceeded(
                f"archive entry exceeds per-file materialization limit ({size} > {max_file})"
            )

        if size >= ratio_min and comp_size > 0 and (size / comp_size) > ratio_max:
            raise nodir_limit_exceeded(
                "archive entry compression ratio exceeds materialization safety limit"
            )

    if total_bytes > max_total:
        raise nodir_limit_exceeded(
            f"materialization request exceeded total byte limit ({total_bytes} > {max_total})"
        )



def _redis_value_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _redis_lock_client():
    override = globals().get("redis_lock_client", _REDIS_LOCK_CLIENT_UNSET)
    if override is not _REDIS_LOCK_CLIENT_UNSET:
        return override

    # Delay import to avoid query-engine bootstrap cycles during module import.
    from wepppy.nodb.base import redis_lock_client

    return redis_lock_client


def _acquire_materialize_lock(lock_key: str, *, purpose: str) -> str:
    redis_client = _redis_lock_client()
    if redis_client is None:
        raise nodir_locked("materialization lock backend unavailable")

    ttl_seconds = _lock_ttl_seconds()
    token = uuid.uuid4().hex
    payload = {
        "token": token,
        "owner": f"{os.uname().nodename}:{os.getpid()}",
        "purpose": purpose,
        "acquired_at": int(datetime.now(timezone.utc).timestamp()),
        "ttl": ttl_seconds,
    }
    lock_value = json.dumps(payload, separators=(",", ":"))

    try:
        acquired = redis_client.set(
            lock_key,
            lock_value,
            nx=True,
            ex=ttl_seconds,
        )
    except Exception as exc:
        raise nodir_locked("failed to acquire materialization lock") from exc

    if not acquired:
        raise nodir_locked("materialization lock is currently held")

    return lock_value


def _release_materialize_lock(lock_key: str, lock_value: str) -> None:
    redis_client = _redis_lock_client()
    if redis_client is None:
        return

    release_lua = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) "
        "else return 0 end"
    )

    try:
        if hasattr(redis_client, "eval"):
            redis_client.eval(release_lua, 1, lock_key, lock_value)
            return
    except Exception:
        pass

    try:
        stored = redis_client.get(lock_key)
    except Exception:
        return

    if _redis_value_text(stored) != lock_value:
        return

    try:
        redis_client.delete(lock_key)
    except Exception:
        pass


def _renew_materialize_lock(lock_key: str, lock_value: str) -> None:
    redis_client = _redis_lock_client()
    if redis_client is None:
        raise nodir_locked("materialization lock backend unavailable")

    ttl_seconds = _lock_ttl_seconds()
    renew_lua = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('expire', KEYS[1], ARGV[2]) "
        "else return 0 end"
    )

    if hasattr(redis_client, "eval"):
        try:
            renewed = redis_client.eval(renew_lua, 1, lock_key, lock_value, ttl_seconds)
        except Exception as exc:
            raise nodir_locked("failed to renew materialization lock") from exc

        if int(renewed or 0) != 1:
            raise nodir_locked("materialization lock ownership lost during extraction")
        return

    raise nodir_locked("materialization lock backend cannot renew atomically")


def _collect_materialize_plans(target: ResolvedNoDirPath) -> list[_MaterializePlan]:
    if target.form != "archive":
        raise nodir_invalid_archive("materialization target must be archive-backed")

    _, index = _get_zip_index(target)
    inner = target.inner_path.strip("/")
    if not inner:
        raise IsADirectoryError(target.root)

    primary_info = index.files.get(inner)
    if primary_info is None:
        if inner in index.dirs or any(name.startswith(f"{inner}/") for name in index.files):
            raise IsADirectoryError(inner)
        raise FileNotFoundError(inner)

    basename = posixpath.basename(inner)
    if not basename or "/" in basename or "\\" in basename:
        raise nodir_invalid_archive("invalid archive entry basename")

    plans: list[_MaterializePlan] = [
        _MaterializePlan(inner_path=inner, basename=basename, info=primary_info)
    ]

    parent = posixpath.dirname(inner)

    def _join_parent(name: str) -> str:
        if parent:
            return f"{parent}/{name}"
        return name

    seen = {inner}
    files_by_casefold = {name.casefold(): name for name in index.files}

    def _append_sidecar(name: str, *, required: bool = False) -> None:
        if name in seen:
            return

        resolved_name = name
        info = index.files.get(name)
        if info is None:
            casefold_match = files_by_casefold.get(name.casefold())
            if casefold_match is not None:
                resolved_name = casefold_match
                info = index.files.get(casefold_match)

        if info is None:
            if required:
                raise nodir_invalid_archive(f"missing required sidecar entry: {name}")
            return

        base = posixpath.basename(resolved_name)
        if not base or "/" in base or "\\" in base:
            raise nodir_invalid_archive("invalid archive sidecar basename")

        plans.append(_MaterializePlan(inner_path=resolved_name, basename=base, info=info))
        seen.add(name)
        seen.add(resolved_name)

    stem, ext = posixpath.splitext(basename)
    ext_lower = ext.lower()
    if ext_lower == ".shp":
        for suffix in _SHP_REQUIRED_SIDECARS:
            _append_sidecar(_join_parent(f"{stem}{suffix}"), required=True)

        for suffix in _SHP_OPTIONAL_SIDECARS:
            _append_sidecar(_join_parent(f"{stem}{suffix}"), required=False)

        _append_sidecar(_join_parent(f"{basename}.xml"), required=False)
    elif ext_lower in {".tif", ".tiff"}:
        candidates = (
            f"{basename}.ovr",
            f"{basename}.aux.xml",
            f"{stem}.aux.xml",
            f"{stem}.tfw",
            f"{stem}.tif.aux.xml",
        )
        for candidate in candidates:
            _append_sidecar(_join_parent(candidate), required=False)

    return plans


def _extract_plans_to_cache(
    *,
    archive_path: Path,
    entry_dir: Path,
    plans: list[_MaterializePlan],
    meta_payload: dict,
    lock_key: str | None = None,
    lock_value: str | None = None,
) -> None:
    max_file = _max_file_bytes()
    max_request = _max_request_bytes()

    stage_dir = entry_dir.parent / f".tmp.{entry_dir.name}.{uuid.uuid4().hex}"
    stage_dir.mkdir(parents=True, exist_ok=False)

    running_total = 0
    renew_lock: Callable[[], None] | None = None
    if lock_key is not None and lock_value is not None:
        def _renew_lock() -> None:
            _renew_materialize_lock(lock_key, lock_value)

        renew_lock = _renew_lock

    try:
        with ZipFile(archive_path, "r") as zf:
            for plan in plans:
                try:
                    live_info = zf.getinfo(plan.inner_path)
                except KeyError as exc:
                    raise nodir_invalid_archive(
                        f"archive entry disappeared during materialization: {plan.inner_path}"
                    ) from exc

                if _entry_fingerprint(live_info) != _entry_fingerprint(plan.info):
                    raise nodir_locked("archive changed during materialization")

                final_path = stage_dir / plan.basename
                extracted = _extract_file(
                    zf,
                    live_info,
                    final_path,
                    max_file_bytes=max_file,
                    max_request_bytes=max_request,
                    running_total=running_total,
                    renew_lock=renew_lock,
                )
                running_total += extracted

        meta_tmp = stage_dir / f"meta.json.tmp.{os.getpid()}.{uuid.uuid4().hex}"
        meta_final = stage_dir / "meta.json"
        meta_tmp.write_text(json.dumps(meta_payload, separators=(",", ":")), encoding="utf-8")
        os.replace(meta_tmp, meta_final)

        _remove_tree(entry_dir)
        os.replace(stage_dir, entry_dir)
    except Exception:
        _remove_tree(stage_dir)
        raise


def _prune_cache_versions(root_cache_dir: Path, *, keep_count: int = 2) -> None:
    try:
        entries = [item for item in root_cache_dir.iterdir() if item.is_dir() and not item.name.startswith(".")]
    except FileNotFoundError:
        return
    except OSError:
        return

    if len(entries) <= keep_count:
        return

    def _sort_key(path: Path) -> tuple[int, int]:
        name = path.name
        mtime_part, _, size_part = name.partition("-")
        try:
            return (int(mtime_part), int(size_part))
        except ValueError:
            try:
                st = path.stat()
                mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
                return (mtime_ns, int(st.st_size))
            except OSError:
                return (0, 0)

    entries.sort(key=_sort_key, reverse=True)
    for stale in entries[keep_count:]:
        _remove_tree(stale)


def materialize_file(wd: str, rel: str, *, purpose: str = "materialize") -> str:
    """Return a real filesystem path for ``rel``.

    For directory-backed NoDir roots this returns the native path. For
    archive-backed roots this extracts the requested entry (plus sidecars) into
    ``WD/.nodir/cache`` and returns the cached path.
    """

    wd_path = Path(os.path.abspath(wd))
    logical_rel = normalize_relpath(rel)

    target = resolve(str(wd_path), logical_rel, view="effective")
    if target is None:
        candidate = (wd_path / logical_rel).resolve(strict=False)
        return str(candidate)

    if target.form == "dir":
        candidate = Path(target.dir_path)
        if target.inner_path:
            candidate = candidate / target.inner_path
        return str(candidate)

    if is_transitioning_locked(wd_path, target.root):
        raise nodir_locked(f"{target.root} is transitioning (thaw/freeze in progress)")

    assert target.archive_fp is not None

    archive_real_path, _ = _get_zip_index(target)
    plans = _collect_materialize_plans(target)
    _enforce_plan_limits(plans)

    entry_hash = _entry_id(target.inner_path)
    archive_fp = _archive_fp_string(target.archive_fp)

    cache_root = wd_path / ".nodir" / "cache" / target.root / archive_fp
    entry_dir = cache_root / entry_hash
    primary_path = entry_dir / plans[0].basename

    runid = _runid_from_wd(wd_path)
    lock_key = f"nodb-lock:{runid}:nodir-materialize/{target.root}/{entry_hash}"

    cache_preexisting = entry_dir.exists()
    started = monotonic()
    outcome = "miss"

    try:
        if _cache_hit(entry_dir, target, plans):
            outcome = "hit"
            return str(primary_path)

        lock_deadline = monotonic() + _lock_wait_seconds()
        lock_attempt = 0
        while True:
            try:
                lock_value = _acquire_materialize_lock(lock_key, purpose=purpose)
                break
            except NoDirError as exc:
                # Contention is expected when multiple readers materialize the
                # same archive entry concurrently; wait briefly for peer fill.
                is_lock_contention = (
                    exc.code == "NODIR_LOCKED"
                    and exc.message == "materialization lock is currently held"
                )
                if not is_lock_contention:
                    raise
                if _cache_hit(entry_dir, target, plans):
                    outcome = "hit"
                    return str(primary_path)
                if monotonic() >= lock_deadline:
                    raise
                lock_attempt += 1
                backoff_seconds = min(0.05 * lock_attempt, 0.5)
                sleep(backoff_seconds)

        try:
            if _cache_hit(entry_dir, target, plans):
                outcome = "hit"
                return str(primary_path)

            _remove_tree(entry_dir)
            outcome = "rebuild" if cache_preexisting else "miss"
            cache_root.mkdir(parents=True, exist_ok=True)
            meta_payload = _build_meta(target, plans, purpose=purpose)
            _extract_plans_to_cache(
                archive_path=archive_real_path,
                entry_dir=entry_dir,
                plans=plans,
                meta_payload=meta_payload,
                lock_key=lock_key,
                lock_value=lock_value,
            )
        finally:
            _release_materialize_lock(lock_key, lock_value)

        _prune_cache_versions((wd_path / ".nodir" / "cache" / target.root), keep_count=2)
        return str(primary_path)
    finally:
        duration_s = monotonic() - started
        try:
            total_uncompressed = sum(int(plan.info.file_size) for plan in plans)
            total_compressed = sum(int(plan.info.compress_size) for plan in plans)
            method = int(plans[0].info.compress_type)
        except Exception:
            total_uncompressed = -1
            total_compressed = -1
            method = -1

        _LOGGER.info(
            "nodir materialize runid=%s root=%s inner_path=%s outcome=%s "
            "archive_mtime_ns=%s archive_size_bytes=%s method=%s compressed=%s uncompressed=%s wall_s=%.3f",
            runid,
            target.root,
            target.inner_path,
            outcome,
            int(target.archive_fp[0]),
            int(target.archive_fp[1]),
            method,
            total_compressed,
            total_uncompressed,
            duration_s,
        )


def materialize_path_if_archive(wd: str, path: str | Path, *, purpose: str = "export") -> str:
    """Materialize ``path`` only when it maps to an archive-backed NoDir root."""

    wd_path = Path(os.path.abspath(wd))
    abs_path = Path(os.path.abspath(str(path)))

    try:
        logical_rel = abs_path.relative_to(wd_path).as_posix()
    except ValueError:
        return str(abs_path)

    target = resolve(str(wd_path), logical_rel, view="effective")
    if target is None:
        return str(abs_path)
    if target.form == "dir":
        return str(abs_path)

    materialized = Path(materialize_file(str(wd_path), logical_rel, purpose=purpose))
    _path_in_cache(wd_path, materialized)
    return str(materialized)
