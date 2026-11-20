from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Iterable

from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.core import Climate, ClimateMode
from wepppy.runtime_paths.errors import nodir_mixed_state
from wepppy.runtime_paths.fs import resolve

SINGLE_STORM_DEPRECATED_MESSAGE = (
    "Single-storm climates are deprecated. Use the Storm Event Analyzer for event-scale analysis."
)
SINGLE_STORM_BATCH_UNAVAILABLE_MESSAGE = (
    "Single-storm batches require per-event postprocessing that this WEPP workflow does not provide. "
    "Run an individual event from a CLI upload or choose a continuous climate."
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


def check_execution_climate(climate: Climate, *, prepared_inputs: bool = False) -> None:
    if not climate.is_single_storm:
        return
    if climate.climate_mode == ClimateMode.SingleStormBatch:
        raise ValueError(SINGLE_STORM_BATCH_UNAVAILABLE_MESSAGE)
    if climate.climate_mode == ClimateMode.UserDefinedSingleStorm and not prepared_inputs:
        try:
            is_event = ClimateFile(climate.cli_path).is_single_storm
        except (AssertionError, IndexError, OSError, TypeError, ValueError) as exc:
            raise ValueError('The active uploaded climate is missing or invalid. Upload a valid CLIGEN file.') from exc
        if not is_event:
            raise ValueError('The active upload does not contain one event as required by its saved single-storm mode. '
                             'Build a continuous climate or upload an individual storm CLI.')
    logging.getLogger(__name__).warning(SINGLE_STORM_DEPRECATED_MESSAGE)


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
