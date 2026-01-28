"""Shared WEPP post-processing helpers for NoDb runners."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from wepppy.nodb.core import Climate, Wepp
from wepppy.query_engine.activate import activate_query_engine
from wepppy.wepp.interchange import (
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


def ensure_hillslope_interchange(
    wepp: Wepp, climate: Climate, logger: Optional[logging.Logger] = None
) -> None:
    interchange_dir = Path(wepp.wepp_interchange_dir)
    pass_path = interchange_dir / "H.pass.parquet"
    wat_path = interchange_dir / "H.wat.parquet"
    if pass_path.exists() and (wat_path.exists() or climate.is_single_storm):
        return

    _log(logger, "building hillslope interchange outputs")
    run_wepp_hillslope_interchange(
        Path(wepp.output_dir),
        start_year=climate.calendar_start_year,
        run_loss_interchange=not climate.is_single_storm,
        run_soil_interchange=not climate.is_single_storm,
        run_wat_interchange=not climate.is_single_storm,
        delete_after_interchange=wepp.delete_after_interchange,
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
    wepp: Wepp, climate: Climate, logger: Optional[logging.Logger] = None
) -> None:
    interchange_dir = Path(wepp.wepp_interchange_dir)
    pass_events = interchange_dir / "pass_pw0.events.parquet"
    if pass_events.exists():
        return

    _log(logger, "building watershed interchange outputs")
    run_wepp_watershed_interchange(
        Path(wepp.output_dir),
        start_year=climate.calendar_start_year,
        run_soil_interchange=not climate.is_single_storm,
        run_chnwb_interchange=not climate.is_single_storm,
        delete_after_interchange=wepp.delete_after_interchange,
    )
    generate_interchange_documentation(wepp.wepp_interchange_dir)


def activate_query_engine_for_run(
    wepp: Wepp, logger: Optional[logging.Logger] = None
) -> None:
    _log(logger, "activating query engine")
    activate_query_engine(wepp.wd, run_interchange=False, force_refresh=True)
