"""Request-scoped scratch cleanup and stale-directory janitor helpers."""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

_REQUEST_SCOPE_PREFIXES = frozenset({"inspect", "convert"})
_REQUEST_DIR_PATTERN = re.compile(r"^(inspect|convert)-[a-f0-9]{8}-[a-z0-9]+$")


@dataclass(frozen=True, slots=True)
class RequestScratchLayout:
    """Standard request-scoped scratch layout."""

    request_dir: Path
    upload_archive_path: Path
    extraction_root: Path
    output_root: Path


@dataclass(frozen=True, slots=True)
class JanitorSweepResult:
    """Summary of a stale request-directory janitor sweep."""

    scanned: int
    removed: int
    skipped_non_owned: int
    skipped_active: int
    skipped_fresh: int
    failed: int


class ActiveRequestScratchRegistry:
    """Thread-safe in-memory registry of active request scratch directories."""

    def __init__(self) -> None:
        self._active_dirs: set[Path] = set()
        self._lock = threading.Lock()

    def register(self, request_dir: Path) -> None:
        with self._lock:
            self._active_dirs.add(request_dir)

    def unregister(self, request_dir: Path) -> None:
        with self._lock:
            self._active_dirs.discard(request_dir)

    def snapshot(self) -> frozenset[Path]:
        with self._lock:
            return frozenset(self._active_dirs)


def build_request_scratch_layout(*, request_dir: Path) -> RequestScratchLayout:
    return RequestScratchLayout(
        request_dir=request_dir,
        upload_archive_path=request_dir / "upload.zip",
        extraction_root=request_dir / "extract",
        output_root=request_dir / "output",
    )


def create_request_scratch_dir(
    *,
    scratch_root: Path,
    request_id: str,
    request_scope: str,
    registry: ActiveRequestScratchRegistry,
    logger: logging.Logger,
) -> RequestScratchLayout:
    if request_scope not in _REQUEST_SCOPE_PREFIXES:
        raise ValueError(
            f"request_scope={request_scope!r} is invalid; expected one of {sorted(_REQUEST_SCOPE_PREFIXES)}."
        )

    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch_root_resolved = scratch_root.resolve()
    request_dir = Path(
        tempfile.mkdtemp(
            dir=scratch_root_resolved,
            prefix=f"{request_scope}-{request_id[:8]}-",
        )
    ).resolve()

    registry.register(request_dir)
    _log_structured_event(
        logger=logger,
        level=logging.INFO,
        event="request_scratch_created",
        request_id=request_id,
        request_scope=request_scope,
        request_dir_name=request_dir.name,
    )
    return build_request_scratch_layout(request_dir=request_dir)


def cleanup_request_scratch_dir(
    *,
    layout: RequestScratchLayout,
    request_id: str,
    request_scope: str,
    cleanup_reason: str,
    registry: ActiveRequestScratchRegistry,
    logger: logging.Logger,
) -> bool:
    request_dir = layout.request_dir
    removed = False
    failed = False
    failure_reason = ""
    start = time.monotonic()
    try:
        shutil.rmtree(request_dir)
        removed = True
    except FileNotFoundError:
        removed = False
    except OSError as exc:
        failed = True
        failure_reason = str(exc)
        _log_structured_event(
            logger=logger,
            level=logging.WARNING,
            event="request_scratch_cleanup_failed",
            request_id=request_id,
            request_scope=request_scope,
            request_dir_name=request_dir.name,
            cleanup_reason=cleanup_reason,
            failure=failure_reason,
        )
    finally:
        registry.unregister(request_dir)

    duration_ms = round((time.monotonic() - start) * 1000, 3)
    if not failed:
        _log_structured_event(
            logger=logger,
            level=logging.INFO,
            event="request_scratch_cleaned",
            request_id=request_id,
            request_scope=request_scope,
            request_dir_name=request_dir.name,
            cleanup_reason=cleanup_reason,
            removed=removed,
            duration_ms=duration_ms,
        )
    return not failed


def sweep_stale_request_dirs(
    *,
    scratch_root: Path,
    stale_after_seconds: int,
    registry: ActiveRequestScratchRegistry,
    logger: logging.Logger,
    now_epoch_seconds: float | None = None,
) -> JanitorSweepResult:
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch_root_resolved = scratch_root.resolve()
    now = time.time() if now_epoch_seconds is None else now_epoch_seconds
    active_dirs = registry.snapshot()

    scanned = 0
    removed = 0
    skipped_non_owned = 0
    skipped_active = 0
    skipped_fresh = 0
    failed = 0

    for candidate in scratch_root_resolved.iterdir():
        if not candidate.is_dir() or candidate.is_symlink():
            continue

        candidate_name = candidate.name
        if not _REQUEST_DIR_PATTERN.fullmatch(candidate_name):
            skipped_non_owned += 1
            continue

        try:
            candidate_resolved = candidate.resolve()
        except OSError as exc:
            failed += 1
            _log_structured_event(
                logger=logger,
                level=logging.WARNING,
                event="request_scratch_janitor_stat_failed",
                request_dir_name=candidate_name,
                failure=str(exc),
            )
            continue

        if candidate_resolved.parent != scratch_root_resolved:
            skipped_non_owned += 1
            continue

        scanned += 1
        if candidate_resolved in active_dirs:
            skipped_active += 1
            continue

        try:
            age_seconds = max(0.0, now - candidate_resolved.stat().st_mtime)
        except OSError as exc:
            failed += 1
            _log_structured_event(
                logger=logger,
                level=logging.WARNING,
                event="request_scratch_janitor_age_failed",
                request_dir_name=candidate_name,
                failure=str(exc),
            )
            continue

        if age_seconds < stale_after_seconds:
            skipped_fresh += 1
            continue

        try:
            shutil.rmtree(candidate_resolved)
            removed += 1
            _log_structured_event(
                logger=logger,
                level=logging.INFO,
                event="request_scratch_janitor_removed",
                request_dir_name=candidate_name,
                age_seconds=round(age_seconds, 3),
            )
        except OSError as exc:
            failed += 1
            _log_structured_event(
                logger=logger,
                level=logging.WARNING,
                event="request_scratch_janitor_remove_failed",
                request_dir_name=candidate_name,
                age_seconds=round(age_seconds, 3),
                failure=str(exc),
            )

    return JanitorSweepResult(
        scanned=scanned,
        removed=removed,
        skipped_non_owned=skipped_non_owned,
        skipped_active=skipped_active,
        skipped_fresh=skipped_fresh,
        failed=failed,
    )


def _log_structured_event(
    *,
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: object,
) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":")))


__all__ = [
    "ActiveRequestScratchRegistry",
    "JanitorSweepResult",
    "RequestScratchLayout",
    "build_request_scratch_layout",
    "cleanup_request_scratch_dir",
    "create_request_scratch_dir",
    "sweep_stale_request_dirs",
]
