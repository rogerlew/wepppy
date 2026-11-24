"""Read run controllers and assemble the revisioned state used for RQ discovery."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from werkzeug.utils import secure_filename

from wepp_runner.wepp_binary_capabilities import binary_selection_revision
from wepppy.nodb.core import Climate, Landuse, Ron, Soils, Watershed, Wepp
from wepppy.nodb.locales.capability_graph import CapabilityGraph, capability_structure_payload
from wepppy.nodb.locales.landuse_catalog import landcover_catalog_id
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    LocaleAuthorityInvalidError,
    RunCapabilityMode,
    capability_authority,
    capability_ids,
    resolve_run_capability_authority,
)
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.wepp_binary_policy import project_wepp_binary_options
from wepppy.weppcloud.utils.helpers import get_wd

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


class CapabilityAuthorityInvalidError(ValueError):
    """Raised when stored run capability authority cannot be used for discovery."""

    def __init__(
        self,
        details: str,
        *,
        code: str = "capability_authority_invalid",
        status_code: int = 409,
        message: str = "Project capability authority is invalid.",
    ) -> None:
        super().__init__(details)
        self.code = code
        self.status_code = status_code
        self.message = message


def _resolve_runtime_capability_graphs(
    config,
) -> tuple[CapabilityGraph | None, CapabilityGraph | None, frozenset[str]]:
    try:
        resolved = resolve_run_capability_authority(config)
        model_graph = (
            capability_authority(config)
            if resolved.mode is RunCapabilityMode.STORED
            else None
        )
        return (
            resolved.graph,
            model_graph,
            getattr(resolved, "projected_domains", frozenset()),
        )
    except LocaleAuthorityInvalidError as exc:
        raise CapabilityAuthorityInvalidError(
            str(exc),
            code="locale_authority_invalid",
            message="Run locale authority is invalid.",
        ) from exc
    except BuilderRegistryUnavailableError as exc:
        raise CapabilityAuthorityInvalidError(
            str(exc),
            code="builder_registry_error",
            status_code=503,
            message="Builder registry is unavailable.",
        ) from exc
    except ValueError as exc:
        raise CapabilityAuthorityInvalidError(str(exc)) from exc


@dataclass(frozen=True)
class RuntimeState:
    runid: str
    config: str
    active_mods: tuple[str, ...]
    region: str | None
    states: Mapping[str, Any]
    generated_at: str
    run_state_revision: str
    capability_graph: CapabilityGraph | None = None
    model_capability_graph: CapabilityGraph | None = None
    v1_capabilities: Mapping[str, tuple[str, ...]] | None = None
    projected_domains: frozenset[str] = frozenset()
    wepp_binary_options: tuple[str, ...] | None = None
    wepp_binary_revision: str | None = None
    wepp_model_tuples: tuple[str, ...] | None = None


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


def _compute_run_state_revision(runid: str, payload: Mapping[str, Any]) -> str:
    digest_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12]
    return f"runstate:{runid}:{digest}"


def _float_list(value: Any, *, expected_len: int) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != expected_len:
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _map_state(ron: Ron) -> dict[str, Any]:
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
        map_bounds = _float_list(extent, expected_len=4)
        if isinstance(center, (list, tuple)) and len(center) == 2:
            try:
                map_center = [float(center[0]), float(center[1])]
            except (TypeError, ValueError):
                map_center = None
        map_zoom = _optional_float(zoom)
        map_resolution = _optional_float(cellsize)

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

    return {
        "map_center": map_center,
        "map_bounds": map_bounds,
        "map_zoom": map_zoom,
        "map_zoom_resolution_m_per_px": map_resolution,
    }


def _watershed_parameters(watershed: Watershed) -> dict[str, Any]:
    watershed_csa = _optional_float(getattr(watershed, "csa", None))
    watershed_mcl = _optional_float(getattr(watershed, "mcl", None))

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

    return {
        "watershed_csa": watershed_csa,
        "watershed_mcl": watershed_mcl,
        "watershed_stream_pruning_method": watershed_stream_pruning_method,
        "delineation_backend": delineation_backend,
    }


def _run_region(ron: Ron) -> str | None:
    region = str(getattr(ron, "region", "") or "").strip() or None
    if region is None:
        locales = getattr(ron, "_locales", None)
        if isinstance(locales, (list, tuple)) and locales:
            region = str(locales[0] or "").strip() or None
    return region


def _controller_states(
    wd: str,
    active_mods: tuple[str, ...],
    ron: Ron,
    watershed: Watershed,
    climate: Climate,
    landuse: Landuse,
    soils: Soils,
    wepp: Wepp,
    prep: RedisPrep,
) -> tuple[dict[str, Any], str | None]:
    active_mod_tokens = {mod.lower() for mod in active_mods}
    disturbed_enabled = "disturbed" in active_mod_tokens
    sbs_upload_supported = bool(active_mod_tokens.intersection({"disturbed", "baer", "ash", "debris_flow"}))
    initial_sat = _optional_float(getattr(soils, "initial_sat", None))
    disturbed_sol_ver = None
    if disturbed_enabled:
        disturbed = Disturbed.getInstance(wd)
        disturbed_sol_ver = _optional_float(getattr(disturbed, "sol_ver", None))

    map_state = _map_state(ron)
    watershed_parameters = _watershed_parameters(watershed)
    region = _run_region(ron)
    dem_source = str(getattr(ron, "dem_db", "") or "").strip() or "unknown"
    uploaded_dem_filename_raw = str(getattr(watershed, "uploaded_dem_filename", "") or "").strip() or None
    uploaded_dem_filename: str | None = None
    if uploaded_dem_filename_raw:
        uploaded_dem_filename = secure_filename(Path(uploaded_dem_filename_raw).name) or None
    climate_station_required = bool(getattr(climate, "has_climatestation_mode", False))
    current_landuse_runtime = str(getattr(landuse, "nlcd_db", "") or "").strip() or None
    try:
        current_landuse_catalog_id = (
            landcover_catalog_id(current_landuse_runtime)
            if current_landuse_runtime is not None
            else None
        )
    except ValueError:
        current_landuse_catalog_id = None

    states: dict[str, Any] = {
        "has_dem": bool(getattr(ron, "has_dem", False)),
        "watershed_has_channels": bool(getattr(watershed, "has_channels", False)),
        "watershed_has_outlet": bool(getattr(watershed, "has_outlet", False)),
        "watershed_is_abstracted": bool(getattr(watershed, "is_abstracted", False)),
        "watershed_subcatchment_count": int(getattr(watershed, "sub_n", 0) or 0),
        **watershed_parameters,
        "watershed_representation": "multiple-ofe" if bool(getattr(landuse, "multi_ofe", False)) else "single-ofe",
        "climate_built": bool(getattr(climate, "has_climate", False)),
        "climate_mode_code": _enum_int(getattr(climate, "climate_mode", None)),
        "climate_mode": _enum_name(getattr(climate, "climate_mode", None)),
        "climate_catalog_id": str(getattr(climate, "catalog_id", "") or "").strip() or None,
        "cligen_seed": getattr(climate, "cligen_seed", None),
        "edde_projection": getattr(climate, "edde_projection", ""),
        "future_start_year": getattr(climate, "future_start_year", ""),
        "future_end_year": getattr(climate, "future_end_year", ""),
        "climate_station_mode_code": _enum_int(getattr(climate, "climatestation_mode", None)),
        "climate_spatial_mode_code": _enum_int(getattr(climate, "climate_spatialmode", None)),
        "climate_has_station": bool(getattr(climate, "has_station", False)),
        "climate_station_required": climate_station_required,
        "landuse_built": bool(getattr(landuse, "has_landuse", False)),
        "landuse_mode": _enum_name(getattr(landuse, "mode", None)),
        "landuse_mode_code": _enum_int(getattr(landuse, "mode", None)),
        "landuse_runtime_dataset": current_landuse_runtime,
        "landuse_catalog_id": current_landuse_catalog_id,
        "soils_built": bool(getattr(soils, "has_soils", False)),
        "soils_mode": _enum_name(getattr(soils, "mode", None)),
        "soils_mode_code": _enum_int(getattr(soils, "mode", None)),
        "initial_sat": initial_sat,
        "clear_ssurgo_cache_on_rebuild": bool(
            getattr(soils, "clear_ssurgo_cache_on_rebuild", False)
        ),
        "wepp_has_run": bool(getattr(wepp, "has_run", False)),
        "wepp_binary": str(getattr(wepp, "wepp_bin", "") or "").strip() or None,
        "disturbed_enabled": disturbed_enabled,
        "sbs_upload_supported": sbs_upload_supported,
        "disturbed_sbs_uploaded": bool(getattr(prep, "has_sbs", False)),
        "disturbed_sol_ver": disturbed_sol_ver,
        **map_state,
        "dem_coverage_source": dem_source,
        "uploaded_dem_filename": uploaded_dem_filename,
    }
    return states, region


def _legacy_capabilities(wepp: Wepp) -> dict[str, tuple[str, ...]] | None:
    discovered_v1: dict[str, tuple[str, ...]] = {}
    for axis in (
        "climate_datasets",
        "climate_station_methods",
        "climate_spatial_methods",
        "landuse_datasets",
        "landuse_methods",
        "soil_datasets",
        "soil_builders",
        "delineation_backends",
        "watershed_representations",
        "wepp_binaries",
        "mods",
    ):
        try:
            values = capability_ids(wepp, axis)
        except ValueError as exc:
            raise CapabilityAuthorityInvalidError(str(exc)) from exc
        if values is not None:
            raw = wepp.config_get_list("capabilities", axis, None)
            assert isinstance(raw, (list, tuple))
            discovered_v1[axis] = tuple(str(item).strip() for item in raw)
    return discovered_v1 or None


def _model_binary_selection(
    wepp: Wepp,
    backend: str | None,
    model_capability_graph: CapabilityGraph | None,
) -> tuple[tuple[str, ...] | None, str | None, tuple[str, ...] | None]:
    try:
        binary_options = project_wepp_binary_options(wepp, backend=backend)
        model_tuples = None
        if binary_options is not None and model_capability_graph is not None:
            model_tuples = tuple(
                f"{backend}|{representation}|{binary}"
                for backend, representation in capability_structure_payload(model_capability_graph)["allowed_model_pairs"]
                for binary in project_wepp_binary_options(
                    wepp, backend=backend, multi_ofe=representation == "multiple-ofe"
                )
            )
        revision_binaries = binary_options
        if model_tuples is not None:
            revision_binaries = tuple(dict.fromkeys(value.rsplit("|", 1)[1] for value in model_tuples))
        binary_revision = binary_selection_revision(revision_binaries) if revision_binaries is not None else None
    except ValueError as exc:
        raise CapabilityAuthorityInvalidError(str(exc)) from exc
    return binary_options, binary_revision, model_tuples


def _resolve_run_config(ron: Ron, config: str) -> str:
    requested_config = _normalize_config_token(config)
    actual_config = _normalize_config_token(getattr(ron, "config_stem", ""))
    if requested_config and actual_config and requested_config != actual_config:
        raise RunConfigMismatchError(
            f"Run config mismatch: path config '{config}' does not match run config '{actual_config}'."
        )
    return actual_config or requested_config or config


def _load_runtime_state(runid: str, config: str) -> RuntimeState:
    wd = get_wd(runid)
    if not Path(wd).is_dir():
        raise FileNotFoundError(f"Unknown run '{runid}'")

    ron = Ron.getInstance(wd)
    resolved_config = _resolve_run_config(ron, config)

    watershed = Watershed.getInstance(wd)
    climate = Climate.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    prep = RedisPrep.getInstance(wd)

    active_mods = tuple(sorted({str(mod).strip() for mod in (ron.mods or ()) if str(mod).strip()}, key=str.casefold))
    states, region = _controller_states(
        wd, active_mods, ron, watershed, climate, landuse, soils, wepp, prep
    )
    capability_graph, model_capability_graph, projected_domains = (
        _resolve_runtime_capability_graphs(wepp)
    )
    v1_capabilities: dict[str, tuple[str, ...]] | None = None
    if capability_graph is None or projected_domains:
        v1_capabilities = _legacy_capabilities(wepp)

    binary_options, binary_revision, model_tuples = _model_binary_selection(
        wepp, states.get("delineation_backend"), model_capability_graph
    )

    generated_at = _utc_timestamp()
    snapshot_fallback_updated_at = _runtime_snapshot_updated_at(
        runid=runid,
        generated_at=generated_at,
    )
    revision_source = {
        "config": resolved_config,
        "active_mods": list(active_mods),
        "region": region,
        "states": states,
        "capability_provider_revision": (
            capability_graph.provider_revision if capability_graph is not None else None
        ),
        "model_capability_provider_revision": (
            model_capability_graph.provider_revision
            if model_capability_graph is not None
            else None
        ),
        "v1_capabilities": v1_capabilities,
        "wepp_binary_options": binary_options,
        "wepp_binary_revision": binary_revision,
        "wepp_model_tuples": model_tuples,
        "projected_domains": sorted(projected_domains),
        "snapshot_fallback_updated_at": snapshot_fallback_updated_at,
    }
    run_state_revision = _compute_run_state_revision(runid, revision_source)

    return RuntimeState(
        runid=runid,
        config=resolved_config,
        active_mods=active_mods,
        region=region,
        states=states,
        capability_graph=capability_graph,
        model_capability_graph=model_capability_graph,
        v1_capabilities=v1_capabilities,
        wepp_binary_options=binary_options,
        wepp_binary_revision=binary_revision,
        wepp_model_tuples=model_tuples,
        projected_domains=projected_domains,
        generated_at=generated_at,
        run_state_revision=run_state_revision,
    )
