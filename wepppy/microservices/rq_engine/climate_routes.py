from __future__ import annotations

import copy
import logging
import os
import re

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import (
    Climate,
    ClimateMode,
    ClimateModeIsUndefinedError,
    NoClimateStationSelectedError,
    WatershedNotAbstractedError,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import build_climate_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback, validation_error_response

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
_OBSERVED_YEAR_REQUIRED_MODES = frozenset(
    (
        ClimateMode.Observed,
        ClimateMode.ObservedPRISM,
        ClimateMode.GridMetPRISM,
        ClimateMode.DepNexrad,
    )
)
_FUTURE_YEAR_REQUIRED_MODES = frozenset((ClimateMode.Future,))
_CLIMATE_YEAR_MAX_SPAN = 1000
_OBSERVED_YEAR_MIN = 1980
_FUTURE_YEAR_MIN = 2006
_FUTURE_YEAR_MAX = 2099
_CLIMATE_FIELD_LABELS = {
    "observed_start_year": "Observed start year",
    "observed_end_year": "Observed end year",
    "future_start_year": "Future start year",
    "future_end_year": "Future end year",
}
_OBSERVED_INTEGER_YEAR_MESSAGE_RE = re.compile(
    r"^(observed_(?:start|end)_year) must be an integer year, got (?P<raw>.+)$"
)
_OBSERVED_ORDER_MESSAGE_RE = re.compile(
    r"^observed_end_year must be greater than or equal to observed_start_year "
    r"\((?P<end>-?\d+) < (?P<start>-?\d+)\)$"
)


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


def _build_climate_validation_errors(
    exc: Exception,
    *,
    payload: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    message = str(exc).strip()

    if isinstance(exc, KeyError):
        missing_field = str(exc.args[0]).strip().strip("'\"")
        if missing_field:
            return [
                {
                    "field": missing_field,
                    "code": "missing_required_field",
                    "message": f"{_field_label(missing_field)} is required.",
                }
            ]

    prefix = "Missing required climate field(s):"
    if message.startswith(prefix):
        field_list = message[len(prefix) :].strip()
        fields = [field.strip() for field in field_list.split(",") if field.strip()]
        if fields:
            return [
                {
                    "field": field,
                    "code": "missing_required_field",
                    "message": f"{_field_label(field)} is required.",
                }
                for field in fields
            ]

    observed_integer_match = _OBSERVED_INTEGER_YEAR_MESSAGE_RE.match(message)
    if observed_integer_match:
        field = observed_integer_match.group(1)
        raw_value = observed_integer_match.group("raw")
        if raw_value == "empty string":
            return [_validation_issue(field=field, code="missing_required_field", message=f"{_field_label(field)} is required.")]
        return [
            _validation_issue(
                field=field,
                code="invalid_year",
                message=(
                    f"{_field_label(field)} must be a whole-number year "
                    f"(received {raw_value})."
                ),
            )
        ]

    observed_order_match = _OBSERVED_ORDER_MESSAGE_RE.match(message)
    if observed_order_match:
        received_end = observed_order_match.group("end")
        received_start = observed_order_match.group("start")
        return [
            _validation_issue(
                field="observed_end_year",
                code="year_order",
                message=(
                    "Observed end year must be greater than or equal to observed start year "
                    f"(received {received_end} < {received_start})."
                ),
            )
        ]

    inferred_errors = _infer_year_validation_errors_from_payload(payload=payload)
    if inferred_errors:
        return inferred_errors

    return [
        {
            "code": "invalid_request",
            "message": "Invalid climate field values.",
        }
    ]


def _field_label(field_name: str) -> str:
    return _CLIMATE_FIELD_LABELS.get(field_name, field_name.replace("_", " ").capitalize())


def _validation_issue(*, code: str, message: str, field: str | None = None) -> dict[str, str]:
    issue: dict[str, str] = {"code": code, "message": message}
    if field:
        issue["field"] = field
    return issue


def _payload_value(payload: dict[str, object], field_name: str) -> object:
    value = payload.get(field_name)
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        return value[-1]
    return value


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _has_value(value: object) -> bool:
    return not _is_blank(value)


def _parse_payload_year(value: object, *, field_name: str) -> tuple[int | None, dict[str, str] | None]:
    label = _field_label(field_name)
    if _is_blank(value):
        return None, _validation_issue(field=field_name, code="missing_required_field", message=f"{label} is required.")
    if isinstance(value, bool):
        return (
            None,
            _validation_issue(
                field=field_name,
                code="invalid_year",
                message=f"{label} must be a whole-number year (received {value!r}).",
            ),
        )
    try:
        return int(value), None
    except (TypeError, ValueError):
        return (
            None,
            _validation_issue(
                field=field_name,
                code="invalid_year",
                message=f"{label} must be a whole-number year (received {value!r}).",
            ),
        )


def _validate_year_pair_from_payload(
    payload: dict[str, object],
    *,
    start_field: str,
    end_field: str,
    min_year: int,
    max_year: int | None,
) -> list[dict[str, str]]:
    start_raw = _payload_value(payload, start_field)
    end_raw = _payload_value(payload, end_field)
    start_label = _field_label(start_field)
    end_label = _field_label(end_field)

    if _is_blank(start_raw) and _is_blank(end_raw):
        return []

    if _is_blank(start_raw) and _has_value(end_raw):
        return [
            _validation_issue(
                field=start_field,
                code="missing_required_field",
                message=f"{start_label} is required when {end_label} is provided.",
            )
        ]
    if _is_blank(end_raw) and _has_value(start_raw):
        return [
            _validation_issue(
                field=end_field,
                code="missing_required_field",
                message=f"{end_label} is required when {start_label} is provided.",
            )
        ]

    start_year, start_issue = _parse_payload_year(start_raw, field_name=start_field)
    end_year, end_issue = _parse_payload_year(end_raw, field_name=end_field)
    issues = [issue for issue in (start_issue, end_issue) if issue is not None]
    if issues:
        return issues
    assert start_year is not None and end_year is not None

    if start_year < min_year:
        return [
            _validation_issue(
                field=start_field,
                code="year_out_of_range",
                message=f"{start_label} must be {min_year} or later.",
            )
        ]
    if max_year is not None and start_year > max_year:
        return [
            _validation_issue(
                field=start_field,
                code="year_out_of_range",
                message=f"{start_label} must be between {min_year} and {max_year}.",
            )
        ]
    if end_year < min_year:
        return [
            _validation_issue(
                field=end_field,
                code="year_out_of_range",
                message=f"{end_label} must be {min_year} or later.",
            )
        ]
    if max_year is not None and end_year > max_year:
        return [
            _validation_issue(
                field=end_field,
                code="year_out_of_range",
                message=f"{end_label} must be between {min_year} and {max_year}.",
            )
        ]
    if end_year < start_year:
        return [
            _validation_issue(
                field=end_field,
                code="year_order",
                message=(
                    f"{end_label} must be greater than or equal to {start_label.lower()} "
                    f"(received {end_year} < {start_year})."
                ),
            )
        ]
    if end_year - start_year > _CLIMATE_YEAR_MAX_SPAN:
        return [
            _validation_issue(
                field=end_field,
                code="year_range_too_large",
                message=(
                    f"The selected year range is too large. "
                    f"Maximum span is {_CLIMATE_YEAR_MAX_SPAN} years."
                ),
            )
        ]
    return []


def _extract_climate_mode(payload: dict[str, object]) -> ClimateMode | None:
    if not payload:
        return None
    raw_value = _payload_value(payload, "climate_mode")
    if _is_blank(raw_value):
        return None
    try:
        return ClimateMode(int(raw_value))
    except (TypeError, ValueError):
        return None


def _infer_year_validation_errors_from_payload(*, payload: dict[str, object] | None) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []

    climate_mode = _extract_climate_mode(payload)

    validate_observed = (
        climate_mode in _OBSERVED_YEAR_REQUIRED_MODES
        or _has_value(_payload_value(payload, "observed_start_year"))
        or _has_value(_payload_value(payload, "observed_end_year"))
    )
    if validate_observed:
        observed_issues = _validate_year_pair_from_payload(
            payload,
            start_field="observed_start_year",
            end_field="observed_end_year",
            min_year=_OBSERVED_YEAR_MIN,
            max_year=None,
        )
        if observed_issues:
            return observed_issues

    validate_future = (
        climate_mode in _FUTURE_YEAR_REQUIRED_MODES
        or _has_value(_payload_value(payload, "future_start_year"))
        or _has_value(_payload_value(payload, "future_end_year"))
    )
    if validate_future:
        future_issues = _validate_year_pair_from_payload(
            payload,
            start_field="future_start_year",
            end_field="future_end_year",
            min_year=_FUTURE_YEAR_MIN,
            max_year=_FUTURE_YEAR_MAX,
        )
        if future_issues:
            return future_issues

    return []


def _validate_observed_year_bounds_before_enqueue(climate: Climate) -> None:
    climate_mode = getattr(climate, "climate_mode", None)
    if climate_mode not in _OBSERVED_YEAR_REQUIRED_MODES:
        return
    with climate.locked():
        climate._require_observed_year_bounds_for_build()


@router.post(
    "/runs/{runid}/{config}/build-climate",
    summary="Build climate inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates climate inputs and, outside batch mode, asynchronously enqueues climate building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_climate"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Climate inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Climate input validation or climate precondition failed. Returns the canonical error payload.",
        },
    ),
)
async def build_climate(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-climate auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    wd = get_wd(runid)
    payload: dict[str, object] = {}

    try:
        _require_directory_root(wd, "climate")
        climate = Climate.getInstance(wd)
        payload = await parse_request_payload(request)
        climate.parse_inputs(payload)
        _validate_observed_year_bounds_before_enqueue(climate)
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.info(
            "rq-engine build-climate validation failed",
            extra={"runid": runid, "config": config, "error": str(exc)},
        )
        return validation_error_response(_build_climate_validation_errors(exc, payload=payload))
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-climate payload parse failed", extra={"runid": runid, "config": config})
        return error_response("Error parsing climate inputs", status_code=400)

    if climate.run_group == "batch":
        return JSONResponse({"message": "Set climate inputs for batch processing"})

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_climate)
        prep.remove_timestamp(TaskEnum.build_rusle)
        prep.remove_timestamp(TaskEnum.run_geneva)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                build_climate_rq,
                (runid,),
                timeout=RQ_TIMEOUT,
                meta={"build_payload": copy.deepcopy(payload)},
            )
            prep.set_rq_job_id("build_climate_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except (
        NoClimateStationSelectedError,
        ClimateModeIsUndefinedError,
        WatershedNotAbstractedError,
    ) as exc:
        return error_response(
            exc.__name__ or "Error building climate",
            status_code=400,
        )
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-climate enqueue failed")
        return error_response_with_traceback("Error building climate")


__all__ = ["router"]
