"""Directory-only projection helpers."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from .paths import NoDirRoot

__all__ = [
    "ProjectionMode",
    "ProjectionHandle",
    "acquire_root_projection",
    "release_root_projection",
    "with_root_projection",
    "commit_mutation_projection",
    "abort_mutation_projection",
]

ProjectionMode = Literal["read", "mutate"]


@dataclass(frozen=True, slots=True)
class ProjectionHandle:
    wd: str
    root: NoDirRoot
    mode: ProjectionMode
    purpose: str
    session_token: str
    mount_path: str
    archive_path: str
    metadata_path: str
    lower_path: str
    upper_path: str | None = None


def acquire_root_projection(
    wd: str,
    root: NoDirRoot,
    *,
    mode: ProjectionMode = "read",
    purpose: str = "runtime-path-projection",
) -> ProjectionHandle:
    wd_path = Path(os.path.abspath(wd))
    mount_path = wd_path / root
    if not mount_path.exists():
        raise FileNotFoundError(str(mount_path))
    if not mount_path.is_dir():
        raise NotADirectoryError(str(mount_path))

    token = uuid.uuid4().hex
    return ProjectionHandle(
        wd=str(wd_path),
        root=root,
        mode=mode,
        purpose=purpose,
        session_token=token,
        mount_path=str(mount_path),
        archive_path=str(wd_path / f"{root}.nodir"),
        metadata_path="",
        lower_path=str(mount_path),
        upper_path=None,
    )


def release_root_projection(handle: ProjectionHandle) -> None:
    _ = handle


def commit_mutation_projection(handle: ProjectionHandle) -> None:
    _ = handle


def abort_mutation_projection(handle: ProjectionHandle) -> None:
    _ = handle


@contextmanager
def with_root_projection(
    wd: str,
    root: NoDirRoot,
    *,
    mode: ProjectionMode = "read",
    purpose: str = "runtime-path-projection",
) -> Iterator[ProjectionHandle]:
    handle = acquire_root_projection(wd, root, mode=mode, purpose=purpose)
    try:
        yield handle
    finally:
        release_root_projection(handle)
