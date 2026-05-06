from __future__ import annotations

import copy
import hashlib
import json
import logging
import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

from wepppy.nodb.mods.features_export import (
    FeaturesExportServiceError,
    load_job_manifest,
    resolve_download_artifact_path,
)
from wepppy.nodb.core import Climate, Landuse, Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, _normalize_scopes, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response
from .upload_climate_routes import UPLOAD_CLI_ALLOWED_EXTENSIONS, UPLOAD_CLI_MAX_BYTES
from .upload_disturbed_routes import (
    UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS,
    UPLOAD_COVER_TRANSFORM_MAX_BYTES,
    UPLOAD_SBS_ALLOWED_EXTENSIONS,
    UPLOAD_SBS_MAX_BYTES,
)
from .watershed_routes import (
    UPLOAD_DEM_ALLOWED_EXTENSIONS,
    UPLOAD_DEM_MAX_BYTES,
    UPLOAD_DEM_MAX_DIMENSION,
)

logger = logging.getLogger(__name__)

router = APIRouter()

CONTRACT_VERSION = "1.0.0-draft"
DEPLOYMENT_REVISION_ENV = "RQ_ENGINE_DEPLOYMENT_REVISION"
DEFAULT_DEPLOYMENT_REVISION = "dev"
SCHEMA_DEFAULTS_ALLOWED_SCOPES = frozenset({"rq:read", "rq:status"})
UNKNOWN_UPDATED_AT = "1970-01-01T00:00:00Z"
UNKNOWN_SOURCE_RUN_STATE_REVISION = "unknown"
FEATURES_EXPORT_JOB_KEY = "features_export"
SESSION_TOKEN_IDEMPOTENCY_TTL_ENV = "RQ_ENGINE_SESSION_TOKEN_IDEMPOTENCY_TTL_SECONDS"
SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT = 86400
RUN_STATE_DOMAIN_METADATA = "metadata"
RUN_STATE_DOMAIN_OUTPUTS = "outputs"
LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM = "include_operation_docs"


class RunConfigMismatchError(ValueError):
    """Raised when a run exists but the requested config token does not match run config."""


@dataclass(frozen=True)
class RuntimeState:
    runid: str
    config: str
    active_mods: tuple[str, ...]
    region: str | None
    states: Mapping[str, Any]
    generated_at: str
    run_state_revision: str


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deployment_revision() -> str:
    value = str(os.getenv(DEPLOYMENT_REVISION_ENV) or DEFAULT_DEPLOYMENT_REVISION).strip()
    return value or DEFAULT_DEPLOYMENT_REVISION


def _session_token_idempotency_window_seconds() -> int:
    raw = str(os.getenv(SESSION_TOKEN_IDEMPOTENCY_TTL_ENV) or "").strip()
    if not raw:
        return SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT


def _base_payload(runtime: RuntimeState) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "deployment_revision": _deployment_revision(),
        "run_state_revision": runtime.run_state_revision,
        "run_state_domain": RUN_STATE_DOMAIN_METADATA,
        "run_state_vector": _run_state_vector(metadata_revision=runtime.run_state_revision),
    }


def _run_state_vector(
    *,
    metadata_revision: str,
    outputs_revision: str | None = None,
) -> dict[str, str | None]:
    return {
        "orchestration_revision": None,
        "metadata_revision": metadata_revision,
        "outputs_revision": outputs_revision,
    }


def _run_directory_updated_at(runid: str) -> str | None:
    if not runid:
        return None
    try:
        wd = Path(get_wd(runid))
        if not wd.exists():
            return None
        now_ts = datetime.now(timezone.utc).timestamp()
        safe_mtime = min(float(wd.stat().st_mtime), float(now_ts))
        return datetime.fromtimestamp(safe_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def _runtime_snapshot_updated_at(*, runid: str, generated_at: str) -> str:
    run_directory_updated_at = _run_directory_updated_at(runid)
    if run_directory_updated_at:
        return run_directory_updated_at

    generated_text = str(generated_at or "").strip()
    if generated_text:
        return generated_text
    return _utc_timestamp()


def _stable_updated_at(
    *,
    candidate_updated_at: str | None,
    fallback_updated_at: str,
) -> str:
    if candidate_updated_at:
        return candidate_updated_at
    return fallback_updated_at


def _snapshot_freshness(
    *,
    data_state: str,
    data_updated_at: str | None,
    fallback_updated_at: str,
) -> dict[str, Any]:
    updated_at = _stable_updated_at(
        candidate_updated_at=data_updated_at,
        fallback_updated_at=fallback_updated_at,
    )
    if data_state in {"materialized", "stale", "error"} and data_updated_at is None:
        data_updated_at = updated_at
    return {
        "updated_at": updated_at,
        "data_state": data_state,
        "data_updated_at": data_updated_at,
    }


def _normalize_config_token(value: str) -> str:
    text = str(value or "").strip().lower()
    if text.endswith(".cfg"):
        return text[:-4]
    return text


def _enum_name(value: Any) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name.lower()
    text = str(value).strip()
    if not text:
        return None
    return text.lower()


def _enum_int(value: Any) -> int | None:
    if value is None:
        return None
    candidate = getattr(value, "value", value)
    try:
        return int(candidate)
    except (TypeError, ValueError):
        return None


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    return _normalize_scopes(claims.get("scope"), get_jwt_config().scope_separator)


def _require_schema_defaults_claims(request: Request, runid: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if not scopes.intersection(SCHEMA_DEFAULTS_ALLOWED_SCOPES):
        required_text = ", ".join(sorted(SCHEMA_DEFAULTS_ALLOWED_SCOPES))
        raise AuthError(
            f"Token missing required scope(s): {required_text}",
            status_code=403,
            code="forbidden",
        )
    authorize_run_access(claims, runid)
    return claims


def _compute_run_state_revision(runid: str, payload: Mapping[str, Any]) -> str:
    digest_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12]
    return f"runstate:{runid}:{digest}"


def _load_runtime_state(runid: str, config: str) -> RuntimeState:
    wd = get_wd(runid)
    if not Path(wd).is_dir():
        raise FileNotFoundError(f"Unknown run '{runid}'")

    ron = Ron.getInstance(wd)
    requested_config = _normalize_config_token(config)
    actual_config = _normalize_config_token(getattr(ron, "config_stem", ""))
    if requested_config and actual_config and requested_config != actual_config:
        raise RunConfigMismatchError(
            f"Run config mismatch: path config '{config}' does not match run config '{actual_config}'."
        )

    watershed = Watershed.getInstance(wd)
    climate = Climate.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    prep = RedisPrep.getInstance(wd)

    active_mods = tuple(sorted({str(mod).strip() for mod in (ron.mods or ()) if str(mod).strip()}, key=str.casefold))
    active_mod_tokens = {mod.lower() for mod in active_mods}
    disturbed_enabled = "disturbed" in active_mod_tokens
    sbs_upload_supported = bool(active_mod_tokens.intersection({"disturbed", "baer", "ash", "debris_flow"}))
    initial_sat: float | None = None
    initial_sat_value = getattr(soils, "initial_sat", None)
    try:
        initial_sat = float(initial_sat_value) if initial_sat_value is not None else None
    except (TypeError, ValueError):
        initial_sat = None

    disturbed_sol_ver: float | None = None
    if disturbed_enabled:
        disturbed = Disturbed.getInstance(wd)
        sol_ver_value = getattr(disturbed, "sol_ver", None)
        try:
            disturbed_sol_ver = float(sol_ver_value) if sol_ver_value is not None else None
        except (TypeError, ValueError):
            disturbed_sol_ver = None

    map_bounds: list[float] | None = None
    map_center: list[float] | None = None
    map_zoom: float | None = None
    map_resolution: float | None = None

    map_obj = getattr(ron, "map", None)
    if map_obj is not None:
        extent = getattr(map_obj, "extent", None)
        center = getattr(map_obj, "center", None)
        zoom = getattr(map_obj, "zoom", None)
        cellsize = getattr(map_obj, "cellsize", None)
        if isinstance(extent, (list, tuple)) and len(extent) == 4:
            try:
                map_bounds = [float(v) for v in extent]
            except (TypeError, ValueError):
                map_bounds = None
        if isinstance(center, (list, tuple)) and len(center) == 2:
            try:
                map_center = [float(center[0]), float(center[1])]
            except (TypeError, ValueError):
                map_center = None
        try:
            map_zoom = float(zoom) if zoom is not None else None
        except (TypeError, ValueError):
            map_zoom = None
        try:
            map_resolution = float(cellsize) if cellsize is not None else None
        except (TypeError, ValueError):
            map_resolution = None

    if map_center is None:
        center0 = getattr(ron, "center0", None)
        if isinstance(center0, (list, tuple)) and len(center0) == 2:
            try:
                # `Ron.center0` is lat/lon while map payloads are lon/lat.
                map_center = [float(center0[1]), float(center0[0])]
            except (TypeError, ValueError):
                map_center = None

    if map_zoom is None:
        zoom0 = getattr(ron, "zoom0", None)
        try:
            map_zoom = float(zoom0) if zoom0 is not None else 11.0
        except (TypeError, ValueError):
            map_zoom = 11.0

    if map_resolution is None:
        try:
            map_resolution = float(getattr(ron, "cellsize", None) or 30.0)
        except (TypeError, ValueError):
            map_resolution = 30.0

    watershed_csa: float | None = None
    csa_value = getattr(watershed, "csa", None)
    try:
        watershed_csa = float(csa_value) if csa_value is not None else None
    except (TypeError, ValueError):
        watershed_csa = None

    watershed_mcl: float | None = None
    mcl_value = getattr(watershed, "mcl", None)
    try:
        watershed_mcl = float(mcl_value) if mcl_value is not None else None
    except (TypeError, ValueError):
        watershed_mcl = None

    watershed_stream_pruning_method_raw = getattr(
        watershed, "stream_pruning_method", None
    )
    watershed_stream_pruning_method = str(
        watershed_stream_pruning_method_raw or "ifolp"
    ).strip().lower()
    if watershed_stream_pruning_method not in {"ifolp", "remove_short_streams"}:
        watershed_stream_pruning_method = "ifolp"

    delineation_backend: str | None = None
    backend_value = getattr(watershed, "delineation_backend", None)
    if backend_value is not None:
        backend_name = getattr(backend_value, "name", str(backend_value))
        backend_text = str(backend_name or "").strip().lower()
        delineation_backend = backend_text or None

    region = str(getattr(ron, "region", "") or "").strip() or None
    if region is None:
        locales = getattr(ron, "_locales", None)
        if isinstance(locales, (list, tuple)) and locales:
            region = str(locales[0] or "").strip() or None

    dem_source = str(getattr(ron, "dem_db", "") or "").strip() or "unknown"
    uploaded_dem_filename_raw = str(getattr(watershed, "uploaded_dem_filename", "") or "").strip() or None
    uploaded_dem_filename: str | None = None
    if uploaded_dem_filename_raw:
        uploaded_dem_filename = secure_filename(Path(uploaded_dem_filename_raw).name) or None
    climate_station_required = bool(getattr(climate, "has_climatestation_mode", False))

    states: dict[str, Any] = {
        "has_dem": bool(getattr(ron, "has_dem", False)),
        "watershed_has_channels": bool(getattr(watershed, "has_channels", False)),
        "watershed_has_outlet": bool(getattr(watershed, "has_outlet", False)),
        "watershed_is_abstracted": bool(getattr(watershed, "is_abstracted", False)),
        "watershed_subcatchment_count": int(getattr(watershed, "sub_n", 0) or 0),
        "watershed_csa": watershed_csa,
        "watershed_mcl": watershed_mcl,
        "watershed_stream_pruning_method": watershed_stream_pruning_method,
        "delineation_backend": delineation_backend,
        "climate_built": bool(getattr(climate, "has_climate", False)),
        "climate_mode_code": _enum_int(getattr(climate, "climate_mode", None)),
        "climate_mode": _enum_name(getattr(climate, "climate_mode", None)),
        "climate_has_station": bool(getattr(climate, "has_station", False)),
        "climate_station_required": climate_station_required,
        "landuse_built": bool(getattr(landuse, "has_landuse", False)),
        "landuse_mode": _enum_name(getattr(landuse, "mode", None)),
        "soils_built": bool(getattr(soils, "has_soils", False)),
        "soils_mode": _enum_name(getattr(soils, "mode", None)),
        "initial_sat": initial_sat,
        "wepp_has_run": bool(getattr(wepp, "has_run", False)),
        "disturbed_enabled": disturbed_enabled,
        "sbs_upload_supported": sbs_upload_supported,
        "disturbed_sbs_uploaded": bool(getattr(prep, "has_sbs", False)),
        "disturbed_sol_ver": disturbed_sol_ver,
        "map_center": map_center,
        "map_bounds": map_bounds,
        "map_zoom": map_zoom,
        "map_zoom_resolution_m_per_px": map_resolution,
        "dem_coverage_source": dem_source,
        "uploaded_dem_filename": uploaded_dem_filename,
    }

    generated_at = _utc_timestamp()
    snapshot_fallback_updated_at = _runtime_snapshot_updated_at(
        runid=runid,
        generated_at=generated_at,
    )
    revision_source = {
        "config": actual_config or requested_config or config,
        "active_mods": list(active_mods),
        "region": region,
        "states": states,
        "snapshot_fallback_updated_at": snapshot_fallback_updated_at,
    }
    run_state_revision = _compute_run_state_revision(runid, revision_source)

    resolved_config = actual_config or requested_config or config
    return RuntimeState(
        runid=runid,
        config=resolved_config,
        active_mods=active_mods,
        region=region,
        states=states,
        generated_at=generated_at,
        run_state_revision=run_state_revision,
    )


def _read_auth_requirements() -> dict[str, Any]:
    return {
        "bearer_jwt": {
            "required_any_scope": sorted(SCHEMA_DEFAULTS_ALLOWED_SCOPES),
        }
    }


def _empty_request_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "additional_properties": False,
    }


