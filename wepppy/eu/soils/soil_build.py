"""Helpers that dispatch EU ESDAC-based soil builds via multiprocessing."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from multiprocessing import Pool
from typing import Any

from wepppy.eu.soils.esdac import ESDAC
from wepppy.eu.soils.esdac.esdac import Horizon
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.soils.ssurgo import SoilSummary

# ESDAC builds are embarrassingly parallel, so the worker pool defaults to an
# aggressive size to keep runtimes down for large watersheds.
NCPU = 32


def _build_esdac_soil(kwargs: dict[str, Any]) -> tuple[str | int, str, Horizon, str]:
    """Invoke :meth:`ESDAC.build_wepp_soil` for a single hillslope.

    Args:
        kwargs: Dictionary produced by :func:`build_esdac_soils` that carries
            the TopoAZ identifier, centroid, and build settings.

    Returns:
        Tuple of ``(topaz_id, soil_key, horizon, description)`` mirroring the
        :meth:`ESDAC.build_wepp_soil` contract so the parent process can build
        :class:`SoilSummary` instances without re-reading the .sol files.
    """
    topaz_id = kwargs["topaz_id"]
    lng = kwargs["lng"]
    lat = kwargs["lat"]
    soils_dir = kwargs["soils_dir"]
    res_lyr_ksat_threshold = kwargs["res_lyr_ksat_threshold"]
    status_channel = kwargs["status_channel"]

    esd = ESDAC()
    key, horizon, desc = esd.build_wepp_soil(lng, lat, soils_dir, res_lyr_ksat_threshold)
    if status_channel is not None:
        StatusMessenger.publish(
            status_channel, f"_build_esdac_soil({topaz_id}) -> {key}, {desc}"
        )

    return topaz_id, key, horizon, desc


def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = 2.0,
    status_channel: str | None = None,
) -> tuple[dict[str, SoilSummary], dict[str, str]]:
    """Build WEPP-ready soils for a collection of hillslopes.

    Args:
        orders: Sequence of ``(topaz_id, (longitude, latitude))`` tuples that
            describe the hillslope centroids to process.
        soils_dir: Output directory where generated ``.sol`` files live.
        res_lyr_ksat_threshold: Hydraulic conductivity threshold that signals a
            restrictive layer.
        status_channel: Optional Redis pub/sub channel for progress updates.

    Returns:
        A tuple containing:
            * Mapping of soil key → :class:`~wepppy.soils.ssurgo.SoilSummary`.
            * Mapping of TopoAZ hillslope id → soil key (dominant soil).
    """
    args: list[dict[str, Any]] = []
    for topaz_id, (lng, lat) in orders:
        args.append(
            dict(
                topaz_id=topaz_id,
                lng=lng,
                lat=lat,
                soils_dir=soils_dir,
                res_lyr_ksat_threshold=res_lyr_ksat_threshold,
                status_channel=status_channel,
            )
        )

    with Pool(processes=NCPU) as pool:
        results = pool.map(_build_esdac_soil, args)

    soils: dict[str, SoilSummary] = {}
    domsoil_d: dict[str, str] = {}
    for topaz_id, key, _horizon, desc in results:
        topaz_str = str(topaz_id)
        key_str = str(key)
        if key_str not in soils:
            fname = f"{key_str}.sol"
            soils[key_str] = SoilSummary(
                mukey=key_str,
                fname=fname,
                soils_dir=soils_dir,
                build_date=str(datetime.now),
                desc=desc,
            )
        domsoil_d[topaz_str] = key_str

    return soils, domsoil_d
