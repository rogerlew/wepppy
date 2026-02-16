"""Symlink resolution policy helpers for NoDir.

These helpers mirror the browse-service allowed-root policy to prevent
symlink escapes when reading from a run working directory.
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_path_safely(path: str | Path) -> Path | None:
    try:
        return Path(path).resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def _derive_allowed_symlink_roots(wd: str | Path) -> tuple[Path, ...]:
    """Roots symlink resolution is allowed to enter for this run tree.

    Keep in sync with browse-service policy:
    `wepppy/microservices/browse/security.py:derive_allowed_symlink_roots`.
    """
    root_path = _resolve_path_safely(wd)
    if root_path is None:
        root_path = Path(os.path.abspath(str(wd)))
    allowed: set[Path] = {root_path}

    # Shared batch roots: <group-root>/runs/<runid>
    if root_path.parent.name.casefold() == "runs":
        allowed.add(root_path.parent.parent.resolve(strict=False))

    normalized = root_path.as_posix()
    normalized_casefolded = normalized.casefold()
    for marker in ("/_pups/omni/scenarios/", "/_pups/omni/contrasts/"):
        marker_index = normalized_casefolded.find(marker)
        if marker_index > 0:
            parent_root = _resolve_path_safely(normalized[:marker_index])
            if parent_root is not None:
                allowed.add(parent_root)
            break

    return tuple(sorted(allowed, key=lambda path: path.as_posix()))


def _is_within_any_root(candidate: str | Path, roots: tuple[str | Path, ...] | tuple[Path, ...]) -> bool:
    candidate_path = _resolve_path_safely(candidate)
    if candidate_path is None:
        return False
    for root in roots:
        root_path = _resolve_path_safely(root)
        if root_path is None:
            continue
        try:
            candidate_path.relative_to(root_path)
            return True
        except ValueError:
            continue
    return False

