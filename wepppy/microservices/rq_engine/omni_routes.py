from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import FormData, UploadFile
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.core import Watershed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.omni_rq import (
    delete_omni_contrasts_rq,
    run_omni_contrasts_rq,
    run_omni_scenarios_rq,
)
from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import resolve as nodir_resolve
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
SBS_ALLOWED_EXTENSIONS = ("tif", "tiff", "img")
SBS_MAX_BYTES = 100 * 1024 * 1024
GEOJSON_ALLOWED_EXTENSIONS = ("geojson", "json")
GEOJSON_MAX_BYTES = 100 * 1024 * 1024
CONTRAST_SELECTION_MODE_DEFAULT = "cumulative"


def _is_base_project_context(runid: str, config: str) -> bool:
    runid_leaf = runid.split(";;")[-1].strip().lower() if runid else ""
    config_token = str(config).strip().lower() if config is not None else ""
    return runid_leaf == "_base" or config_token == "_base"


def _normalize_extensions(allowed_extensions: tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = ext.lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def _validate_upload_filename(upload: UploadFile) -> str:
    raw_name = upload.filename or ""
    if raw_name.strip() == "":
        raise ValueError("no filename specified")
    safe_name = secure_filename(raw_name)
    if not safe_name:
        raise ValueError("Invalid filename")
    safe_name = safe_name.lower().strip()
    if not safe_name:
        raise ValueError("Invalid filename")
    return safe_name


def _enforce_extension(filename: str, allowed_extensions: set[str]) -> None:
    if not allowed_extensions:
        return
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed_extensions:
        allowed_list = ", ".join(sorted(f".{ext}" for ext in allowed_extensions))
        raise ValueError(f"Invalid file extension. Allowed: {allowed_list}")


def _enforce_max_bytes(upload: UploadFile, max_bytes: int | None) -> None:
    if max_bytes is None:
        return
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > max_bytes:
        raise ValueError("File exceeds maximum allowed size")


def _save_upload(
    upload: UploadFile,
    *,
    destination_dir: Path,
    allowed_extensions: set[str],
    max_bytes: int | None,
) -> Path:
    filename = _validate_upload_filename(upload)
    _enforce_extension(filename, allowed_extensions)
    _enforce_max_bytes(upload, max_bytes)

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    if destination.exists():
        destination.unlink()

    with destination.open("wb") as dest:
        shutil.copyfileobj(upload.file, dest)

    return destination


def _coerce_omni_scenario_list(payload: dict[str, Any], raw_json: Any) -> list[dict[str, Any]] | None:
    if isinstance(raw_json, list):
        return raw_json

    scenarios_raw = payload.get("scenarios")
    if scenarios_raw is None:
        return None

    if isinstance(scenarios_raw, list):
        if len(scenarios_raw) == 1 and isinstance(scenarios_raw[0], str):
            scenarios_raw = scenarios_raw[0]
        else:
            return scenarios_raw  # type: ignore[return-value]

    if isinstance(scenarios_raw, dict):
        return [scenarios_raw]

    if isinstance(scenarios_raw, str):
        try:
            parsed = json.loads(scenarios_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Scenarios data must be valid JSON") from exc
        if not isinstance(parsed, list):
            raise ValueError("Scenarios data must be a list")
        return parsed

    raise ValueError("Scenarios data must be a list")


def _coerce_contrast_pairs(payload: dict[str, Any], raw_json: Any) -> list[dict[str, str]] | None:
    raw_pairs: Any = None
    if isinstance(raw_json, dict):
        raw_pairs = raw_json.get("contrast_pairs") or raw_json.get("omni_contrast_pairs")
    if raw_pairs is None:
        raw_pairs = payload.get("omni_contrast_pairs") or payload.get("contrast_pairs")
    if raw_pairs is None:
        return None

    if isinstance(raw_pairs, str):
        try:
            parsed = json.loads(raw_pairs)
        except json.JSONDecodeError as exc:
            raise ValueError("contrast_pairs must be valid JSON") from exc
    else:
        parsed = raw_pairs

    if isinstance(parsed, dict):
        parsed_list = [parsed]
    elif isinstance(parsed, list):
        parsed_list = parsed
    else:
        raise ValueError("contrast_pairs must be a list")

    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for idx, entry in enumerate(parsed_list, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"contrast_pairs[{idx}] must be an object")
        control_raw = entry.get("control_scenario")
        contrast_raw = entry.get("contrast_scenario")
        if control_raw in (None, "") or contrast_raw in (None, ""):
            raise ValueError("contrast_pairs entries require control_scenario and contrast_scenario")
        control = str(control_raw).strip()
        contrast = str(contrast_raw).strip()
        if not control or not contrast:
            raise ValueError("contrast_pairs entries require control_scenario and contrast_scenario")
        key = (control, contrast)
        if key in seen:
            continue
        normalized.append({"control_scenario": control, "contrast_scenario": contrast})
        seen.add(key)

    return normalized or None


def _extract_upload(form: FormData, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _normalize_contrast_selection_mode(value: Any) -> str:
    if value is None:
        return CONTRAST_SELECTION_MODE_DEFAULT
    token = str(value).strip().lower()
    if not token:
        return CONTRAST_SELECTION_MODE_DEFAULT
    aliases = {
        "objective": "cumulative",
        "objective_parameter": "cumulative",
        "cumulative_objective": "cumulative",
        "cumulative_obj_param": "cumulative",
        "stream_order_pruning": "stream_order",
        "stream-order-pruning": "stream_order",
        "user-defined-hillslope-groups": "user_defined_hillslope_groups",
        "user-defined-hillslope-group": "user_defined_hillslope_groups",
    }
    return aliases.get(token, token)


def _coerce_optional_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _coerce_optional_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_optional_int_list(value: Any, field_name: str) -> list[int] | None:
    if value is None or value == "":
        return None
    raw_values: list[Any]
    if isinstance(value, str):
        raw_values = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]

    parsed: list[int] = []
    for item in raw_values:
        if item is None or item == "":
            continue
        try:
            parsed.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} entries must be integers") from exc
    return parsed or None


def _coerce_optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"1", "true", "yes", "on"}:
            return True
        if token in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field_name} must be a boolean")


