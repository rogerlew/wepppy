from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron, Soils, SoilsMode, WatershedNotAbstractedError
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    LocaleAuthorityInvalidError,
    soil_capability_modes,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import build_soils_rq
from wepppy.rq.submission_recovery import RqSubmissionConflict, enqueue_tracked_rq_job
from wepppy.soils.ssurgo import NoValidSoilsException
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _soil_modes_or_error(
    soils: Soils,
) -> tuple[frozenset[int] | None, JSONResponse | None]:
    try:
        return soil_capability_modes(soils), None
    except LocaleAuthorityInvalidError as exc:
        return None, error_response(
            "Run locale authority is invalid.",
            status_code=409,
            code="locale_authority_invalid",
            details=str(exc),
        )
    except BuilderRegistryUnavailableError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return None, response
    except ValueError as exc:
        return None, error_response(
            "Project capability authority is invalid.",
            status_code=409,
            code="capability_authority_invalid",
            details=str(exc),
        )
    return None, None


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


def _to_float(value: Any) -> float:
    if value is None:
        raise ValueError("missing")
    if isinstance(value, (list, tuple)):
        if not value:
            raise ValueError("missing")
        return _to_float(value[0])
    return float(value)


def _first(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _normalize_config_token(value: str) -> str:
    token = str(value or "").strip().lower()
    return token[:-4] if token.endswith(".cfg") else token


def _config_mismatch_response(wd: str, config: str) -> JSONResponse | None:
    """Reject a mismatched mutable run/config route before any state change."""
    actual_config = _normalize_config_token(getattr(Ron.getInstance(wd), "config_stem", ""))
    requested_config = _normalize_config_token(config)
    if requested_config and actual_config and requested_config != actual_config:
        return error_response(
            f"Run config mismatch: path config '{config}' does not match run config '{actual_config}'.",
            status_code=409,
            code="run_config_mismatch",
        )
    return None


@router.post(
    "/runs/{runid}/{config}/build-soils",
    summary="Build soils inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates soils settings and, outside batch mode, asynchronously enqueues soils building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_soils"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Soils inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Soils validation or precondition failed. Returns the canonical error payload.",
            409: "Run config or project capability/locale authority conflict; no mutation.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
async def build_soils(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-soils auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _require_directory_root(wd, "soils")

        mismatch_response = _config_mismatch_response(wd, config)
        if mismatch_response is not None:
            return mismatch_response

        payload = await parse_request_payload(
            request,
            boolean_fields={"clear_ssurgo_cache_on_rebuild"},
        )
        try:
            initial_sat = _to_float(payload.get("initial_sat"))
        except (TypeError, ValueError):
            return error_response("initial_sat must be numeric", status_code=400)

        soils = Soils.getInstance(wd)
        allowed_modes, authority_error = _soil_modes_or_error(soils)
        if authority_error is not None:
            return authority_error
        soil_mode_raw = _first(payload.get("soil_mode"))
        mode_alias_raw = _first(payload.get("mode"))
        requested_mode = None
        if soil_mode_raw is not None or mode_alias_raw is not None:
            try:
                soil_mode = SoilsMode(int(soil_mode_raw)) if soil_mode_raw is not None else None
                mode_alias = SoilsMode(int(mode_alias_raw)) if mode_alias_raw is not None else None
            except (TypeError, ValueError):
                return error_response("Invalid soil mode", status_code=400)
            if soil_mode is not None and mode_alias is not None and soil_mode != mode_alias:
                return error_response(
                    "soil_mode and mode must identify the same soil builder",
                    status_code=400,
                )
            requested_mode = soil_mode if soil_mode is not None else mode_alias
            assert requested_mode is not None
            if (
                requested_mode != soils.mode
                and allowed_modes is not None
                and requested_mode.value not in allowed_modes
            ):
                return error_response(
                    "Soil builder is not supported by this project.",
                    status_code=400,
                    code="unsupported_capability",
                    details=f"Unsupported soil builder mode: {requested_mode.value}",
                )

        disturbed = None
        sol_ver = None
        if "disturbed" in soils.mods:
            disturbed = Disturbed.getInstance(wd)
            try:
                sol_ver = _to_float(payload.get("sol_ver"))
            except (TypeError, ValueError):
                return error_response("sol_ver must be numeric", status_code=400)

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_soils)
        prep.remove_timestamp(TaskEnum.run_geneva)

        if requested_mode is not None:
            soils.mode = requested_mode
        soils.initial_sat = initial_sat
        soils.clear_ssurgo_cache_on_rebuild = bool(
            payload.get("clear_ssurgo_cache_on_rebuild", False)
        )

        if disturbed is not None:
            assert sol_ver is not None
            disturbed.sol_ver = sol_ver

        if soils.run_group == "batch":
            return JSONResponse({"message": "Set soils inputs for batch processing"})

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = enqueue_tracked_rq_job(
                q,
                build_soils_rq,
                prep=prep,
                job_key="build_soils_rq",
                runid=runid,
                args=(runid,),
                timeout=RQ_TIMEOUT,
            )
        return JSONResponse({"job_id": job.id})
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except (NoValidSoilsException, WatershedNotAbstractedError) as exc:
        return error_response(
            exc.__name__ or "Building Soil Failed",
            status_code=400,
        )
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-soils enqueue failed")
        return error_response_with_traceback("Building Soil Failed")


__all__ = ["router"]
