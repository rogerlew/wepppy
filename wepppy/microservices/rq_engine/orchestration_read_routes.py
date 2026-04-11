from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from wepppy.nodb.core import Climate, Landuse, Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.job_info import get_wepppy_rq_jobs_info
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, _normalize_scopes, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response

logger = logging.getLogger(__name__)

router = APIRouter()

CONTRACT_VERSION = "1.0.0-draft"
DEPLOYMENT_REVISION_ENV = "RQ_ENGINE_DEPLOYMENT_REVISION"
DEFAULT_DEPLOYMENT_REVISION = "dev"
ORCHESTRATION_ALLOWED_SCOPES = frozenset({"rq:read", "rq:status"})
UNKNOWN_UPDATED_AT = "2000-01-01T00:00:00Z"
RUN_STATE_DOMAIN_ORCHESTRATION = "orchestration"


class RunConfigMismatchError(ValueError):
    """Raised when a run exists but the requested config path token is not the run's config."""


@dataclass(frozen=True)
class StepSpec:
    step_id: str
    operation_id: str
    path: str
    method: str
    execution_mode: str
    depends_on: tuple[str, ...]
    blocks: tuple[str, ...]
    parallel_group: str | None
    returns_job: bool
    success_status_codes: tuple[int, ...]
    estimated_duration_bucket: str
    estimated_duration_seconds: int
    required_mods_any: tuple[str, ...] = ()
    required_state_keys: tuple[str, ...] = ()
    completion_state_keys: tuple[str, ...] = ()
    job_key: str | None = None
    timestamp_task: TaskEnum | None = None
    request_content_type: str | None = None
    required_fields: tuple[str, ...] = ()