def _preflight_omni_roots(wd: str) -> None:
    nodir_resolve(wd, "climate", view="effective")
    nodir_resolve(wd, "watershed", view="effective")
    nodir_resolve(wd, "landuse", view="effective")
    nodir_resolve(wd, "soils", view="effective")


def _prepare_omni_scenarios(
    payload: dict[str, Any],
    raw_json: Any,
    form: FormData,
    *,
    runid: str,
    config: str,
    wd: str,
) -> list[tuple[OmniScenario, dict[str, Any]]]:
    scenarios_payload = _coerce_omni_scenario_list(payload, raw_json)
    if scenarios_payload is None:
        raise ValueError("Missing scenarios data")
    if not isinstance(scenarios_payload, list):
        raise ValueError("Scenarios data must be a list")

    limbo_dir = Path(wd) / "omni" / "_limbo"
    limbo_dir.mkdir(parents=True, exist_ok=True)

    allowed_extensions = _normalize_extensions(SBS_ALLOWED_EXTENSIONS)
    parsed_inputs: list[tuple[OmniScenario, dict[str, Any]]] = []
    for idx, scenario in enumerate(scenarios_payload):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario {idx} must be an object")

        scenario_type = scenario.get("type")
        if not scenario_type:
            raise ValueError(f"Scenario {idx} is missing type")

        scenario_enum = OmniScenario.parse(scenario_type)
        scenario_params: dict[str, Any] = dict(scenario)
        scenario_params["type"] = scenario_type

        if scenario_enum == OmniScenario.SBSmap:
            file_key = f"scenarios[{idx}][sbs_file]"
            upload = _extract_upload(form, file_key)
            if upload and upload.filename:
                try:
                    upload_path = _save_upload(
                        upload,
                        destination_dir=limbo_dir / f"{idx:02d}",
                        allowed_extensions=allowed_extensions,
                        max_bytes=SBS_MAX_BYTES,
                    )
                except ValueError as exc:
                    raise ValueError(f"Invalid SBS file for scenario {idx}: {exc}") from exc
                scenario_params["sbs_file_path"] = str(upload_path)
            elif scenario_params.get("sbs_file_path"):
                scenario_params["sbs_file_path"] = str(scenario_params["sbs_file_path"])
            else:
                raise ValueError(f"Missing SBS file for scenario {idx}")

            scenario_params.pop("sbs_file", None)

        parsed_inputs.append((scenario_enum, scenario_params))

    return parsed_inputs


