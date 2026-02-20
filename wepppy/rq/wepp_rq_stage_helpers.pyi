from __future__ import annotations

from typing import Iterable

from wepppy.nodb.core import Climate

SINGLE_STORM_DEPRECATED_MESSAGE: str
NODIR_RECOVERY_ROOTS: tuple[str, ...]


def recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: Iterable[str] = ...,
) -> tuple[str, ...]: ...


def assert_supported_climate(climate: Climate) -> None: ...


def with_stage_read_projections(
    wd: str,
    *,
    roots: tuple[str, ...],
    purpose: str,
): ...