STEP_SPECS: tuple[StepSpec, ...] = (
    StepSpec(
        step_id="fetch-dem-and-build-channels",
        operation_id=rq_operation_id("fetch_dem_and_build_channels"),
        path="/api/runs/{runid}/{config}/fetch-dem-and-build-channels",
        method="POST",
        execution_mode="async",
        depends_on=(),
        blocks=("set-outlet",),
        parallel_group="watershed_foundation",
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=180,
        job_key="fetch_dem_and_build_channels_rq",
        timestamp_task=TaskEnum.build_channels,
    ),
    StepSpec(
        step_id="set-outlet",
        operation_id=rq_operation_id("set_outlet"),
        path="/api/runs/{runid}/{config}/set-outlet",
        method="POST",
        execution_mode="async",
        depends_on=("fetch-dem-and-build-channels",),
        blocks=("build-subcatchments-and-abstract-watershed",),
        parallel_group="watershed_foundation",
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="fast",
        estimated_duration_seconds=20,
        required_state_keys=("watershed_has_channels",),
        job_key="set_outlet_rq",
        timestamp_task=TaskEnum.set_outlet,
    ),
    StepSpec(
        step_id="build-subcatchments-and-abstract-watershed",
        operation_id=rq_operation_id("build_subcatchments_and_abstract_watershed"),
        path="/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed",
        method="POST",
        execution_mode="async",
        depends_on=("set-outlet",),
        blocks=("build-climate", "build-landuse", "build-soils"),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=240,
        required_state_keys=("watershed_has_outlet",),
        job_key="build_subcatchments_and_abstract_watershed_rq",
        timestamp_task=TaskEnum.abstract_watershed,
    ),
    StepSpec(
        step_id="upload-sbs",
        operation_id=rq_operation_id("upload_sbs"),
        path="/api/runs/{runid}/{config}/tasks/upload-sbs/",
        method="POST",
        execution_mode="sync",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=("build-soils", "build-landuse"),
        parallel_group=None,
        returns_job=False,
        success_status_codes=(200,),
        estimated_duration_bucket="fast",
        estimated_duration_seconds=8,
        required_mods_any=("disturbed", "baer", "ash", "debris_flow"),
        completion_state_keys=("disturbed_sbs_uploaded",),
        timestamp_task=TaskEnum.landuse_map,
        request_content_type="multipart/form-data",
        required_fields=("input_upload_sbs",),
    ),
    StepSpec(
        step_id="build-climate",
        operation_id=rq_operation_id("build_climate"),
        path="/api/runs/{runid}/{config}/build-climate",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=("prep-wepp-watershed", "run-wepp"),
        parallel_group="prep_after_abstraction",
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=120,
        required_state_keys=("climate_station_ready",),
        completion_state_keys=("climate_built",),
        job_key="build_climate_rq",
        timestamp_task=TaskEnum.build_climate,
    ),
    StepSpec(
        step_id="build-landuse",
        operation_id=rq_operation_id("build_landuse"),
        path="/api/runs/{runid}/{config}/build-landuse",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=("prep-wepp-watershed", "run-wepp"),
        parallel_group="prep_after_abstraction",
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=120,
        completion_state_keys=("landuse_built",),
        job_key="build_landuse_rq",
        timestamp_task=TaskEnum.build_landuse,
    ),
    StepSpec(
        step_id="build-soils",
        operation_id=rq_operation_id("build_soils"),
        path="/api/runs/{runid}/{config}/build-soils",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=("prep-wepp-watershed", "run-wepp"),
        parallel_group="prep_after_abstraction",
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=120,
        completion_state_keys=("soils_built",),
        job_key="build_soils_rq",
        timestamp_task=TaskEnum.build_soils,
    ),
    StepSpec(
        step_id="prep-wepp-watershed",
        operation_id=rq_operation_id("prep_wepp_watershed"),
        path="/api/runs/{runid}/{config}/prep-wepp-watershed",
        method="POST",
        execution_mode="async",
        depends_on=("build-climate", "build-landuse", "build-soils"),
        blocks=("run-wepp", "run-wepp-watershed"),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=90,
        completion_state_keys=("wepp_hillslopes_run",),
        job_key="prep_wepp_watershed_rq",
    ),
    StepSpec(
        step_id="run-wepp",
        operation_id=rq_operation_id("run_wepp"),
        path="/api/runs/{runid}/{config}/run-wepp",
        method="POST",
        execution_mode="async",
        depends_on=("prep-wepp-watershed",),
        blocks=("run-wepp-watershed",),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=300,
        completion_state_keys=("wepp_hillslopes_run",),
        job_key="run_wepp_rq",
        timestamp_task=TaskEnum.run_wepp_hillslopes,
    ),
    StepSpec(
        step_id="run-wepp-watershed",
        operation_id=rq_operation_id("run_wepp_watershed"),
        path="/api/runs/{runid}/{config}/run-wepp-watershed",
        method="POST",
        execution_mode="async",
        depends_on=("run-wepp",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=300,
        completion_state_keys=("wepp_watershed_run",),
        job_key="run_wepp_watershed_rq",
        timestamp_task=TaskEnum.run_wepp_watershed,
    ),
    StepSpec(
        step_id="build-rusle",
        operation_id=rq_operation_id("build_rusle"),
        path="/api/runs/{runid}/{config}/build-rusle",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=120,
        required_mods_any=("disturbed", "baer"),
        job_key="build_rusle_rq",
        timestamp_task=TaskEnum.build_rusle,
    ),
    StepSpec(
        step_id="build-treatments",
        operation_id=rq_operation_id("build_treatments"),
        path="/api/runs/{runid}/{config}/build-treatments",
        method="POST",
        execution_mode="async",
        depends_on=("build-landuse",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=120,
        required_mods_any=("treatments",),
        job_key="build_treatments_rq",
        timestamp_task=TaskEnum.build_treatments,
    ),
    StepSpec(
        step_id="run-ash",
        operation_id=rq_operation_id("run_ash"),
        path="/api/runs/{runid}/{config}/run-ash",
        method="POST",
        execution_mode="async",
        depends_on=("run-wepp-watershed",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=240,
        required_mods_any=("ash",),
        job_key="run_ash_rq",
        timestamp_task=TaskEnum.run_watar,
    ),
    StepSpec(
        step_id="run-debris-flow",
        operation_id=rq_operation_id("run_debris_flow"),
        path="/api/runs/{runid}/{config}/run-debris-flow",
        method="POST",
        execution_mode="async",
        depends_on=("run-wepp-watershed",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=240,
        required_mods_any=("debris_flow",),
        job_key="run_debris_flow_rq",
        timestamp_task=TaskEnum.run_debris,
    ),
    StepSpec(
        step_id="prepare-roads",
        operation_id=rq_operation_id("prepare_roads"),
        path="/api/runs/{runid}/{config}/prepare-roads",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=("run-roads",),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(202,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=180,
        required_mods_any=("roads",),
        job_key="run_roads_prepare_rq",
        timestamp_task=TaskEnum.run_roads,
    ),
    StepSpec(
        step_id="run-roads",
        operation_id=rq_operation_id("run_roads"),
        path="/api/runs/{runid}/{config}/run-roads",
        method="POST",
        execution_mode="async",
        depends_on=("prepare-roads",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(202,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=300,
        required_mods_any=("roads",),
        job_key="run_roads_rq",
        timestamp_task=TaskEnum.run_roads,
    ),
    StepSpec(
        step_id="run-rhem",
        operation_id=rq_operation_id("run_rhem"),
        path="/api/runs/{runid}/{config}/run-rhem",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=240,
        required_mods_any=("rhem",),
        job_key="run_rhem_rq",
        timestamp_task=TaskEnum.run_rhem,
    ),
    StepSpec(
        step_id="run-swat",
        operation_id=rq_operation_id("run_swat"),
        path="/api/runs/{runid}/{config}/run-swat",
        method="POST",
        execution_mode="async",
        depends_on=("build-subcatchments-and-abstract-watershed",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(200,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=300,
        required_mods_any=("swat",),
        job_key="run_swat_rq",
    ),
    StepSpec(
        step_id="run-omni",
        operation_id=rq_operation_id("run_omni"),
        path="/api/runs/{runid}/{config}/run-omni",
        method="POST",
        execution_mode="async",
        depends_on=("run-wepp-watershed",),
        blocks=("run-omni-contrasts",),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(202,),
        estimated_duration_bucket="slow",
        estimated_duration_seconds=300,
        required_mods_any=("omni",),
        job_key="run_omni_rq",
        timestamp_task=TaskEnum.run_omni_scenarios,
    ),
    StepSpec(
        step_id="run-omni-contrasts",
        operation_id=rq_operation_id("run_omni_contrasts"),
        path="/api/runs/{runid}/{config}/run-omni-contrasts",
        method="POST",
        execution_mode="async",
        depends_on=("run-omni",),
        blocks=(),
        parallel_group=None,
        returns_job=True,
        success_status_codes=(202,),
        estimated_duration_bucket="medium",
        estimated_duration_seconds=180,
        required_mods_any=("omni",),
        job_key="run_omni_contrasts_rq",
        timestamp_task=TaskEnum.run_omni_contrasts,
    ),
)

STEP_BY_ID = {spec.step_id: spec for spec in STEP_SPECS}

INVALIDATION_EDGES: Mapping[str, tuple[str, ...]] = {
    "fetch-dem-and-build-channels": (
        "set-outlet",
        "build-subcatchments-and-abstract-watershed",
        "build-climate",
        "build-landuse",
        "build-soils",
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "set-outlet": (
        "build-subcatchments-and-abstract-watershed",
        "build-climate",
        "build-landuse",
        "build-soils",
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "build-subcatchments-and-abstract-watershed": (
        "build-climate",
        "build-landuse",
        "build-soils",
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "upload-sbs": (
        "build-landuse",
        "build-soils",
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "build-climate": (
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "build-landuse": (
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "build-soils": (
        "prep-wepp-watershed",
        "run-wepp",
        "run-wepp-watershed",
    ),
    "run-wepp": ("run-wepp-watershed",),
    "run-wepp-watershed": ("run-ash", "run-debris-flow", "run-omni"),
    "run-omni": ("run-omni-contrasts",),
}

_NON_TERMINAL_JOB_STATUSES = frozenset({"queued", "started", "deferred", "scheduled"})
_FAILED_JOB_STATUSES = frozenset({"failed", "stopped"})
_TERMINAL_OUTCOMES = frozenset({"finished", "failed", "stopped", "canceled"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deployment_revision() -> str:
    value = str(os.getenv(DEPLOYMENT_REVISION_ENV) or DEFAULT_DEPLOYMENT_REVISION).strip()
    return value or DEFAULT_DEPLOYMENT_REVISION


def _base_payload() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "deployment_revision": _deployment_revision(),
    }


def _run_state_vector(*, orchestration_revision: str) -> dict[str, str | None]:
    return {
        "orchestration_revision": orchestration_revision,
        "metadata_revision": None,
        "outputs_revision": None,
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
        return _timestamp_to_iso(int(safe_mtime))
    except OSError:
        return None


def _runtime_snapshot_updated_at(runtime: Mapping[str, Any]) -> str:
    runid = str(runtime.get("runid") or "").strip()
    run_directory_updated_at = _run_directory_updated_at(runid)
    if run_directory_updated_at:
        return run_directory_updated_at

    generated_at = str(runtime.get("generated_at") or "").strip()
    if generated_at:
        return generated_at
    return _utc_now_iso()


def _stable_updated_at(
    *,
    candidate_updated_at: str | None,
    fallback_updated_at: str,
) -> str:
    if candidate_updated_at:
        return candidate_updated_at
    return fallback_updated_at


def _timestamp_to_iso(timestamp_value: int | None) -> str | None:
    if timestamp_value is None:
        return None
    return datetime.fromtimestamp(float(timestamp_value), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_datetime_to_timestamp(value: Any) -> int | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    return _normalize_scopes(claims.get("scope"), get_jwt_config().scope_separator)


def _require_orchestration_claims(request: Request, runid: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if not scopes.intersection(ORCHESTRATION_ALLOWED_SCOPES):
        required_text = ", ".join(sorted(ORCHESTRATION_ALLOWED_SCOPES))
        raise AuthError(
            f"Token missing required scope(s): {required_text}",
            status_code=403,
            code="forbidden",
        )
    authorize_run_access(claims, runid)
    return claims


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


def _step_completion_task_value(prep: RedisPrep, task: TaskEnum | None) -> int | None:
    if task is None:
        return None
    value = prep[task]
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_config_token(value: str) -> str:
    text = str(value or "").strip().lower()
    if text.endswith(".cfg"):
        return text[:-4]
    return text


def _load_runtime_state(runid: str, config: str) -> dict[str, Any]:
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
    disturbed_enabled = "disturbed" in active_mods

    disturbed_sol_ver_selected = False
    if disturbed_enabled:
        disturbed = Disturbed.getInstance(wd)
        disturbed_sol_ver_selected = bool(getattr(disturbed, "sol_ver", None) is not None)

    climate_station_required = bool(getattr(climate, "has_climatestation_mode"))
    climate_station_ready = bool(getattr(climate, "has_station")) or not climate_station_required

    states: dict[str, Any] = {
        "has_dem": bool(getattr(ron, "has_dem")),
        "watershed_has_channels": bool(getattr(watershed, "has_channels")),
        "watershed_has_outlet": bool(getattr(watershed, "has_outlet")),
        "watershed_is_abstracted": bool(getattr(watershed, "is_abstracted")),
        "watershed_subcatchment_count": int(getattr(watershed, "sub_n") or 0),
        "climate_built": bool(getattr(climate, "has_climate")),
        "climate_station_ready": climate_station_ready,
        "climate_mode": _enum_name(getattr(climate, "climate_mode")),
        "landuse_built": bool(getattr(landuse, "has_landuse")),
        "landuse_mode": _enum_name(getattr(landuse, "mode")),
        "soils_built": bool(getattr(soils, "has_soils")),
        "soils_mode": _enum_name(getattr(soils, "mode")),
        "wepp_has_run": bool(getattr(wepp, "has_run")),
        "disturbed_enabled": disturbed_enabled,
        "disturbed_sbs_uploaded": bool(getattr(prep, "has_sbs")),
        "disturbed_sol_ver_selected": disturbed_sol_ver_selected,
    }

    step_completion_ts: dict[str, int | None] = {}
    for spec in STEP_SPECS:
        step_completion_ts[spec.step_id] = _step_completion_task_value(prep, spec.timestamp_task)

    wepp_hillslopes_timestamp = _step_completion_task_value(prep, TaskEnum.run_wepp_hillslopes)
    wepp_watershed_timestamp = _step_completion_task_value(prep, TaskEnum.run_wepp_watershed)
    states["wepp_hillslopes_run"] = bool(wepp_hillslopes_timestamp is not None or states["wepp_has_run"])
    states["wepp_watershed_run"] = bool(wepp_watershed_timestamp is not None or states["wepp_has_run"])

    if step_completion_ts.get("run-wepp") is None and wepp_hillslopes_timestamp is not None:
        step_completion_ts["run-wepp"] = wepp_hillslopes_timestamp
    if step_completion_ts.get("run-wepp-watershed") is None and wepp_watershed_timestamp is not None:
        step_completion_ts["run-wepp-watershed"] = wepp_watershed_timestamp

    prep_job_ids = prep.get_rq_job_ids()
    step_job_id: dict[str, str] = {}
    for spec in STEP_SPECS:
        if spec.job_key is None:
            continue
        job_id = prep_job_ids.get(spec.job_key)
        if job_id:
            step_job_id[spec.step_id] = str(job_id)

    job_info_by_id: dict[str, dict[str, Any]] = {}
    unique_job_ids = sorted({job_id for job_id in step_job_id.values() if job_id})
    if unique_job_ids:
        raw = get_wepppy_rq_jobs_info(unique_job_ids)
        job_info_by_id = {str(job_id): info for job_id, info in raw.items()}

    step_job: dict[str, dict[str, Any]] = {}
    for step_id, job_id in step_job_id.items():
        info = job_info_by_id.get(job_id, {})
        status = _effective_job_status(info)
        ended_at = _effective_job_ended_at(info)
        progress = _job_progress_payload(info)
        step_job[step_id] = {
            "job_id": job_id,
            "status": status,
            "ended_at": ended_at,
            "exc_info": info.get("exc_info"),
        }
        if progress is not None:
            step_job[step_id]["progress"] = progress
        if step_completion_ts.get(step_id) is None:
            if status == "finished":
                ended_ts = _parse_datetime_to_timestamp(ended_at)
                if ended_ts is not None:
                    step_completion_ts[step_id] = ended_ts

    return {
        "runid": runid,
        "config": config,
        "active_mods": active_mods,
        "states": states,
        "step_completion_ts": step_completion_ts,
        "step_job": step_job,
        "generated_at": _utc_now_iso(),
    }


def _is_step_applicable(spec: StepSpec, active_mods: Sequence[str]) -> bool:
    if not spec.required_mods_any:
        return True
    active_mod_set = {mod.lower() for mod in active_mods}
    return bool(active_mod_set.intersection({mod.lower() for mod in spec.required_mods_any}))


def _applicable_specs(active_mods: Sequence[str]) -> list[StepSpec]:
    return [spec for spec in STEP_SPECS if _is_step_applicable(spec, active_mods)]


def _dependency_issue_id(step_id: str) -> str:
    return f"issue_step_{step_id.replace('-', '_')}_incomplete"


def _first_line(text: Any) -> str | None:
    if text is None:
        return None
    value = str(text).strip()
    if not value:
        return None
    return value.splitlines()[0]


def _normalize_job_status(value: Any) -> str | None:
    status = str(value or "").strip().lower()
    return status or None


def _iter_child_job_nodes(job_info: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    children = job_info.get("children")
    if not isinstance(children, Mapping):
        return []

    nodes: list[Mapping[str, Any]] = []
    for child_entries in children.values():
        if not isinstance(child_entries, list):
            continue
        for child in child_entries:
            if not isinstance(child, Mapping):
                continue
            nodes.append(child)
            nodes.extend(_iter_child_job_nodes(child))
    return nodes


def _effective_job_status(job_info: Mapping[str, Any]) -> str | None:
    root_status = _normalize_job_status(job_info.get("status"))
    child_nodes = _iter_child_job_nodes(job_info)
    if not child_nodes:
        return root_status

    child_statuses = [status for status in (_normalize_job_status(node.get("status")) for node in child_nodes) if status]
    if not child_statuses:
        return root_status

    if any(status in _FAILED_JOB_STATUSES for status in child_statuses):
        return "failed"
    if any(status == "canceled" for status in child_statuses):
        return "canceled"
    if any(status in _NON_TERMINAL_JOB_STATUSES for status in child_statuses):
        return "started"
    if all(status in _TERMINAL_OUTCOMES for status in child_statuses):
        return "finished"
    return root_status


def _effective_job_ended_at(job_info: Mapping[str, Any]) -> str | None:
    all_nodes = [job_info, *_iter_child_job_nodes(job_info)]
    latest_ended_ts: int | None = None
    for node in all_nodes:
        ended_ts = _parse_datetime_to_timestamp(node.get("ended_at"))
        if ended_ts is None:
            continue
        if latest_ended_ts is None or ended_ts > latest_ended_ts:
            latest_ended_ts = ended_ts

    if latest_ended_ts is None:
        return _first_line(job_info.get("ended_at"))
    return _timestamp_to_iso(latest_ended_ts)


def _effective_job_updated_at(job_info: Mapping[str, Any]) -> str | None:
    all_nodes = [job_info, *_iter_child_job_nodes(job_info)]
    latest_seen_ts: int | None = None
    for node in all_nodes:
        for field in ("ended_at", "started_at"):
            seen_ts = _parse_datetime_to_timestamp(node.get(field))
            if seen_ts is None:
                continue
            if latest_seen_ts is None or seen_ts > latest_seen_ts:
                latest_seen_ts = seen_ts

    if latest_seen_ts is not None:
        return _timestamp_to_iso(latest_seen_ts)
    return _first_line(job_info.get("ended_at")) or _first_line(job_info.get("started_at"))


def _job_progress_payload(job_info: Mapping[str, Any]) -> dict[str, Any] | None:
    nodes = [job_info, *_iter_child_job_nodes(job_info)]
    statuses = [status for status in (_normalize_job_status(node.get("status")) for node in nodes) if status]
    if not statuses:
        return None

    total = len(statuses)
    completed = sum(1 for status in statuses if status in _TERMINAL_OUTCOMES)
    percent = round((completed / total) * 100.0, 2)
    updated_at = _effective_job_updated_at(job_info) or UNKNOWN_UPDATED_AT
    return {
        "completed": completed,
        "total": total,
        "unit": "jobs",
        "percent": percent,
        "updated_at": updated_at,
    }


def _last_attempt_payload(step_job: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not step_job:
        return None
    job_id = step_job.get("job_id")
    status = str(step_job.get("status") or "").strip().lower() or None
    if not job_id and not status:
        return None

    outcome = status if status in _TERMINAL_OUTCOMES else None
    error_code = None
    error_message = None
    if status in _FAILED_JOB_STATUSES:
        error_code = "job_failed"
        error_message = "Last attempt failed. Inspect jobinfo for details."
    elif status == "canceled":
        error_code = "job_canceled"
        error_message = "Last attempt was canceled."

    recoverable = True if status in (_FAILED_JOB_STATUSES | {"canceled"}) else None
    recovery_hint = (
        "Retry after resolving the blocking issue."
        if status in (_FAILED_JOB_STATUSES | {"canceled"})
        else None
    )
    return {
        "job_id": job_id,
        "outcome": outcome,
        "ended_at": step_job.get("ended_at"),
        "error_code": error_code,
        "error_message": error_message,
        "recoverable": recoverable,
        "recovery_hint": recovery_hint,
    }


def _compute_payloads(runtime: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    runid = str(runtime["runid"])
    config = str(runtime["config"])
    active_mods = tuple(runtime["active_mods"])
    states = dict(runtime["states"])
    completion_ts = dict(runtime["step_completion_ts"])
    step_job = dict(runtime["step_job"])

    specs = _applicable_specs(active_mods)
    spec_by_id = {spec.step_id: spec for spec in specs}
    order = {spec.step_id: idx for idx, spec in enumerate(specs)}

    invalidated_by: dict[str, tuple[str, int]] = {}
    invalidations_by_source: dict[str, dict[str, Any]] = {}
    for source_step_id, target_step_ids in INVALIDATION_EDGES.items():
        source_spec = spec_by_id.get(source_step_id)
        if source_spec is None:
            continue
        source_ts = completion_ts.get(source_step_id)
        if source_ts is None:
            continue

        for target_step_id in target_step_ids:
            target_spec = spec_by_id.get(target_step_id)
            if target_spec is None:
                continue
            target_ts = completion_ts.get(target_step_id)
            if target_ts is None:
                continue
            if source_ts <= target_ts:
                continue

            previous = invalidated_by.get(target_step_id)
            if previous is not None and previous[1] >= source_ts:
                continue
            invalidated_by[target_step_id] = (source_step_id, source_ts)

            bucket = invalidations_by_source.setdefault(
                source_step_id,
                {
                    "source_operation_id": source_spec.operation_id,
                    "at": _timestamp_to_iso(source_ts),
                    "invalidated_steps": set(),
                },
            )
            bucket["invalidated_steps"].add(target_step_id)

    issues_by_id: dict[str, dict[str, Any]] = {}
    step_issue_ids: dict[str, list[str]] = {}
    step_payloads: list[dict[str, Any]] = []

    def _record_issue(step_id: str, issue: dict[str, Any]) -> None:
        issue_id = issue["issue_id"]
        issues_by_id.setdefault(issue_id, issue)
        step_issue_ids.setdefault(step_id, [])
        if issue_id not in step_issue_ids[step_id]:
            step_issue_ids[step_id].append(issue_id)

    status_by_step: dict[str, str] = {}
    for spec in specs:
        step_id = spec.step_id
        dep_missing = [dep for dep in spec.depends_on if status_by_step.get(dep) != "completed"]
        for dep_step in dep_missing:
            dep_spec = spec_by_id[dep_step]
            issue_id = _dependency_issue_id(dep_step)
            _record_issue(
                step_id,
                {
                    "issue_id": issue_id,
                    "code": "dependency_not_completed",
                    "message": f"Step '{dep_step}' must complete before '{step_id}' can run.",
                    "severity": "warning",
                    "controller": "pipeline",
                    "field": dep_step,
                    "operation_id": dep_spec.operation_id,
                    "recoverable": True,
                    "recovery_hint": "Run the dependency step first.",
                    "recovery_actions": [
                        {
                            "operation_id": dep_spec.operation_id,
                            "required_fields": [],
                            "priority": 1,
                        }
                    ],
                },
            )

        if step_id == "build-climate" and not states.get("climate_station_ready", False):
            _record_issue(
                step_id,
                {
                    "issue_id": "issue_climate_station_missing",
                    "code": "climate_station_missing",
                    "message": "No climate station selected for the active climate mode.",
                    "severity": "error",
                    "controller": "climate",
                    "field": "climatestation",
                    "operation_id": spec.operation_id,
                    "recoverable": True,
                    "recovery_hint": "Set climatestation or choose a compatible climate_mode.",
                    "recovery_actions": [
                        {
                            "operation_id": spec.operation_id,
                            "required_fields": ["climatestation"],
                            "priority": 1,
                        },
                        {
                            "operation_id": spec.operation_id,
                            "required_fields": ["climate_mode"],
                            "priority": 2,
                        },
                    ],
                },
            )

        for required_key in spec.required_state_keys:
            if states.get(required_key, False):
                continue
            issue_id = f"issue_state_{required_key}"
            _record_issue(
                step_id,
                {
                    "issue_id": issue_id,
                    "code": "state_precondition_missing",
                    "message": f"State precondition '{required_key}' is not satisfied.",
                    "severity": "warning",
                    "controller": "state",
                    "field": required_key,
                    "operation_id": spec.operation_id,
                    "recoverable": True,
                    "recovery_hint": f"Satisfy '{required_key}' before running '{step_id}'.",
                    "recovery_actions": [],
                },
            )

        issue_ids = step_issue_ids.get(step_id, [])
        preconditions_met = len(issue_ids) == 0

        step_job_info = step_job.get(step_id)
        job_status = str((step_job_info or {}).get("status") or "").strip().lower() or None

        invalidation = invalidated_by.get(step_id)
        step_completed_ts = completion_ts.get(step_id)
        completed_via_state = any(bool(states.get(key, False)) for key in spec.completion_state_keys)
        completed_via_job = job_status == "finished"
        completed = (step_completed_ts is not None or completed_via_state or completed_via_job) and invalidation is None

        if job_status in _NON_TERMINAL_JOB_STATUSES:
            status = "running"
        elif completed:
            status = "completed"
        elif job_status in _FAILED_JOB_STATUSES:
            status = "failed"
        elif job_status == "canceled":
            status = "canceled"
        elif preconditions_met:
            status = "ready"
        else:
            status = "blocked"

        status_by_step[step_id] = status

        payload: dict[str, Any] = {
            "step_id": step_id,
            "operation_id": spec.operation_id,
            "status": status,
            "execution_mode": spec.execution_mode,
            "preconditions_met": preconditions_met,
            "depends_on": list(spec.depends_on),
            "blocks": list(spec.blocks),
            "can_run_now": status == "ready" and preconditions_met,
            "allow_rerun": True,
            "parallel_group": spec.parallel_group,
            "endpoint": spec.path,
            "method": spec.method,
            "returns_job": spec.returns_job,
            "success_status_codes": list(spec.success_status_codes),
            "estimated_duration_bucket": spec.estimated_duration_bucket,
            "estimated_duration_seconds": spec.estimated_duration_seconds,
        }

        if spec.request_content_type is not None:
            payload["request_content_type"] = spec.request_content_type
        if spec.required_fields:
            payload["required_fields"] = list(spec.required_fields)
        if step_completed_ts is not None:
            payload["completed_at"] = _timestamp_to_iso(step_completed_ts)

        if invalidation is not None:
            source_step_id, _source_ts = invalidation
            source_spec = spec_by_id[source_step_id]
            payload["invalidated_by_operation_id"] = source_spec.operation_id

        if step_job_info and status == "running":
            payload["active_job_id"] = step_job_info.get("job_id")
            progress = step_job_info.get("progress")
            if isinstance(progress, Mapping):
                payload["progress"] = dict(progress)

        last_attempt = _last_attempt_payload(step_job_info)
        if last_attempt is not None:
            payload["last_attempt"] = last_attempt

        step_payloads.append(payload)

    ordered_recent_invalidations = []
    for source_step_id, entry in invalidations_by_source.items():
        invalidated_steps = sorted(entry["invalidated_steps"], key=lambda item: order.get(item, 10_000))
        ordered_recent_invalidations.append(
            {
                "source_operation_id": entry["source_operation_id"],
                "at": entry["at"],
                "invalidated_steps": invalidated_steps,
            }
        )
    ordered_recent_invalidations.sort(
        key=lambda entry: (
            entry["at"] or "",
            entry["source_operation_id"],
        ),
        reverse=True,
    )

    invalidated_step_entries: list[dict[str, Any]] = []
    for target_step_id, (source_step_id, source_ts) in sorted(
        invalidated_by.items(),
        key=lambda item: (-item[1][1], order.get(item[0], 10_000), item[0]),
    ):
        target_spec = spec_by_id[target_step_id]
        source_spec = spec_by_id[source_step_id]
        invalidated_step_entries.append(
            {
                "step_id": target_step_id,
                "operation_id": target_spec.operation_id,
                "source_operation_id": source_spec.operation_id,
                "invalidated_at": _timestamp_to_iso(source_ts),
            }
        )

    ready_operations: list[dict[str, Any]] = []
    ineligible_operations: list[dict[str, Any]] = []
    for payload in step_payloads:
        step_id = payload["step_id"]
        status = payload["status"]
        issue_ids = sorted(step_issue_ids.get(step_id, []))
        if status in {"failed", "canceled"} and not issue_ids:
            synthetic_issue_id = f"issue_step_{step_id.replace('-', '_')}_{status}"
            issues_by_id.setdefault(
                synthetic_issue_id,
                {
                    "issue_id": synthetic_issue_id,
                    "code": "last_attempt_failed" if status == "failed" else "last_attempt_canceled",
                    "message": f"Last attempt for '{step_id}' ended with status '{status}'.",
                    "severity": "error",
                    "controller": "pipeline",
                    "field": "last_attempt",
                    "operation_id": payload["operation_id"],
                    "recoverable": True,
                    "recovery_hint": "Re-run the step after resolving the failure cause.",
                    "recovery_actions": [
                        {
                            "operation_id": payload["operation_id"],
                            "required_fields": [],
                            "priority": 1,
                        }
                    ],
                },
            )
            issue_ids = [synthetic_issue_id]
            step_issue_ids[step_id] = issue_ids

        if status == "ready":
            ready_reason = "dependencies_satisfied"
            if "invalidated_by_operation_id" in payload:
                ready_reason = "invalidated_by_recent_mutation"
            ready_operations.append(
                {
                    "operation_id": payload["operation_id"],
                    "step_id": step_id,
                    "reason": ready_reason,
                }
            )
        elif status in {"blocked", "failed", "canceled"}:
            ineligible_operations.append(
                {
                    "operation_id": payload["operation_id"],
                    "step_id": step_id,
                    "blocked_by_issue_ids": issue_ids,
                }
            )

    blocking_issues = [issues_by_id[key] for key in sorted(issues_by_id)]

    next_actionable_steps: list[dict[str, Any]] = []
    queued_step_ids: set[str] = set()
    step_by_operation = {payload["operation_id"]: payload for payload in step_payloads}

    for issue in sorted(blocking_issues, key=lambda item: item["issue_id"]):
        if issue.get("severity") != "error":
            continue
        recovery_actions = issue.get("recovery_actions") or []
        for action in sorted(
            recovery_actions,
            key=lambda item: (int(item.get("priority", 99)), str(item.get("operation_id") or "")),
        ):
            operation_id = str(action.get("operation_id") or "")
            step_payload = step_by_operation.get(operation_id)
            if step_payload is None:
                continue
            step_id = step_payload["step_id"]
            if step_id in queued_step_ids:
                continue
            if step_payload["status"] == "completed":
                continue
            queued_step_ids.add(step_id)
            next_actionable_steps.append(
                {
                    "step_id": step_id,
                    "operation_id": operation_id,
                    "reason": "resolve_blocking_issue",
                    "related_issue_ids": [issue["issue_id"]],
                }
            )

    for payload in sorted(step_payloads, key=lambda item: order.get(item["step_id"], 10_000)):
        if payload["status"] != "ready":
            continue
        step_id = payload["step_id"]
        if step_id in queued_step_ids:
            continue
        queued_step_ids.add(step_id)
        entry = {
            "step_id": step_id,
            "operation_id": payload["operation_id"],
            "reason": (
                "invalidated_by_recent_mutation"
                if "invalidated_by_operation_id" in payload
                else "dependencies_satisfied"
            ),
        }
        if "invalidated_by_operation_id" in payload:
            entry["invalidated_by_operation_id"] = payload["invalidated_by_operation_id"]
        next_actionable_steps.append(entry)

    for idx, entry in enumerate(next_actionable_steps, start=1):
        entry["priority"] = idx

    timeline_candidates = [ts for ts in completion_ts.values() if ts is not None]
    for info in step_job.values():
        ended_ts = _parse_datetime_to_timestamp(info.get("ended_at"))
        if ended_ts is not None:
            timeline_candidates.append(ended_ts)
    data_updated_at = _timestamp_to_iso(max(timeline_candidates)) if timeline_candidates else None
    fallback_updated_at = _runtime_snapshot_updated_at(runtime)

    state_signature = {
        "runid": runid,
        "config": config,
        "active_mods": list(active_mods),
        "states": states,
        "data_updated_at": data_updated_at,
        "snapshot_fallback_updated_at": fallback_updated_at if data_updated_at is None else None,
        "steps": [
            {
                "step_id": payload["step_id"],
                "status": payload["status"],
                "preconditions_met": payload["preconditions_met"],
                "can_run_now": payload["can_run_now"],
                "active_job_id": payload.get("active_job_id"),
                "invalidated_by_operation_id": payload.get("invalidated_by_operation_id"),
                "last_attempt": payload.get("last_attempt"),
            }
            for payload in step_payloads
        ],
        "invalidations": invalidated_step_entries,
        "issues": sorted(issues_by_id),
        "ready_operations": ready_operations,
        "ineligible_operations": ineligible_operations,
        "next_actionable_steps": next_actionable_steps,
    }
    digest = hashlib.sha256(json.dumps(state_signature, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:12]
    run_state_revision = f"runstate:{runid}:{digest}"
    run_state_vector = _run_state_vector(orchestration_revision=run_state_revision)
    updated_at = _stable_updated_at(
        candidate_updated_at=data_updated_at,
        fallback_updated_at=fallback_updated_at,
    )
    if data_updated_at is None:
        data_updated_at = updated_at

    pipeline_payload = _base_payload()
    pipeline_payload.update(
        {
            "run_state_domain": RUN_STATE_DOMAIN_ORCHESTRATION,
            "run_state_revision": run_state_revision,
            "run_state_vector": run_state_vector,
            "updated_at": updated_at,
            "data_state": "materialized",
            "data_updated_at": data_updated_at,
            "etag": f'W/"pipeline:{runid}:{digest}"',
            "runid": runid,
            "config": config,
            "active_mods": list(active_mods),
            "recent_invalidations": ordered_recent_invalidations,
            "steps": step_payloads,
        }
    )

    readiness_payload = _base_payload()
    readiness_payload.update(
        {
            "run_state_domain": RUN_STATE_DOMAIN_ORCHESTRATION,
            "run_state_revision": run_state_revision,
            "run_state_vector": run_state_vector,
            "updated_at": updated_at,
            "data_state": "materialized",
            "data_updated_at": data_updated_at,
            "etag": f'W/"readiness:{runid}:{digest}"',
            "run": {
                "has_dem": bool(states.get("has_dem", False)),
                "mods": list(active_mods),
            },
            "watershed": {
                "channels_built": bool(states.get("watershed_has_channels", False)),
                "outlet_set": bool(states.get("watershed_has_outlet", False)),
                "abstracted": bool(states.get("watershed_is_abstracted", False)),
                "num_subcatchments": int(states.get("watershed_subcatchment_count", 0)),
            },
            "climate": {
                "built": bool(states.get("climate_built", False)),
                "mode": states.get("climate_mode"),
            },
            "landuse": {
                "built": bool(states.get("landuse_built", False)),
                "mode": states.get("landuse_mode"),
            },
            "soils": {
                "built": bool(states.get("soils_built", False)),
                "mode": states.get("soils_mode"),
            },
            "wepp": {
                "hillslopes_run": bool(states.get("wepp_hillslopes_run", False)),
                "watershed_run": bool(states.get("wepp_watershed_run", False)),
            },
            "mods": {
                "disturbed": {
                    "enabled": bool(states.get("disturbed_enabled", False)),
                    "sbs_uploaded": bool(states.get("disturbed_sbs_uploaded", False)),
                    "sol_ver_selected": bool(states.get("disturbed_sol_ver_selected", False)),
                }
            },
            "invalidated_steps": invalidated_step_entries,
            "blocking_issues": blocking_issues,
            "ready_operations": ready_operations,
            "ineligible_operations": ineligible_operations,
            "next_actionable_steps": next_actionable_steps,
        }
    )

    return pipeline_payload, readiness_payload


@router.get(
    "/runs/{runid}/{config}/pipeline",
    summary="Get run pipeline state",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only orchestration snapshot; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_pipeline"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Pipeline payload returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def get_pipeline(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_orchestration_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine pipeline auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine pipeline state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        payload, _readiness_payload = _compute_payloads(runtime)
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine pipeline payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/readiness",
    summary="Get run readiness state",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only readiness summary with deterministic next-action ordering; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_readiness"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Readiness payload returned.",
        extra={404: "Run not found. Returns the canonical error payload."},
    ),
)
def get_readiness(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _require_orchestration_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine readiness auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        runtime = _load_runtime_state(runid, config)
    except FileNotFoundError:
        return error_response("Run not found", status_code=404, code="not_found")
    except RunConfigMismatchError:
        return error_response("Run not found", status_code=404, code="not_found")
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine readiness state load failed")
        return error_response("Error Handling Request", status_code=500)

    try:
        _pipeline_payload, payload = _compute_payloads(runtime)
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine readiness payload build failed")
        return error_response("Error Handling Request", status_code=500)


__all__ = ["router"]
