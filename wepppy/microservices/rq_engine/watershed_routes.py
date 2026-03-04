from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile
import utm
from werkzeug.utils import secure_filename
from osgeo import gdal, osr

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.all_your_base.geo import utm_srid
from wepppy.all_your_base.geo.locationinfo import RasterDatasetInterpolator
from wepppy.nodb.core import (
    Map,
    MinimumChannelLengthTooShortError,
    Ron,
    Watershed,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.project_rq import (
    build_subcatchments_and_abstract_watershed_rq,
    fetch_dem_and_build_channels_rq,
    set_outlet_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
FETCH_DEM_AND_BUILD_CHANNELS_TIMEOUT = int(os.getenv("RQ_ENGINE_FETCH_DEM_BUILD_CHANNELS_TIMEOUT", "600"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
UPLOAD_DEM_MAX_DIMENSION = 2560
UPLOAD_DEM_ALLOWED_EXTENSIONS = ("tif",)


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


def nodir_resolve(_wd: str, _root: str, *, view: str = "effective") -> None:
    return _nodir_resolve(_wd, _root, view=view)


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _preflight_watershed_mutation_root(wd: str) -> None:
    _require_directory_root(wd, "watershed")


def _run_with_watershed_lock(wd: str, callback, *, purpose: str):
    _preflight_watershed_mutation_root(wd)
    with nodir_maintenance_lock(wd, "watershed", purpose=purpose):
        _preflight_watershed_mutation_root(wd)
        return callback()


def _is_base_project_context(runid: str, config: str) -> bool:
    runid_leaf = runid.split(";;")[-1].strip().lower() if runid else ""
    config_token = str(config).strip().lower() if config is not None else ""
    return runid_leaf == "_base" or config_token == "_base"


def _parse_map_change(payload: dict[str, Any]) -> tuple[JSONResponse | None, list[Any] | None]:
    center_raw = payload.get("map_center")
    zoom_raw = payload.get("map_zoom")
    bounds_raw = payload.get("map_bounds")
    mcl_raw = payload.get("mcl")
    csa_raw = payload.get("csa")
    wbt_fill_or_breach_raw = payload.get("wbt_fill_or_breach")
    wbt_blc_dist_raw = payload.get("wbt_blc_dist")
    set_extent_mode_raw = payload.get("set_extent_mode", 0)
    map_bounds_text_raw = payload.get("map_bounds_text", "")
    map_object_raw = payload.get("map_object")

    def _as_float_sequence(value: Any, expected_len: int, label: str) -> list[float]:
        candidate = value
        if isinstance(value, dict) and "py/tuple" in value:
            candidate = value.get("py/tuple")
        if isinstance(candidate, (list, tuple)):
            parts = list(candidate)
        elif isinstance(candidate, str):
            parts = [part.strip() for part in candidate.split(",") if part.strip()]
        else:
            raise ValueError(f"Invalid {label} payload.")
        if len(parts) != expected_len:
            raise ValueError(f"{label} must contain {expected_len} values.")
        result: list[float] = []
        for part in parts:
            try:
                result.append(float(part))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Could not parse {label}.") from exc
        return result

    def _as_float(value: Any, label: str) -> float:
        try:
            if isinstance(value, bool):
                return float(int(value))
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Could not parse {label}.") from exc

    def _as_int(value: Any, label: str) -> int:
        try:
            if isinstance(value, bool):
                return int(value)
            if value is None or value == "":
                raise ValueError(f"Missing {label}.")
            return int(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Could not parse {label}.") from exc

    try:
        set_extent_mode = _as_int(set_extent_mode_raw, "set_extent_mode")
        if set_extent_mode not in (0, 1, 2, 3):
            raise ValueError("set_extent_mode must be 0, 1, 2, or 3.")

        map_object = None
        extent = None
        center = None
        zoom = None
        if set_extent_mode == 2:
            if map_object_raw in (None, ""):
                raise ValueError("map_object is required when set_extent_mode is 2.")
            map_object = Map.from_payload(map_object_raw)
            center = _as_float_sequence(map_object.center, 2, "center")
            extent = _as_float_sequence(map_object.extent, 4, "bounds")
            zoom = _as_float(map_object.zoom, "zoom")
        elif set_extent_mode == 3:
            if center_raw not in (None, ""):
                center = _as_float_sequence(center_raw, 2, "center")
            if bounds_raw not in (None, ""):
                extent = _as_float_sequence(bounds_raw, 4, "bounds")
            if zoom_raw not in (None, ""):
                zoom = _as_float(zoom_raw, "zoom")
        else:
            if center_raw is None or zoom_raw is None or bounds_raw is None:
                return (
                    error_response(
                        "Expecting center, zoom, bounds, mcl, and csa",
                        status_code=400,
                    ),
                    None,
                )
            center = _as_float_sequence(center_raw, 2, "center")
            extent = _as_float_sequence(bounds_raw, 4, "bounds")
            zoom = _as_float(zoom_raw, "zoom")

        if mcl_raw is None or csa_raw is None:
            return (
                error_response("Expecting mcl and csa", status_code=400),
                None,
            )

        mcl = _as_float(mcl_raw, "mcl")
        csa = _as_float(csa_raw, "csa")

        if extent is not None:
            l, b, r, t = extent
            if not (l < r and b < t):
                raise ValueError("Invalid bounds ordering.")

        if isinstance(wbt_fill_or_breach_raw, (list, tuple)):
            wbt_fill_or_breach = next(
                (str(item) for item in wbt_fill_or_breach_raw if item not in (None, "")),
                None,
            )
        elif wbt_fill_or_breach_raw in (None, ""):
            wbt_fill_or_breach = None
        else:
            wbt_fill_or_breach = str(wbt_fill_or_breach_raw)

        if wbt_blc_dist_raw in (None, "", []):
            wbt_blc_dist = None
        elif isinstance(wbt_blc_dist_raw, (list, tuple)):
            wbt_blc_dist = _as_int(wbt_blc_dist_raw[0], "wbt_blc_dist")
        else:
            wbt_blc_dist = _as_int(wbt_blc_dist_raw, "wbt_blc_dist")

        if isinstance(map_bounds_text_raw, (list, tuple)):
            map_bounds_text_candidates = [
                item for item in map_bounds_text_raw if item not in (None, "")
            ]
            map_bounds_text = (
                str(map_bounds_text_candidates[0]) if map_bounds_text_candidates else ""
            )
        else:
            map_bounds_text = str(map_bounds_text_raw or "")
        if set_extent_mode in (2, 3) and map_bounds_text == "" and extent is not None:
            map_bounds_text = ", ".join([str(v) for v in extent])
    except ValueError as exc:
        return error_response(str(exc), status_code=400), None

    return (
        None,
        [
            extent,
            center,
            zoom,
            mcl,
            csa,
            wbt_fill_or_breach,
            wbt_blc_dist,
            set_extent_mode,
            map_bounds_text,
            map_object,
        ],
    )


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _require_spatial_reference(ds: gdal.Dataset) -> osr.SpatialReference:
    wkt = ds.GetProjection()
    if not wkt:
        raise UploadError("DEM is missing a spatial reference.")
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def _validate_dem_dimensions(ds: gdal.Dataset) -> None:
    if ds.RasterXSize > UPLOAD_DEM_MAX_DIMENSION or ds.RasterYSize > UPLOAD_DEM_MAX_DIMENSION:
        raise UploadError(
            f"DEM must be {UPLOAD_DEM_MAX_DIMENSION}x{UPLOAD_DEM_MAX_DIMENSION} pixels or smaller."
        )


def _ensure_square_pixels(transform: tuple[float, ...]) -> float:
    if transform is None or len(transform) != 6:
        raise UploadError("DEM geotransform is missing.")
    if not math.isclose(transform[2], 0.0, rel_tol=0.0, abs_tol=1.0e-9) or not math.isclose(
        transform[4], 0.0, rel_tol=0.0, abs_tol=1.0e-9
    ):
        raise UploadError("DEM must be north-up with no rotation.")
    cellsize_x = abs(transform[1])
    cellsize_y = abs(transform[5])
    if cellsize_x <= 0 or cellsize_y <= 0:
        raise UploadError("DEM pixel size must be positive.")
    if not math.isclose(cellsize_x, cellsize_y, rel_tol=0.0, abs_tol=1.0e-6):
        raise UploadError("DEM pixels must be square (equal x/y resolution).")
    return float(cellsize_x)


def _validate_float_dem(dem_path: Path) -> None:
    ds = gdal.Open(str(dem_path))
    if ds is None:
        raise UploadError("Unable to read uploaded DEM.")
    try:
        band = ds.GetRasterBand(1)
        dtype = gdal.GetDataTypeName(band.DataType) if band is not None else ""
        if "float" not in dtype.lower():
            raise UploadError(
                f"DEM must be floating point (Float32/Float64). Detected {dtype or 'unknown'}."
            )
    finally:
        ds = None


def _top_left_wgs(srs: osr.SpatialReference, transform: tuple[float, ...]) -> tuple[float, float]:
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transformer = osr.CoordinateTransformation(srs, wgs)
    lon, lat, _ = transformer.TransformPoint(transform[0], transform[3])
    return float(lon), float(lat)


def _utm_hint_from_srs(srs: osr.SpatialReference) -> tuple[int | None, bool | None]:
    zone = srs.GetUTMZone()
    if zone:
        return abs(zone), zone > 0
    code = srs.GetAuthorityCode("PROJCS") or srs.GetAuthorityCode(None)
    if code and str(code).isdigit():
        epsg = int(code)
        if 32601 <= epsg <= 32660:
            return epsg - 32600, True
        if 32701 <= epsg <= 32760:
            return epsg - 32700, False
        if 26901 <= epsg <= 26960:
            return epsg - 26900, True
        if 26701 <= epsg <= 26760:
            return epsg - 26700, True
        if 25801 <= epsg <= 25860:
            return epsg - 25800, True
    return None, None


def _normalize_utm_projcs(
    srs: osr.SpatialReference,
    zone_number: int,
    northern: bool,
) -> osr.SpatialReference:
    projcs = srs.GetAttrValue("projcs") or ""
    projcs_compact = projcs.replace(" ", "").replace("_", "")
    if "UTM" in projcs_compact:
        return srs
    adjusted = srs.Clone()
    hemisphere = "N" if northern else "S"
    datum_raw = (adjusted.GetAttrValue("DATUM") or "").upper()
    datum_compact = datum_raw.replace(" ", "").replace("_", "")
    datum_label = None
    if "NAD83" in datum_compact or "NAD1983" in datum_compact:
        datum_label = "NAD83"
    elif "NAD27" in datum_compact or "NAD1927" in datum_compact:
        datum_label = "NAD27"
    elif "WGS84" in datum_compact or "WGS1984" in datum_compact:
        datum_label = "WGS84"
    if datum_label:
        projcs_name = f"{datum_label} / UTM zone {zone_number}{hemisphere}"
    else:
        projcs_name = f"UTM zone {zone_number}{hemisphere}"
    adjusted.SetProjCS(projcs_name)
    return adjusted


def _install_uploaded_dem(
    *,
    ron: Ron,
    watershed: Watershed,
    saved_path: Path,
) -> dict[str, Any]:
    ds = gdal.Open(str(saved_path))
    if ds is None:
        raise UploadError("Unable to read uploaded DEM.")

    try:
        _validate_dem_dimensions(ds)
        srs = _require_spatial_reference(ds)
        transform = ds.GetGeoTransform()
        if transform is None or len(transform) != 6:
            raise UploadError("DEM geotransform is missing.")
        utm_zone, utm_northern = _utm_hint_from_srs(srs)
    finally:
        ds = None

    dem_path = saved_path
    utm_srs = None
    if utm_zone is not None and utm_northern is not None:
        ds = gdal.Open(str(saved_path))
        if ds is None:
            raise UploadError("Unable to read uploaded DEM.")
        try:
            transform = ds.GetGeoTransform()
            cellsize = _ensure_square_pixels(transform)
        finally:
            ds = None
        utm_srs = _normalize_utm_projcs(srs, utm_zone, utm_northern)
    else:
        lon, lat = _top_left_wgs(srs, transform)
        _, _, zone_number, _ = utm.from_latlon(lat, lon)
        epsg = utm_srid(zone_number, lat >= 0)
        dem_path = saved_path.with_name(f"{saved_path.stem}_utm.tif")
        if dem_path.exists():
            dem_path.unlink()
        warp_options = gdal.WarpOptions(
            dstSRS=f"EPSG:{epsg}",
            resampleAlg="bilinear",
        )
        warped = gdal.Warp(str(dem_path), str(saved_path), options=warp_options)
        if warped is None:
            raise UploadError("Failed to warp DEM to UTM.")
        warped = None

        ds = gdal.Open(str(dem_path))
        if ds is None:
            raise UploadError("Unable to read warped DEM.")
        try:
            _validate_dem_dimensions(ds)
            transform = ds.GetGeoTransform()
            cellsize = _ensure_square_pixels(transform)
            warped_srs = _require_spatial_reference(ds)
            warped_zone, warped_northern = _utm_hint_from_srs(warped_srs)
            if warped_zone is None or warped_northern is None:
                raise UploadError("Unable to determine UTM zone after warp.")
            utm_srs = _normalize_utm_projcs(warped_srs, warped_zone, warped_northern)
        finally:
            ds = None

    _validate_float_dem(dem_path)
    rdi = RasterDatasetInterpolator(str(dem_path))
    extent = list(rdi.extent)
    center = [(extent[0] + extent[2]) / 2.0, (extent[1] + extent[3]) / 2.0]
    zoom = getattr(ron, "_zoom0", None)
    zoom = int(zoom) if isinstance(zoom, int) else 11

    map_payload = {
        "extent": extent,
        "center": center,
        "zoom": float(zoom),
        "cellsize": float(cellsize),
        "utm": {
            "py/tuple": [
                float(rdi.left),
                float(rdi.upper),
                int(rdi.utm_n),
                str(rdi.utm_h),
            ]
        },
        "_ul_x": float(rdi.left),
        "_ul_y": float(rdi.upper),
        "_lr_x": float(rdi.right),
        "_lr_y": float(rdi.lower),
        "_num_cols": int(rdi.width),
        "_num_rows": int(rdi.height),
    }
    map_object = Map.from_payload(map_payload, default_cellsize=cellsize)

    vrt_path = Path(ron.dem_dir) / "dem.vrt"
    if vrt_path.exists():
        vrt_path.unlink()
    translate_options = {}
    if utm_srs is not None:
        translate_options["outputSRS"] = utm_srs.ExportToWkt()
    vrt_ds = gdal.Translate(str(vrt_path), str(dem_path), format="VRT", **translate_options)
    if vrt_ds is None or not vrt_path.exists():
        raise UploadError("Failed to create DEM VRT.")
    vrt_ds = None

    with ron.locked():
        ron._cellsize = float(cellsize)
        ron._map = map_object
        ron._w3w = None
        ron._dem_is_vrt = True

    with watershed.locked():
        watershed._uploaded_dem_filename = saved_path.name
        watershed._set_extent_mode = 3

    try:
        prep = RedisPrep.getInstance(ron.wd)
        prep.timestamp(TaskEnum.fetch_dem)
    except FileNotFoundError:
        pass

    return {
        "dem_filename": saved_path.name,
        "extent": extent,
        "center": center,
        "zoom": float(zoom),
        "cellsize": float(cellsize),
        "map_object": map_object.to_payload(),
    }


@router.post(
    "/runs/{runid}/{config}/tasks/upload-dem/",
    summary="Upload and validate DEM",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously uploads/validates DEM content and updates watershed map metadata; no queue enqueue."
    ),
    tags=["rq-engine", "uploads"],
    operation_id=rq_operation_id("upload_dem"),
    responses=agent_route_responses(
        success_code=200,
        success_description="DEM upload accepted and watershed DEM metadata updated.",
        extra={
            400: "DEM upload or validation failed. Returns the canonical error payload.",
        },
    ),
)
async def upload_dem(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-dem auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _preflight_watershed_mutation_root(wd)

        form = await request.form()
        upload = _extract_upload(form, "input_upload_dem")
        if upload is None or not upload.filename:
            return upload_failure("input_upload_dem must be provided")

        filename = secure_filename(upload.filename)
        if not filename:
            return upload_failure("input_upload_dem must have a valid filename")

        def _mutate_upload_dem():
            ron = Ron.getInstance(wd)
            watershed = Watershed.getInstance(wd)
            saved_path = save_upload_file(
                upload,
                allowed_extensions=UPLOAD_DEM_ALLOWED_EXTENSIONS,
                dest_dir=Path(ron.dem_dir),
                filename_transform=lambda value: filename,
                overwrite=True,
            )
            return _install_uploaded_dem(
                ron=ron,
                watershed=watershed,
                saved_path=saved_path,
            )

        result = _run_with_watershed_lock(
            wd,
            _mutate_upload_dem,
            purpose="rq-upload-dem",
        )
        return upload_success(result=result)
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-dem failed")
        return error_response_with_traceback("Failed validating DEM", status_code=500)


@router.post(
    "/runs/{runid}/{config}/fetch-dem-and-build-channels",
    summary="Fetch DEM and build channels",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates watershed delineation settings and, outside batch mode, asynchronously enqueues DEM/channel processing."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("fetch_dem_and_build_channels"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Watershed inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Watershed map/change validation failed. Returns the canonical error payload.",
        },
    ),
)
async def fetch_dem_and_build_channels(
    runid: str, config: str, request: Request
) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine channel delineation auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(request)
        error, args = _parse_map_change(payload)
        if error is not None:
            return error

        (
            extent,
            center,
            zoom,
            mcl,
            csa,
            wbt_fill_or_breach,
            wbt_blc_dist,
            set_extent_mode,
            map_bounds_text,
            map_object,
        ) = args

        wd = get_wd(runid)
        _preflight_watershed_mutation_root(wd)
        watershed = Watershed.getInstance(wd)
        if watershed.run_group == "batch" or _is_base_project_context(runid, config):
            with watershed.locked():
                watershed._mcl = mcl
                watershed._csa = csa
                watershed._set_extent_mode = int(set_extent_mode)
                watershed._map_bounds_text = map_bounds_text
                if watershed.delineation_backend_is_wbt:
                    if wbt_fill_or_breach is not None:
                        watershed._wbt_fill_or_breach = wbt_fill_or_breach
                    if wbt_blc_dist is not None:
                        watershed._wbt_blc_dist = wbt_blc_dist

            if map_object is not None:
                ron = Ron.getInstance(wd)
                ron.set_map_object(map_object)

            return JSONResponse({"message": "Set watershed inputs for batch processing"})

        prep = RedisPrep.getInstance(wd)
        if int(set_extent_mode) != 3:
            prep.remove_timestamp(TaskEnum.fetch_dem)
        prep.remove_timestamp(TaskEnum.build_channels)

        if int(set_extent_mode) == 3:
            ron = Ron.getInstance(wd)
            if ron.map is None or not ron.has_dem:
                return error_response(
                    "Upload DEM mode requires a validated DEM upload.",
                    status_code=400,
                )

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                fetch_dem_and_build_channels_rq,
                (
                    runid,
                    extent,
                    center,
                    zoom,
                    csa,
                    mcl,
                    wbt_fill_or_breach,
                    wbt_blc_dist,
                    set_extent_mode,
                    map_bounds_text,
                    map_object,
                ),
                timeout=FETCH_DEM_AND_BUILD_CHANNELS_TIMEOUT,
            )
            prep.set_rq_job_id("fetch_dem_and_build_channels_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except MinimumChannelLengthTooShortError as exc:
        return error_response(
            exc.__class__.__name__ or "Minimum Channel Length TooShort Error",
            status_code=400,
            details=exc.__doc__,
        )
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine channel delineation enqueue failed")
        return error_response_with_traceback("fetch_dem_and_build_channels Failed")


@router.post(
    "/runs/{runid}/{config}/set-outlet",
    summary="Set watershed outlet",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates outlet coordinates and asynchronously enqueues outlet-setting work."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("set_outlet"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Outlet job accepted and `job_id` returned.",
        extra={
            400: "Outlet coordinates were invalid. Returns the canonical error payload.",
        },
    ),
)
async def set_outlet(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine set-outlet auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    payload = await parse_request_payload(request)

    def _resolve_coordinate(key: str) -> Any:
        value = payload.get(key)
        if value is not None:
            return value
        coordinates = payload.get("coordinates")
        if isinstance(coordinates, dict):
            if key in coordinates:
                return coordinates[key]
            if key == "latitude":
                return coordinates.get("lat")
            if key == "longitude":
                return coordinates.get("lng") or coordinates.get("lon")
        return None

    def _to_float(value: Any) -> float:
        if value is None:
            raise ValueError("missing coordinate")
        if isinstance(value, (list, tuple)):
            if not value:
                raise ValueError("missing coordinate")
            return _to_float(value[0])
        return float(value)

    try:
        outlet_lng = _to_float(_resolve_coordinate("longitude"))
        outlet_lat = _to_float(_resolve_coordinate("latitude"))
    except (TypeError, ValueError):
        return error_response(
            "latitude and longitude must be provided as floats",
            status_code=400,
        )

    try:
        wd = get_wd(runid)
        _preflight_watershed_mutation_root(wd)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.set_outlet)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                set_outlet_rq,
                (runid, outlet_lng, outlet_lat),
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("set_outlet_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine set-outlet enqueue failed")
        return error_response_with_traceback("Could not set outlet")


@router.post(
    "/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed",
    summary="Build subcatchments and abstract watershed",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates watershed abstraction options and, outside batch mode, asynchronously enqueues abstraction work."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_subcatchments_and_abstract_watershed"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Watershed abstraction inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Watershed abstraction validation/business rule failed. Returns the canonical error payload.",
        },
    ),
)
async def build_subcatchments_and_abstract_watershed(
    runid: str, config: str, request: Request
) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine subcatchments auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    payload = await parse_request_payload(
        request,
        boolean_fields=(
            "clip_hillslopes",
            "walk_flowpaths",
            "mofe_buffer",
            "bieger2015_widths",
        ),
    )

    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return _to_float(value[0] if value else None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_bool(value: Any, default: bool | None = None) -> bool | None:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def _apply_watershed_updates(target: Watershed, updates: dict[str, Any]) -> None:
        if not updates:
            return
        if "clip_hillslopes" in updates:
            target.clip_hillslopes = bool(updates["clip_hillslopes"])
        if "walk_flowpaths" in updates:
            target.walk_flowpaths = bool(updates["walk_flowpaths"])
        if "clip_hillslope_length" in updates:
            target.clip_hillslope_length = float(updates["clip_hillslope_length"])
        if "mofe_target_length" in updates:
            target.mofe_target_length = float(updates["mofe_target_length"])
        if "mofe_buffer" in updates:
            target.mofe_buffer = bool(updates["mofe_buffer"])
        if "mofe_buffer_length" in updates:
            target.mofe_buffer_length = float(updates["mofe_buffer_length"])
        if "bieger2015_widths" in updates:
            target.bieger2015_widths = bool(updates["bieger2015_widths"])

    try:
        wd = get_wd(runid)
        _preflight_watershed_mutation_root(wd)
        watershed = Watershed.getInstance(wd)

        updates: dict[str, Any] = {}
        if "clip_hillslopes" in payload:
            value = _to_bool(payload.get("clip_hillslopes"))
            if value is not None:
                updates["clip_hillslopes"] = value

        if "walk_flowpaths" in payload:
            value = _to_bool(payload.get("walk_flowpaths"))
            if value is not None:
                updates["walk_flowpaths"] = value

        if "clip_hillslope_length" in payload:
            value = _to_float(payload.get("clip_hillslope_length"))
            if value is not None:
                updates["clip_hillslope_length"] = value

        if "mofe_target_length" in payload:
            value = _to_float(payload.get("mofe_target_length"))
            if value is not None:
                updates["mofe_target_length"] = value

        if "mofe_buffer" in payload:
            value = _to_bool(payload.get("mofe_buffer"))
            if value is not None:
                updates["mofe_buffer"] = value

        if "mofe_buffer_length" in payload:
            value = _to_float(payload.get("mofe_buffer_length"))
            if value is not None:
                updates["mofe_buffer_length"] = value

        if "bieger2015_widths" in payload:
            value = _to_bool(payload.get("bieger2015_widths"))
            if value is not None:
                updates["bieger2015_widths"] = value

        if watershed.run_group == "batch" or _is_base_project_context(runid, config):
            _apply_watershed_updates(watershed, updates)
            return JSONResponse({"message": "Set subcatchment inputs for batch processing"})

        _apply_watershed_updates(watershed, updates)

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.abstract_watershed)
        prep.remove_timestamp(TaskEnum.build_subcatchments)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                build_subcatchments_and_abstract_watershed_rq,
                (runid,),
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("build_subcatchments_and_abstract_watershed_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except WatershedBoundaryTouchesEdgeError as exc:
        return error_response(
            exc.__class__.__name__ or "Watershed Boundary Touches Edge Error",
            status_code=400,
            details=exc.__doc__,
        )
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine subcatchments enqueue failed")
        return error_response_with_traceback("Building Subcatchments Failed")


__all__ = ["router"]
