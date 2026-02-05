from __future__ import annotations

import logging
import os

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.swat import Swat
from wepppy.nodb.mods.swat.print_prt import mask_from_flags
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.swat_rq import run_swat_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]

_PRINT_PRT_META_FIELDS = (
    "nyskip",
    "day_start",
    "yrc_start",
    "day_end",
    "yrc_end",
    "interval",
)


def _parse_int(value: object) -> int | None:
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@router.post("/runs/{runid}/{config}/run-swat")
async def run_swat(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-swat auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        payload = await parse_request_payload(request)

        ron = Ron.getInstance(wd)
        mods = ron.mods or []
        if "swat" in mods:
            swat = Swat.getInstance(wd)
            swat.parse_inputs(payload)

        prep = RedisPrep.getInstance(wd)
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_swat_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("run_swat_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine run-swat enqueue failed")
        return error_response_with_traceback("Error Handling Request")


@router.post("/runs/{runid}/{config}/swat/print-prt")
async def update_swat_print_prt(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine swat print.prt auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        payload = await parse_request_payload(
            request,
            boolean_fields=("daily", "monthly", "yearly", "avann"),
        )
        object_name = payload.get("object") or payload.get("object_name")
        if not object_name:
            return error_response("Missing print.prt object", status_code=400)

        daily = bool(payload.get("daily", False))
        monthly = bool(payload.get("monthly", False))
        yearly = bool(payload.get("yearly", False))
        avann = bool(payload.get("avann", False))
        mask = mask_from_flags(daily=daily, monthly=monthly, yearly=yearly, avann=avann)

        swat = Swat.getInstance(wd)
        with swat.locked():
            if swat.print_prt is None:
                swat.print_prt = swat._load_print_prt_template() or swat.print_prt
                if swat.print_prt_template_dir is None:
                    swat.print_prt_template_dir = swat.template_dir
            if swat.print_prt is None:
                return error_response("print.prt configuration unavailable", status_code=400)
            swat.print_prt.objects.set_mask(str(object_name), mask)
        return JSONResponse(
            {
                "object": str(object_name),
                "daily": daily,
                "monthly": monthly,
                "yearly": yearly,
                "avann": avann,
            }
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine swat print.prt update failed")
        return error_response_with_traceback("Error Handling Request")


@router.post("/runs/{runid}/{config}/swat/print-prt/meta")
async def update_swat_print_prt_meta(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine swat print.prt meta auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        payload = await parse_request_payload(request)

        updates: dict[str, int] = {}
        for key in _PRINT_PRT_META_FIELDS:
            value = _parse_int(payload.get(key))
            if value is not None:
                updates[key] = value

        if not updates:
            return error_response("No print.prt metadata updates supplied", status_code=400)

        swat = Swat.getInstance(wd)
        with swat.locked():
            if swat.print_prt is None:
                swat.print_prt = swat._load_print_prt_template() or swat.print_prt
                if swat.print_prt_template_dir is None:
                    swat.print_prt_template_dir = swat.template_dir
            if swat.print_prt is None:
                return error_response("print.prt configuration unavailable", status_code=400)

            for key, value in updates.items():
                setattr(swat.print_prt, key, int(value))

        return JSONResponse(updates)
    except Exception:
        logger.exception("rq-engine swat print.prt meta update failed")
        return error_response_with_traceback("Error Handling Request")


__all__ = ["router"]
