"""Shared NoDir root-mutation orchestration helpers."""

from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, Iterable, TypeVar

from .fs import resolve
from .paths import NODIR_ROOTS, NoDirRoot
from .thaw_freeze import NoDirMaintenanceLock, freeze_locked, maintenance_lock, thaw_locked

__all__ = [
    "preflight_root_forms",
    "mutate_root",
    "mutate_roots",
]


T = TypeVar("T")


def _normalize_root(root: str) -> NoDirRoot:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported NoDir root: {root}")
    return root


def _normalize_roots(roots: Iterable[str]) -> tuple[NoDirRoot, ...]:
    normalized = tuple(sorted({_normalize_root(root) for root in roots}))
    if not normalized:
        raise ValueError("at least one NoDir root is required")
    return normalized


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
) -> T:
    """Run ``callback`` with canonical NoDir lock/thaw/freeze orchestration.

    Behavior:
    - Mixed/invalid/transitional states fail with canonical NoDir errors.
    - NoDir maintenance locks are held around callback execution.
    - Archive roots are thawed before callback and frozen after successful callback.
    - Callback failures after thaw preserve thawed/dirty state (no implicit freeze).
    """

    wd_path = Path(os.path.abspath(str(wd)))
    normalized_roots = _normalize_roots(roots)

    # Fail fast on mixed/invalid/transitional states before lock attempts.
    preflight_root_forms(wd_path, normalized_roots)

    with ExitStack() as stack:
        locks: dict[NoDirRoot, NoDirMaintenanceLock] = {}
        for root in normalized_roots:
            lock_purpose = purpose if len(normalized_roots) == 1 else f"{purpose}/{root}"
            locks[root] = stack.enter_context(
                maintenance_lock(wd_path, root, purpose=lock_purpose)
            )

        # Re-check after lock acquisition so form decisions are race-safe.
        forms = preflight_root_forms(wd_path, normalized_roots)

        thawed: list[NoDirRoot] = []
        for root in normalized_roots:
            if forms[root] == "archive":
                thaw_locked(wd_path, root, lock=locks[root])
                thawed.append(root)

        try:
            result = callback()
        except Exception:
            raise

        for root in reversed(thawed):
            freeze_locked(wd_path, root, lock=locks[root])

        return result


def mutate_root(
    wd: str | Path,
    root: str,
    callback: Callable[[], T],
    *,
    purpose: str = "nodir-mutation",
) -> T:
    """Single-root wrapper around :func:`mutate_roots`."""

    return mutate_roots(wd, (root,), callback, purpose=purpose)
