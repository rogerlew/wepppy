"""Shared NoDir root-mutation orchestration helpers."""

from __future__ import annotations

import json
import os
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep
from typing import Callable, Iterable, TypeVar

from .errors import NoDirError
from .fs import resolve
from .paths import NODIR_ROOTS, NoDirRoot
from .projections import (
    ProjectionHandle,
    abort_mutation_projection,
    acquire_root_projection,
    commit_mutation_projection,
    release_root_projection,
)
from .thaw_freeze import NoDirMaintenanceLock, freeze_locked, maintenance_lock

__all__ = [
    "default_archive_roots_path",
    "enable_default_archive_roots",
    "read_default_archive_roots",
    "preflight_root_forms",
    "mutate_root",
    "mutate_roots",
]


T = TypeVar("T")
_DEFAULT_ARCHIVE_ROOTS_FILENAME = ".nodir/default_archive_roots.json"
_DEFAULT_ARCHIVE_ROOTS_SCHEMA_VERSION = 1
_DEFAULT_ARCHIVE_ROOTS_ENV = "WEPP_NODIR_DEFAULT_NEW_RUNS"
_MIN_LOCK_RETRY_INTERVAL_SECONDS = 0.01


def default_archive_roots_path(wd: str | Path) -> Path:
    return Path(os.path.abspath(str(wd))) / _DEFAULT_ARCHIVE_ROOTS_FILENAME


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported NoDir root: {root}")
    return root


def _normalize_roots(roots: Iterable[str]) -> tuple[NoDirRoot, ...]:
    normalized = tuple(sorted({_normalize_root(root) for root in roots}))
    if not normalized:
        raise ValueError("at least one NoDir root is required")
    return normalized


def _default_archiving_enabled() -> bool:
    raw = os.getenv(_DEFAULT_ARCHIVE_ROOTS_ENV)
    if raw is None:
        return True
    token = raw.strip().lower()
    if token in {"0", "false", "no", "off"}:
        return False
    if token in {"1", "true", "yes", "on"}:
        return True
    return True


