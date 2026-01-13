from __future__ import annotations

import logging
import os
from typing import Any, Iterable

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Watershed, Wepp
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.wepp_rq import post_dss_export_rq
from wepppy.topo.peridot.flowpath import PeridotChannel
from wepppy.wepp.interchange.dss_dates import format_dss_date, parse_dss_date
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _safe_int(value: Any) -> int | None:
    try:
        candidate = int(str(value))
    except (TypeError, ValueError):
        return None
    return candidate


def _dedupe_positive_ints(values: Iterable[Any]) -> list[int]:
    seen: set[int] = set()
    cleaned: list[int] = []
    for raw in values:
        numeric = _safe_int(raw)
        if numeric is None or numeric <= 0 or numeric in seen:
            continue
        seen.add(numeric)
        cleaned.append(numeric)
    return cleaned


@router.post("/runs/{runid}/{config}/post-dss-export-rq")
async def post_dss_export(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine post-dss-export auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        boolean_fields = {f"dss_export_exclude_order_{i}" for i in range(1, 6)}
        payload = await parse_request_payload(request, boolean_fields=boolean_fields)

        def _coerce_int_list(raw_value: Any) -> list[int]:
            if raw_value in (None, "", []):
                return []
            if isinstance(raw_value, (list, tuple, set)):
                iterable = raw_value
            else:
                iterable = str(raw_value).split(",")
            seen: set[int] = set()
            result: list[int] = []
            for item in iterable:
                if item in (None, ""):
                    continue
                try:
                    parsed = int(str(item).strip())
                except (TypeError, ValueError):
                    continue
                if parsed not in seen:
                    seen.add(parsed)
                    result.append(parsed)
            return result

        def _first_value(raw_value: Any) -> Any:
            if isinstance(raw_value, (list, tuple, set)):
                for candidate in raw_value:
                    if candidate not in (None, ""):
                        return candidate
                return None
            return raw_value

        raw_mode = payload.get("dss_export_mode")
        try:
            dss_export_mode = int(raw_mode) if raw_mode not in (None, "") else None
        except (TypeError, ValueError):
            dss_export_mode = None
        if dss_export_mode not in (None, 1, 2):
            dss_export_mode = None

        exclude_orders_payload = payload.get("dss_export_exclude_orders")
        if exclude_orders_payload is not None:
            dss_excluded_channel_orders = [
                order for order in _coerce_int_list(exclude_orders_payload) if 1 <= order <= 5
            ]
        else:
            dss_excluded_channel_orders = [
                order
                for order in range(1, 6)
                if payload.get(f"dss_export_exclude_order_{order}")
            ]

        dss_export_channel_ids_payload = payload.get("dss_export_channel_ids")
        if isinstance(dss_export_channel_ids_payload, dict):
            dss_export_channel_ids: list[int] = []
        else:
            dss_export_channel_ids = _coerce_int_list(dss_export_channel_ids_payload)

        if dss_export_mode == 2:
            watershed = Watershed.getInstance(wd)
            dss_export_channel_ids = []
            for chn_id, chn_summary in watershed.chns_summary.items():
                if isinstance(chn_summary, PeridotChannel):
                    order = int(chn_summary.order)
                else:
                    order = int(chn_summary["order"])
                if order in dss_excluded_channel_orders:
                    continue
                dss_export_channel_ids.append(int(chn_id))

        dss_export_channel_ids = _dedupe_positive_ints(dss_export_channel_ids)

        try:
            start_date = parse_dss_date(_first_value(payload.get("dss_start_date")))
        except ValueError:
            return error_response(
                "Invalid DSS start date; use MM/DD/YYYY.",
                status_code=400,
            )

        try:
            end_date = parse_dss_date(_first_value(payload.get("dss_end_date")))
        except ValueError:
            return error_response(
                "Invalid DSS end date; use MM/DD/YYYY.",
                status_code=400,
            )

        if start_date and end_date and start_date > end_date:
            return error_response(
                "DSS start date must be on or before the end date.",
                status_code=400,
            )

        with wepp.locked():
            if dss_export_mode is not None:
                wepp._dss_export_mode = dss_export_mode
            wepp._dss_excluded_channel_orders = dss_excluded_channel_orders
            wepp._dss_export_channel_ids = dss_export_channel_ids
            wepp._dss_start_date = format_dss_date(start_date)
            wepp._dss_end_date = format_dss_date(end_date)

        prep = RedisPrep.getInstance(wd)
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(post_dss_export_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("post_dss_export_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine post-dss-export enqueue failed")
        return error_response_with_traceback("Error Handling Request")


__all__ = ["router"]