def _prepare_omni_contrasts(
    payload: dict[str, Any],
    raw_json: Any,
    form: FormData,
    *,
    runid: str,
    config: str,
    wd: str,
) -> dict[str, Any]:
    selection_mode = _normalize_contrast_selection_mode(payload.get("omni_contrast_selection_mode"))
    contrast_pairs = _coerce_contrast_pairs(payload, raw_json)
    control_scenario = payload.get("omni_control_scenario")
    contrast_scenario = payload.get("omni_contrast_scenario")
    hillslope_groups = payload.get("omni_contrast_hillslope_groups")

    if selection_mode == "cumulative":
        if not control_scenario:
            raise ValueError("Missing control scenario")
        if not contrast_scenario:
            raise ValueError("Missing contrast scenario")
    if selection_mode == "user_defined_areas":
        if not contrast_pairs:
            raise ValueError("contrast_pairs is required for user-defined contrasts")
    if selection_mode == "user_defined_hillslope_groups":
        if not contrast_pairs:
            raise ValueError("contrast_pairs is required for user-defined hillslope groups")
        if hillslope_groups is None:
            raise ValueError(
                "omni_contrast_hillslope_groups is required for user-defined hillslope groups"
            )
        if isinstance(hillslope_groups, str) and not hillslope_groups.strip():
            raise ValueError(
                "omni_contrast_hillslope_groups is required for user-defined hillslope groups"
            )
        if isinstance(hillslope_groups, (list, tuple)) and not hillslope_groups:
            raise ValueError(
                "omni_contrast_hillslope_groups is required for user-defined hillslope groups"
            )
    if selection_mode == "stream_order":
        if not contrast_pairs:
            raise ValueError("contrast_pairs is required for stream-order contrasts")
        watershed = Watershed.getInstance(wd)
        if not watershed.delineation_backend_is_wbt:
            raise ValueError("Stream-order pruning requires the WBT delineation backend.")

    objective_parameter = payload.get("omni_contrast_objective_parameter")
    threshold_fraction = None
    hillslope_limit = None
    hill_min_slope = None
    hill_max_slope = None
    burn_severities = None
    topaz_ids = None
    order_reduction_passes = None

    if selection_mode == "cumulative":
        if not objective_parameter:
            objective_parameter = "Runoff_mm"
        threshold_fraction = _coerce_optional_float(
            payload.get("omni_contrast_cumulative_obj_param_threshold_fraction"),
            "omni_contrast_cumulative_obj_param_threshold_fraction",
        )
        hillslope_limit = _coerce_optional_int(
            payload.get("omni_contrast_hillslope_limit"),
            "omni_contrast_hillslope_limit",
        )
        hill_min_slope = _coerce_optional_float(
            payload.get("omni_contrast_hill_min_slope"),
            "omni_contrast_hill_min_slope",
        )
        hill_max_slope = _coerce_optional_float(
            payload.get("omni_contrast_hill_max_slope"),
            "omni_contrast_hill_max_slope",
        )
        burn_severities = _coerce_optional_int_list(
            payload.get("omni_contrast_select_burn_severities"),
            "omni_contrast_select_burn_severities",
        )
        topaz_ids = _coerce_optional_int_list(
            payload.get("omni_contrast_select_topaz_ids"),
            "omni_contrast_select_topaz_ids",
        )
    elif selection_mode == "stream_order":
        order_reduction_passes = _coerce_optional_int(
            payload.get("order_reduction_passes"),
            "order_reduction_passes",
        )
        if order_reduction_passes is None or order_reduction_passes == 0:
            order_reduction_passes = 1
        if order_reduction_passes < 0:
            raise ValueError("order_reduction_passes must be >= 1")

    geojson_name_key = payload.get("omni_contrast_geojson_name_key")
    geojson_path = payload.get("omni_contrast_geojson_path")
    upload = _extract_upload(form, "omni_contrast_geojson")
    if upload and upload.filename:
        allowed_extensions = _normalize_extensions(GEOJSON_ALLOWED_EXTENSIONS)
        uploads_dir = Path(wd) / "_pups" / "omni" / "contrasts" / "_uploads" / uuid4().hex
        try:
            geojson_path = str(
                _save_upload(
                    upload,
                    destination_dir=uploads_dir,
                    allowed_extensions=allowed_extensions,
                    max_bytes=GEOJSON_MAX_BYTES,
                )
            )
        except ValueError as exc:
            raise ValueError(f"Invalid GeoJSON upload: {exc}") from exc
    if selection_mode == "user_defined_areas" and not geojson_path:
        raise ValueError("GeoJSON upload or path is required for user-defined contrasts.")

    output_options: dict[str, Any] = {}
    for key in (
        "omni_contrast_output_chan_out",
        "omni_contrast_output_tcr_out",
        "omni_contrast_output_chnwb",
        "omni_contrast_output_soil_pw0",
        "omni_contrast_output_plot_pw0",
        "omni_contrast_output_ebe_pw0",
    ):
        if key in payload:
            output_options[key] = _coerce_optional_bool(payload.get(key), key)

    return {
        "omni_contrast_selection_mode": selection_mode,
        "omni_control_scenario": control_scenario,
        "omni_contrast_scenario": contrast_scenario,
        "omni_contrast_pairs": contrast_pairs,
        "omni_contrast_hillslope_groups": hillslope_groups,
        "omni_contrast_objective_parameter": objective_parameter,
        "omni_contrast_cumulative_obj_param_threshold_fraction": threshold_fraction,
        "omni_contrast_hillslope_limit": hillslope_limit,
        "omni_contrast_hill_min_slope": hill_min_slope,
        "omni_contrast_hill_max_slope": hill_max_slope,
        "omni_contrast_select_burn_severities": burn_severities,
        "omni_contrast_select_topaz_ids": topaz_ids,
        "omni_contrast_geojson_name_key": geojson_name_key,
        "omni_contrast_geojson_path": geojson_path,
        "order_reduction_passes": order_reduction_passes,
        **output_options,
    }