def enable_default_archive_roots(
    wd: str | Path,
    *,
    roots: Iterable[str] = NODIR_ROOTS,
) -> Path | None:
    """Persist per-run default NoDir archive roots for new runs.

    Returns marker path when defaults are enabled, otherwise ``None``.
    """
    if not _default_archiving_enabled():
        return None

    wd_path = Path(os.path.abspath(str(wd)))
    normalized_roots = list(_normalize_roots(roots))
    marker_path = default_archive_roots_path(wd_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": _DEFAULT_ARCHIVE_ROOTS_SCHEMA_VERSION,
        "roots": normalized_roots,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    tmp_path = marker_path.with_name(f"{marker_path.name}.tmp.{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, marker_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return marker_path


def read_default_archive_roots(wd: str | Path) -> frozenset[NoDirRoot]:
    """Return configured per-run default archive roots.

    Raises ``ValueError`` when a marker exists but is malformed.
    """
    marker_path = default_archive_roots_path(wd)
    if not marker_path.exists():
        return frozenset()

    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid NoDir defaults marker: {marker_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"invalid NoDir defaults marker payload: {marker_path}")
    if payload.get("schema_version") != _DEFAULT_ARCHIVE_ROOTS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported NoDir defaults marker schema: {payload.get('schema_version')}"
        )

    roots_raw = payload.get("roots")
    if not isinstance(roots_raw, list):
        raise ValueError("NoDir defaults marker must contain list field 'roots'")

    normalized_roots = _normalize_roots(str(root) for root in roots_raw)
    return frozenset(normalized_roots)


def preflight_root_forms(
    wd: str | Path,
    roots: Iterable[str],
) -> dict[NoDirRoot, str]:
    """Resolve each NoDir root to `dir` or `archive` form.

    This helper enforces canonical mixed/invalid/transitional errors through
    ``resolve(view="effective")``.
    """

    wd_path = Path(os.path.abspath(str(wd)))
    forms: dict[NoDirRoot, str] = {}
    for root in _normalize_roots(roots):
        target = resolve(str(wd_path), root, view="effective")
        forms[root] = "archive" if target is not None and target.form == "archive" else "dir"
    return forms


def mutate_roots(
    wd: str | Path,
    roots: Iterable[str],
    callback: Callable[[], T],
    *,
    purpose: str = "nodir-mutation",
    lock_wait_seconds: float = 0.0,
    lock_retry_interval_seconds: float = 0.25,
) -> T:
    """Run ``callback`` with canonical NoDir lock + mutation-session orchestration.

    Behavior:
    - Mixed/invalid/transitional states fail with canonical NoDir errors.
    - NoDir maintenance locks are held around callback execution.
    - Archive roots are projected in ``mode="mutate"`` before callback and committed on success.
    - Callback failures abort active mutation projections (no implicit archive commit).
    """

    wd_path = Path(os.path.abspath(str(wd)))
    normalized_roots = _normalize_roots(roots)
    default_archive_roots = read_default_archive_roots(wd_path)
    lock_wait_budget = max(0.0, float(lock_wait_seconds))
    lock_retry_interval = max(_MIN_LOCK_RETRY_INTERVAL_SECONDS, float(lock_retry_interval_seconds))

    # Fail fast on mixed/invalid/transitional states before lock attempts.
    preflight_root_forms(wd_path, normalized_roots)

    with ExitStack() as stack:
        locks: dict[NoDirRoot, NoDirMaintenanceLock] = {}
        for root in normalized_roots:
            lock_purpose = purpose if len(normalized_roots) == 1 else f"{purpose}/{root}"
            wait_deadline = monotonic() + lock_wait_budget
            while True:
                try:
                    locks[root] = stack.enter_context(
                        maintenance_lock(wd_path, root, purpose=lock_purpose)
                    )
                    break
                except NoDirError as exc:
                    if (
                        exc.code != "NODIR_LOCKED"
                        or "currently held:" not in exc.message
                        or lock_wait_budget <= 0.0
                    ):
                        raise

                    now = monotonic()
                    if now >= wait_deadline:
                        raise
                    sleep(min(lock_retry_interval, wait_deadline - now))

        # Re-check after lock acquisition so form decisions are race-safe.
        forms = preflight_root_forms(wd_path, normalized_roots)

        mutation_sessions: list[tuple[NoDirRoot, ProjectionHandle]] = []
        freeze_after_callback: list[NoDirRoot] = []
        for root in normalized_roots:
            mutation_purpose = purpose if len(normalized_roots) == 1 else f"{purpose}/{root}"
            if forms[root] == "archive":
                handle = acquire_root_projection(
                    wd_path,
                    root,
                    mode="mutate",
                    purpose=mutation_purpose,
                )
                mutation_sessions.append((root, handle))
            elif root in default_archive_roots:
                freeze_after_callback.append(root)

        try:
            result = callback()
        except Exception:
            for _root, handle in reversed(mutation_sessions):
                try:
                    abort_mutation_projection(handle)
                except Exception:
                    # Preserve original callback failure; release still runs in finally.
                    pass
            raise
        else:
            for _root, handle in reversed(mutation_sessions):
                commit_mutation_projection(handle)

            # New-run default NoDir policy: directory-form roots configured via
            # marker are archived after successful mutation callbacks.
            for root in reversed(freeze_after_callback):
                target = resolve(str(wd_path), root, view="effective")
                if target is None or target.form == "archive":
                    continue

                # Effective view can still report dir form when the root path is
                # absent (no archive + no directory). Only auto-freeze when an
                # actual directory-form root is present.
                if resolve(str(wd_path), root, view="dir") is None:
                    continue

                freeze_locked(wd_path, root, lock=locks[root])

            return result
        finally:
            for _root, handle in reversed(mutation_sessions):
                release_root_projection(handle)


def mutate_root(
    wd: str | Path,
    root: str,
    callback: Callable[[], T],
    *,
    purpose: str = "nodir-mutation",
    lock_wait_seconds: float = 0.0,
    lock_retry_interval_seconds: float = 0.25,
) -> T:
    """Single-root wrapper around :func:`mutate_roots`."""

    return mutate_roots(
        wd,
        (root,),
        callback,
        purpose=purpose,
        lock_wait_seconds=lock_wait_seconds,
        lock_retry_interval_seconds=lock_retry_interval_seconds,
    )