def _predicate(field: str, op: str, value: Any) -> dict[str, Any]:
    return {
        "field": field,
        "op": op,
        "value": value,
    }


def _sbs_available_if() -> dict[str, Any]:
    return {
        "any": [
            _predicate("context.active_mods", "contains", "disturbed"),
            _predicate("context.active_mods", "contains", "baer"),
            _predicate("context.active_mods", "contains", "ash"),
            _predicate("context.active_mods", "contains", "debris_flow"),
        ]
    }


def _rusle_available_if() -> dict[str, Any]:
    return {
        "any": [
            _predicate("context.active_mods", "contains", "disturbed"),
            _predicate("context.active_mods", "contains", "baer"),
        ]
    }


def _base_run_read_descriptor(
    *,
    runtime: RuntimeState,
    operation_id: str,
    path: str,
    required_fields: list[str],
) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "run_scoped": True,
        "method": "GET",
        "path": path,
        "accepted_auth": ["bearer_jwt"],
        "auth_requirements": _read_auth_requirements(),
        "required_if": [],
        "available_if": [],
        "error_catalog_url": (
            f"/api/runs/{runtime.runid}/{runtime.config}/endpoints/{operation_id}/errors"
        ),
        "write_precondition": {
            "required": False,
            "accepted": [],
            "conflict_status_code": 409,
            "conflict_error_code": "stale_run_state",
        },
        "idempotency_policy": {
            "supported": False,
            "key_locations": [],
            "dedupe_window_seconds": 0,
            "replay_behavior": "return_original_success",
            "mismatch_status_code": 409,
            "mismatch_error_code": "idempotency_key_conflict",
        },
        "execution_mode": "sync",
        "returns_job": False,
        "job_key": None,
        "content_types": ["application/json"],
        "file_fields": [],
        "success_status_codes": [200],
        "response_mode": "json",
        "result_contract": {
            "kind": "sync_result",
            "required_response_fields": required_fields,
            "terminal_signal": "http_status_2xx",
        },
        "estimated_duration": {
            "bucket": "fast",
            "typical_seconds": 1,
        },
        "batch_mode_behavior": "n/a",
        "base_project_behavior": "allowed",
        "mutates_controllers": [],
        "invalidates_steps": [],
    }


def _base_run_mutation_descriptor(
    *,
    runtime: RuntimeState,
    operation_id: str,
    path: str,
    execution_mode: str,
    returns_job: bool,
    job_key: str | None,
    required_fields: list[str],
    estimated_duration_bucket: str,
    estimated_duration_seconds: int,
    mutates_controllers: list[str],
    invalidates_steps: list[str],
    content_types: list[str] | None = None,
    file_fields: list[dict[str, Any]] | None = None,
    auth_requirements: dict[str, Any] | None = None,
    accepted_auth: list[str] | None = None,
    write_precondition_required: bool = False,
    write_precondition_accepted: list[str] | None = None,
    idempotency_supported: bool = False,
    idempotency_dedupe_window_seconds: int | None = None,
    replay_behavior: str = "return_original_success",
    required_if: list[dict[str, Any]] | None = None,
    available_if: list[dict[str, Any]] | None = None,
    batch_mode_behavior: str = "n/a",
    base_project_behavior: str = "allowed",
    async_poll_url_field: str | None = None,
) -> dict[str, Any]:
    descriptor_auth_requirements = auth_requirements or {
        "bearer_jwt": {
            "required_scope": ["rq:enqueue"],
        }
    }
    descriptor_accepted_auth = accepted_auth or ["bearer_jwt"]
    accepted_preconditions = (
        write_precondition_accepted
        if write_precondition_accepted is not None
        else (["x_run_state_match", "expected_run_state_revision"] if write_precondition_required else [])
    )

    resolved_replay_behavior = replay_behavior if idempotency_supported else "not_supported"

    dedupe_window_seconds = (
        int(idempotency_dedupe_window_seconds)
        if idempotency_dedupe_window_seconds is not None and idempotency_supported
        else 86400
    )

    idempotency_policy: dict[str, Any] = {
        "supported": idempotency_supported,
        "key_locations": ["header:Idempotency-Key"] if idempotency_supported else [],
        "dedupe_window_seconds": dedupe_window_seconds if idempotency_supported else 0,
        "replay_behavior": resolved_replay_behavior,
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict",
    }
    if idempotency_supported and resolved_replay_behavior == "reject_duplicate":
        idempotency_policy["duplicate_replay_status_code"] = 409
        idempotency_policy["duplicate_replay_error_code"] = "idempotency_replay_rejected"

    result_contract: dict[str, Any] = {
        "kind": "sync_result",
        "required_response_fields": required_fields,
        "terminal_signal": "http_status_2xx",
    }
    if execution_mode == "async":
        result_contract = {
            "kind": "async_job",
            "required_response_fields": required_fields,
            "terminal_signal": "jobstatus.status in terminal_*_statuses",
            "status_field": "status",
            "non_terminal_statuses": ["queued", "started", "deferred", "scheduled"],
            "terminal_success_statuses": ["finished"],
            "terminal_failure_statuses": ["failed", "stopped", "canceled"],
            "suggested_poll_interval_seconds": 5,
            "progress_field": "progress",
        }
        if async_poll_url_field:
            result_contract["next_poll_url_field"] = async_poll_url_field
        else:
            result_contract["status_url_template"] = "/api/jobstatus/{job_id}"

    return {
        "operation_id": operation_id,
        "run_scoped": True,
        "method": "POST",
        "path": path,
        "accepted_auth": descriptor_accepted_auth,
        "auth_requirements": descriptor_auth_requirements,
        "required_if": required_if or [],
        "available_if": available_if or [],
        "error_catalog_url": (
            f"/api/runs/{runtime.runid}/{runtime.config}/endpoints/{operation_id}/errors"
        ),
        "write_precondition": {
            "required": write_precondition_required,
            "accepted": accepted_preconditions,
            "conflict_status_code": 409,
            "conflict_error_code": "stale_run_state",
        },
        "idempotency_policy": idempotency_policy,
        "execution_mode": execution_mode,
        "returns_job": returns_job,
        "job_key": job_key,
        "content_types": content_types or ["application/json", "application/x-www-form-urlencoded"],
        "file_fields": file_fields or [],
        "success_status_codes": [200],
        "response_mode": "json",
        "result_contract": result_contract,
        "estimated_duration": {
            "bucket": estimated_duration_bucket,
            "typical_seconds": estimated_duration_seconds,
        },
        "batch_mode_behavior": batch_mode_behavior,
        "base_project_behavior": base_project_behavior,
        "mutates_controllers": mutates_controllers,
        "invalidates_steps": invalidates_steps,
    }


def _controller_names(runtime: RuntimeState) -> tuple[str, ...]:
    names = ["watershed", "climate", "landuse", "soils", "wepp"]
    if bool(runtime.states.get("disturbed_enabled", False)):
        names.append("disturbed")
    return tuple(sorted(names))


