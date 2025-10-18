"""
Elevation Query Microservice
============================

This Starlette application replaces the legacy Flask-based elevationquery
service. It mirrors the request/response format exposed at
``/weppcloud/runs/{runid}/{config}/elevationquery/`` and samples elevations
from the run's locally staged ``dem/dem.tif`` raster whenever available.

Expected JSON response payloads follow the historical shape:

.. code-block:: json

    {
        "Elevation": 1234.5,
        "Units": "m",
        "Longitude": -116.123,
        "Latitude": 45.987,
        "Error": "Optional diagnostic message"
    }

When the DEM is missing or a coordinate falls outside of the raster bounds the
service returns ``Elevation: null`` alongside an ``Error`` field describing the
issue while keeping the HTTP status at 200 so existing clients continue to
function without change.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.errors import RasterioIOError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from wepppy.weppcloud.utils.helpers import get_wd

logger = logging.getLogger(__name__)


class ElevationQueryError(Exception):
    """Base exception for predictable elevation query failures."""


class RunNotFoundError(ElevationQueryError):
    """Raised when the run directory cannot be located."""


class PupNotFoundError(ElevationQueryError):
    """Raised when a requested pup project cannot be resolved."""


class DemNotFoundError(ElevationQueryError):
    """Raised when a DEM raster cannot be located in the run directory."""


class OutsideDemError(ElevationQueryError):
    """Raised when the requested coordinate falls outside the DEM extent."""


class InvalidDemError(ElevationQueryError):
    """Raised when the DEM lacks critical metadata (e.g., CRS)."""


class InputValidationError(ElevationQueryError):
    """Raised when the incoming request payload cannot be parsed."""


WGS84 = CRS.from_epsg(4326)

_json_dumps = partial(json.dumps, ensure_ascii=False)


def _normalize_prefix(prefix: Optional[str]) -> str:
    if not prefix:
        return ''
    trimmed = prefix.strip()
    if not trimmed or trimmed == '/':
        return ''
    return '/' + trimmed.strip('/')


SITE_PREFIX = _normalize_prefix(os.getenv('SITE_PREFIX', '/weppcloud'))


def _build_route(path: str) -> str:
    if SITE_PREFIX:
        if path.startswith('/'):
            return f'{SITE_PREFIX}{path}'
        return f'{SITE_PREFIX}/{path}'
    return path


def _parse_float(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise InputValidationError(f'could not parse {field}')


async def _extract_coordinates(request: Request) -> Tuple[float, float]:
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    srs = request.query_params.get('srs')

    if lat is None or lng is None:
        data = await _safe_json(request)
        if lat is None:
            lat = data.get('lat')
        if lng is None:
            lng = data.get('lng')
        if srs is None:
            srs = data.get('srs')

    if lat is None:
        raise InputValidationError('lat not supplied')
    if lng is None:
        raise InputValidationError('lng not supplied')

    lat_value = _parse_float(lat, field='lat')
    lng_value = _parse_float(lng, field='lng')

    if srs:
        lng_value, lat_value = _transform_to_wgs84(lng_value, lat_value, srs)

    return lat_value, lng_value


async def _safe_json(request: Request) -> Dict[str, Any]:
    if request.method not in ('POST', 'PUT', 'PATCH'):
        return {}
    try:
        return await request.json()
    except Exception:
        return {}


def _transform_to_wgs84(lng: float, lat: float, srs: str) -> Tuple[float, float]:
    try:
        source_crs = CRS.from_user_input(srs)
        transformer = Transformer.from_crs(source_crs, WGS84, always_xy=True)
        transformed_lng, transformed_lat = transformer.transform(lng, lat)
    except Exception as exc:
        raise InputValidationError('Could not transform lng, lat to wgs') from exc

    if not (math.isfinite(transformed_lng) and math.isfinite(transformed_lat)):
        raise InputValidationError('Could not transform lng, lat to wgs')

    return transformed_lng, transformed_lat


def _resolve_active_root(runid: str, pup_relpath: Optional[str]) -> Path:
    run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    if not run_root.is_dir():
        raise RunNotFoundError(f"Run '{runid}' not found")

    if not pup_relpath:
        return run_root

    pups_root = (run_root / '_pups').resolve()
    if not pups_root.is_dir():
        raise PupNotFoundError(f"Pup project '{pup_relpath}' not found for run '{runid}'")

    candidate = (pups_root / pup_relpath).resolve()
    try:
        candidate.relative_to(pups_root)
    except ValueError as exc:
        raise PupNotFoundError(f"Pup project '{pup_relpath}' not found for run '{runid}'") from exc

    if not candidate.is_dir():
        raise PupNotFoundError(f"Pup project '{pup_relpath}' not found for run '{runid}'")

    return candidate


def _locate_dem(active_root: Path) -> Path:
    dem_dir = active_root / 'dem'
    if dem_dir.is_file():
        return dem_dir

    canonical = dem_dir / 'dem.tif'
    if canonical.is_file():
        return canonical

    secondary = dem_dir / 'dem.tiff'
    if secondary.is_file():
        return secondary

    if dem_dir.is_dir():
        for pattern in ('*.tif', '*.tiff', '*.TIF', '*.TIFF'):
            for candidate in sorted(dem_dir.glob(pattern)):
                if candidate.is_file():
                    return candidate

    raise DemNotFoundError('DEM not found under run directory')


def _sample_dem(dem_path: Path, lng: float, lat: float) -> float:
    try:
        dataset = rasterio.open(dem_path)
    except RasterioIOError as exc:
        raise DemNotFoundError('Unable to open DEM raster') from exc

    with dataset:
        if dataset.crs is None:
            raise InvalidDemError('DEM missing coordinate reference system')

        to_dataset = Transformer.from_crs(WGS84, dataset.crs, always_xy=True)
        x, y = to_dataset.transform(lng, lat)

        bounds = dataset.bounds
        if x < bounds.left or x > bounds.right or y < bounds.bottom or y > bounds.top:
            raise OutsideDemError('Location outside DEM extent')

        sample = next(dataset.sample([(x, y)], indexes=1, masked=True))
        value = sample[0]

        if np.ma.is_masked(value):
            raise OutsideDemError('No elevation data at requested location')

        value = float(value)
        nodata = dataset.nodata
        if nodata is not None and math.isfinite(nodata) and math.isclose(value, nodata, abs_tol=1e-6):
            raise OutsideDemError('No elevation data at requested location')

        if not math.isfinite(value):
            raise OutsideDemError('No elevation data at requested location')

        return value


def _build_response(
    *,
    elevation: Optional[float],
    lat: Optional[float],
    lng: Optional[float],
    error: Optional[str] = None,
    status_code: int = 200,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        'Elevation': elevation,
        'Units': 'm',
        'Longitude': lng,
        'Latitude': lat,
    }

    if error:
        payload['Error'] = error

    return JSONResponse(payload, status_code=status_code, dumps=_json_dumps)


async def elevationquery_endpoint(request: Request) -> JSONResponse:
    runid = request.path_params['runid']
    _config = request.path_params['config']  # reserved for future use / parity with route structure
    pup_relpath = request.query_params.get('pup')

    try:
        lat, lng = await _extract_coordinates(request)
    except InputValidationError as exc:
        return _build_response(elevation=None, lat=None, lng=None, error=str(exc))

    try:
        active_root = await asyncio.to_thread(_resolve_active_root, runid, pup_relpath)
    except RunNotFoundError as exc:
        return _build_response(elevation=None, lat=lat, lng=lng, error=str(exc))
    except PupNotFoundError as exc:
        return _build_response(elevation=None, lat=lat, lng=lng, error=str(exc))
    except Exception:
        logger.exception("Unexpected failure resolving run root for %s", runid)
        return _build_response(
            elevation=None,
            lat=lat,
            lng=lng,
            error='Unexpected error resolving run directory',
        )

    try:
        dem_path = await asyncio.to_thread(_locate_dem, active_root)
    except DemNotFoundError as exc:
        return _build_response(elevation=None, lat=lat, lng=lng, error=str(exc))

    try:
        elevation = await asyncio.to_thread(_sample_dem, dem_path, lng, lat)
    except OutsideDemError as exc:
        return _build_response(elevation=None, lat=lat, lng=lng, error=str(exc))
    except InvalidDemError as exc:
        return _build_response(elevation=None, lat=lat, lng=lng, error=str(exc))
    except Exception:
        logger.exception("Unexpected error sampling elevation for %s using %s", runid, dem_path)
        return _build_response(
            elevation=None,
            lat=lat,
            lng=lng,
            error='Unexpected error sampling elevation',
        )

    return _build_response(elevation=float(elevation), lat=lat, lng=lng)


def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse('OK')


def create_app() -> Starlette:
    routes = [
        Route('/health', health, methods=['GET']),
        Route(
            _build_route('/runs/{runid}/{config}/elevationquery/'),
            elevationquery_endpoint,
            methods=['GET', 'POST'],
        ),
        Route(
            _build_route('/runs/{runid}/{config}/elevationquery'),
            elevationquery_endpoint,
            methods=['GET', 'POST'],
        ),
    ]
    return Starlette(routes=routes)


app = create_app()

__all__ = ['app', 'create_app']


if __name__ == '__main__':  # pragma: no cover - manual execution helper
    import uvicorn

    port = int(os.getenv('PORT', '8002'))
    uvicorn.run(app, host=os.getenv('HOST', '0.0.0.0'), port=port)
