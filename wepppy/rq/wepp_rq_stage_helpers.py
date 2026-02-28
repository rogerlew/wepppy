from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Iterable

from wepppy.nodb.core import Climate
from wepppy.runtime_paths.errors import nodir_mixed_state
from wepppy.runtime_paths.fs import resolve

SINGLE_STORM_DEPRECATED_MESSAGE = (
    "Single-storm climate modes are deprecated and unsupported. "
    "Use continuous/multi-year climate datasets for WEPP runs."
)

NODIR_RECOVERY_ROOTS = ("climate", "landuse", "soils", "watershed")


def _assert_directory_roots_available(wd: str, roots: Iterable[str]) -> None:
    wd_path = Path(wd)
    for root in roots:
        root_dir = wd_path / root
        root_archive = wd_path / f"{root}.nodir"
        if root_dir.exists() and root_archive.exists():
            raise nodir_mixed_state(f"{root} is in mixed state (dir + .nodir present)")
        resolve(wd, root, view="effective")


def recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: Iterable[str] = NODIR_RECOVERY_ROOTS,
) -> tuple[str, ...]:
    # Directory-only runtime: mixed/archive roots are explicit boundaries.
    _assert_directory_roots_available(wd, roots)
    return tuple()


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
    _ = purpose
    # Directory-only runtime: projection mounts are retired.
    _assert_directory_roots_available(wd, roots)
    yield
