"""OpenTopography DEM retrieval helpers."""

from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Tuple

import requests
from requests.exceptions import RequestException

from wepppy.all_your_base.geo import utm_raster_transform
from wepppy.config.secrets import require_secret

Extent = Tuple[float, float, float, float]

__all__ = ["opentopo_retrieve"]

_OPENTOPOGRAPHY_URL = "https://portal.opentopography.org/API/globaldem"


def opentopo_retrieve(
    extent: Extent,
    dst_fn: str,
    cellsize: float,
    dataset: str = 'SRTMGL1_E',
    resample: str = 'bilinear',
) -> None:
    """Download and reproject an OpenTopography DEM into the target workspace.

    Args:
        extent: Bounding box tuple ``(west, south, east, north)`` in degrees.
        dst_fn: Destination GeoTIFF path for the warped raster.
        cellsize: Desired output pixel size (meters).
        dataset: DEM identifier (``SRTMGL1_E``, ``COP30``, etc.). Accepts
            ``opentopo://`` prefixes but they are stripped automatically.
        resample: GDAL resampling mode passed to ``utm_raster_transform``.

    Raises:
        RuntimeError: When ``OPENTOPOGRAPHY_API_KEY`` is unset.
        RuntimeError: If the OpenTopography API returns an error.
        OSError: When the download succeeds but the file cannot be written.
    """

    api_key = require_secret("OPENTOPOGRAPHY_API_KEY")

    dataset = dataset.replace('opentopo://', '').upper()

    data_dir, _ = _split(os.path.abspath(dst_fn))

    west, south, east, north = extent
    params = {
        "demtype": dataset,
        "south": south,
        "north": north,
        "west": west,
        "east": east,
        "outputFormat": "GTiff",
        "API_Key": api_key,
    }

    src_fn = None
    try:
        response = requests.get(_OPENTOPOGRAPHY_URL, params=params, timeout=60)
        response.raise_for_status()

        cd = response.headers.get('content-disposition')
        if cd:
            filename = cd.split('filename=')[1].strip(' "')
        else:
            filename = 'default_filename.tif'

        src_fn = _join(data_dir, filename)
        with open(src_fn, 'wb') as file:
            file.write(response.content)

    except RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        hint = f" (status={status})" if status is not None else ""
        # Never chain the original HTTPError: its message typically includes the full URL
        # (including query params).
        raise RuntimeError(f"OpenTopography DEM request failed{hint}.") from None

    if not _exists(src_fn):
        raise RuntimeError("OpenTopography DEM request succeeded but produced no file.")

    utm_raster_transform(extent, src_fn, dst_fn, cellsize, resample=resample)


if __name__ == "__main__":
    opentopo_retrieve((-120.5, 38.5, -120.4, 38.6), 'test.tif', 30)
