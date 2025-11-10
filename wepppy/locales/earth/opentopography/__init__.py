"""OpenTopography DEM retrieval helpers."""

from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Tuple

import requests
from requests.exceptions import HTTPError

from wepppy.all_your_base.geo import utm_raster_transform

Extent = Tuple[float, float, float, float]

OPENTOPOGRAPHY_API_KEY = os.environ.get('OPENTOPOGRAPHY_API_KEY')

__all__ = ["opentopo_retrieve"]


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
        AssertionError: When ``OPENTOPOGRAPHY_API_KEY`` is unset.
        HTTPError: If the OpenTopography API returns an error.
        Exception: When the download succeeds but the file cannot be written.
    """

    assert OPENTOPOGRAPHY_API_KEY is not None, 'You must set OPENTOPOGRAPHY_API_KEY in .env file'

    dataset = dataset.replace('opentopo://', '').upper()

    data_dir, _ = _split(os.path.abspath(dst_fn))

    west, south, east, north = extent
    url = (
        'https://portal.opentopography.org/API/globaldem'
        f'?demtype={dataset}'
        f'&south={south}&north={north}&west={west}&east={east}'
        f'&outputFormat=GTiff&API_Key={OPENTOPOGRAPHY_API_KEY}'
    )

    src_fn = None
    try:
        response = requests.get(url)
        response.raise_for_status()

        cd = response.headers.get('content-disposition')
        if cd:
            filename = cd.split('filename=')[1].strip(' "')
        else:
            filename = 'default_filename.tif'

        src_fn = _join(data_dir, filename)
        with open(src_fn, 'wb') as file:
            file.write(response.content)

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        raise
    except Exception as err:
        print(f'An error occurred: {err}')
        raise

    if not _exists(src_fn):
        raise Exception(response.text)

    utm_raster_transform(extent, src_fn, dst_fn, cellsize, resample=resample)


if __name__ == "__main__":
    opentopo_retrieve((-120.5, 38.5, -120.4, 38.6), 'test.tif', 30)
