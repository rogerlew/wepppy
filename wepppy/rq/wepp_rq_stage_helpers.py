from __future__ import annotations

import contextlib
import shutil
from pathlib import Path
from typing import Iterable

from wepppy.nodb.core import Climate
from wepppy.nodir.errors import nodir_mixed_state
from wepppy.nodir.fs import resolve
from wepppy.nodir.projections import with_root_projection

SINGLE_STORM_DEPRECATED_MESSAGE = (
    "Single-storm climate modes are deprecated and unsupported. "
    "Use continuous/multi-year climate datasets for WEPP runs."
)

NODIR_RECOVERY_ROOTS = ("climate", "landuse", "soils", "watershed")


def recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: Iterable[str] = NODIR_RECOVERY_ROOTS,
) -> tuple[str, ...]:
    """Recover mixed NoDir roots by preserving archive form as source of truth."""

    wd_path = Path(wd)
    recovered: list[str] = []
    for root in roots:
        root_dir = wd_path / root
        root_archive = wd_path / f"{root}.nodir"
        if not root_dir.exists() or not root_archive.exists():
            continue

        # Mixed state means both forms exist. Keep the archive and discard the
        # thawed directory-form tree, which may be partially mutated after a
        # failed callback.
        if root_dir.is_dir() and not root_dir.is_symlink():
            shutil.rmtree(root_dir)
        else:
            root_dir.unlink()
        recovered.append(root)

    return tuple(recovered)


def assert_supported_climate(climate: Climate) -> None:
    if climate.is_single_storm:
        raise ValueError(SINGLE_STORM_DEPRECATED_MESSAGE)


@contextlib.contextmanager
def with_stage_read_projections(
    wd: str,
    *,
    roots: tuple[str, ...],
    purpose: str,
):
    with contextlib.ExitStack() as stack:
        for root in roots:
            target = resolve(wd, root, view="archive")
            if target is None:
                continue

            mount_path = Path(wd) / root
            if mount_path.exists() and not mount_path.is_symlink():
                raise nodir_mixed_state(f"{root} is in mixed state (dir + .nodir present)")

            stack.enter_context(with_root_projection(wd, root, mode="read", purpose=purpose))
        yield
