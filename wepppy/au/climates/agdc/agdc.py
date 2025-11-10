# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#

"""Thin adapter for running CLIGEN against the AGDC monthly dataset.

The implementation intentionally keeps the WEPPcloud side as small as possible—
all heavy lifting is handled by :func:`wepppy.climates.cligen.par_mod`.  This
module simply wires up the AGDC-specific ``monthly_dataset`` and metadata so
callers can request an Australian run without duplicating boilerplate.
"""

from __future__ import annotations

import logging

from wepppy.climates.cligen import par_mod


def agdc_mod(
    par: int,
    years: int,
    lng: float,
    lat: float,
    wd: str,
    nwds_method: str = '',
    randseed: int | None = None,
    cliver: str | None = None,
    suffix: str = '',
    logger: logging.Logger | None = None,
) -> dict[str, list[float]]:
    """Generate CLIGEN monthlies localized with AGDC means.

    Args:
        par: Station identifier in the CLIGEN catalog.
        years: Number of synthetic years to generate.
        lng: Longitude used for localization.
        lat: Latitude used for localization.
        wd: Working directory where CLIGEN artifacts are stored.
        nwds_method: Native wet/dry sequence handling strategy to pass through
            to CLIGEN.
        randseed: Optional deterministic seed for CLIGEN.
        cliver: CLIGEN executable version tag; when omitted the default binary
            is used.
        suffix: Text appended to generated filenames so parallel requests do
            not clobber one another.
        logger: Optional logger for progress messages. When ``None`` the core
            CLIGEN adapter will fall back to its module-level logger.

    Returns:
        Localized CLIGEN monthly statistics as produced by ``par_mod``.
    """

    return par_mod(
        par=par,
        years=years,
        lng=lng,
        lat=lat,
        wd=wd,
        monthly_dataset='agdc',
        nwds_method=nwds_method,
        randseed=randseed,
        cliver=cliver,
        suffix=suffix,
        logger=logger,
        version='ghcn_stations.db',
    )
