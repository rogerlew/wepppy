from __future__ import annotations

from contextlib import nullcontext
import json
import logging
import math
import os
from typing import Any

import redis
from .payloads import PayloadRoute
from wepppy.request_payload import RequestPayloadError

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
from wepppy.eu.soils.esdac.subsoil import validate_subsoil_profile
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock
from wepppy.rq.project_rq import build_soils_rq
from wepppy.rq.submission_recovery import RqSubmissionConflict, enqueue_tracked_rq_job
from wepppy.soils.ssurgo import NoValidSoilsException
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from wepppy.nodb.base import NoDbAlreadyLockedError
from .single_input_uploads import input_payload
from wepppy.rq.single_input_admission import accept_input, input_submission
from wepppy.wepp.single_input import SingleInputError
from wepppy.nodb.single_input_policy import SingleInputPolicyError, require_single_input_policy, single_input_uploads_enabled
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback
from .webhooks import reject_unsupported_payload

logger = logging.getLogger(__name__)

router = APIRouter(route_class=PayloadRoute)

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


_ESDAC_SUBSOIL_PREFIX = "esdac_subsoil_"


async def _esdac_profile_input(request: Request, payload: dict[str, Any]) -> dict[str, float] | None:
    values = {key.removeprefix(_ESDAC_SUBSOIL_PREFIX): value for key, value in payload.items()
              if key.startswith(_ESDAC_SUBSOIL_PREFIX)}
    if not values:
        return None
    if isinstance(getattr(request, "_json", None), dict):
        seen: set[str] = set()

        def reject_repeated_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            for key, _ in pairs:
                if key.startswith(_ESDAC_SUBSOIL_PREFIX):
                    if key in seen:
                        raise ValueError("Repeat ESDAC subsoil fields are not allowed.")
                    seen.add(key)
            return dict(pairs)

        json.loads(await request.body(), object_pairs_hook=reject_repeated_fields)
        if any(isinstance(value, str) for value in values.values()):
            raise ValueError("JSON ESDAC subsoil fields must be numbers.")
    return validate_subsoil_profile(values)


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
    if isinstance(exc, NoDbAlreadyLockedError):
        return error_response("Soils is busy; retry after the current mutation finishes.", status_code=409, code="conflict")
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
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("must be finite")
    return result


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

        async with input_payload(
            request, "soils",
            boolean_fields={"clear_ssurgo_cache_on_rebuild"},
            blank_false_fields={"clear_ssurgo_cache_on_rebuild"},
        ) as (payload, upload_form):
            webhook_error = reject_unsupported_payload(payload)
            if webhook_error is not None:
                return webhook_error
            try:
                initial_sat = _to_float(payload.get("initial_sat"))
            except (TypeError, ValueError, OverflowError):
                return error_response("initial_sat must be numeric", status_code=400)

            soils = Soils.getInstance(wd)
            is_single_input_project = single_input_uploads_enabled(soils)
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
                except (TypeError, ValueError, OverflowError):
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
                except (TypeError, ValueError, OverflowError):
                    return error_response("sol_ver must be numeric", status_code=400)


            effective_mode = requested_mode if requested_mode is not None else soils.mode
            esdac_project = soils.uses_esdac(SoilsMode.Gridded)
            esdac = esdac_project and effective_mode == SoilsMode.Gridded
            try:
                profile_input = await _esdac_profile_input(request, payload)
            except ValueError as exc:
                return error_response(str(exc), status_code=400, code="invalid_esdac_subsoil")
            if profile_input is not None and not esdac:
                return error_response(
                    "Subsoil defaults apply only to gridded ESDAC soils.",
                    status_code=400,
                    code="invalid_esdac_subsoil",
                )

            esdac_lock = (
                maintenance_lock(wd, "soils", purpose="admit-esdac-soils")
                if esdac_project and not is_single_input_project
                else nullcontext()
            )
            with esdac_lock, input_submission(soils, "soils", runid):
                await accept_input(soils, "soils", upload_form, effective_mode)
                prep = RedisPrep.getInstance(wd)
                try:
                    profile = (profile_input or soils.esdac_subsoil_defaults) if esdac else None
                except ValueError as exc:
                    return error_response(str(exc), status_code=400, code="invalid_esdac_subsoil")

                changes: list[tuple[Any, str, Any]] = [
                    (soils, "initial_sat", initial_sat),
                    (soils, "clear_ssurgo_cache_on_rebuild", bool(payload.get("clear_ssurgo_cache_on_rebuild", False))),
                ]
                if requested_mode is not None:
                    changes.append((soils, "mode", requested_mode))
                if disturbed is not None:
                    assert sol_ver is not None
                    changes.append((disturbed, "sol_ver", sol_ver))
                if profile_input is not None:
                    changes.append((soils, "esdac_subsoil_defaults", profile_input))

                removed_tasks = (TaskEnum.build_soils, TaskEnum.run_geneva)
                applied: list[tuple[Any, str, Any]] = []
                removed: dict[str, int] = {}

                def persist_inputs() -> None:
                    for controller, field, value in changes:
                        if esdac_project:
                            saved_field = "_esdac_subsoil_defaults" if field == "esdac_subsoil_defaults" else field
                            applied.append((controller, saved_field, getattr(controller, saved_field, None)))
                        setattr(controller, field, value)
                    for task in removed_tasks:
                        if esdac_project:
                            previous = prep[str(task)]
                            if previous is not None:
                                removed[str(task)] = previous
                        prep.remove_timestamp(task)

                if not esdac_project or soils.run_group == "batch":
                    persist_inputs()
                if soils.run_group == "batch":
                    return JSONResponse({"message": "Set soils inputs for batch processing"})

                conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
                tracked_options: dict[str, Any] = {}
                if esdac_project:
                    admitted: dict[str, Any] = {"admitted_soil_mode": int(effective_mode)}
                    if esdac:
                        admitted["esdac_subsoil_defaults"] = profile
                    tracked_options = {"kwargs": admitted, "before_enqueue": persist_inputs}
                try:
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
                            **tracked_options,
                        )
                except Exception:  # broad-except: restore run inputs across admission failures
                    for controller, field, previous in reversed(applied):
                        if field == "_esdac_subsoil_defaults":
                            with controller.locked():
                                controller._esdac_subsoil_defaults = previous
                        else:
                            setattr(controller, field, previous)
                    for task, previous in removed.items():
                        prep[task] = previous
                    raise
                response = {"job_id": job.id}
                if int(soils.mode) == 5:
                    response["result"] = {"single_user_defined_filename": soils.single_user_defined_filename}
                return JSONResponse(response)
    except SingleInputError as exc:
        return error_response(str(exc), status_code=exc.status_code, code=exc.code)
    except SingleInputPolicyError as exc:
        return error_response(str(exc), status_code=400, code="unsupported_capability")
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="job_active")
    except (NoValidSoilsException, WatershedNotAbstractedError) as exc:
        return error_response(
            exc.__name__ or "Building Soil Failed",
            status_code=400,
        )
    except RequestPayloadError:
        raise
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-soils enqueue failed")
        if locals().get("is_single_input_project", False):
            return error_response("Building Soil Failed", status_code=500)
        return error_response_with_traceback("Building Soil Failed")


__all__ = ["router"]
