"""Shared WEPP post-processing helpers for NoDb runners."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from wepppy.nodb.core import Climate, Wepp
from wepppy.query_engine.activate import activate_query_engine
from wepppy.wepp.interchange import (
    cleanup_hillslope_sources_for_completed_interchange,
    generate_interchange_documentation,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
)

__all__ = [
    "activate_query_engine_for_run",
    "ensure_hillslope_interchange",
    "ensure_totalwatsed3",
    "ensure_watershed_interchange",
]


def _log(logger: Optional[logging.Logger], message: str) -> None:
    if logger is not None:
        logger.info(message)


def _delete_after_interchange_enabled(*, wepp: Wepp, climate: Climate) -> bool:
    value = getattr(wepp, "delete_after_interchange", None)
    if value is None:
        value = getattr(climate, "delete_after_interchange", False)
    return bool(value)


def ensure_hillslope_interchange(
    wepp: Wepp,
    climate: Climate,
    logger: Optional[logging.Logger] = None,
    *,
    watershed_pending: bool = False,
) -> None:
    interchange_dir = Path(wepp.wepp_interchange_dir)
    pass_path = interchange_dir / "H.pass.parquet"
    wat_path = interchange_dir / "H.wat.parquet"
    if pass_path.exists() and (wat_path.exists() or climate.is_single_storm):
        return

    delete_after_interchange = _delete_after_interchange_enabled(wepp=wepp, climate=climate)
    if watershed_pending:
        # Watershed routing still depends on H*.dat outputs.
        delete_after_interchange = False

    _log(logger, "building hillslope interchange outputs")
    run_wepp_hillslope_interchange(
        Path(wepp.output_dir),
        start_year=climate.calendar_start_year,
        run_loss_interchange=not climate.is_single_storm,
        run_soil_interchange=not climate.is_single_storm,
        run_wat_interchange=not climate.is_single_storm,
        delete_after_interchange=delete_after_interchange,
    )


def ensure_totalwatsed3(
    wepp: Wepp, climate: Climate, logger: Optional[logging.Logger] = None
) -> None:
    if climate.is_single_storm:
        return
    interchange_dir = Path(wepp.wepp_interchange_dir)
    totalwatsed_path = interchange_dir / "totalwatsed3.parquet"
    if totalwatsed_path.exists():
        return
    if not (interchange_dir / "H.pass.parquet").exists():
        _log(logger, "skipping totalwatsed3; H.pass.parquet missing")
        return
    if not (interchange_dir / "H.wat.parquet").exists():
        _log(logger, "skipping totalwatsed3; H.wat.parquet missing")
        return

    _log(logger, "building totalwatsed3")
    wepp._build_totalwatsed3()


def ensure_watershed_interchange(
    wepp: Wepp,
    climate: Climate,
    logger: Optional[logging.Logger] = None,
    *,
    cleanup_deferred_hillslope_sources: bool = True,
) -> None:
    interchange_dir = Path(wepp.wepp_interchange_dir)
    pass_events = interchange_dir / "pass_pw0.events.parquet"
    delete_after_interchange = _delete_after_interchange_enabled(wepp=wepp, climate=climate)

    if pass_events.exists():
        _log(logger, "watershed interchange outputs already exist; skipping rebuild")
    else:
        _log(logger, "building watershed interchange outputs")
        run_wepp_watershed_interchange(
            Path(wepp.output_dir),
            start_year=climate.calendar_start_year,
            run_soil_interchange=not climate.is_single_storm,
            run_chnwb_interchange=not climate.is_single_storm,
            delete_after_interchange=delete_after_interchange,
        )
        generate_interchange_documentation(wepp.wepp_interchange_dir)

    if delete_after_interchange and cleanup_deferred_hillslope_sources:
        _log(logger, "cleaning deferred hillslope sources after watershed interchange")
        cleanup_hillslope_sources_for_completed_interchange(
            Path(wepp.output_dir),
            run_loss_interchange=not climate.is_single_storm,
            run_soil_interchange=not climate.is_single_storm,
            run_wat_interchange=not climate.is_single_storm,
        )


def activate_query_engine_for_run(
    wepp: Wepp, logger: Optional[logging.Logger] = None
) -> None:
    _log(logger, "activating query engine")
    activate_query_engine(wepp.wd, run_interchange=False, force_refresh=True)
