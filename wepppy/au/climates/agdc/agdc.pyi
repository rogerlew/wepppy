from __future__ import annotations

import logging

def agdc_mod(
    par: int,
    years: int,
    lng: float,
    lat: float,
    wd: str,
    nwds_method: str = ...,
    randseed: int | None = ...,
    cliver: str | None = ...,
    suffix: str = ...,
    logger: logging.Logger | None = ...,
) -> dict[str, list[float]]: ...
