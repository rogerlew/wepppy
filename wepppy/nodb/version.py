"""Schema version tracking and migration helpers for NoDb payloads."""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

logger = logging.getLogger(__name__)

CURRENT_VERSION: int = 1000
VERSION_FILENAME = "nodb.version"


@dataclass(frozen=True)
class Migration:
    """Represents a single step upgrade to a target schema version."""

    target_version: int
    func: Callable[[Path], None]
    description: str | None = None


def _noop_initialize(_: Path) -> None:
    """Initial migration placeholder to stamp the baseline version."""
    return None


MIGRATIONS: Sequence[Migration] = (
    Migration(1000, _noop_initialize, "Initialize NoDb schema version tracking"),
)

_migration_stack = threading.local()


def _determine_version(wd_path: Path) -> int:
    """
    Best-effort inference for runs created before version files existed.

    New runs (no `.nodb` artifacts yet) default to the current schema version.
    Legacy runs without a version marker remain at 0 until purpose-built
    migrations assign them a concrete revision.
    """
    if len(tuple(wd_path.glob("*.nodb"))) == 0:
        # No top-level NoDb payloads yet; assume this run is being created
        # under the current codebase.
        return CURRENT_VERSION
    

    # Legacy run—either no heuristics yet or inference failed.
    return 0


def _get_inflight() -> set[str]:
    inflight = getattr(_migration_stack, "value", None)
    if inflight is None:
        inflight = set()
        setattr(_migration_stack, "value", inflight)
    return inflight


def _version_file(wd: Path) -> Path:
    return wd / VERSION_FILENAME


def _atomic_write(path: Path, contents: str) -> None:
    """Write ``contents`` to ``path`` atomically using a unique temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as tmp_file:
            tmp_file.write(contents)
            tmp_file.flush()
            fsync = getattr(os, "fsync", None)
            if fsync is not None:
                try:
                    fsync(tmp_file.fileno())
                except OSError:
                    # Best-effort fsync; fall back to relying on rename if it fails.
                    pass

        tmp_path.replace(path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


def read_version(wd: str | Path) -> int:
    """Return the stored schema version for ``wd`` (defaults to 0)."""
    wd_path = Path(wd)
    path = _version_file(wd_path)
    try:
        raw = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return _determine_version(wd_path)
    except OSError as exc:
        logger.warning("Failed to read NoDb version file %s: %s", path, exc)
        return _determine_version(wd_path)

    if not raw:
        return _determine_version(wd_path)

    try:
        value = int(raw, 10)
    except ValueError:
        logger.warning("Invalid NoDb version value '%s' in %s; treating as version 0", raw, path)
        return _determine_version(wd_path)

    if value > 0:
        return value

    return _determine_version(wd_path)


def write_version(wd: str | Path, version: int) -> None:
    """Persist ``version`` to the NoDb version file under ``wd``."""
    wd_path = Path(wd)
    path = _version_file(wd_path)
    try:
        _atomic_write(path, f"{version}\n")
    except OSError as exc:
        logger.error("Failed to write NoDb version file %s: %s", path, exc)
        raise


def copy_version_for_clone(base_wd: str | Path, new_wd: str | Path) -> None:
    """
    Copy the recorded schema version from ``base_wd`` into ``new_wd``.

    If the source version file does not exist, no file is written.
    """
    base_path = _version_file(Path(base_wd).resolve())
    if not base_path.exists():
        return

    target_root = Path(new_wd).resolve()
    target_path = _version_file(target_root)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        contents = base_path.read_text(encoding="ascii")
    except OSError as exc:
        logger.error("Failed to read NoDb version file %s: %s", base_path, exc)
        raise

    try:
        _atomic_write(target_path, contents)
    except OSError as exc:
        logger.error(
            "Failed to copy NoDb version file from %s to %s: %s",
            base_path,
            target_path,
            exc,
        )
        raise


def ensure_version(
    wd: str | Path,
    *,
    target_version: int = CURRENT_VERSION,
    migrations: Iterable[Migration] | None = None,
) -> int:
    """
    Upgrade the NoDb payloads under ``wd`` to ``target_version`` if necessary.

    Returns the resulting schema version (which may be less than ``target_version`` if
    an error occurs during migration).
    """
    wd_path = Path(wd).resolve()
    if not wd_path.exists():
        return 0

    inflight = _get_inflight()
    wd_key = str(wd_path)
    if wd_key in inflight:
        return read_version(wd_path)

    inflight.add(wd_key)
    try:
        current = read_version(wd_path)
        if current == 0:
            write_version(wd_path, 0)
            return 0

        if current >= target_version:
            return current

        sequence = tuple(sorted(migrations or MIGRATIONS, key=lambda m: m.target_version))
        for migration in sequence:
            if migration.target_version <= current:
                continue

            if migration.target_version > target_version:
                break

            desc = migration.description or migration.func.__name__
            logger.info(
                "Migrating NoDb run at %s from version %s to %s (%s)",
                wd_path,
                current,
                migration.target_version,
                desc,
            )
            migration.func(wd_path)
            write_version(wd_path, migration.target_version)
            current = migration.target_version

        if current < target_version:
            # Allow jumping directly to the target if no explicit migrations exist.
            write_version(wd_path, target_version)
            current = target_version

        return current
    finally:
        inflight.remove(wd_key)


__all__ = [
    "CURRENT_VERSION",
    "VERSION_FILENAME",
    "Migration",
    "ensure_version",
    "read_version",
    "write_version",
    "copy_version_for_clone",
]
