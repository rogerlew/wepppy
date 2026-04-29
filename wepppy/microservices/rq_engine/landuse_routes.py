from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import tempfile
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import Any, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import (
    Landuse,
    LanduseCustomMappingError,
    LanduseMode,
    Watershed,
    WatershedNotAbstractedError,
)
from wepppy.nodb.core.landuse import MOFE_SINGLE_LANDUSE_MESSAGE
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.project_rq import build_landuse_rq, modify_landuse_mapping_rq
from wepppy.wepp.management import ManagementMapLoadError
from wepppy.wepp.management.managements import landuse_management_mapping_options
from wepppy.microservices.upload_boundary import UploadBoundaryError
import wepppy.weppcloud.routes.nodb_api.landuse_bp as landuse_flask
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import (
    AuthError,
    _normalize_scopes,
    authorize_run_access,
    require_jwt,
    require_token_class,
)
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response
from .upload_helpers import UploadError, save_upload_file

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
RQ_READ_ALLOWED_SCOPES = frozenset({"rq:read", "rq:status"})
LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES = ("user", "session", "service", "mcp")
LANDUSE_ALLOWED_MAPPING_SELECTIONS = frozenset(
    str(option.get("Key") or "").strip()
    for option in landuse_management_mapping_options
    if str(option.get("Key") or "").strip()
)
LANDUSE_USER_DEFINED_ALLOWED_EXTENSIONS = ("tif", "tiff", "img", "vrt")
LANDUSE_USER_DEFINED_MAX_BYTES = 500 * 1024 * 1024
LANDUSE_MAPPING_MAX_KEY_LENGTH = 128
LANDUSE_MAPPING_BATCH_MAX_EDITS = 500
LANDUSE_MAPPING_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


class RunContextResolutionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 404,
        code: str = "not_found",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


def nodir_resolve(_wd: str, _root: str, *, view: str = "effective") -> None:
    return _nodir_resolve(_wd, _root, view=view)


