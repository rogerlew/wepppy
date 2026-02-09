"""Shared browse-service path security helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Literal

PathSecurityCode = Literal[
    "forbidden_recorder",
    "forbidden_hidden",
    "outside_allowed_roots",
    "invalid_path",
]

__all__ = [
    "PATH_SECURITY_FORBIDDEN_HIDDEN",
    "PATH_SECURITY_FORBIDDEN_RECORDER",
    "PATH_SECURITY_INVALID_PATH",
    "PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS",
    "RESTRICTED_PATH_SEGMENTS",
    "derive_allowed_symlink_roots",
    "is_hidden_path",
    "path_security_detail",
    "is_restricted_recorder_path",
    "is_within_any_root",
    "path_has_hidden_segments_within_roots",
    "path_has_restricted_recorder_segments",
    "resolve_path_safely",
    "validate_raw_subpath",
    "validate_resolved_path_against_roots",
    "validate_resolved_target",
]


RESTRICTED_PATH_SEGMENTS = frozenset({"_logs", "profile.events.jsonl"})
_RESTRICTED_PATH_SEGMENTS_CASEFOLDED = frozenset(
    segment.casefold() for segment in RESTRICTED_PATH_SEGMENTS
)
PATH_SECURITY_FORBIDDEN_RECORDER: PathSecurityCode = "forbidden_recorder"
PATH_SECURITY_FORBIDDEN_HIDDEN: PathSecurityCode = "forbidden_hidden"
PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS: PathSecurityCode = "outside_allowed_roots"
PATH_SECURITY_INVALID_PATH: PathSecurityCode = "invalid_path"


def resolve_path_safely(path: str | Path) -> Path | None:
    """Resolve a path without raising on symlink loops or invalid targets."""
    try:
        return Path(path).resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def is_restricted_recorder_path(raw_path: str) -> bool:
    if not raw_path:
        return False
    normalized = raw_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if not parts:
        return False
    lowered = {part.casefold() for part in parts}
    return any(segment in lowered for segment in _RESTRICTED_PATH_SEGMENTS_CASEFOLDED)


def is_hidden_path(raw_path: str) -> bool:
    if not raw_path:
        return False
    normalized = raw_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part not in ("", ".", "..")]
    if not parts:
        return False
    return any(part.startswith(".") for part in parts)


def path_security_detail(code: PathSecurityCode) -> str:
    if code == PATH_SECURITY_FORBIDDEN_RECORDER:
        return "Access to recorder log artifacts is forbidden."
    if code == PATH_SECURITY_FORBIDDEN_HIDDEN:
        return "Access to hidden paths is forbidden."
    return "Invalid path."


def validate_raw_subpath(raw_path: str) -> PathSecurityCode | None:
    if is_restricted_recorder_path(raw_path):
        return PATH_SECURITY_FORBIDDEN_RECORDER
    if is_hidden_path(raw_path):
        return PATH_SECURITY_FORBIDDEN_HIDDEN
    return None


def path_has_restricted_recorder_segments(path: str | Path) -> bool:
    parts = [part for part in Path(path).parts if part not in ("", ".")]
    if not parts:
        return False
    lowered = {part.casefold() for part in parts}
    return any(segment in lowered for segment in _RESTRICTED_PATH_SEGMENTS_CASEFOLDED)


def path_has_hidden_segments_within_roots(
    candidate: str | Path,
    roots: Iterable[str | Path],
) -> bool:
    candidate_path = resolve_path_safely(candidate)
    if candidate_path is None:
        return False

    for root in roots:
        root_path = resolve_path_safely(root)
        if root_path is None:
            continue
        try:
            rel_path = candidate_path.relative_to(root_path)
        except ValueError:
            continue
        parts = [part for part in rel_path.parts if part not in ("", ".", "..")]
        return any(part.startswith(".") for part in parts)

    return False


def validate_resolved_path_against_roots(
    candidate: str | Path,
    roots: Iterable[str | Path],
) -> PathSecurityCode | None:
    root_candidates = tuple(roots)
    candidate_path = resolve_path_safely(candidate)
    if candidate_path is None:
        return PATH_SECURITY_INVALID_PATH
    if not is_within_any_root(candidate_path, root_candidates):
        return PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS
    if path_has_restricted_recorder_segments(candidate_path):
        return PATH_SECURITY_FORBIDDEN_RECORDER
    if path_has_hidden_segments_within_roots(candidate_path, root_candidates):
        return PATH_SECURITY_FORBIDDEN_HIDDEN
    return None


def is_within_any_root(candidate: str | Path, roots: Iterable[str | Path]) -> bool:
    candidate_path = resolve_path_safely(candidate)
    if candidate_path is None:
        return False
    for root in roots:
        root_path = resolve_path_safely(root)
        if root_path is None:
            continue
        try:
            candidate_path.relative_to(root_path)
            return True
        except ValueError:
            continue
    return False


def derive_allowed_symlink_roots(root: str | Path) -> tuple[Path, ...]:
    """Return roots that symlink resolution is allowed to enter for this run tree.

    Supported shared-root layouts:
    - Omni child runs (`.../_pups/omni/scenarios/<name>` and contrasts) can resolve
      into the parent run root that owns `_pups/`.
    - Grouped run trees with `/runs/<runid>` can resolve into the grouped batch root
      (for example culvert and batch runner shared maps/assets).
    """
    root_path = resolve_path_safely(root)
    if root_path is None:
        root_path = Path(os.path.abspath(str(root)))
    allowed = {root_path}

    # Shared batch roots: <group-root>/runs/<runid>
    if root_path.parent.name.casefold() == "runs":
        allowed.add(root_path.parent.parent.resolve(strict=False))

    normalized = root_path.as_posix()
    normalized_casefolded = normalized.casefold()
    for marker in ("/_pups/omni/scenarios/", "/_pups/omni/contrasts/"):
        marker_index = normalized_casefolded.find(marker)
        if marker_index > 0:
            parent_root = resolve_path_safely(normalized[:marker_index])
            if parent_root is not None:
                allowed.add(parent_root)
            break

    return tuple(sorted(allowed, key=lambda path: path.as_posix()))


def validate_resolved_target(root: str | Path, target: str | Path) -> PathSecurityCode | None:
    allowed_roots = derive_allowed_symlink_roots(root)
    target_path = Path(os.path.abspath(str(target)))
    return validate_resolved_path_against_roots(target_path, allowed_roots)
