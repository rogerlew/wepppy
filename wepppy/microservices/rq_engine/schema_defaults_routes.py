from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

from wepppy.nodb.core import Climate, Landuse, Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep
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


def _base_payload(runtime: RuntimeState) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "deployment_revision": _deployment_revision(),
        "run_state_revision": runtime.run_state_revision,
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
    revision_source = {
        "config": actual_config or requested_config or config,
        "active_mods": list(active_mods),
        "region": region,
        "states": states,
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
    idempotency_supported: bool = False,
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

    idempotency_policy: dict[str, Any] = {
        "supported": idempotency_supported,
        "key_locations": ["header:Idempotency-Key"] if idempotency_supported else [],
        "dedupe_window_seconds": 86400 if idempotency_supported else 0,
        "replay_behavior": replay_behavior,
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict",
    }
    if not idempotency_supported and replay_behavior == "reject_duplicate":
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
            "accepted": ["x_run_state_match", "expected_run_state_revision"] if write_precondition_required else [],
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
        return {
            "climate_mode": resolved_mode,
            "observed_start_year": 1990,
            "observed_end_year": 2020,
        }
    if controller == "landuse":
        return {
            "landuse_mode": runtime.states.get("landuse_mode") or "nlcd",
        }
    if controller == "soils":
        defaults = {
            "soils_mode": runtime.states.get("soils_mode") or "ssurgo",
        }
        if disturbed_enabled:
            defaults["sol_ver"] = runtime.states.get("disturbed_sol_ver") or 2018.0
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
            "sol_ver": runtime.states.get("disturbed_sol_ver") or 2018.0,
        }
    return {}


def _controller_schema(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))

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
                    "enum": [0, 2, 6, 11],
                    "enum_available": available_modes,
                    "enum_labels": {
                        "0": "Synthetic CLIGEN",
                        "2": "Observed station",
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
                    "required_if": _predicate("climate_mode", "in", [2, 6]),
                },
                "observed_end_year": {
                    "type": "integer",
                    "minimum": 1900,
                    "maximum": 2100,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [2, 6]),
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
        sol_ver_available = ["v2006", "v2018"] if disturbed_enabled else []
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
                    "enum_available": [2006.0, 2018.0] if sol_ver_available else [],
                    "enum_labels": {
                        "2006.0": "Legacy disturbed defaults",
                        "2018.0": "Updated disturbed defaults",
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
                    "enum_available": [2006.0, 2018.0],
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


def _available_climate_modes(runtime: RuntimeState) -> list[int]:
    modes = [0, 6, 11]
    if bool(runtime.states.get("climate_has_station", False)):
        modes.insert(1, 2)
    return modes


def _supported_soils_modes() -> list[str]:
    return ["ssurgo", "statsgo"]


def _resolved_watershed_defaults(runtime: RuntimeState) -> dict[str, float]:
    csa_value = runtime.states.get("watershed_csa")
    mcl_value = runtime.states.get("watershed_mcl")
    csa = float(csa_value) if isinstance(csa_value, (int, float)) else 10.0
    mcl = float(mcl_value) if isinstance(mcl_value, (int, float)) else 75.0
    return {"csa": csa, "mcl": mcl}


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
    watershed_defaults = _resolved_watershed_defaults(runtime)
    csa = watershed_defaults["csa"]
    mcl = watershed_defaults["mcl"]

    climate_modes = _available_climate_modes(runtime)

    soils_modes_available = _supported_soils_modes()

    sol_ver_available = [2006.0, 2018.0] if bool(runtime.states.get("disturbed_enabled", False)) else []

    map_center_available = map_center is not None
    map_bounds_available = map_bounds_is_run_resolved
    csa_available = isinstance(csa_value, (int, float))
    mcl_available = isinstance(mcl_value, (int, float))
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
    pipeline_id = rq_operation_id("get_pipeline")
    readiness_id = rq_operation_id("get_readiness")

    build_climate_id = rq_operation_id("build_climate")
    build_landuse_id = rq_operation_id("build_landuse")
    build_soils_id = rq_operation_id("build_soils")
    prep_wepp_id = rq_operation_id("prep_wepp_watershed")
    run_wepp_id = rq_operation_id("run_wepp")
    run_wepp_watershed_id = rq_operation_id("run_wepp_watershed")
    upload_dem_id = rq_operation_id("upload_dem")
    upload_cli_id = rq_operation_id("upload_cli")
    upload_cover_transform_id = rq_operation_id("upload_cover_transform")
    upload_sbs_id = rq_operation_id("upload_sbs")
    issue_session_token_id = rq_operation_id("issue_session_token")

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
        geospatial_metadata_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=geospatial_metadata_id,
                path="/api/runs/{runid}/{config}/geospatial-metadata",
                required_fields=["dem_coverage", "recommended_defaults", "field_availability"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {
                    "success": {
                        "required": ["dem_coverage", "recommended_defaults", "field_availability"],
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
                "request": _empty_request_schema(),
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
        pipeline_id: {
            "descriptor": _base_run_read_descriptor(
                runtime=runtime,
                operation_id=pipeline_id,
                path="/api/runs/{runid}/{config}/pipeline",
                required_fields=["steps"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["steps"]}},
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
                required_fields=["next_actionable_steps"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["next_actionable_steps"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {
                    **_defaults_context(runtime),
                },
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
                            "enum": [0, 2, 6, 11],
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
                            "required_if": _predicate("climate_mode", "in", [2, 6]),
                        },
                        "observed_end_year": {
                            "type": "integer",
                            "minimum": 1900,
                            "maximum": 2100,
                            "constraint_mode": "static",
                            "required_if": _predicate("climate_mode", "in", [2, 6]),
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
                            "constraint_mode": "static",
                            "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                            "required_if": _predicate("context.active_mods", "contains", "disturbed"),
                        },
                    },
                    "required": ["initial_sat"],
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
                                else 2018.0
                            )
                        }
                        if runtime.states.get("disturbed_enabled")
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
                idempotency_supported=False,
                replay_behavior="reject_duplicate",
                content_types=["application/json"],
            ),
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
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
    }

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
        payload = _base_payload(runtime)
        payload.update(_geospatial_payload(runtime))
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
        "Read-only run-scoped operation catalog; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("list_run_endpoints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run-scoped endpoint catalog returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def list_run_endpoints(runid: str, config: str, request: Request) -> JSONResponse:
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

        payload = _base_payload(runtime)
        payload.update(
            {
                "operations": [copy.deepcopy(operation["descriptor"]) for operation in operations.values()],
            }
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


__all__ = ["router"]