def _controller_defaults(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    climate_mode = runtime.states.get("climate_mode_code")
    default_climate_mode = 11 if disturbed_enabled else 0

    if controller == "climate":
        resolved_mode = climate_mode if climate_mode is not None else default_climate_mode
        defaults: dict[str, Any] = {
            "climate_mode": resolved_mode,
        }
        if resolved_mode == 3:
            defaults.update(
                {
                    "future_start_year": 2040,
                    "future_end_year": 2060,
                }
            )
        else:
            defaults.update(
                {
                    "observed_start_year": 1990,
                    "observed_end_year": 2020,
                }
            )
        return defaults
    if controller == "landuse":
        return {
            "landuse_mode": runtime.states.get("landuse_mode") or "nlcd",
        }
    if controller == "soils":
        defaults = {
            "soils_mode": runtime.states.get("soils_mode") or "ssurgo",
        }
        if disturbed_enabled:
            defaults["sol_ver"] = _default_disturbed_sol_ver(runtime)
        return defaults
    if controller == "watershed":
        return _resolved_watershed_defaults(runtime)
    if controller == "wepp":
        return {
            "clip_soils": disturbed_enabled,
            "clip_soils_depth": 25.0,
        }
    if controller == "disturbed":
        return {
            "sol_ver": _default_disturbed_sol_ver(runtime),
        }
    return {}


def _controller_schema(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    sol_ver_available = _disturbed_sol_ver_options(runtime)
    sol_ver_labels = {
        "2006.0": "Legacy disturbed defaults",
        "2018.0": "Updated disturbed defaults",
        "9002.0": "Disturbed9002 calibration defaults",
    }

    if controller == "climate":
        available_modes = _available_climate_modes(runtime)

        return {
            "schema_version": 1,
            "fields": {
                "climate_mode": {
                    "type": "integer",
                    "required": True,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "enum": [0, 2, 3, 5, 6, 11],
                    "enum_available": available_modes,
                    "enum_labels": {
                        "0": "Synthetic CLIGEN",
                        "2": "Observed station",
                        "3": "Future CMIP5",
                        "5": "Stochastic PRISM",
                        "6": "Observed database",
                        "11": "GridMet+PRISM",
                    },
                },
                "climatestation": {
                    "type": "string",
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "available_if": _predicate("climate_mode", "in", [2, 6]),
                    "required_if": _predicate("climate_mode", "in", [2, 6]),
                },
                "observed_start_year": {
                    "type": "integer",
                    "minimum": 1900,
                    "maximum": 2100,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [2, 11]),
                },
                "observed_end_year": {
                    "type": "integer",
                    "minimum": 1900,
                    "maximum": 2100,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [2, 11]),
                },
                "future_start_year": {
                    "type": "integer",
                    "minimum": 2006,
                    "maximum": 2099,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "eq", 3),
                },
                "future_end_year": {
                    "type": "integer",
                    "minimum": 2006,
                    "maximum": 2099,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "eq", 3),
                },
            },
        }

    if controller == "landuse":
        modes = ["nlcd", "custom"]
        if disturbed_enabled:
            modes.append("disturbed")

        return {
            "schema_version": 1,
            "fields": {
                "landuse_mode": {
                    "type": "string",
                    "required": True,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "enum": sorted(modes),
                    "enum_available": sorted(modes),
                },
                "cover_transform_uploaded": {
                    "type": "boolean",
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                },
            },
        }

    if controller == "soils":
        soils_modes = _supported_soils_modes()
        return {
            "schema_version": 1,
            "fields": {
                "soils_mode": {
                    "type": "string",
                    "required": True,
                    "constraint_mode": "static",
                    "enum": soils_modes,
                    "enum_available": soils_modes,
                },
                "sol_ver": {
                    "type": "number",
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "enum_available": sol_ver_available if disturbed_enabled else [],
                    "enum_labels": {
                        key: value
                        for key, value in sol_ver_labels.items()
                        if float(key) in sol_ver_available
                    },
                    "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                    "required_if": _predicate("context.active_mods", "contains", "disturbed"),
                },
            },
        }

    if controller == "watershed":
        return {
            "schema_version": 1,
            "fields": {
                "csa": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": resolved_at,
                },
                "mcl": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": resolved_at,
                },
                "expected_run_state_revision": {
                    "type": "string",
                    "required": False,
                    "constraint_mode": "static",
                },
            },
        }

    if controller == "wepp":
        return {
            "schema_version": 1,
            "fields": {
                "clip_soils": {
                    "type": "boolean",
                    "required": False,
                    "constraint_mode": "static",
                },
                "clip_soils_depth": {
                    "type": "number",
                    "minimum": 0.0,
                    "required": False,
                    "constraint_mode": "static",
                    "available_if": _predicate("clip_soils", "eq", True),
                    "required_if": _predicate("clip_soils", "eq", True),
                },
                "initial_sat": {
                    "type": "number",
                    "required": False,
                    "constraint_mode": "static",
                },
            },
        }

    if controller == "disturbed":
        return {
            "schema_version": 1,
            "fields": {
                "sol_ver": {
                    "type": "number",
                    "required": True,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                    "enum_available": sol_ver_available,
                },
                "sbs_uploaded": {
                    "type": "boolean",
                    "required": False,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": resolved_at,
                },
            },
        }

    raise KeyError(controller)


def _controller_hints(controller: str) -> dict[str, Any]:
    hints: dict[str, dict[str, Any]] = {
        "climate": {
            "schema_version": 1,
            "context_fields": ["context.active_mods", "context.region"],
            "groups": [
                {
                    "id": "mode",
                    "label": "Mode",
                    "fields": ["climate_mode", "climatestation"],
                },
                {
                    "id": "window",
                    "label": "Observed window",
                    "fields": ["observed_start_year", "observed_end_year"],
                },
                {
                    "id": "future_window",
                    "label": "Future window",
                    "fields": ["future_start_year", "future_end_year"],
                },
            ],
            "field_hints": {
                "climate_mode": {
                    "label": "Climate mode",
                    "help": "Choose station or gridded mode before build-climate.",
                },
                "climatestation": {
                    "label": "Climate station",
                    "help": "Required only for observed station/database modes.",
                },
                "future_start_year": {
                    "label": "Future start year",
                    "help": "Required only for future climate mode.",
                },
                "future_end_year": {
                    "label": "Future end year",
                    "help": "Required only for future climate mode.",
                },
            },
        },
        "landuse": {
            "schema_version": 1,
            "context_fields": ["context.active_mods"],
            "groups": [
                {
                    "id": "landuse",
                    "label": "Landuse",
                    "fields": ["landuse_mode", "cover_transform_uploaded"],
                }
            ],
            "field_hints": {
                "landuse_mode": {
                    "label": "Landuse mode",
                    "help": "Use disturbed mode after SBS/cover-transform uploads.",
                }
            },
        },
        "soils": {
            "schema_version": 1,
            "context_fields": ["context.active_mods"],
            "groups": [
                {
                    "id": "soils",
                    "label": "Soils",
                    "fields": ["soils_mode", "sol_ver"],
                }
            ],
            "field_hints": {
                "sol_ver": {
                    "label": "Disturbed soil profile",
                    "help": "Needed when disturbed mod is active.",
                }
            },
        },
        "watershed": {
            "schema_version": 1,
            "context_fields": ["context.region"],
            "groups": [
                {
                    "id": "delineation",
                    "label": "Delineation",
                    "fields": ["csa", "mcl"],
                }
            ],
            "field_hints": {
                "csa": {
                    "label": "Critical source area",
                    "help": "Higher values reduce channel density.",
                }
            },
        },
        "wepp": {
            "schema_version": 1,
            "context_fields": ["context.active_mods"],
            "groups": [
                {
                    "id": "run_options",
                    "label": "Run options",
                    "fields": ["clip_soils", "clip_soils_depth", "initial_sat"],
                }
            ],
            "field_hints": {
                "clip_soils": {
                    "label": "Clip soils",
                    "help": "Enable for disturbed workflows to constrain soil updates.",
                },
                "initial_sat": {
                    "label": "Initial saturation",
                    "help": "Optional saturation override applied before running WEPP.",
                },
            },
        },
        "disturbed": {
            "schema_version": 1,
            "context_fields": ["context.active_mods"],
            "groups": [
                {
                    "id": "disturbed",
                    "label": "Disturbed",
                    "fields": ["sol_ver", "sbs_uploaded"],
                }
            ],
            "field_hints": {
                "sbs_uploaded": {
                    "label": "SBS uploaded",
                    "help": "Upload SBS before build-soils/build-landuse reruns.",
                }
            },
        },
    }

    if controller not in hints:
        raise KeyError(controller)
    return hints[controller]


def _controller_templates(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    active_mods = list(runtime.active_mods)
    region = runtime.region or "unknown"
    run_defaults = _controller_defaults(controller, runtime)

    if controller == "climate":
        templates = [
            {
                "template_id": "default_run_resolved",
                "display_name": "Run-resolved climate defaults",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": copy.deepcopy(run_defaults),
                "sufficient_without_overrides": True,
            },
            {
                "template_id": "observed_station_required",
                "display_name": "Observed station climate",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": {
                    "climate_mode": 2,
                    "observed_start_year": 1990,
                    "observed_end_year": 2020,
                },
                "sufficient_without_overrides": False,
                "missing_required_fields": ["climatestation"],
            },
        ]
    else:
        templates = [
            {
                "template_id": f"{controller}_default",
                "display_name": f"{controller.title()} default",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": copy.deepcopy(run_defaults),
                "sufficient_without_overrides": True,
            }
        ]

    return {
        "templates": templates,
        "run_resolved_defaults": run_defaults,
    }


def _controller_catalog(runtime: RuntimeState) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for name in _controller_names(runtime):
        base_url = f"/api/runs/{runtime.runid}/{runtime.config}/controllers/{name}"
        catalog[name] = {
            "name": name,
            "enabled": True,
            "schema_url": f"{base_url}/schema",
            "hints_url": f"{base_url}/hints",
            "templates_url": f"{base_url}/templates",
            "capabilities": {
                "schema": True,
                "hints": True,
                "templates": True,
            },
        }
    return catalog


def _defaults_context(runtime: RuntimeState) -> dict[str, Any]:
    return {
        "config": runtime.config,
        "active_mods": list(runtime.active_mods),
        "region": runtime.region,
    }


def _operation_required_fields(operation_docs: Mapping[str, Any]) -> list[str]:
    schema = operation_docs.get("schema")
    if not isinstance(schema, Mapping):
        return []
    request = schema.get("request")
    if not isinstance(request, Mapping):
        return []
    required = request.get("required")
    if not isinstance(required, list):
        return []
    fields: list[str] = []
    for raw in required:
        value = str(raw or "").strip()
        if not value or value in fields:
            continue
        fields.append(value)
    return fields


