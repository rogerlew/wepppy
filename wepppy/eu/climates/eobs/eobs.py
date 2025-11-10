"""CLIGEN helpers that localize WEPP runs using the E-OBS dataset."""

from __future__ import annotations

from logging import Logger

from wepppy.climates.cligen import par_mod


def eobs_mod(
    par: int,
    years: int,
    lng: float,
    lat: float,
    wd: str,
    nwds_method: str = '',
    randseed: int | None = None,
    cliver: str | None = None,
    suffix: str = '',
    logger: Logger | None = None,
) -> dict[str, list[float]]:
    """Generate E-OBS-adjusted CLIGEN parameters for a WEPP run.

    Args:
        par: CLIGEN station identifier used as the localization seed.
        years: Number of synthetic climate years to produce.
        lng: Longitude in decimal degrees.
        lat: Latitude in decimal degrees.
        wd: Working directory that receives the output ``.par``/``.cli`` files.
        nwds_method: Optional override for the monthly wet/dry switch method.
        randseed: Random seed passed directly to CLIGEN for reproducibility.
        cliver: Explicit CLIGEN binary tag; defaults to the version in ``par_mod``.
        suffix: Extra text appended to generated filenames (for example ``"_custom"``).
        logger: Optional logger for streaming progress to the telemetry pipeline.

    Returns:
        Dictionary of localized monthly statistics returned by :func:`par_mod`.
    """
    return par_mod(
        par=par,
        years=years,
        lng=lng,
        lat=lat,
        wd=wd,
        monthly_dataset='eobs',
        nwds_method=nwds_method,
        randseed=randseed,
        cliver=cliver,
        suffix=suffix,
        logger=logger,
        version='ghcn_stations.db',
    )