def mutate_root(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str = "rq-landuse",
):
    _require_directory_root(wd, root)
    with nodir_maintenance_lock(wd, root, purpose=purpose):
        _require_directory_root(wd, root)
        return callback()


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _extract_upload(form: Any, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _preflight_landuse_mutation_root(wd: str) -> None:
    _require_directory_root(wd, "landuse")


def _upload_status_from_message(message: str) -> int:
    if "maximum allowed size" in message.lower():
        return 413
    return 400


def _set_no_store_headers(response: JSONResponse) -> JSONResponse:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _landuse_mapping_error_message(exc: LanduseCustomMappingError | ManagementMapLoadError) -> str:
    if isinstance(exc, ManagementMapLoadError):
        code = str(getattr(exc, "code", "") or "").strip().lower()
        if code == "management_map_missing":
            return "Management map file does not exist"
        if code == "management_map_invalid_json":
            return "Management map file is not valid JSON"
        if code == "management_map_invalid_shape":
            return "Management map payload is invalid"
        return "Failed to load management map"
    return str(exc)


def _landuse_mapping_error_response(exc: LanduseCustomMappingError | ManagementMapLoadError) -> JSONResponse:
    code = getattr(exc, "code", landuse_flask._LANDUSE_MAP_INVALID_CODE)
    details: dict[str, Any] = {}
    raw_details = getattr(exc, "details", None)
    if isinstance(raw_details, dict):
        details.update(raw_details)
    details.pop("map_path", None)
    return error_response(
        _landuse_mapping_error_message(exc),
        status_code=400,
        code=code,
        details=details or None,
    )


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    return _normalize_scopes(claims.get("scope"), get_jwt_config().scope_separator)


def _normalize_landuse_mapping_selection(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    if not token:
        return None
    if token.lower().endswith(".json") or "/" in token or "\\" in token:
        raise ValueError("landuse_management_mapping_selection must be one of the supported mapping keys")
    if token not in LANDUSE_ALLOWED_MAPPING_SELECTIONS:
        raise ValueError(f"Unknown landuse_management_mapping_selection '{token}'")
    return token


def _require_landuse_read_claims(request: Request, runid: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
    scopes = _extract_scopes(claims)
    if not scopes.intersection(RQ_READ_ALLOWED_SCOPES):
        required_text = ", ".join(sorted(RQ_READ_ALLOWED_SCOPES))
        raise AuthError(
            f"Token missing required scope(s): {required_text}",
            status_code=403,
            code="forbidden",
        )
    authorize_run_access(claims, runid)
    return claims


def _normalize_pup_relpath(value: str) -> str:
    normalized = str(value or "").strip().replace("\\", "/").lstrip("/")
    if normalized.startswith("_pups/"):
        normalized = normalized[len("_pups/"):]
    normalized = normalized.rstrip("/")
    if not normalized:
        raise RunContextResolutionError("Unknown pup project")

    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise RunContextResolutionError("Unknown pup project")
    return "/".join(parts)


def _resolve_run_root_for_request(runid: str, request: Request) -> str:
    try:
        run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    except TypeError:
        run_root = Path(get_wd(runid)).resolve()

    # Composite runids already encode scenario/contrast targeting in the slug.
    if ";;" in runid:
        return str(run_root)

    pup_relpath = request.query_params.get("pup")
    if not pup_relpath:
        return str(run_root)

    normalized = _normalize_pup_relpath(pup_relpath)
    pups_root = (run_root / "_pups").resolve()
    if not pups_root.is_dir():
        raise RunContextResolutionError("Unknown pup project")

    candidate = (pups_root / normalized).resolve()
    try:
        candidate.relative_to(pups_root)
    except ValueError as exc:
        raise RunContextResolutionError("Unknown pup project") from exc
    if not candidate.is_dir():
        raise RunContextResolutionError("Unknown pup project")
    return str(candidate)


def _landuse_state_payload(
    *,
    runid: str,
    config: str,
    landuse: Landuse,
) -> dict[str, Any]:
    mode = getattr(landuse, "mode", None)
    mode_name = getattr(mode, "name", None)
    mode_code = int(mode) if isinstance(mode, (LanduseMode, int)) else None

    domlc_d = getattr(landuse, "domlc_d", None)
    if isinstance(domlc_d, Mapping):
        dominant_landcover_count = len(domlc_d)
    else:
        dominant_landcover_count = None

    state = {
        "mode_code": mode_code,
        "mode_name": mode_name.lower() if isinstance(mode_name, str) else None,
        "single_selection": getattr(landuse, "single_selection", None),
        "landuse_db": getattr(landuse, "nlcd_db", None),
        "mapping": getattr(landuse, "mapping", None),
        "custom_mapping_relpath": getattr(landuse, "custom_mapping_relpath", None),
        "has_landuse": bool(getattr(landuse, "has_landuse", False)),
        "dominant_landcover_count": dominant_landcover_count,
    }

    signature = {
        "mode_code": state["mode_code"],
        "single_selection": state["single_selection"],
        "landuse_db": state["landuse_db"],
        "mapping": state["mapping"],
        "custom_mapping_relpath": state["custom_mapping_relpath"],
        "has_landuse": state["has_landuse"],
        "dominant_landcover_count": state["dominant_landcover_count"],
    }
    digest = hashlib.sha256(
        json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    run_state_revision = f"runstate:{runid}:{digest}"

    return {
        "contract_version": "1.0.0-draft",
        "deployment_revision": str(os.getenv("RQ_ENGINE_DEPLOYMENT_REVISION") or "dev"),
        "run_state_domain": "metadata",
        "run_state_revision": run_state_revision,
        "run_state_vector": {
            "orchestration_revision": None,
            "metadata_revision": run_state_revision,
            "outputs_revision": None,
        },
        "etag": f'W/"landuse:{runid}:{digest}"',
        "runid": runid,
        "config": config,
        "controller": "landuse",
        "state": state,
    }


def _normalize_landuse_mapping_key(value: Any, *, field: str) -> str:
    if value is None:
        raise ValueError(f"{field} must be provided")
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("dom and newdom must be provided")
    if len(normalized) > LANDUSE_MAPPING_MAX_KEY_LENGTH:
        raise ValueError(f"{field} exceeds {LANDUSE_MAPPING_MAX_KEY_LENGTH} characters")
    if LANDUSE_MAPPING_CONTROL_CHAR_RE.search(normalized):
        raise ValueError(f"{field} contains unsupported control characters")
    return normalized


def _normalize_landuse_mapping_edits(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_mappings = payload.get("mappings")
    if raw_mappings is None:
        dom = payload.get("dom")
        newdom = payload.get("newdom")
        if dom is None or newdom is None:
            raise ValueError("mappings or dom/newdom must be provided")
        raw_mappings = [{"dom": dom, "newdom": newdom}]
    elif isinstance(raw_mappings, dict):
        # `parse_request_payload` collapses single-item lists to scalar values.
        raw_mappings = [raw_mappings]

    if not isinstance(raw_mappings, list):
        raise ValueError("mappings must be a list of objects")
    if len(raw_mappings) == 0:
        raise ValueError("mappings must include at least one edit")
    if len(raw_mappings) > LANDUSE_MAPPING_BATCH_MAX_EDITS:
        raise ValueError(f"mappings exceeds {LANDUSE_MAPPING_BATCH_MAX_EDITS} edits")

    collapsed: dict[str, dict[str, str]] = {}
    order: list[str] = []

    for idx, raw_edit in enumerate(raw_mappings):
        if not isinstance(raw_edit, dict):
            raise ValueError(f"mappings[{idx}] must be an object")
        if "dom" not in raw_edit or "newdom" not in raw_edit:
            raise ValueError(f"mappings[{idx}] must include dom and newdom")

        dom_value = _normalize_landuse_mapping_key(raw_edit.get("dom"), field=f"mappings[{idx}].dom")
        newdom_value = _normalize_landuse_mapping_key(raw_edit.get("newdom"), field=f"mappings[{idx}].newdom")

        if dom_value not in collapsed:
            order.append(dom_value)
        collapsed[dom_value] = {"dom": dom_value, "newdom": newdom_value}

    return [collapsed[dom] for dom in order]


def _validate_effective_mapping(landuse: Landuse) -> JSONResponse | None:
    getter = getattr(landuse, "get_mapping_dict", None)
    if not callable(getter):
        return None
    try:
        getter()
    except LanduseCustomMappingError as exc:
        return error_response(
            str(exc),
            status_code=400,
            code=exc.code,
            details=exc.details,
        )
    return None


def _validate_mofe_landuse_mode_for_build(landuse: Any) -> JSONResponse | None:
    validator = getattr(landuse, "validate_landuse_mode_for_mofe", None)
    try:
        if callable(validator):
            validator()
        elif (
            getattr(landuse, "mode", None) == LanduseMode.Single
            and bool(getattr(landuse, "multi_ofe", False))
        ):
            raise ValueError(MOFE_SINGLE_LANDUSE_MESSAGE)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="invalid_landuse_mode")
    return None


@router.post(
    "/runs/{runid}/{config}/build-landuse",
    summary="Build landuse inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates landuse settings/files and, outside batch mode, asynchronously enqueues landuse building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_landuse"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Landuse validation/business-rule error (including upload validation). Returns the canonical error payload.",
        },
    ),
)
async def build_landuse(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-landuse auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)

        payload = await parse_request_payload(
            request,
            boolean_fields=(
                "checkbox_burn_shrubs",
                "checkbox_burn_grass",
                "burn_shrubs",
                "burn_grass",
            ),
        )

        def _first(value: Any) -> Any:
            if isinstance(value, (list, tuple)):
                return value[0] if value else None
            return value

        mode_error = _validate_mofe_landuse_mode_for_build(landuse)
        if mode_error is not None:
            return mode_error

        try:
            landuse.parse_inputs(payload)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        if "disturbed" in landuse.mods:
            disturbed = Disturbed.getInstance(wd)
            burn_shrubs_value = payload.get("checkbox_burn_shrubs")
            if burn_shrubs_value is None:
                burn_shrubs_value = payload.get("burn_shrubs")

            burn_grass_value = payload.get("checkbox_burn_grass")
            if burn_grass_value is None:
                burn_grass_value = payload.get("burn_grass")
            disturbed.apply_build_landuse_updates(
                burn_shrubs=bool(burn_shrubs_value),
                burn_grass=bool(burn_grass_value),
            )

        try:
            mapping = _normalize_landuse_mapping_selection(_first(payload.get("landuse_management_mapping_selection")))
        except ValueError as exc:
            return error_response(str(exc), status_code=400, code="invalid_mapping_selection")

        if landuse.mode == LanduseMode.UserDefined:
            from wepppy.all_your_base.geo import raster_stacker

            watershed = Watershed.getInstance(wd)
            if mapping is None:
                return error_response(
                    "landuse_management_mapping_selection must be provided",
                    status_code=400,
                )
            landuse.mapping = mapping

            form = await request.form()
            upload = _extract_upload(form, "input_upload_landuse")
            filename: str | None = None
            user_defined_fn: str | None = None

            def _mutate_landuse_user_defined() -> None:
                nonlocal filename
                nonlocal user_defined_fn

                if upload is not None:
                    if not upload.filename:
                        raise ValueError("no filename specified")

                    filename = secure_filename(upload.filename)
                    if not filename:
                        raise ValueError("Could not obtain filename")

                    try:
                        saved_path = save_upload_file(
                            upload,
                            allowed_extensions=LANDUSE_USER_DEFINED_ALLOWED_EXTENSIONS,
                            dest_dir=Path(landuse.lc_dir),
                            filename_transform=lambda _value: f"_{filename}",
                            overwrite=True,
                            max_bytes=LANDUSE_USER_DEFINED_MAX_BYTES,
                        )
                    except UploadError as exc:
                        raise ValueError(str(exc)) from exc
                    user_defined_fn = str(saved_path)
                else:
                    filename = landuse.user_defined_landcover_fn
                    if filename:
                        user_defined_fn = _join(landuse.lc_dir, f"_{filename}")
                    if not filename or not user_defined_fn or not _exists(user_defined_fn):
                        raise FileNotFoundError(
                            "input_upload_landuse is required when no existing user-defined landuse file is available."
                        )

                raster_stacker(user_defined_fn, watershed.subwta, landuse.lc_fn)

                if not _exists(landuse.lc_fn):
                    raise RuntimeError("Failed creating landuse file")
                if filename:
                    landuse.user_defined_landcover_fn = filename

            try:
                mutate_root(
                    wd,
                    "landuse",
                    _mutate_landuse_user_defined,
                    purpose="rq-build-landuse-user-defined",
                )
            except ValueError as exc:
                return error_response(
                    str(exc),
                    status_code=_upload_status_from_message(str(exc)),
                )
            except FileNotFoundError as exc:
                return error_response(str(exc), status_code=400)
            except RuntimeError as exc:
                return error_response(str(exc), status_code=400)

        mapping_error = _validate_effective_mapping(landuse)
        if mapping_error is not None:
            return mapping_error

        if landuse.run_group == "batch":
            return JSONResponse({"message": "Set landuse inputs for batch processing"})

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)
        prep.remove_timestamp(TaskEnum.run_geneva)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_landuse_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("build_landuse_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except WatershedNotAbstractedError as exc:
        return error_response(
            exc.__name__ or "Watershed Not Abstracted Error",
            status_code=400,
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-landuse enqueue failed")
        return error_response("Building Landuse Failed", status_code=500)


@router.post(
    "/runs/{runid}/{config}/set-landuse-mode",
    summary="Set landuse mode",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously updates landuse mode metadata for the target run."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("set_landuse_mode"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse mode metadata updated.",
        extra={400: "Invalid mode payload. Returns the canonical error payload."},
    ),
)
async def set_landuse_mode(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine set-landuse-mode auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        payload = await parse_request_payload(request)
        mode_raw = payload.get("mode")
        single_selection = payload.get("landuse_single_selection")
        if mode_raw is None:
            return error_response("mode and landuse_single_selection must be provided", status_code=400)
        try:
            mode = LanduseMode(int(mode_raw))
        except (TypeError, ValueError):
            return error_response("mode and landuse_single_selection must be provided", status_code=400)

        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)
        if mode == LanduseMode.Single and bool(getattr(landuse, "multi_ofe", False)):
            return error_response(MOFE_SINGLE_LANDUSE_MESSAGE, status_code=400, code="invalid_landuse_mode")
        if mode == LanduseMode.Single and single_selection is None:
            return error_response("mode and landuse_single_selection must be provided", status_code=400)
        landuse.apply_set_landuse_mode_updates(
            mode=mode,
            single_selection=str(single_selection) if single_selection is not None else None,
        )
        return JSONResponse({"message": "Landuse mode updated"})
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine set-landuse-mode failed")
        return error_response("error setting landuse mode", status_code=500)


@router.post(
    "/runs/{runid}/{config}/set-landuse-db",
    summary="Set landuse database",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously persists the selected landuse database token."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("set_landuse_db"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse database metadata updated.",
        extra={400: "Invalid landuse database payload. Returns the canonical error payload."},
    ),
)
async def set_landuse_db(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine set-landuse-db auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        payload = await parse_request_payload(request)
        db = payload.get("landuse_db")
        if db is None:
            return error_response("landuse_db must be provided", status_code=400)

        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)
        landuse.nlcd_db = str(db)
        return JSONResponse({"message": "Landuse database updated"})
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine set-landuse-db failed")
        return error_response("error setting landuse db", status_code=500)


@router.post(
    "/runs/{runid}/{config}/modify-landuse-coverage",
    summary="Modify landuse coverage",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously applies one dominant-class cover adjustment."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("modify_landuse_coverage"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse coverage updated.",
        extra={400: "Invalid coverage payload. Returns the canonical error payload."},
    ),
)
async def modify_landuse_coverage(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine modify-landuse-coverage auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        payload = await parse_request_payload(request)
        dom = payload.get("dom")
        cover = payload.get("cover")
        value_raw = payload.get("value")
        if dom is None or cover is None or value_raw is None:
            return error_response("dom, cover, and value must be provided", status_code=400)
        try:
            value = float(value_raw)
        except (TypeError, ValueError):
            return error_response("dom, cover, and value must be provided", status_code=400)

        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)
        landuse.modify_coverage(str(dom), str(cover), value)
        return JSONResponse({"message": "Landuse coverage updated"})
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine modify-landuse-coverage failed")
        return error_response("Failed to modify landuse coverage", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/landuse/state",
    summary="Read landuse controller state",
    description=(
        "Requires JWT Bearer auth plus run access. Supports `rq:read` or `rq:status` "
        "and returns read-only landuse controller state."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_landuse_state"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Read-only landuse controller state returned.",
        extra={404: "Run or pup context not found. Returns the canonical error payload."},
    ),
)
async def get_landuse_state(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_landuse_read_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine get-landuse-state auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        landuse = Landuse.getInstance(wd)
        return JSONResponse(_landuse_state_payload(runid=runid, config=config, landuse=landuse))
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine get-landuse-state failed")
        return error_response("Error reading landuse state", status_code=500)


@router.post(
    "/runs/{runid}/{config}/modify-landuse-mapping",
    summary="Queue a landuse mapping update",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Enqueues one run-scoped mapping batch mutation so long-running MOFE remaps do not block web workers."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("modify_landuse_mapping"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Mapping update accepted; returns enqueued `job_id` and `mapping_count`.",
        extra={400: "Validation error for required mapping payload fields."},
    ),
)
async def modify_landuse_mapping(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine modify-landuse-mapping auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        payload = await parse_request_payload(request)
        try:
            mapping_edits = _normalize_landuse_mapping_edits(payload)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)

        prep = RedisPrep.getInstance(wd)
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                modify_landuse_mapping_rq,
                (runid, mapping_edits),
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("modify_landuse_mapping_rq", job.id)

        return JSONResponse({"job_id": job.id, "mapping_count": len(mapping_edits)})
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine modify-landuse-mapping enqueue failed")
        return error_response("Failed to modify landuse mapping", status_code=500)


