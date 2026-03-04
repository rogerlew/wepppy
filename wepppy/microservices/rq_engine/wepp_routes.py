from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.swat import Swat
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.wepp_rq import prep_wepp_watershed_rq, run_wepp_rq, run_wepp_watershed_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _is_base_project_context(runid: str, config: str) -> bool:
    runid_leaf = runid.split(";;")[-1].strip().lower() if runid else ""
    config_token = str(config).strip().lower() if config is not None else ""
    return runid_leaf == "_base" or config_token == "_base"


def _pop_scalar(mapping: dict[str, Any], key: str, default: Any = None) -> Any:
    if key not in mapping:
        return default
    value = mapping.pop(key)
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if item not in (None, ""):
                return item
        return default
    return value


def _parse_int(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    if value in (None, "", False):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_swat_channel_params(wd: str, payload: dict[str, Any]) -> None:
    ron = Ron.getInstance(wd)
    mods = ron.mods or []
    if "swat" not in mods:
        return
    swat = Swat.getInstance(wd)
    swat.parse_inputs(payload)


async def _handle_run_wepp_request(
    runid: str,
    config: str,
    request: Request,
    *,
    job_fn,
    job_key: str,
    boolean_fields: set[str],
) -> JSONResponse:
    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        soils = Soils.getInstance(wd)
        watershed = Watershed.getInstance(wd)

        payload = await parse_request_payload(request, boolean_fields=boolean_fields)
        controller_payload: dict[str, Any] = dict(payload)

        clip_soils = bool(_pop_scalar(controller_payload, "clip_soils", False))
        soils.clip_soils = clip_soils

        clip_soils_depth = _parse_int(_pop_scalar(controller_payload, "clip_soils_depth"))
        if clip_soils_depth is not None:
            soils.clip_soils_depth = clip_soils_depth

        clip_hillslopes = bool(_pop_scalar(controller_payload, "clip_hillslopes", False))
        watershed.clip_hillslopes = clip_hillslopes

        clip_hillslope_length = _parse_int(_pop_scalar(controller_payload, "clip_hillslope_length"))
        if clip_hillslope_length is not None:
            watershed.clip_hillslope_length = clip_hillslope_length

        initial_sat = _parse_float(_pop_scalar(controller_payload, "initial_sat"))
        if initial_sat is not None:
            soils.initial_sat = initial_sat

        reveg_scenario = _pop_scalar(controller_payload, "reveg_scenario", None)
        if isinstance(reveg_scenario, str):
            reveg_scenario = reveg_scenario.strip()
        if reveg_scenario is not None:
            from wepppy.nodb.mods.revegetation import Revegetation

            reveg = Revegetation.getInstance(wd)
            reveg.load_cover_transform(reveg_scenario)

        prep_details_on_run_completion = bool(
            _pop_scalar(controller_payload, "prep_details_on_run_completion", False)
        )
        arc_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "arc_export_on_run_completion", False)
        )
        legacy_arc_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "legacy_arc_export_on_run_completion", False)
        )
        dss_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "dss_export_on_run_completion", False)
        )

        dss_export_exclude_orders: list[int] = []
        exclude_orders_supplied = False
        for i in range(1, 6):
            key = f"dss_export_exclude_order_{i}"
            if key not in controller_payload:
                continue
            exclude_orders_supplied = True
            if bool(_pop_scalar(controller_payload, key, False)):
                dss_export_exclude_orders.append(i)
        if not exclude_orders_supplied:
            dss_export_exclude_orders = wepp.dss_excluded_channel_orders

        try:
            wepp.parse_inputs(controller_payload)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)
        except Exception as exc:
            logger.exception("rq-engine run-wepp parse failed")
            return error_response_with_traceback(str(exc))

        _apply_swat_channel_params(wd, controller_payload)

        with wepp.locked():
            wepp._prep_details_on_run_completion = prep_details_on_run_completion
            wepp._arc_export_on_run_completion = arc_export_on_run_completion
            wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion
            wepp._dss_export_on_run_completion = dss_export_on_run_completion
            wepp._dss_excluded_channel_orders = dss_export_exclude_orders
    except Exception:
        logger.exception("rq-engine run-wepp request preparation failed")
        return error_response_with_traceback("Error preparing WEPP run request")
    if getattr(wepp, "run_group", "") == "batch" or _is_base_project_context(runid, config):
        return JSONResponse({"message": "Set wepp inputs for batch processing"})

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)
        prep.remove_timestamp(TaskEnum.run_wepp_watershed)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)
        prep.remove_timestamp(TaskEnum.run_path_cost_effective)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(job_fn, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id(job_key, job.id)
        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine run-wepp enqueue failed")
        return error_response_with_traceback("Error Handling Request")


@router.post(
    "/runs/{runid}/{config}/run-wepp",
    summary="Run WEPP hillslope workflow",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/soil/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues hillslope WEPP."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_wepp"),
    responses=agent_route_responses(
        success_code=200,
        success_description="WEPP inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_wepp(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    boolean_fields = {
        "clip_soils",
        "clip_hillslopes",
        "prep_details_on_run_completion",
        "arc_export_on_run_completion",
        "legacy_arc_export_on_run_completion",
        "dss_export_on_run_completion",
    }
    for i in range(1, 6):
        boolean_fields.add(f"dss_export_exclude_order_{i}")

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=run_wepp_rq,
        job_key="run_wepp_rq",
        boolean_fields=boolean_fields,
    )


@router.post(
    "/runs/{runid}/{config}/run-wepp-watershed",
    summary="Run WEPP watershed workflow",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues watershed WEPP."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_wepp_watershed"),
    responses=agent_route_responses(
        success_code=200,
        success_description=(
            "WEPP watershed inputs accepted; returns batch update message or enqueued `job_id`."
        ),
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_wepp_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp-watershed auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    boolean_fields = {
        "clip_hillslopes",
        "prep_details_on_run_completion",
        "arc_export_on_run_completion",
        "legacy_arc_export_on_run_completion",
        "dss_export_on_run_completion",
    }
    for i in range(1, 6):
        boolean_fields.add(f"dss_export_exclude_order_{i}")

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=run_wepp_watershed_rq,
        job_key="run_wepp_watershed_rq",
        boolean_fields=boolean_fields,
    )


@router.post(
    "/runs/{runid}/{config}/prep-wepp-watershed",
    summary="Prepare WEPP hillslope and watershed inputs only",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/soil/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues prep-only hillslope + watershed input generation."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("prep_wepp_watershed"),
    responses=agent_route_responses(
        success_code=200,
        success_description=(
            "WEPP prep-only inputs accepted; returns batch update message or enqueued `job_id`."
        ),
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def prep_wepp_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine prep-wepp-watershed auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    boolean_fields = {
        "clip_soils",
        "clip_hillslopes",
        "prep_details_on_run_completion",
        "arc_export_on_run_completion",
        "legacy_arc_export_on_run_completion",
        "dss_export_on_run_completion",
    }
    for i in range(1, 6):
        boolean_fields.add(f"dss_export_exclude_order_{i}")

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=prep_wepp_watershed_rq,
        job_key="prep_wepp_watershed_rq",
        boolean_fields=boolean_fields,
    )


__all__ = ["router"]