async def _run_omni(
    runid: str,
    config: str,
    request: Request,
) -> JSONResponse:
    wd = get_wd(runid)
    _preflight_omni_roots(wd)
    omni = Omni.getInstance(wd)

    payload = await parse_request_payload(request)
    try:
        raw_json = await request.json()
    except (ValueError, UnicodeDecodeError):
        raw_json = None
    form = await request.form()

    is_batch_run = getattr(omni, "run_group", "") == "batch" or _is_base_project_context(
        runid,
        config,
    )
    has_scenarios_payload = (
        (isinstance(raw_json, dict) and raw_json.get("scenarios") is not None)
        or payload.get("scenarios") is not None
        or isinstance(raw_json, list)
    )
    if is_batch_run and not has_scenarios_payload:
        return JSONResponse({"message": "Set omni inputs for batch processing"})

    try:
        parsed_inputs = _prepare_omni_scenarios(
            payload,
            raw_json,
            form,
            runid=runid,
            config=config,
            wd=wd,
        )
        omni.parse_scenarios(parsed_inputs)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        # API boundary: translate unexpected parse failures into canonical error payload.
        logger.exception("rq-engine run-omni scenario parse failed", extra={"runid": runid, "config": config})
        return error_response_with_traceback(f"Error parsing omni inputs: {exc}")

    if is_batch_run:
        return JSONResponse({"message": "Set omni inputs for batch processing"})

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(run_omni_scenarios_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("run_omni_rq", job.id)
    except Exception:
        logger.exception("rq-engine run-omni enqueue failed")
        return error_response_with_traceback("Error Handling Request")

    status_url = f"/rq-engine/api/jobstatus/{job.id}"
    return JSONResponse(
        {"job_id": job.id, "message": "Job enqueued.", "status_url": status_url},
        status_code=202,
    )


async def _run_omni_contrasts(
    runid: str,
    config: str,
    request: Request,
) -> JSONResponse:
    wd = get_wd(runid)
    _preflight_omni_roots(wd)
    omni = Omni.getInstance(wd)

    payload = await parse_request_payload(request)
    try:
        raw_json = await request.json()
    except (ValueError, UnicodeDecodeError):
        raw_json = None
    form = await request.form()

    try:
        parsed_inputs = _prepare_omni_contrasts(
            payload,
            raw_json,
            form,
            runid=runid,
            config=config,
            wd=wd,
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        # API boundary: translate unexpected parse failures into canonical error payload.
        logger.exception(
            "rq-engine run-omni-contrasts input parse failed",
            extra={"runid": runid, "config": config},
        )
        return error_response_with_traceback(f"Error parsing omni contrast inputs: {exc}")

    selection_mode = parsed_inputs.get("omni_contrast_selection_mode") or CONTRAST_SELECTION_MODE_DEFAULT
    if selection_mode not in {
        "cumulative",
        "user_defined_areas",
        "user_defined_hillslope_groups",
        "stream_order",
    }:
        return error_response(
            f'Contrast selection mode "{selection_mode}" is not implemented yet.',
            status_code=400,
        )

    try:
        omni.parse_inputs(parsed_inputs)
        if getattr(omni, "run_group", "") == "batch" or _is_base_project_context(
            runid,
            config,
        ):
            return JSONResponse({"message": "Set omni inputs for batch processing"})
        if selection_mode == "cumulative":
            threshold_fraction = parsed_inputs.get("omni_contrast_cumulative_obj_param_threshold_fraction")
            if threshold_fraction is None:
                threshold_fraction = 0.8
            objective_parameter = parsed_inputs.get("omni_contrast_objective_parameter") or "Runoff_mm"
            hillslope_limit = parsed_inputs.get("omni_contrast_hillslope_limit")
            hill_min_slope = parsed_inputs.get("omni_contrast_hill_min_slope")
            hill_max_slope = parsed_inputs.get("omni_contrast_hill_max_slope")
            burn_severities = parsed_inputs.get("omni_contrast_select_burn_severities")
            topaz_ids = parsed_inputs.get("omni_contrast_select_topaz_ids")
        else:
            threshold_fraction = getattr(
                omni, "contrast_cumulative_obj_param_threshold_fraction", None
            )
            if threshold_fraction is None:
                threshold_fraction = 0.8
            objective_parameter = getattr(omni, "contrast_object_param", None) or "Runoff_mm"
            hillslope_limit = getattr(omni, "contrast_hillslope_limit", None)
            hill_min_slope = getattr(omni, "contrast_hill_min_slope", None)
            hill_max_slope = getattr(omni, "contrast_hill_max_slope", None)
            burn_severities = getattr(omni, "contrast_select_burn_severities", None)
            topaz_ids = getattr(omni, "contrast_select_topaz_ids", None)
        contrast_pairs = parsed_inputs.get("omni_contrast_pairs")
        if selection_mode in {"user_defined_areas", "user_defined_hillslope_groups", "stream_order"}:
            control_def = None
            contrast_def = None
        else:
            control_def = {"type": parsed_inputs.get("omni_control_scenario")}
            contrast_def = {"type": parsed_inputs.get("omni_contrast_scenario")}
        omni.build_contrasts(
            control_scenario_def=control_def,
            contrast_scenario_def=contrast_def,
            obj_param=objective_parameter,
            contrast_cumulative_obj_param_threshold_fraction=threshold_fraction,
            contrast_hillslope_limit=hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=burn_severities,
            select_topaz_ids=topaz_ids,
            contrast_pairs=contrast_pairs,
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        # API boundary: translate unexpected build failures into canonical error payload.
        logger.exception("rq-engine run-omni-contrasts build failed", extra={"runid": runid, "config": config})
        return error_response_with_traceback(f"Error building omni contrasts: {exc}")

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_contrasts)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(run_omni_contrasts_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("run_omni_contrasts_rq", job.id)
    except Exception:
        logger.exception("rq-engine run-omni-contrasts enqueue failed")
        return error_response_with_traceback("Error Handling Request")

    status_url = f"/rq-engine/api/jobstatus/{job.id}"
    return JSONResponse(
        {"job_id": job.id, "message": "Job enqueued.", "status_url": status_url},
        status_code=202,
    )


async def _dry_run_omni_contrasts(
    runid: str,
    config: str,
    request: Request,
) -> JSONResponse:
    wd = get_wd(runid)
    _preflight_omni_roots(wd)
    omni = Omni.getInstance(wd)

    payload = await parse_request_payload(request)
    try:
        raw_json = await request.json()
    except (ValueError, UnicodeDecodeError):
        raw_json = None
    form = await request.form()

    try:
        parsed_inputs = _prepare_omni_contrasts(
            payload,
            raw_json,
            form,
            runid=runid,
            config=config,
            wd=wd,
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        # API boundary: translate unexpected parse failures into canonical error payload.
        logger.exception("rq-engine dry-run-omni-contrasts input parse failed", extra={"runid": runid, "config": config})
        return error_response_with_traceback(f"Error parsing omni contrast inputs: {exc}")

    selection_mode = parsed_inputs.get("omni_contrast_selection_mode") or CONTRAST_SELECTION_MODE_DEFAULT
    if selection_mode not in {
        "cumulative",
        "user_defined_areas",
        "user_defined_hillslope_groups",
        "stream_order",
    }:
        return error_response(
            f'Contrast selection mode "{selection_mode}" is not implemented yet.',
            status_code=400,
        )

    try:
        omni.parse_inputs(parsed_inputs)
        if selection_mode == "cumulative":
            threshold_fraction = parsed_inputs.get("omni_contrast_cumulative_obj_param_threshold_fraction")
            if threshold_fraction is None:
                threshold_fraction = 0.8
            objective_parameter = parsed_inputs.get("omni_contrast_objective_parameter") or "Runoff_mm"
            hillslope_limit = parsed_inputs.get("omni_contrast_hillslope_limit")
            hill_min_slope = parsed_inputs.get("omni_contrast_hill_min_slope")
            hill_max_slope = parsed_inputs.get("omni_contrast_hill_max_slope")
            burn_severities = parsed_inputs.get("omni_contrast_select_burn_severities")
            topaz_ids = parsed_inputs.get("omni_contrast_select_topaz_ids")
        else:
            threshold_fraction = getattr(
                omni, "contrast_cumulative_obj_param_threshold_fraction", None
            )
            if threshold_fraction is None:
                threshold_fraction = 0.8
            objective_parameter = getattr(omni, "contrast_object_param", None) or "Runoff_mm"
            hillslope_limit = getattr(omni, "contrast_hillslope_limit", None)
            hill_min_slope = getattr(omni, "contrast_hill_min_slope", None)
            hill_max_slope = getattr(omni, "contrast_hill_max_slope", None)
            burn_severities = getattr(omni, "contrast_select_burn_severities", None)
            topaz_ids = getattr(omni, "contrast_select_topaz_ids", None)
        contrast_pairs = parsed_inputs.get("omni_contrast_pairs")
        if selection_mode in {"user_defined_areas", "user_defined_hillslope_groups", "stream_order"}:
            control_def = None
            contrast_def = None
        else:
            control_def = {"type": parsed_inputs.get("omni_control_scenario")}
            contrast_def = {"type": parsed_inputs.get("omni_contrast_scenario")}
        report = omni.build_contrasts_dry_run_report(
            control_scenario_def=control_def,
            contrast_scenario_def=contrast_def,
            obj_param=objective_parameter,
            contrast_cumulative_obj_param_threshold_fraction=threshold_fraction,
            contrast_hillslope_limit=hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=burn_severities,
            select_topaz_ids=topaz_ids,
            contrast_pairs=contrast_pairs,
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        # API boundary: translate unexpected build failures into canonical error payload.
        logger.exception(
            "rq-engine dry-run-omni-contrasts report build failed",
            extra={"runid": runid, "config": config},
        )
        return error_response_with_traceback(f"Error building omni contrast dry-run: {exc}")

    report = dict(report)
    report["runid"] = runid
    report["config"] = config

    return JSONResponse(
        {
            "message": "Dry run complete.",
            "result": report,
        }
    )


async def _delete_omni_contrasts(runid: str, config: str) -> JSONResponse:
    wd = get_wd(runid)
    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_contrasts)
    except FileNotFoundError:
        prep = None

    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(delete_omni_contrasts_rq, (runid,), timeout=RQ_TIMEOUT)
            if prep is not None:
                prep.set_rq_job_id("delete_omni_contrasts_rq", job.id)
    except Exception as exc:
        logger.exception("rq-engine delete-omni-contrasts enqueue failed")
        return error_response_with_traceback(f"Error deleting omni contrasts: {exc}")

    return JSONResponse(
        {
            "message": "Delete contrasts job submitted.",
            "result": {"job_id": job.id, "queued": True},
        }
    )


@router.post(
    "/runs/{runid}/{config}/run-omni",
    summary="Run OMNI scenarios",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates OMNI scenario payload/upload inputs, mutates OMNI state, and, outside batch mode, "
        "asynchronously enqueues OMNI runs."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_omni"),
    responses=agent_route_responses(
        success_code=202,
        success_description="OMNI inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            200: "OMNI batch/_base inputs accepted; no enqueue and message-only payload returned.",
            400: "OMNI scenario input validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_omni(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-omni auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        return await _run_omni(runid, config, request)
    except NoDirError as exc:
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)


@router.post(
    "/runs/{runid}/{config}/run-omni-contrasts",
    summary="Run OMNI contrasts",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates OMNI contrast inputs, mutates contrast configuration, and, outside batch mode, "
        "asynchronously enqueues contrast processing."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_omni_contrasts"),
    responses=agent_route_responses(
        success_code=202,
        success_description=(
            "OMNI contrast inputs accepted; returns batch update message or enqueued `job_id`."
        ),
        extra={
            200: "OMNI contrast batch/_base inputs accepted; no enqueue and message-only payload returned.",
            400: "OMNI contrast validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_omni_contrasts(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-omni-contrasts auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        return await _run_omni_contrasts(runid, config, request)
    except NoDirError as exc:
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)


@router.post(
    "/runs/{runid}/{config}/run-omni-contrasts-dry-run",
    summary="Dry-run OMNI contrasts",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates OMNI contrast inputs and synchronously returns a dry-run contrast report; no queue enqueue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_omni_contrasts_dry_run"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Dry-run contrast report returned.",
        extra={
            400: "OMNI contrast validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_omni_contrasts_dry_run(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-omni-contrasts-dry-run auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        return await _dry_run_omni_contrasts(runid, config, request)
    except NoDirError as exc:
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)


@router.post(
    "/runs/{runid}/{config}/delete-omni-contrasts",
    summary="Delete OMNI contrasts",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Asynchronously enqueues OMNI contrast deletion and returns the queued job metadata."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("delete_omni_contrasts"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Delete-contrasts job accepted and returned in `result.job_id`.",
    ),
)
async def delete_omni_contrasts(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine delete-omni-contrasts auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _delete_omni_contrasts(runid, config)


__all__ = ["router"]