@router.get(
    "/runs/{runid}/{config}/landuse-user-defined/catalog",
    summary="Read run-scoped landuse user-defined catalog",
    description=(
        "Requires JWT Bearer auth plus run access. Supports `rq:read` or `rq:status` and "
        "returns read-only run-scoped user-defined management catalog metadata with no queue enqueue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_landuse_user_defined_catalog"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Catalog items and lookup fingerprint returned.",
        extra={400: "Invalid run path or catalog metadata. Returns the canonical error payload."},
    ),
)
async def get_landuse_user_defined_catalog(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        _require_landuse_read_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine landuse-user-defined catalog auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        catalog_items = landuse_flask._catalog_items_with_file_fingerprints(wd)
        lookup_sha256 = hashlib.sha256(
            json.dumps(catalog_items, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return _set_no_store_headers(
            JSONResponse(
                {
                    "items": catalog_items,
                    "lookup_sha256": lookup_sha256,
                }
            )
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-user-defined catalog failed")
        return error_response("Failed to read landuse catalog", status_code=500)


@router.post(
    "/runs/{runid}/{config}/landuse-user-defined/upload",
    summary="Upload run-scoped user-defined management files",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Accepts one `.man` file or one `.zip` archive of `.man` files and applies the "
        "catalog mutation atomically."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("upload_landuse_user_defined_managements"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Catalog upload succeeded and returns normalized catalog entries.",
        extra={
            400: "Upload validation, archive policy, or run-path error.",
            409: "Catalog conflict without replace permission.",
        },
    ),
)
async def upload_landuse_user_defined_managements(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine landuse-user-defined upload auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        try:
            catalog_dir = landuse_flask._landuse_user_defined_dir(wd)
            catalog_dir.mkdir(parents=True, exist_ok=True)
        except ValueError as exc:
            return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")

        payload = await parse_request_payload(request, boolean_fields={"replace"})
        replace = bool(payload.get("replace", False))

        form = await request.form()
        upload = _extract_upload(form, "management_upload")
        if upload is None:
            return error_response("management_upload is required", status_code=400)
        if not upload.filename:
            return error_response("Uploaded file must include a filename", status_code=400)

        suffix = Path(upload.filename).suffix.lower()
        staged_files: list[Path] = []
        installed_filenames: list[str] = []

        with tempfile.TemporaryDirectory(prefix="rq-landuse-user-defined-") as tmpdir:
            scratch_dir = Path(tmpdir)
            try:
                if suffix == ".man":
                    staged_path = landuse_flask.save_upload_from_stream(
                        raw_filename=upload.filename,
                        stream=upload.file,
                        dest_dir=scratch_dir,
                        allowed_extensions=landuse_flask._LANDUSE_ALLOWED_MAN_EXTENSIONS,
                        lowercase_by_default=True,
                        max_bytes=landuse_flask._LANDUSE_MAN_UPLOAD_MAX_BYTES,
                    )
                    landuse_flask._validate_management_file(staged_path)
                    staged_files = [staged_path]
                elif suffix == ".zip":
                    archive_bytes = landuse_flask._read_upload_bytes_with_limit(
                        upload.file,
                        max_bytes=landuse_flask._LANDUSE_ZIP_UPLOAD_MAX_BYTES,
                    )
                    extraction = landuse_flask.validate_and_extract_zip_archive(
                        archive_name=upload.filename,
                        archive_bytes=archive_bytes,
                        extraction_root=scratch_dir,
                        limits=landuse_flask._LANDUSE_ZIP_LIMITS,
                        member_policy=landuse_flask._man_archive_member_policy,
                        sanitize_metadata_sidecars=False,
                    )
                    staged_files = sorted(
                        (
                            path
                            for path in extraction.extracted_files
                            if path.is_file()
                            and path.parent == extraction.extraction_root
                            and path.suffix.lower() == ".man"
                            and not path.name.startswith("._")
                        ),
                        key=lambda path: path.name.lower(),
                    )
                    if not staged_files:
                        return error_response("Archive must include at least one .man file", status_code=400)
                    for staged_path in staged_files:
                        landuse_flask._validate_management_file(staged_path)
                else:
                    return error_response(
                        "Upload must be a single .man file or one .zip archive",
                        status_code=400,
                    )
            except UploadBoundaryError as exc:
                return error_response(str(exc), status_code=exc.status_code)
            except landuse_flask.ShapeConverterError as exc:
                return error_response(
                    exc.message,
                    status_code=exc.status_code,
                    code=exc.code,
                    details=exc.details,
                )
            except ValueError as exc:
                return error_response(str(exc), status_code=400)

            landuse = Landuse.getInstance(wd)
            with landuse.locked():
                try:
                    installed_filenames = landuse_flask._install_uploaded_managements(
                        target_dir=catalog_dir,
                        staged_files=staged_files,
                        replace=replace,
                    )
                except FileExistsError as exc:
                    return error_response(str(exc), status_code=409, code="CATALOG_CONFLICT")

                metadata = landuse_flask._read_catalog_metadata(wd)
                by_filename: dict[str, dict[str, Any]] = {
                    item["filename"]: dict(item)
                    for item in metadata.get("items", [])
                    if isinstance(item, dict) and "filename" in item
                }
                timestamp = landuse_flask._utc_iso_timestamp()
                for filename in installed_filenames:
                    prior = by_filename.get(filename, {})
                    by_filename[filename] = {
                        "filename": filename,
                        "description": str(prior.get("description") or "").strip()
                        or landuse_flask._catalog_default_description(filename),
                        "uploaded_at": timestamp,
                    }
                landuse_flask._persist_catalog_items(wd, list(by_filename.values()))
                catalog_items = landuse_flask._catalog_items_with_file_fingerprints(wd, sync_metadata=True)

        return JSONResponse(
            {
                "message": "Landuse user-defined upload completed",
                "imported_files": installed_filenames,
                "replace": replace,
                "catalog_count": len(catalog_items),
                "items": catalog_items,
            }
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-user-defined upload failed")
        return error_response("Failed to upload landuse management files", status_code=500)


@router.post(
    "/runs/{runid}/{config}/landuse-user-defined/delete",
    summary="Delete one run-scoped user-defined management file",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Deletes one catalog entry and file atomically."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("delete_landuse_user_defined_management"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Catalog entry removed.",
        extra={400: "Invalid filename or run-path contract.", 404: "Catalog file not found."},
    ),
)
async def delete_landuse_user_defined_management(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine landuse-user-defined delete auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        payload = await parse_request_payload(request)
        raw_filename = payload.get("filename")
        if raw_filename is None:
            return error_response("filename must be provided", status_code=400)
        try:
            filename = landuse_flask._safe_catalog_filename(str(raw_filename))
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        landuse = Landuse.getInstance(wd)
        with landuse.locked():
            target_path = landuse_flask._landuse_user_defined_dir(wd) / filename
            if not target_path.exists():
                return error_response(
                    f"Management file not found: {filename}",
                    status_code=404,
                    code="CATALOG_FILE_NOT_FOUND",
                )

            target_path.unlink()
            metadata = landuse_flask._read_catalog_metadata(wd)
            remaining_items = [
                item
                for item in metadata.get("items", [])
                if isinstance(item, dict) and str(item.get("filename", "")).lower() != filename
            ]
            landuse_flask._persist_catalog_items(wd, remaining_items)
            catalog_items = landuse_flask._catalog_items_with_file_fingerprints(wd, sync_metadata=True)

        return JSONResponse(
            {
                "message": "Landuse user-defined catalog entry deleted",
                "deleted": filename,
                "catalog_count": len(catalog_items),
                "items": catalog_items,
            }
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-user-defined delete failed")
        return error_response("Failed to delete landuse management file", status_code=500)


@router.post(
    "/runs/{runid}/{config}/landuse-user-defined/update-description",
    summary="Update one run-scoped user-defined management description",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Updates metadata description without rewriting management file bytes."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("update_landuse_user_defined_management_description"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Description updated.",
        extra={400: "Invalid filename/description payload.", 404: "Catalog file not found."},
    ),
)
async def update_landuse_user_defined_management_description(
    runid: str,
    config: str,
    request: Request,
) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine landuse-user-defined update-description auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        payload = await parse_request_payload(request)

        raw_filename = payload.get("filename")
        if raw_filename is None:
            return error_response("filename must be provided", status_code=400)
        try:
            filename = landuse_flask._safe_catalog_filename(str(raw_filename))
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        description = str(payload.get("description") or "").strip()
        if not description:
            return error_response("description must be provided", status_code=400)

        landuse = Landuse.getInstance(wd)
        with landuse.locked():
            target_path = landuse_flask._landuse_user_defined_dir(wd) / filename
            if not target_path.exists():
                return error_response(
                    f"Management file not found: {filename}",
                    status_code=404,
                    code="CATALOG_FILE_NOT_FOUND",
                )

            metadata = landuse_flask._read_catalog_metadata(wd)
            by_filename: dict[str, dict[str, Any]] = {
                item["filename"]: dict(item)
                for item in metadata.get("items", [])
                if isinstance(item, dict) and "filename" in item
            }
            prior = by_filename.get(filename, {})
            by_filename[filename] = {
                "filename": filename,
                "description": description,
                "uploaded_at": str(prior.get("uploaded_at") or "").strip()
                or landuse_flask._utc_iso_timestamp(),
            }
            landuse_flask._persist_catalog_items(wd, list(by_filename.values()))
            catalog_items = landuse_flask._catalog_items_with_file_fingerprints(wd, sync_metadata=True)

        updated_item = next((item for item in catalog_items if item["filename"] == filename), None)
        return JSONResponse(
            {
                "message": "Landuse user-defined description updated",
                "item": updated_item,
                "catalog_count": len(catalog_items),
                "items": catalog_items,
            }
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-user-defined update-description failed")
        return error_response("Failed to update landuse management description", status_code=500)


@router.get(
    "/runs/{runid}/{config}/landuse-map/snapshot",
    summary="Read run-scoped landuse map snapshot",
    description=(
        "Requires JWT Bearer auth plus run access. Supports `rq:read` or `rq:status` and "
        "returns read-only map rows/options plus optimistic-concurrency hash with no queue enqueue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_landuse_map_snapshot"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Map snapshot returned.",
        extra={400: "Invalid run-path or mapping configuration."},
    ),
)
async def get_landuse_map_snapshot(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        _require_landuse_read_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary auth contract
        logger.exception("rq-engine landuse-map snapshot auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        landuse = Landuse.getInstance(wd)
        with landuse.locked():
            snapshot = landuse_flask._build_landuse_map_snapshot_payload(landuse, wd)
        return _set_no_store_headers(JSONResponse(landuse_flask._snapshot_payload_for_client(snapshot)))
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (LanduseCustomMappingError, ManagementMapLoadError) as exc:
        return _landuse_mapping_error_response(exc)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-map snapshot failed")
        return error_response("Failed to read landuse map snapshot", status_code=500)


@router.post(
    "/runs/{runid}/{config}/landuse-map/save",
    summary="Save run-scoped landuse map override",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates and atomically saves mapping assignments/descriptions with optimistic concurrency checks. "
        "Precondition hash may be sent via `X-If-Match-Sha256` header or `if_match_sha256` body field."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("save_landuse_map"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Map override saved and lookup hash rotated.",
        extra={
            400: "Invalid row payload.",
            409: "Stale lookup precondition mismatch.",
            428: "Missing precondition hash (`if_match_sha256`).",
        },
    ),
)
async def save_landuse_map(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine landuse-map save auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)

        raw_json = await request.json()
    except json.JSONDecodeError:
        raw_json = None
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-map save request parsing failed")
        return error_response("Failed to parse request", status_code=400)

    if_match_sha256 = request.headers.get("X-If-Match-Sha256")
    if isinstance(raw_json, list):
        rows = raw_json
    elif isinstance(raw_json, dict):
        rows = raw_json.get("rows", [])
        requested_sha = raw_json.get("if_match_sha256")
        if requested_sha is not None:
            if_match_sha256 = str(requested_sha).strip()
        if isinstance(rows, dict):
            rows = [rows]
    else:
        return error_response(
            'rows payload must be JSON list or {"rows": [...]}',
            status_code=400,
            code="invalid_rows_payload",
        )

    if not isinstance(rows, list) or len(rows) == 0:
        return error_response("rows payload must be a non-empty list", status_code=400, code="invalid_rows_payload")

    if if_match_sha256 is not None:
        if_match_sha256 = if_match_sha256.strip()
    if not if_match_sha256:
        return error_response("if_match_sha256 is required", status_code=428, code="PRECONDITION_REQUIRED")

    landuse = Landuse.getInstance(wd)
    try:
        override_path = landuse_flask._landuse_mapping_override_path(wd)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")

    try:
        with landuse.locked():
            try:
                snapshot = landuse_flask._build_landuse_map_snapshot_payload(landuse, wd)
            except ValueError as exc:
                return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")

            current_sha256 = str(snapshot["lookup_sha256"])
            if current_sha256 != if_match_sha256:
                return error_response(
                    "Stale landuse map snapshot. Reload current data before saving.",
                    status_code=409,
                    code="STALE_LOOKUP",
                    details={
                        "expected_sha256": if_match_sha256,
                        "current_sha256": current_sha256,
                    },
                )

            mapping_reference = snapshot.get("mapping_reference")
            current_map = landuse_flask.load_map(mapping_reference)
            try:
                catalog_items = landuse_flask._catalog_items_with_file_fingerprints(wd)
            except ValueError as exc:
                return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")

            management_index = landuse_flask._candidate_management_index(
                mapping_dict=current_map,
                catalog_items=catalog_items,
                catalog_dir=landuse_flask._landuse_user_defined_dir(wd),
            )

            expected_keys = {str(key) for key in current_map.keys()}
            submitted: dict[str, dict[str, str | None]] = {}
            for idx, raw_row in enumerate(rows):
                if not isinstance(raw_row, dict):
                    raise ValueError(f"rows[{idx}] must be an object")

                raw_key = raw_row.get("key")
                raw_management_file = raw_row.get("management_file")
                if raw_key is None or raw_management_file is None:
                    raise ValueError(f"rows[{idx}] must include key and management_file")

                key = str(raw_key).strip()
                management_file = str(raw_management_file).strip()
                description: str | None = None
                if "description" in raw_row:
                    description = str(raw_row.get("description") or "").strip()
                    if (
                        description
                        and len(description) > landuse_flask._LANDUSE_MAP_DESCRIPTION_MAX_LENGTH
                    ):
                        raise ValueError(
                            f"rows[{idx}].description exceeds "
                            f"{landuse_flask._LANDUSE_MAP_DESCRIPTION_MAX_LENGTH} characters"
                        )
                    if not description:
                        description = None
                if not key:
                    raise ValueError(f"rows[{idx}].key must be non-empty")
                if not management_file:
                    raise ValueError(f"rows[{idx}].management_file must be non-empty")
                if len(management_file) > landuse_flask._LANDUSE_MANAGEMENT_FILE_KEY_MAX_LENGTH:
                    raise ValueError(
                        f"rows[{idx}].management_file exceeds "
                        f"{landuse_flask._LANDUSE_MANAGEMENT_FILE_KEY_MAX_LENGTH} characters"
                    )
                if key in submitted:
                    raise ValueError(f"rows includes duplicate key '{key}'")
                submitted[key] = {"management_file": management_file, "description": description}

            missing_keys = sorted(expected_keys.difference(submitted.keys()))
            extra_keys = sorted(submitted.keys() - expected_keys)
            if missing_keys or extra_keys:
                raise ValueError(
                    "rows must include exactly one entry for each current landuse key "
                    f"(missing={missing_keys}, extra={extra_keys})"
                )

            updated_map = copy.deepcopy(current_map)
            for key, payload_row in submitted.items():
                management_file = str(payload_row["management_file"] or "").strip()
                submitted_description = payload_row["description"]
                if management_file not in management_index:
                    raise ValueError(f"Unknown management_file '{management_file}' for key '{key}'")

                metadata = management_index[management_file]
                entry = updated_map[key]
                previous_management_file = str(entry.get("ManagementFile") or "").strip()
                entry["ManagementFile"] = management_file
                entry["ManagementDir"] = str(metadata["management_dir"])
                soil_file = metadata.get("soil_file")
                if soil_file in (None, ""):
                    entry.pop("SoilFile", None)
                else:
                    entry["SoilFile"] = str(soil_file)

                if submitted_description is not None:
                    entry["Description"] = submitted_description
                elif management_file != previous_management_file:
                    description = str(metadata.get("description") or "").strip()
                    if not description or str(metadata.get("source") or "").strip().lower() == "mapping":
                        description = landuse_flask._catalog_default_description(management_file)
                    if description:
                        entry["Description"] = description

            landuse_flask._write_json_atomic(override_path, updated_map)
            # Direct assignment avoids nested lock acquisition inside nodb_setter wrappers.
            landuse._custom_mapping_relpath = landuse_flask._LANDUSE_MAPPING_OVERRIDE_RELPATH
    except (LanduseCustomMappingError, ManagementMapLoadError) as exc:
        return _landuse_mapping_error_response(exc)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="invalid_rows_payload")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-map save validation failed")
        return error_response("Failed to save landuse map", status_code=500)

    # Map save only persists the override snapshot; full management rebuild stays in build-landuse/clear-override flows.
    prep = RedisPrep.getInstance(wd)
    prep.timestamp(TaskEnum.landuse_map)
    snapshot = landuse_flask._build_landuse_map_snapshot_payload(landuse, wd)
    response = JSONResponse(
        {
            "message": "Landuse map saved",
            "lookup_sha256": snapshot["lookup_sha256"],
        }
    )
    response.headers["X-Lookup-Sha256"] = str(snapshot["lookup_sha256"])
    return response


@router.post(
    "/runs/{runid}/{config}/landuse-map/clear-override",
    summary="Clear run-scoped landuse map override",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Clears run-scoped landuse map override and rebuilds management outputs."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("clear_landuse_map_override"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Map override cleared.",
        extra={400: "Invalid run path or mapping configuration."},
    ),
)
async def clear_landuse_map_override(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine landuse-map clear-override auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)

        with landuse.locked():
            landuse._custom_mapping_relpath = None

        landuse_flask._landuse_mapping_override_path(wd).unlink(missing_ok=True)
        landuse.build_managements()

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.landuse_map)
        return JSONResponse({"message": "Landuse map override cleared"})
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (LanduseCustomMappingError, ManagementMapLoadError) as exc:
        return _landuse_mapping_error_response(exc)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="INVALID_RUN_PATH")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine landuse-map clear-override failed")
        return error_response("Failed to clear landuse map override", status_code=500)


@router.post(
    "/runs/{runid}/{config}/modify-landuse",
    summary="Modify landuse class assignments",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously applies explicit landuse class assignments for selected Topaz IDs."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("modify_landuse"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse assignments updated.",
        extra={400: "Invalid Topaz or landuse payload. Returns the canonical error payload."},
    ),
)
async def modify_landuse(runid: str, config: str, request: Request) -> JSONResponse:
    _ = config
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_token_class(claims, LANDUSE_MUTATION_ALLOWED_TOKEN_CLASSES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine modify-landuse auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        wd = _resolve_run_root_for_request(runid, request)
        _preflight_landuse_mutation_root(wd)
        payload = await parse_request_payload(request)
        topaz_ids = landuse_flask._coerce_topaz_ids(payload.get("topaz_ids"))
        lccode = landuse_flask._coerce_landuse_code(payload.get("landuse"))

        landuse = Landuse.getInstance(wd)
        landuse.modify(topaz_ids, lccode)
        return JSONResponse(
            {
                "message": "Landuse assignments updated",
                "topaz_count": len(topaz_ids),
            }
        )
    except RunContextResolutionError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except ValueError as exc:
        return error_response(str(exc), status_code=400, code="validation_error")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine modify-landuse failed")
        return error_response("Modifying landuse failed", status_code=500)


__all__ = ["router"]