def _build_operation_error_catalog(
    *,
    operation_id: str,
    operation_docs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    descriptor = operation_docs.get("descriptor")
    descriptor_map = descriptor if isinstance(descriptor, Mapping) else {}
    method = str(descriptor_map.get("method") or "").strip().upper()
    execution_mode = str(descriptor_map.get("execution_mode") or "").strip().lower()
    write_precondition = descriptor_map.get("write_precondition")
    write_precondition_map = write_precondition if isinstance(write_precondition, Mapping) else {}
    idempotency_policy = descriptor_map.get("idempotency_policy")
    idempotency_policy_map = idempotency_policy if isinstance(idempotency_policy, Mapping) else {}
    required_fields = _operation_required_fields(operation_docs)

    list_run_endpoints_id = rq_operation_id("list_run_endpoints")
    errors: list[dict[str, Any]] = [
        {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
        {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
        {
            "error_code": "not_found",
            "recoverable": True,
            "http_statuses": [404],
            "recovery_actions": [{"operation_id": list_run_endpoints_id, "required_fields": []}],
        },
    ]

    if method == "POST":
        errors.append(
            {
                "error_code": "validation_error",
                "recoverable": True,
                "http_statuses": [400],
                "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
            }
        )

        accepted_preconditions = write_precondition_map.get("accepted")
        has_accepted_preconditions = isinstance(accepted_preconditions, list) and len(accepted_preconditions) > 0
        if bool(write_precondition_map.get("required")) or has_accepted_preconditions:
            errors.append(
                {
                    "error_code": "stale_run_state",
                    "recoverable": True,
                    "http_statuses": [409],
                    "recovery_actions": [
                        {
                            "operation_id": operation_id,
                            "required_fields": ["expected_run_state_revision"],
                        }
                    ],
                }
            )

        if bool(idempotency_policy_map.get("supported")):
            mismatch_status_code = int(idempotency_policy_map.get("mismatch_status_code") or 409)
            mismatch_error_code = str(idempotency_policy_map.get("mismatch_error_code") or "idempotency_key_conflict")
            errors.append(
                {
                    "error_code": mismatch_error_code,
                    "recoverable": True,
                    "http_statuses": [mismatch_status_code],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
                }
            )

            replay_behavior = str(idempotency_policy_map.get("replay_behavior") or "").strip().lower()
            if replay_behavior == "reject_duplicate":
                duplicate_status_code = int(idempotency_policy_map.get("duplicate_replay_status_code") or 409)
                duplicate_error_code = str(
                    idempotency_policy_map.get("duplicate_replay_error_code") or "idempotency_replay_rejected"
                )
                errors.append(
                    {
                        "error_code": duplicate_error_code,
                        "recoverable": True,
                        "http_statuses": [duplicate_status_code],
                        "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
                    }
                )

        if execution_mode == "async":
            errors.append(
                {
                    "error_code": "enqueue_failed",
                    "recoverable": True,
                    "http_statuses": [500],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": []}],
                }
            )

    if operation_id == rq_operation_id("build_climate"):
        errors.extend(
            [
                {
                    "error_code": "missing_station_selection",
                    "recoverable": True,
                    "http_statuses": [400, 409],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": ["climatestation"]}],
                },
                {
                    "error_code": "climate_mode_unavailable_for_region",
                    "recoverable": True,
                    "http_statuses": [400],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": ["climate_mode"]}],
                },
            ]
        )

    if operation_id in {
        rq_operation_id("run_wepp"),
        rq_operation_id("run_wepp_watershed"),
    }:
        errors.append(
            {
                "error_code": "invalid_watershed_abstraction_state",
                "recoverable": True,
                "http_statuses": [409],
                "recovery_actions": [
                    {
                        "operation_id": rq_operation_id(
                            "build_subcatchments_and_abstract_watershed"
                        ),
                        "required_fields": [],
                    }
                ],
                "recovery_notes": [
                    "This recovery action enqueues subcatchment rebuild work only "
                    "outside batch/_base contexts. Batch/_base callers must "
                    "materialize watershed.subwta through their normal setup flow "
                    "before retrying run-wepp endpoints."
                ],
            }
        )

    return errors


def _build_operation_docs_snapshot(
    *,
    operations: Mapping[str, Mapping[str, Any]],
    computed_at: str,
) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for operation_id, operation_docs in operations.items():
        descriptor = copy.deepcopy(operation_docs["descriptor"])
        schema = copy.deepcopy(operation_docs["schema"])
        defaults_doc = copy.deepcopy(operation_docs["defaults"])
        snapshot[operation_id] = {
            "operation_descriptor": descriptor,
            "schema_version": schema["schema_version"],
            "request": schema["request"],
            "responses": schema["responses"],
            "resolved_defaults": defaults_doc["resolved_defaults"],
            "defaults_context": defaults_doc["defaults_context"],
            "computed_at": computed_at,
            "errors": _build_operation_error_catalog(
                operation_id=operation_id,
                operation_docs=operation_docs,
            ),
        }
    return snapshot


def _parse_iso_datetime(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=256)
def _sha256_file_cached(path_text: str, size_bytes: int, mtime_ns: int) -> str:
    path = Path(path_text)
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file(path: Path, *, size_bytes: int | None = None, mtime_ns: int | None = None) -> str:
    stat_result = path.stat() if (size_bytes is None or mtime_ns is None) else None
    resolved_size = int(size_bytes if size_bytes is not None else stat_result.st_size)
    if mtime_ns is not None:
        resolved_mtime_ns = int(mtime_ns)
    else:
        raw_mtime_ns = getattr(stat_result, "st_mtime_ns", int(float(stat_result.st_mtime) * 1_000_000_000))
        resolved_mtime_ns = int(raw_mtime_ns)
    return _sha256_file_cached(str(path.resolve()), resolved_size, resolved_mtime_ns)


def _artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "zip"
    if suffix == ".gpkg":
        return "geopackage"
    if suffix == ".gdb":
        return "geodatabase"
    return suffix.lstrip(".") or "artifact"


def _build_features_export_artifact(runtime: RuntimeState, *, wd: str) -> dict[str, Any] | None:
    try:
        prep = RedisPrep.getInstance(wd)
        job_id = prep.get_rq_job_id(FEATURES_EXPORT_JOB_KEY)
        if not job_id:
            job_id = prep.get_rq_job_ids().get(FEATURES_EXPORT_JOB_KEY)
        if not job_id:
            return None

        job_info = get_wepppy_rq_job_info(job_id)
        job_runid = str(job_info.get("runid") or "").strip()
        if job_runid and job_runid != runtime.runid:
            logger.warning(
                "rq-engine outputs ignored features-export artifact with mismatched runid",
                extra={"requested_runid": runtime.runid, "job_runid": job_runid, "job_id": job_id},
            )
            return None

        job_status = str(job_info.get("status") or "").strip().lower()
        if job_status != "finished":
            return None

        job_result = job_info.get("result")
        if not isinstance(job_result, Mapping):
            job_result = None

        artifact_path, _artifact_relpath = resolve_download_artifact_path(
            wd,
            job_id=job_id,
            job_result=job_result,
        )
        artifact_path = artifact_path.resolve()
        wd_path = Path(wd).resolve()
        if wd_path != artifact_path and wd_path not in artifact_path.parents:
            logger.warning(
                "rq-engine outputs ignored artifact path outside run directory",
                extra={"runid": runtime.runid, "job_id": job_id, "artifact_path": str(artifact_path)},
            )
            return None

        artifact_stat = artifact_path.stat()
        manifest = load_job_manifest(wd, job_id)

        produced_at = None
        if isinstance(manifest, Mapping):
            produced_at = _parse_iso_datetime(manifest.get("generated_at_utc"))
        if produced_at is None:
            produced_at = _parse_iso_datetime(job_info.get("ended_at"))
        if produced_at is None:
            produced_at = UNKNOWN_UPDATED_AT

        source_run_state_revision = None
        if isinstance(manifest, Mapping):
            source_run_state_revision = str(
                manifest.get("source_run_state_revision")
                or manifest.get("run_state_revision")
                or ""
            ).strip() or None
            if source_run_state_revision is None:
                request_map = manifest.get("request")
                if isinstance(request_map, Mapping):
                    resolved_map = request_map.get("resolved")
                    if isinstance(resolved_map, Mapping):
                        source_run_state_revision = str(resolved_map.get("run_state_revision") or "").strip() or None
        if source_run_state_revision is None and isinstance(job_result, Mapping):
            source_run_state_revision = str(
                job_result.get("source_run_state_revision")
                or job_result.get("run_state_revision")
                or ""
            ).strip() or None
        if source_run_state_revision is None:
            source_run_state_revision = UNKNOWN_SOURCE_RUN_STATE_REVISION

        artifact_id = (
            str((job_result or {}).get("artifact_id") or "").strip()
            if isinstance(job_result, Mapping)
            else ""
        )
        if not artifact_id:
            artifact_id = f"features_export_{job_id}"

        download_url_template = "/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download"
        download_url = download_url_template.format(
            runid=runtime.runid,
            config=runtime.config,
            job_id=job_id,
        )
        content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"

        return {
            "id": artifact_id,
            "kind": _artifact_kind(artifact_path),
            "producer_operation_id": rq_operation_id("export_features_submit"),
            "producer_step_id": "export-features",
            "producer_job_id": job_id,
            "produced_at": produced_at,
            "source_run_state_revision": source_run_state_revision,
            "expires_at": None,
            "content_type": content_type,
            "size_bytes": artifact_stat.st_size,
            "sha256": _sha256_file(
                artifact_path,
                size_bytes=artifact_stat.st_size,
                mtime_ns=getattr(artifact_stat, "st_mtime_ns", None),
            ),
            "result_source": "jobinfo.result",
            "download_url": download_url,
            "download_url_params": {
                "runid": runtime.runid,
                "config": runtime.config,
                "job_id": job_id,
            },
            "download_url_template": download_url_template,
        }
    except (FeaturesExportServiceError, FileNotFoundError, OSError):
        return None
    except Exception:  # broad-except: outputs discovery best-effort boundary
        logger.exception("rq-engine outputs features-export artifact discovery failed")
        return None


def _outputs_export_catalog() -> list[dict[str, Any]]:
    return [
        {
            "operation_id": rq_operation_id("export_ermit"),
            "path": "/api/runs/{runid}/{config}/export/ermit",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_geopackage"),
            "path": "/api/runs/{runid}/{config}/export/geopackage",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_geodatabase"),
            "path": "/api/runs/{runid}/{config}/export/geodatabase",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_prep_details"),
            "path": "/api/runs/{runid}/{config}/export/prep_details",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_features_submit"),
            "path": "/api/runs/{runid}/{config}/export/features",
            "response_mode": "json",
        },
        {
            "operation_id": rq_operation_id("export_features_download"),
            "path": "/api/runs/{runid}/{config}/export/features/job/{job_id}/download",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_features_download_published"),
            "path": "/api/runs/{runid}/{config}/export/features/published/{profile}/download",
            "response_mode": "file",
        },
    ]


def _build_outputs_payload(runtime: RuntimeState) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    feature_artifact = _build_features_export_artifact(runtime, wd=get_wd(runtime.runid))
    if feature_artifact is not None:
        artifacts.append(feature_artifact)

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("produced_at") or ""),
            str(artifact.get("id") or ""),
        ),
        reverse=True,
    )

    exports = _outputs_export_catalog()
    data_updated_candidates = [str(item.get("produced_at")) for item in artifacts if item.get("produced_at")]
    data_updated_at = max(data_updated_candidates) if data_updated_candidates else None
    data_state = "materialized" if artifacts else "not_materialized"

    revision_input = {
        "metadata_revision": runtime.run_state_revision,
        "artifacts": artifacts,
        "exports": exports,
    }
    revision_digest = hashlib.sha256(
        json.dumps(revision_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    outputs_revision = f"runstate:{runtime.runid}:{revision_digest}"
    freshness = _snapshot_freshness(
        data_state=data_state,
        data_updated_at=data_updated_at,
        fallback_updated_at=_runtime_snapshot_updated_at(
            runid=runtime.runid,
            generated_at=runtime.generated_at,
        ),
    )

    return {
        "run_state_domain": RUN_STATE_DOMAIN_OUTPUTS,
        "run_state_revision": outputs_revision,
        "run_state_vector": _run_state_vector(
            metadata_revision=runtime.run_state_revision,
            outputs_revision=outputs_revision,
        ),
        **freshness,
        "etag": f'W/"outputs:{runtime.runid}:{revision_digest}"',
        "artifacts": artifacts,
        "exports": exports,
    }


def _available_climate_modes(runtime: RuntimeState) -> list[int]:
    modes = [0, 5, 6, 11]
    if bool(runtime.states.get("climate_has_station", False)):
        modes.insert(1, 2)

    supported_runtime_modes = {
        0,  # Vanilla
        2,  # Observed
        3,  # Future
        5,  # PRISM
        6,  # ObservedDb
        7,  # FutureDb
        8,  # EOBS
        9,  # ObservedPRISM
        10,  # AGDC
        11,  # GridMetPRISM
        12,  # UserDefined
        13,  # DepNexrad
    }

    current_mode_raw = runtime.states.get("climate_mode_code")
    try:
        current_mode = int(current_mode_raw) if current_mode_raw is not None else None
    except (TypeError, ValueError):
        current_mode = None
    if current_mode is not None and current_mode in supported_runtime_modes and current_mode not in modes:
        modes.append(current_mode)

    return modes


def _supported_soils_modes() -> list[str]:
    return ["ssurgo", "statsgo"]


def _inferred_config_sol_ver(config: str) -> float | None:
    token = str(config or "").strip().lower()
    if "9002" in token:
        return 9002.0
    return None


def _runtime_disturbed_sol_ver(runtime: RuntimeState) -> float | None:
    raw_value = runtime.states.get("disturbed_sol_ver")
    try:
        value = float(raw_value) if raw_value is not None else None
    except (TypeError, ValueError):
        return None
    return value if value is not None and value > 0 else None


def _default_disturbed_sol_ver(runtime: RuntimeState) -> float:
    runtime_value = _runtime_disturbed_sol_ver(runtime)
    if runtime_value is not None:
        return runtime_value

    inferred = _inferred_config_sol_ver(runtime.config)
    if inferred is not None:
        return inferred

    return 2018.0


def _disturbed_sol_ver_options(runtime: RuntimeState) -> list[float]:
    if not bool(runtime.states.get("disturbed_enabled", False)):
        return []

    options: list[float] = []
    for candidate in [2006.0, 2018.0, _inferred_config_sol_ver(runtime.config), _runtime_disturbed_sol_ver(runtime)]:
        if candidate is None:
            continue
        value = float(candidate)
        if value not in options:
            options.append(value)
    return options


def _resolved_watershed_defaults(runtime: RuntimeState) -> dict[str, Any]:
    csa_value = runtime.states.get("watershed_csa")
    mcl_value = runtime.states.get("watershed_mcl")
    stream_pruning_method_value = runtime.states.get("watershed_stream_pruning_method")
    csa = float(csa_value) if isinstance(csa_value, (int, float)) else 10.0
    mcl = float(mcl_value) if isinstance(mcl_value, (int, float)) else 75.0
    if isinstance(stream_pruning_method_value, str):
        stream_pruning_method = stream_pruning_method_value.strip().lower()
    else:
        stream_pruning_method = "ifolp"
    if stream_pruning_method not in {"ifolp", "remove_short_streams"}:
        stream_pruning_method = "ifolp"
    return {
        "csa": csa,
        "mcl": mcl,
        "stream_pruning_method": stream_pruning_method,
    }


def _float_list(value: Any, *, expected_len: int) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != expected_len:
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def _geospatial_payload(runtime: RuntimeState) -> dict[str, Any]:
    map_center = _float_list(runtime.states.get("map_center"), expected_len=2)
    map_bounds_raw = _float_list(runtime.states.get("map_bounds"), expected_len=4)
    map_bounds = map_bounds_raw
    map_bounds_is_run_resolved = map_bounds_raw is not None

    if map_bounds is None and map_center is not None:
        # Deterministic fallback extent for runs without a resolved DEM/map object yet.
        lon, lat = map_center
        map_bounds = [lon - 0.1, lat - 0.1, lon + 0.1, lat + 0.1]

    try:
        map_zoom = int(round(float(runtime.states.get("map_zoom"))))
    except (TypeError, ValueError):
        map_zoom = 11

    try:
        zoom_resolution = float(runtime.states.get("map_zoom_resolution_m_per_px"))
    except (TypeError, ValueError):
        zoom_resolution = 30.0

    csa_value = runtime.states.get("watershed_csa")
    mcl_value = runtime.states.get("watershed_mcl")
    stream_pruning_method_value = runtime.states.get("watershed_stream_pruning_method")
    watershed_defaults = _resolved_watershed_defaults(runtime)
    csa = watershed_defaults["csa"]
    mcl = watershed_defaults["mcl"]
    stream_pruning_method = watershed_defaults["stream_pruning_method"]

    climate_modes = _available_climate_modes(runtime)

    soils_modes_available = _supported_soils_modes()

    sol_ver_available = _disturbed_sol_ver_options(runtime)

    map_center_available = map_center is not None
    map_bounds_available = map_bounds_is_run_resolved
    csa_available = isinstance(csa_value, (int, float))
    mcl_available = isinstance(mcl_value, (int, float))
    stream_pruning_method_available = isinstance(stream_pruning_method_value, str)
    station_catalog_available = bool(runtime.states.get("has_dem", False) or map_bounds_is_run_resolved)

    field_availability: dict[str, dict[str, Any]] = {
        "map_center": {
            "state": "available" if map_center_available else "pending",
            **({} if map_center_available else {"reason_code": "awaiting_dem_upload"}),
        },
        "map_bounds": {
            "state": "available" if map_bounds_available else "pending",
            **({} if map_bounds_available else {"reason_code": "awaiting_dem_upload"}),
        },
        "map_zoom": {
            "state": "available",
        },
        "csa": {
            "state": "available" if csa_available else "pending",
            **({} if csa_available else {"reason_code": "awaiting_watershed_defaults"}),
        },
        "mcl": {
            "state": "available" if mcl_available else "pending",
            **({} if mcl_available else {"reason_code": "awaiting_watershed_defaults"}),
        },
        "stream_pruning_method": {
            "state": "available" if stream_pruning_method_available else "pending",
            **(
                {}
                if stream_pruning_method_available
                else {"reason_code": "awaiting_watershed_defaults"}
            ),
        },
        "station_catalog": {
            "state": "available" if station_catalog_available else "pending",
            **({} if station_catalog_available else {"reason_code": "awaiting_dem_fetch"}),
        },
    }

    dem_coverage: dict[str, Any] = {
        "supported": True,
        "source": str(runtime.states.get("dem_coverage_source") or "unknown"),
        "has_dem": bool(runtime.states.get("has_dem", False)),
        "extent_bbox": map_bounds_raw,
    }
    uploaded_dem_filename = runtime.states.get("uploaded_dem_filename")
    if isinstance(uploaded_dem_filename, str) and uploaded_dem_filename:
        dem_coverage["uploaded_dem_filename"] = uploaded_dem_filename
    delineation_backend = runtime.states.get("delineation_backend")
    if isinstance(delineation_backend, str) and delineation_backend:
        dem_coverage["delineation_backend"] = delineation_backend

    return {
        "runid": runtime.runid,
        "config": runtime.config,
        "region": runtime.region,
        "dem_coverage": dem_coverage,
        "recommended_defaults": {
            "map_center": map_center,
            "map_bounds": map_bounds,
            "map_zoom": map_zoom,
            "map_zoom_resolution_m_per_px": zoom_resolution,
            "csa": csa,
            "mcl": mcl,
            "stream_pruning_method": stream_pruning_method,
        },
        "dynamic_constraints": {
            "climate_mode": {
                "enum_available": climate_modes,
            },
            "soils_mode": {
                "enum_available": soils_modes_available,
            },
            "sol_ver": {
                "enum_available": sol_ver_available,
            },
        },
        "field_availability": field_availability,
        "computed_at": runtime.generated_at,
    }


def _build_run_operations(runtime: RuntimeState) -> dict[str, dict[str, Any]]:
    geospatial_metadata_id = rq_operation_id("geospatial_metadata")
    list_controllers_id = rq_operation_id("list_controllers")
    controller_schema_id = rq_operation_id("get_controller_schema")
    controller_hints_id = rq_operation_id("get_controller_hints")
    controller_templates_id = rq_operation_id("get_controller_templates")
    list_endpoints_id = rq_operation_id("list_run_endpoints")
    endpoint_schema_id = rq_operation_id("get_run_endpoint_schema")
    endpoint_defaults_id = rq_operation_id("get_run_endpoint_defaults")
    endpoint_errors_id = rq_operation_id("get_run_endpoint_errors")
    pipeline_id = rq_operation_id("get_pipeline")
    readiness_id = rq_operation_id("get_readiness")
    outputs_id = rq_operation_id("get_outputs")

    fetch_dem_and_build_channels_id = rq_operation_id("fetch_dem_and_build_channels")
    set_outlet_id = rq_operation_id("set_outlet")
    build_subcatchments_and_abstract_watershed_id = rq_operation_id(
        "build_subcatchments_and_abstract_watershed"
    )
    get_landuse_state_id = rq_operation_id("get_landuse_state")
    set_landuse_mode_id = rq_operation_id("set_landuse_mode")
    set_landuse_db_id = rq_operation_id("set_landuse_db")
    modify_landuse_coverage_id = rq_operation_id("modify_landuse_coverage")
    modify_landuse_mapping_id = rq_operation_id("modify_landuse_mapping")
    get_landuse_user_defined_catalog_id = rq_operation_id("get_landuse_user_defined_catalog")
    upload_landuse_user_defined_managements_id = rq_operation_id("upload_landuse_user_defined_managements")
    delete_landuse_user_defined_management_id = rq_operation_id("delete_landuse_user_defined_management")
    update_landuse_user_defined_management_description_id = rq_operation_id(
        "update_landuse_user_defined_management_description"
    )
    get_landuse_map_snapshot_id = rq_operation_id("get_landuse_map_snapshot")
    save_landuse_map_id = rq_operation_id("save_landuse_map")
    clear_landuse_map_override_id = rq_operation_id("clear_landuse_map_override")
    modify_landuse_id = rq_operation_id("modify_landuse")
    build_climate_id = rq_operation_id("build_climate")
    build_landuse_id = rq_operation_id("build_landuse")
    build_soils_id = rq_operation_id("build_soils")
    prep_wepp_id = rq_operation_id("prep_wepp_watershed")
    run_wepp_id = rq_operation_id("run_wepp")
    run_wepp_watershed_id = rq_operation_id("run_wepp_watershed")
    build_rusle_id = rq_operation_id("build_rusle")
    fork_project_id = rq_operation_id("fork_project")
    upload_dem_id = rq_operation_id("upload_dem")
    upload_cli_id = rq_operation_id("upload_cli")
    upload_cover_transform_id = rq_operation_id("upload_cover_transform")
    upload_sbs_id = rq_operation_id("upload_sbs")
    issue_session_token_id = rq_operation_id("issue_session_token")
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    active_mod_tokens = {mod.lower() for mod in runtime.active_mods}
    rusle_enabled = bool(active_mod_tokens.intersection({"disturbed", "baer"}))
    disturbed_sol_ver_options = _disturbed_sol_ver_options(runtime)
    build_soils_required_fields = ["initial_sat", "sol_ver"] if disturbed_enabled else ["initial_sat"]
    geospatial_defaults = _geospatial_payload(runtime).get("recommended_defaults", {})
    map_bounds_default = geospatial_defaults.get("map_bounds")
    map_center_default = geospatial_defaults.get("map_center")
    map_zoom_default = geospatial_defaults.get("map_zoom")
    watershed_defaults = _resolved_watershed_defaults(runtime)

    operations: dict[str, dict[str, Any]] = {
        list_controllers_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=list_controllers_id,
                path="/api/runs/{runid}/{config}/controllers",
                required_fields=["controllers"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["controllers"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    "controller_count": len(_controller_names(runtime)),
                    **_defaults_context(runtime),
                },
            },
        },
        get_landuse_state_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=get_landuse_state_id,
                path="/api/runs/{runid}/{config}/controllers/landuse/state",
                required_fields=[
                    "controller",
                    "state",
                    "run_state_domain",
                    "run_state_vector",
                    "run_state_revision",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": [
                            "controller",
                            "state",
                            "run_state_domain",
                            "run_state_vector",
                            "run_state_revision",
                        ]
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {
                    "controller": "landuse",
                    "state": _controller_defaults("landuse", runtime),
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        geospatial_metadata_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=geospatial_metadata_id,
                path="/api/runs/{runid}/{config}/geospatial-metadata",
                required_fields=[
                    "run_state_domain",
                    "run_state_vector",
                    "updated_at",
                    "data_state",
                    "data_updated_at",
                    "etag",
                    "dem_coverage",
                    "recommended_defaults",
                    "field_availability",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": [
                            "run_state_domain",
                            "run_state_vector",
                            "updated_at",
                            "data_state",
                            "data_updated_at",
                            "etag",
                            "dem_coverage",
                            "recommended_defaults",
                            "field_availability",
                        ],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        controller_schema_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=controller_schema_id,
                path="/api/runs/{runid}/{config}/controllers/{controller}/schema",
                required_fields=["controller", "fields"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "controller": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["controller"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["controller", "fields"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "controller": "climate",
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        controller_hints_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=controller_hints_id,
                path="/api/runs/{runid}/{config}/controllers/{controller}/hints",
                required_fields=["controller", "hints"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "controller": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["controller"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["controller", "hints"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "controller": "climate",
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        controller_templates_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=controller_templates_id,
                path="/api/runs/{runid}/{config}/controllers/{controller}/templates",
                required_fields=["controller", "templates"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "controller": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["controller"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["controller", "templates"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "controller": "climate",
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        list_endpoints_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=list_endpoints_id,
                path="/api/runs/{runid}/{config}/endpoints",
                required_fields=["operations"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM: {
                            "type": "boolean",
                            "constraint_mode": "static",
                            "required": False,
                            "default": False,
                        }
                    },
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["operations"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                    "operation_count": 0,
                },
            },
        },
        endpoint_schema_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=endpoint_schema_id,
                path="/api/runs/{runid}/{config}/endpoints/{operation_id}/schema",
                required_fields=["operation_id", "request"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "operation_id": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["operation_id"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["operation_id", "request"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "operation_id": build_climate_id,
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        endpoint_defaults_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=endpoint_defaults_id,
                path="/api/runs/{runid}/{config}/endpoints/{operation_id}/defaults",
                required_fields=["operation_id", "resolved_defaults"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "operation_id": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["operation_id"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["operation_id", "resolved_defaults"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "operation_id": build_climate_id,
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        endpoint_errors_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=endpoint_errors_id,
                path="/api/runs/{runid}/{config}/endpoints/{operation_id}/errors",
                required_fields=["operation_id", "errors"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "operation_id": {
                            "type": "string",
                            "constraint_mode": "static",
                        }
                    },
                    "required": ["operation_id"],
                    "additional_properties": False,
                },
                "responses": {"success": {"required": ["operation_id", "errors"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "operation_id": build_climate_id,
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                    "error_catalog": "stable",
                },
            },
        },
        pipeline_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=pipeline_id,
                path="/api/runs/{runid}/{config}/pipeline",
                required_fields=[
                    "run_state_domain",
                    "run_state_vector",
                    "updated_at",
                    "data_state",
                    "data_updated_at",
                    "etag",
                    "steps",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": [
                            "run_state_domain",
                            "run_state_vector",
                            "updated_at",
                            "data_state",
                            "data_updated_at",
                            "etag",
                            "steps",
                        ]
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        readiness_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=readiness_id,
                path="/api/runs/{runid}/{config}/readiness",
                required_fields=[
                    "run_state_domain",
                    "run_state_vector",
                    "updated_at",
                    "data_state",
                    "data_updated_at",
                    "etag",
                    "next_actionable_steps",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": [
                            "run_state_domain",
                            "run_state_vector",
                            "updated_at",
                            "data_state",
                            "data_updated_at",
                            "etag",
                            "next_actionable_steps",
                        ]
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                },
            },
        },
        outputs_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=outputs_id,
                path="/api/runs/{runid}/{config}/outputs",
                required_fields=[
                    "run_state_domain",
                    "run_state_vector",
                    "updated_at",
                    "data_state",
                    "data_updated_at",
                    "etag",
                    "artifacts",
                    "exports",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": [
                            "run_state_domain",
                            "run_state_vector",
                            "updated_at",
                            "data_state",
                            "data_updated_at",
                            "etag",
                            "artifacts",
                            "exports",
                        ]
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                    "outputs_mode": "artifact_index",
                },
            },
        },
        fetch_dem_and_build_channels_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=fetch_dem_and_build_channels_id,
                path="/api/runs/{runid}/{config}/fetch-dem-and-build-channels",
                execution_mode="async",
                returns_job=True,
                job_key="fetch_dem_and_build_channels_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="slow",
                estimated_duration_seconds=180,
                mutates_controllers=["watershed"],
                invalidates_steps=[
                    "set-outlet",
                    "build-subcatchments-and-abstract-watershed",
                    "build-climate",
                    "build-landuse",
                    "build-soils",
                    "prep-wepp-watershed",
                    "run-wepp",
                    "run-wepp-watershed",
                ],
                batch_mode_behavior="batch_returns_message_no_queue",
                base_project_behavior="base_project_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "map_bounds": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 4,
                            "maxItems": 4,
                            "constraint_mode": "run_resolved",
                            "constraint_source": "geospatial_metadata",
                            "resolved_at": runtime.generated_at,
                            "required_if": _predicate("set_extent_mode", "in", [0, 1]),
                        },
                        "map_center": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "constraint_mode": "run_resolved",
                            "constraint_source": "geospatial_metadata",
                            "resolved_at": runtime.generated_at,
                            "derived_if_missing": {
                                "field": "map_bounds",
                                "strategy": "bounds_midpoint",
                            },
                        },
                        "map_zoom": {
                            "type": "number",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "geospatial_metadata",
                            "resolved_at": runtime.generated_at,
                            "derived_if_missing": {
                                "field": "map_bounds",
                                "strategy": "bounds_fit_zoom",
                            },
                        },
                        "csa": {
                            "type": "number",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "resolved_at": runtime.generated_at,
                        },
                        "mcl": {
                            "type": "number",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "resolved_at": runtime.generated_at,
                        },
                        "set_extent_mode": {
                            "type": "integer",
                            "constraint_mode": "static",
                            "enum": [0, 1, 2, 3],
                        },
                        "map_object": {
                            "type": "object",
                            "constraint_mode": "static",
                            "required_if": _predicate("set_extent_mode", "eq", 2),
                        },
                        "map_bounds_text": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "wbt_fill_or_breach": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "stream_pruning_method": {
                            "type": "string",
                            "constraint_mode": "static",
                            "enum": ["ifolp", "remove_short_streams"],
                        },
                        "wbt_blc_dist": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["mcl", "csa"],
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {
                    "map_bounds": map_bounds_default,
                    "map_center": map_center_default,
                    "map_zoom": map_zoom_default,
                    "csa": watershed_defaults["csa"],
                    "mcl": watershed_defaults["mcl"],
                    "stream_pruning_method": watershed_defaults["stream_pruning_method"],
                    "set_extent_mode": 0,
                },
                "defaults_context": {
                    **_defaults_context(runtime),
                    "derived_map_fields": ["map_center", "map_zoom"],
                },
            },
        },
        set_outlet_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=set_outlet_id,
                path="/api/runs/{runid}/{config}/set-outlet",
                execution_mode="async",
                returns_job=True,
                job_key="set_outlet_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=20,
                mutates_controllers=["watershed"],
                invalidates_steps=[
                    "build-subcatchments-and-abstract-watershed",
                    "build-climate",
                    "build-landuse",
                    "build-soils",
                    "prep-wepp-watershed",
                    "run-wepp",
                    "run-wepp-watershed",
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "longitude": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "coordinates": {
                            "type": "object",
                            "constraint_mode": "static",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"},
                                "lon": {"type": "number"},
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                            },
                            "additional_properties": True,
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": (
                    {
                        "latitude": float(map_center_default[1]),
                        "longitude": float(map_center_default[0]),
                    }
                    if isinstance(map_center_default, list) and len(map_center_default) == 2
                    else {}
                ),
                "defaults_context": _defaults_context(runtime),
            },
        },
        build_subcatchments_and_abstract_watershed_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=build_subcatchments_and_abstract_watershed_id,
                path="/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed",
                execution_mode="async",
                returns_job=True,
                job_key="build_subcatchments_and_abstract_watershed_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="slow",
                estimated_duration_seconds=240,
                mutates_controllers=["watershed"],
                invalidates_steps=[
                    "build-climate",
                    "build-landuse",
                    "build-soils",
                    "prep-wepp-watershed",
                    "run-wepp",
                    "run-wepp-watershed",
                ],
                batch_mode_behavior="batch_returns_message_no_queue",
                base_project_behavior="base_project_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "clip_hillslopes": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "walk_flowpaths": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "clip_hillslope_length": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "mofe_target_length": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "mofe_buffer": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "mofe_buffer_length": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "mofe_max_ofes": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 19,
                            "constraint_mode": "static",
                        },
                        "bieger2015_widths": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        build_climate_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=build_climate_id,
                path="/api/runs/{runid}/{config}/build-climate",
                execution_mode="async",
                returns_job=True,
                job_key="build_climate_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=120,
                mutates_controllers=["climate"],
                invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="batch_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "climate_mode": {
                            "type": "integer",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "resolved_at": runtime.generated_at,
                            "enum": [0, 2, 3, 5, 6, 11],
                        },
                        "climatestation": {
                            "type": "string",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "available_if": _predicate("climate_mode", "in", [2, 6]),
                            "required_if": _predicate("climate_mode", "in", [2, 6]),
                        },
                        "observed_start_year": {
                            "type": "integer",
                            "minimum": 1900,
                            "maximum": 2100,
                            "constraint_mode": "static",
                            "required_if": _predicate("climate_mode", "in", [2, 11]),
                        },
                        "observed_end_year": {
                            "type": "integer",
                            "minimum": 1900,
                            "maximum": 2100,
                            "constraint_mode": "static",
                            "required_if": _predicate("climate_mode", "in", [2, 11]),
                        },
                        "future_start_year": {
                            "type": "integer",
                            "minimum": 2006,
                            "maximum": 2099,
                            "constraint_mode": "static",
                            "required_if": _predicate("climate_mode", "eq", 3),
                        },
                        "future_end_year": {
                            "type": "integer",
                            "minimum": 2006,
                            "maximum": 2099,
                            "constraint_mode": "static",
                            "required_if": _predicate("climate_mode", "eq", 3),
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    },
                },
            },
            "defaults": {
                "resolved_defaults": _controller_defaults("climate", runtime),
                "defaults_context": _defaults_context(runtime),
            },
        },
        build_landuse_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=build_landuse_id,
                path="/api/runs/{runid}/{config}/build-landuse",
                execution_mode="async",
                returns_job=True,
                job_key="build_landuse_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=120,
                mutates_controllers=["landuse"],
                invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="batch_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "mofe_buffer_selection": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                        "checkbox_burn_shrubs": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "checkbox_burn_grass": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "burn_shrubs": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "burn_grass": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "landuse_management_mapping_selection": {
                            "type": "string",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "resolved_at": runtime.generated_at,
                        },
                        "input_upload_landuse": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        set_landuse_mode_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=set_landuse_mode_id,
                path="/api/runs/{runid}/{config}/set-landuse-mode",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=2,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                        "landuse_single_selection": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["mode"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        set_landuse_db_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=set_landuse_db_id,
                path="/api/runs/{runid}/{config}/set-landuse-db",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=2,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "landuse_db": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["landuse_db"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        modify_landuse_coverage_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=modify_landuse_coverage_id,
                path="/api/runs/{runid}/{config}/modify-landuse-coverage",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=3,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "dom": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "cover": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "value": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["dom", "cover", "value"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        modify_landuse_mapping_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=modify_landuse_mapping_id,
                path="/api/runs/{runid}/{config}/modify-landuse-mapping",
                execution_mode="async",
                returns_job=True,
                job_key="modify_landuse_mapping_rq",
                required_fields=["job_id", "mapping_count"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=45,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="queue_job",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "mappings": {
                            "type": "array",
                            "constraint_mode": "static",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "dom": {"type": "string"},
                                    "newdom": {"type": "string"},
                                },
                                "required": ["dom", "newdom"],
                                "additional_properties": False,
                            },
                        },
                        "dom": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "newdom": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["job_id", "mapping_count"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        get_landuse_user_defined_catalog_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=get_landuse_user_defined_catalog_id,
                path="/api/runs/{runid}/{config}/landuse-user-defined/catalog",
                required_fields=["items", "lookup_sha256"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["items", "lookup_sha256"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        upload_landuse_user_defined_managements_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=upload_landuse_user_defined_managements_id,
                path="/api/runs/{runid}/{config}/landuse-user-defined/upload",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message", "imported_files", "catalog_count", "items", "replace"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=5,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "replace": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "management_upload": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["management_upload"],
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["message", "imported_files", "catalog_count", "items", "replace"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {"replace": False},
                "defaults_context": _defaults_context(runtime),
            },
        },
        delete_landuse_user_defined_management_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=delete_landuse_user_defined_management_id,
                path="/api/runs/{runid}/{config}/landuse-user-defined/delete",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message", "deleted", "catalog_count", "items"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=2,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["filename"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message", "deleted", "catalog_count", "items"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        update_landuse_user_defined_management_description_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=update_landuse_user_defined_management_description_id,
                path="/api/runs/{runid}/{config}/landuse-user-defined/update-description",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message", "item", "catalog_count", "items"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=2,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "description": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["filename", "description"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message", "item", "catalog_count", "items"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        get_landuse_map_snapshot_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=get_landuse_map_snapshot_id,
                path="/api/runs/{runid}/{config}/landuse-map/snapshot",
                required_fields=["rows", "management_options", "lookup_sha256"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["rows", "management_options", "lookup_sha256"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        save_landuse_map_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=save_landuse_map_id,
                path="/api/runs/{runid}/{config}/landuse-map/save",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message", "lookup_sha256"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=8,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "if_match_sha256": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "rows": {
                            "type": "array",
                            "constraint_mode": "static",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "management_file": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["key", "management_file"],
                                "additional_properties": True,
                            },
                        },
                    },
                    "required": ["rows"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message", "lookup_sha256"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        clear_landuse_map_override_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=clear_landuse_map_override_id,
                path="/api/runs/{runid}/{config}/landuse-map/clear-override",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=3,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["message"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        modify_landuse_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=modify_landuse_id,
                path="/api/runs/{runid}/{config}/modify-landuse",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["message", "topaz_count"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=3,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="sync_update_no_queue",
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                        "token_classes": ["user", "session", "service", "mcp"],
                    }
                },
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "topaz_ids": {
                            "type": ["array", "string"],
                            "constraint_mode": "static",
                        },
                        "landuse": {
                            "type": ["integer", "string"],
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["topaz_ids", "landuse"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["message", "topaz_count"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        build_soils_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=build_soils_id,
                path="/api/runs/{runid}/{config}/build-soils",
                execution_mode="async",
                returns_job=True,
                job_key="build_soils_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=120,
                mutates_controllers=["soils"],
                invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="batch_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "initial_sat": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "sol_ver": {
                            "type": "number",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "controller_state",
                            "resolved_at": runtime.generated_at,
                            "enum_available": disturbed_sol_ver_options,
                            "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                            "required_if": _predicate("context.active_mods", "contains", "disturbed"),
                        },
                    },
                    "required": build_soils_required_fields,
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {
                    **{
                        "initial_sat": (
                            runtime.states.get("initial_sat")
                            if runtime.states.get("initial_sat") is not None
                            else 0.75
                        )
                    },
                    **(
                        {
                            "sol_ver": (
                                runtime.states.get("disturbed_sol_ver")
                                if runtime.states.get("disturbed_sol_ver") is not None
                                else _default_disturbed_sol_ver(runtime)
                            )
                        }
                        if disturbed_enabled
                        else {}
                    ),
                },
                "defaults_context": _defaults_context(runtime),
            },
        },
        prep_wepp_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=prep_wepp_id,
                path="/api/runs/{runid}/{config}/prep-wepp-watershed",
                execution_mode="async",
                returns_job=True,
                job_key="prep_wepp_watershed_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=90,
                mutates_controllers=["wepp"],
                invalidates_steps=["run-wepp", "run-wepp-watershed"],
                batch_mode_behavior="batch_returns_message_no_queue",
                base_project_behavior="base_project_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "clip_soils": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "clip_soils_depth": {
                            "type": "number",
                            "minimum": 0.0,
                            "constraint_mode": "static",
                            "available_if": _predicate("clip_soils", "eq", True),
                            "required_if": _predicate("clip_soils", "eq", True),
                        },
                        "initial_sat": {
                            "type": "number",
                            "constraint_mode": "static",
                        }
                    },
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["job_id"]}},
            },
            "defaults": {
                "resolved_defaults": _controller_defaults("wepp", runtime),
                "defaults_context": _defaults_context(runtime),
            },
        },
        run_wepp_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=run_wepp_id,
                path="/api/runs/{runid}/{config}/run-wepp",
                execution_mode="async",
                returns_job=True,
                job_key="run_wepp_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="slow",
                estimated_duration_seconds=300,
                mutates_controllers=["wepp", "soils"],
                invalidates_steps=["run-wepp-watershed"],
                batch_mode_behavior="batch_returns_message_no_queue",
                base_project_behavior="base_project_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "clip_soils": {
                            "type": "boolean",
                            "constraint_mode": "static",
                            "source_controller": "soils",
                        },
                        "clip_soils_depth": {
                            "type": "number",
                            "minimum": 0.0,
                            "constraint_mode": "static",
                            "source_controller": "soils",
                            "available_if": _predicate("clip_soils", "eq", True),
                            "required_if": _predicate("clip_soils", "eq", True),
                        },
                        "initial_sat": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id"],
                    },
                },
            },
            "defaults": {
                "resolved_defaults": {
                    **_controller_defaults("wepp", runtime),
                },
                "defaults_context": _defaults_context(runtime),
            },
        },
        run_wepp_watershed_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=run_wepp_watershed_id,
                path="/api/runs/{runid}/{config}/run-wepp-watershed",
                execution_mode="async",
                returns_job=True,
                job_key="run_wepp_watershed_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="slow",
                estimated_duration_seconds=300,
                mutates_controllers=["wepp"],
                invalidates_steps=[],
                batch_mode_behavior="batch_returns_message_no_queue",
                base_project_behavior="base_project_returns_message_no_queue",
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "clip_soils": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "clip_soils_depth": {
                            "type": "number",
                            "minimum": 0.0,
                            "constraint_mode": "static",
                            "available_if": _predicate("clip_soils", "eq", True),
                            "required_if": _predicate("clip_soils", "eq", True),
                        },
                        "initial_sat": {
                            "type": "number",
                            "constraint_mode": "static",
                        }
                    },
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["job_id"]}},
            },
            "defaults": {
                "resolved_defaults": _controller_defaults("wepp", runtime),
                "defaults_context": _defaults_context(runtime),
            },
        },
        build_rusle_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=build_rusle_id,
                path="/api/runs/{runid}/{config}/build-rusle",
                execution_mode="async",
                returns_job=True,
                job_key="build_rusle_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="medium",
                estimated_duration_seconds=120,
                mutates_controllers=["disturbed"],
                invalidates_steps=[],
                batch_mode_behavior="batch_returns_message_no_queue",
                available_if=[_rusle_available_if()],
                required_if=[_rusle_available_if()],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "r_mode": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                        "c_mode": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                        "rap_year": {
                            "type": "integer",
                            "constraint_mode": "static",
                        },
                        "k_modes": {
                            "type": "array",
                            "constraint_mode": "static",
                        },
                        "default_k_mode": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "max_slope_length_m": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "p_value": {
                            "type": "number",
                            "constraint_mode": "static",
                        },
                        "force_polaris_refresh": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["job_id"]}},
            },
            "defaults": {
                "resolved_defaults": {
                    "force_polaris_refresh": False,
                },
                "defaults_context": _defaults_context(runtime),
            },
        },
        upload_dem_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=upload_dem_id,
                path="/api/runs/{runid}/{config}/tasks/upload-dem/",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["result"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=10,
                mutates_controllers=["watershed"],
                invalidates_steps=[
                    "fetch-dem-and-build-channels",
                    "set-outlet",
                    "build-subcatchments-and-abstract-watershed",
                    "build-climate",
                    "build-landuse",
                    "build-soils",
                    "prep-wepp-watershed",
                    "run-wepp",
                    "run-wepp-watershed",
                ],
                content_types=["multipart/form-data"],
                file_fields=[
                    {
                        "name": "input_upload_dem",
                        "required": True,
                        "allowed_extensions": [f".{ext}" for ext in UPLOAD_DEM_ALLOWED_EXTENSIONS],
                        "allowed_media_types": ["image/tiff", "application/geotiff", "application/x-geotiff"],
                        "max_bytes": UPLOAD_DEM_MAX_BYTES,
                        "crs_requirements": {
                            "mode": "must_define_spatial_reference",
                            "allow_reprojection": True,
                            "preferred_projection_family": "utm",
                        },
                        "extent_requirements": {
                            "mode": "must_define_georeferenced_extent",
                        },
                        "resolution_requirements": {
                            "mode": "square_pixels_required",
                            "max_dimension_px": UPLOAD_DEM_MAX_DIMENSION,
                        },
                        "value_semantics": {
                            "classification_type": "continuous_elevation",
                            "required_numeric_type": "float32_or_float64",
                        },
                    }
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "input_upload_dem": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "geospatial_metadata",
                            "resolved_at": runtime.generated_at,
                        },
                    },
                    "required": ["input_upload_dem"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["result"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        upload_cli_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=upload_cli_id,
                path="/api/runs/{runid}/{config}/tasks/upload-cli/",
                execution_mode="async",
                returns_job=True,
                job_key="upload_cli_rq",
                required_fields=["job_id"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=8,
                mutates_controllers=["climate"],
                invalidates_steps=["build-climate", "prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
                content_types=["multipart/form-data"],
                file_fields=[
                    {
                        "name": "input_upload_cli",
                        "required": True,
                        "allowed_extensions": [f".{ext}" for ext in UPLOAD_CLI_ALLOWED_EXTENSIONS],
                        "allowed_media_types": ["text/plain", "application/octet-stream"],
                        "max_bytes": UPLOAD_CLI_MAX_BYTES,
                        "value_semantics": {
                            "classification_type": "station_climate_timeseries",
                        },
                    }
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "input_upload_cli": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["input_upload_cli"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["job_id"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        upload_cover_transform_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=upload_cover_transform_id,
                path="/api/runs/{runid}/{config}/tasks/upload-cover-transform",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=[],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=5,
                mutates_controllers=["landuse"],
                invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
                content_types=["multipart/form-data"],
                file_fields=[
                    {
                        "name": "input_upload_cover_transform",
                        "required": True,
                        "allowed_extensions": [f".{ext}" for ext in UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS],
                        "allowed_media_types": ["text/csv", "application/vnd.ms-excel"],
                        "max_bytes": UPLOAD_COVER_TRANSFORM_MAX_BYTES,
                        "value_semantics": {
                            "classification_type": "cover_transform_table",
                        },
                    }
                ],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "input_upload_cover_transform": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "static",
                        },
                    },
                    "required": ["input_upload_cover_transform"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": []}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        issue_session_token_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=issue_session_token_id,
                path="/api/runs/{runid}/{config}/session-token",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["token", "session_id", "runid", "config", "scopes"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=1,
                mutates_controllers=[],
                invalidates_steps=[],
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:status"],
                    },
                    "session_cookie_same_origin": {
                        "same_origin_required": True,
                        "public_run_fallback": True,
                    },
                },
                accepted_auth=["bearer_jwt", "session_cookie_same_origin"],
                write_precondition_required=False,
                write_precondition_accepted=["x_run_state_match", "expected_run_state_revision"],
                idempotency_supported=True,
                idempotency_dedupe_window_seconds=_session_token_idempotency_window_seconds(),
                replay_behavior="reject_duplicate",
                content_types=["application/json"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "expected_run_state_revision": {
                            "type": "string",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "run_state_revision",
                        }
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["token", "session_id", "runid", "config", "scopes"],
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        },
        fork_project_id: {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=fork_project_id,
                path="/api/runs/{runid}/{config}/fork",
                execution_mode="async",
                returns_job=True,
                job_key="fork_rq",
                required_fields=["job_id", "new_runid", "undisturbify", "skip_wepp_runs_output"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=15,
                mutates_controllers=[],
                invalidates_steps=[],
                auth_requirements={
                    "bearer_jwt": {
                        "required_scope": ["rq:enqueue"],
                    },
                    "captcha": {
                        "challenge_required": True,
                        "required_if_no_authenticated_token": True,
                    },
                },
                accepted_auth=["bearer_jwt", "captcha"],
                content_types=["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "undisturbify": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "skip_wepp_runs_output": {
                            "type": "boolean",
                            "constraint_mode": "static",
                        },
                        "target_runid": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                        "cap_token": {
                            "type": "string",
                            "constraint_mode": "static",
                        },
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": ["job_id", "new_runid", "undisturbify", "skip_wepp_runs_output"]
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {"undisturbify": False, "skip_wepp_runs_output": False},
                "defaults_context": _defaults_context(runtime),
            },
        },
    }

    if not rusle_enabled:
        operations.pop(build_rusle_id, None)

    if runtime.states.get("sbs_upload_supported", False):
        operations[upload_sbs_id] = {
            "descriptor": _base_run_mutation_descriptor(
                runtime=runtime,
                operation_id=upload_sbs_id,
                path="/api/runs/{runid}/{config}/tasks/upload-sbs/",
                execution_mode="sync",
                returns_job=False,
                job_key=None,
                required_fields=["result"],
                estimated_duration_bucket="fast",
                estimated_duration_seconds=8,
                mutates_controllers=["disturbed", "landuse", "soils"],
                invalidates_steps=["build-landuse", "build-soils", "run-wepp", "run-wepp-watershed"],
                content_types=["multipart/form-data"],
                file_fields=[
                    {
                        "name": "input_upload_sbs",
                        "required": True,
                        "allowed_extensions": [f".{ext}" for ext in UPLOAD_SBS_ALLOWED_EXTENSIONS],
                        "allowed_media_types": [],
                        "max_bytes": UPLOAD_SBS_MAX_BYTES,
                        "crs_requirements": {
                            "mode": "must_have_valid_projection",
                        },
                        "value_semantics": {
                            "classification_type": "integer_class_raster",
                            "required_integer_values": True,
                            "max_unique_classes": 256,
                            "color_table_mode": "optional_but_if_present_must_map_known_severity",
                        },
                    }
                ],
                required_if=[_sbs_available_if()],
                available_if=[_sbs_available_if()],
            ),
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "properties": {
                        "input_upload_sbs": {
                            "type": "string",
                            "format": "binary",
                            "constraint_mode": "run_resolved",
                            "constraint_source": "geospatial_metadata",
                            "resolved_at": runtime.generated_at,
                            "required_if": _sbs_available_if(),
                        },
                    },
                    "required": ["input_upload_sbs"],
                    "additional_properties": True,
                },
                "responses": {"success": {"required": ["result"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": _defaults_context(runtime),
            },
        }

    operations[list_endpoints_id]["defaults"]["defaults_context"]["operation_count"] = len(operations)

    ordered_ids = sorted(operations, key=str.casefold)
    return {operation_id: operations[operation_id] for operation_id in ordered_ids}


def _resolve_controller(controller: str, runtime: RuntimeState) -> str | None:
    normalized = str(controller or "").strip().lower()
    if normalized in _controller_catalog(runtime):
        return normalized
    return None


@router.get(
    "/runs/{runid}/{config}/geospatial-metadata",
    summary="Get run geospatial metadata",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only geospatial constraints/defaults metadata for run-scoped planning; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geospatial_metadata"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Geospatial metadata returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def get_geospatial_metadata(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine geospatial-metadata auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine geospatial-metadata state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        geospatial_payload = _geospatial_payload(runtime)
        etag_input = {
            "run_state_revision": runtime.run_state_revision,
            "geospatial": {
                key: value
                for key, value in geospatial_payload.items()
                if key != "computed_at"
            },
        }
        etag_digest = hashlib.sha256(
            json.dumps(etag_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        freshness = _snapshot_freshness(
            data_state="materialized",
            data_updated_at=None,
            fallback_updated_at=_runtime_snapshot_updated_at(
                runid=runtime.runid,
                generated_at=runtime.generated_at,
            ),
        )

        payload = _base_payload(runtime)
        payload.update(geospatial_payload)
        payload.update(freshness)
        payload["etag"] = f'W/"geospatial:{runtime.runid}:{etag_digest}"'
        payload["computed_at"] = freshness["updated_at"]
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine geospatial-metadata payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers",
    summary="List run controllers",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller catalog; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("list_controllers"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller catalog returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def list_controllers(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine controllers auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controllers state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        payload = _base_payload(runtime)
        payload.update(
            {
                "runid": runtime.runid,
                "config": runtime.config,
                "active_mods": list(runtime.active_mods),
                "endpoints_url": f"/api/runs/{runtime.runid}/{runtime.config}/endpoints",
                "pipeline_url": f"/api/runs/{runtime.runid}/{runtime.config}/pipeline",
                "readiness_url": f"/api/runs/{runtime.runid}/{runtime.config}/readiness",
                "outputs_url": f"/api/runs/{runtime.runid}/{runtime.config}/outputs",
                "controllers": list(_controller_catalog(runtime).values()),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controllers payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/schema",
    summary="Get controller schema",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller schema + constraints; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_schema"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller schema returned.",
        extra={404: "Run or controller not found. Returns the canonical error payload."},
    ),
)
def get_controller_schema(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine controller schema auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller schema state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        controller_schema = _controller_schema(resolved_controller, runtime)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "schema_version": controller_schema["schema_version"],
                "fields": controller_schema["fields"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller schema failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/hints",
    summary="Get controller hints",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller hint metadata; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_hints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller hints returned.",
        extra={404: "Run or controller not found. Returns the canonical error payload."},
    ),
)
def get_controller_hints(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine controller hints auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller hints state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        hints = _controller_hints(resolved_controller)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "schema_version": hints["schema_version"],
                "hints": {
                    "context_fields": hints["context_fields"],
                    "groups": hints["groups"],
                    "field_hints": hints["field_hints"],
                },
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller hints failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/templates",
    summary="Get controller templates",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only templates + run-resolved defaults; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_templates"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller templates returned.",
        extra={404: "Run or controller not found. Returns the canonical error payload."},
    ),
)
def get_controller_templates(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine controller templates auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller templates state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        templates_payload = _controller_templates(resolved_controller, runtime)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "templates": templates_payload["templates"],
                "run_resolved_defaults": templates_payload["run_resolved_defaults"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller templates failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints",
    summary="List run endpoints",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only run-scoped operation catalog; no queue. "
        f"Set `{LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM}=true` to include per-operation schema/defaults/errors in one response."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("list_run_endpoints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run-scoped endpoint catalog returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def list_run_endpoints(
    runid: str,
    config: str,
    request: Request,
    include_operation_docs: bool = Query(
        default=False,
        description=(
            "Optional boolean. When true, include per-operation schema/defaults/errors snapshot "
            "under `operation_docs`."
        ),
    ),
) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine run-endpoints auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoints state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        operations = _build_run_operations(runtime)
        operation_descriptors = [copy.deepcopy(operation["descriptor"]) for operation in operations.values()]

        payload = _base_payload(runtime)
        payload["operations"] = operation_descriptors
        if include_operation_docs:
            payload["operation_docs"] = _build_operation_docs_snapshot(
                operations=operations,
                computed_at=_utc_timestamp(),
            )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoints payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/schema",
    summary="Get run endpoint schema",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only request schema + operation descriptor; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_schema"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation schema returned.",
        extra={404: "Run or operation not found. Returns the canonical error payload."},
    ),
)
def get_run_endpoint_schema(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine run-endpoint schema auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint schema state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        descriptor = copy.deepcopy(operation_docs["descriptor"])
        schema = copy.deepcopy(operation_docs["schema"])

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": descriptor["operation_id"],
                "run_scoped": descriptor["run_scoped"],
                "method": descriptor["method"],
                "path": descriptor["path"],
                "operation_descriptor": descriptor,
                "schema_version": schema["schema_version"],
                "request": schema["request"],
                "responses": schema["responses"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint schema failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/defaults",
    summary="Get run endpoint defaults",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only run-resolved defaults for an operation; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_defaults"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation defaults returned.",
        extra={404: "Run or operation not found. Returns the canonical error payload."},
    ),
)
def get_run_endpoint_defaults(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine run-endpoint defaults auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint defaults state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        defaults_doc = copy.deepcopy(operation_docs["defaults"])
        defaults_doc["computed_at"] = _utc_timestamp()

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": operation_id,
                "resolved_defaults": defaults_doc["resolved_defaults"],
                "defaults_context": defaults_doc["defaults_context"],
                "computed_at": defaults_doc["computed_at"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint defaults failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/errors",
    summary="Get run endpoint errors",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only operation error taxonomy for one run-scoped operation; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_errors"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation error catalog returned.",
        extra={404: "Run or operation not found. Returns the canonical error payload."},
    ),
)
def get_run_endpoint_errors(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine run-endpoint errors auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint errors state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": operation_id,
                "errors": _build_operation_error_catalog(
                    operation_id=operation_id,
                    operation_docs=operation_docs,
                ),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint errors failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/outputs",
    summary="Get run outputs",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only outputs/artifact discovery snapshot with retrieval handles and provenance metadata; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_outputs"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run outputs snapshot returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def get_outputs(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: auth boundary contract
        logger.exception("rq-engine outputs auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine outputs state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        payload = _base_payload(runtime)
        payload.update(_build_outputs_payload(runtime))
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine outputs failed")
        return error_response("Error Handling Request", status_code=500)


__all__ = ["router"]
