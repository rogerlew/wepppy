from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import (
    Map,
    MinimumChannelLengthTooShortError,
    Ron,
    Watershed,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import (
    build_subcatchments_and_abstract_watershed_rq,
    fetch_dem_and_build_channels_rq,
    set_outlet_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


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
        if set_extent_mode not in (0, 1, 2):
            raise ValueError("set_extent_mode must be 0, 1, or 2.")

        map_object = None
        if set_extent_mode == 2:
            if map_object_raw in (None, ""):
                raise ValueError("map_object is required when set_extent_mode is 2.")
            map_object = Map.from_payload(map_object_raw)
            center = _as_float_sequence(map_object.center, 2, "center")
            extent = _as_float_sequence(map_object.extent, 4, "bounds")
            zoom = _as_float(map_object.zoom, "zoom")
        else:
            if (
                center_raw is None
                or zoom_raw is None
                or bounds_raw is None
                or mcl_raw is None
                or csa_raw is None
            ):
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

        mcl = _as_float(mcl_raw, "mcl")
        csa = _as_float(csa_raw, "csa")

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
        if set_extent_mode == 2 and map_bounds_text == "":
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


@router.post("/runs/{runid}/{config}/fetch-dem-and-build-channels")
async def fetch_dem_and_build_channels(
    runid: str, config: str, request: Request
) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
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
        watershed = Watershed.getInstance(wd)
        if watershed.run_group == "batch":
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
        prep.remove_timestamp(TaskEnum.fetch_dem)
        prep.remove_timestamp(TaskEnum.build_channels)

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
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("fetch_dem_and_build_channels_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except MinimumChannelLengthTooShortError as exc:
        return error_response(
            exc.__name__ or "Minimum Channel Length TooShort Error",
            status_code=400,
            details=exc.__doc__,
        )
    except Exception:
        logger.exception("rq-engine channel delineation enqueue failed")
        return error_response_with_traceback("fetch_dem_and_build_channels Failed")


@router.post("/runs/{runid}/{config}/set-outlet")
async def set_outlet(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
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
    except Exception:
        logger.exception("rq-engine set-outlet enqueue failed")
        return error_response_with_traceback("Could not set outlet")


@router.post("/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed")
async def build_subcatchments_and_abstract_watershed(
    runid: str, config: str, request: Request
) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
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

        if watershed.run_group == "batch":
            _apply_watershed_updates(watershed, updates)
            return JSONResponse({"message": "Set watershed inputs for batch processing"})

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
            exc.__name__ or "Watershed Boundary Touches Edge Error",
            status_code=400,
            details=exc.__doc__,
        )
    except Exception:
        logger.exception("rq-engine subcatchments enqueue failed")
        return error_response_with_traceback("Building Subcatchments Failed")


__all__ = ["router"]
