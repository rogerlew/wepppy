from __future__ import annotations

import logging
import math
import os
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Callable, Sequence
from uuid import uuid4

import redis
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Dependency, Job
from starlette.datastructures import UploadFile

from wepp_runner.wepp_runner import get_linux_wepp_bin_opts
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.shape_converter.archive_validation import (
    ArchiveLimits,
    read_upload_bytes_with_limit,
    validate_and_extract_zip_archive,
)
from wepppy.microservices.shape_converter.errors import ShapeConverterError
from wepppy.nodb.mods.ag_fields import (
    AgFields,
    AgFieldsNoDbLockedException,
    RotationLookupValidationError,
)
from wepppy.nodb.mods.ag_fields.routing_schemes import (
    AgFieldsRoutingScheme,
    expand_routing_scheme_request,
    validate_watershed_max_workers,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.ag_fields_rq import (
    AGFIELDS_BUILD_SUBFIELDS_JOB_KEY,
    AGFIELDS_PLANTDB_JOB_KEY,
    AGFIELDS_RUN_WATERSHED_JOB_KEY,
    AGFIELDS_RUN_WATERSHED_JOB_KEYS,
    AGFIELDS_RUN_WEPP_JOB_KEY,
    build_ag_fields_subfields_rq,
    process_ag_fields_plant_db_rq,
    run_ag_fields_watershed_rq,
    run_ag_fields_wepp_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response
from .upload_helpers import UploadError, save_upload_file


logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
RQ_READ_SCOPES = ["rq:status"]
AGFIELDS_SUBMIT_LOCK_TTL_SECONDS = 30
ACTIVE_RQ_JOB_STATUSES = {"queued", "started", "deferred", "scheduled"}
TERMINAL_RQ_JOB_STATUSES = {
    "canceled",
    "cancelled",
    "failed",
    "finished",
    "missing",
    "stopped",
}
AGFIELDS_CURRENT_WATERSHED_JOB_KEYS = tuple(AGFIELDS_RUN_WATERSHED_JOB_KEYS.values())

AGFIELDS_BOUNDARY_ALLOWED_EXTENSIONS = ("geojson", "json")
AGFIELDS_BOUNDARY_MAX_BYTES = 10 * 1024 * 1024
AGFIELDS_PLANT_DB_MAX_BYTES = 100 * 1024 * 1024
AGFIELDS_PLANT_DB_LIMITS = ArchiveLimits(
    max_compressed_bytes=AGFIELDS_PLANT_DB_MAX_BYTES,
    max_uncompressed_bytes=600 * 1024 * 1024,
    max_member_count=200,
)


class AgFieldsJobConflict(RuntimeError):
    pass


def _authorize(request: Request, runid: str, scopes: Sequence[str]) -> Response | None:
    try:
        claims = require_jwt(request, required_scopes=list(scopes))
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: authentication boundary contract
        logger.exception("rq-engine AgFields authorization failed", extra={"runid": runid})
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")
    return None


def _extract_upload(form: Any, key: str) -> UploadFile | None:
    upload = form.get(key)
    return upload if isinstance(upload, UploadFile) else None


def _plant_archive_member_policy(member: zipfile.ZipInfo, path: PurePosixPath) -> None:
    if member.is_dir():
        return
    if path.suffix.lower() != ".man":
        raise ShapeConverterError(
            code="invalid_archive",
            message="Plant database archive contains an unsupported file type.",
            details=f"Entry '{member.filename}' is not a .man file.",
        )


def _upload_error_response(exc: UploadError) -> JSONResponse:
    message = str(exc)
    status = getattr(exc, "status_code", None) or (413 if "maximum allowed size" in message.lower() else 400)
    return error_response(message, status_code=status)


def _invalidate_ag_fields_preflight(wd: str) -> None:
    RedisPrep.getInstance(wd).remove_timestamp(TaskEnum.run_ag_fields)


def _enqueue_job(
    wd: str,
    job_key: str,
    func: Callable[..., Any],
    args: tuple[Any, ...],
) -> JSONResponse:
    runid = str(args[0])
    submit_owner = f"{job_key}:{uuid4().hex}"
    submit_lock_key = f"agfields:submit_lock:{runid}"
    prep = RedisPrep.getInstance(wd)
    with redis.Redis(
        **redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    ) as lock_conn:
        if not lock_conn.set(
            submit_lock_key,
            submit_owner,
            nx=True,
            ex=AGFIELDS_SUBMIT_LOCK_TTL_SECONDS,
        ):
            raise AgFieldsJobConflict("Another AgFields submission is in progress for this run.")
        try:
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
                active = _find_active_job(prep, redis_conn)
                if active is not None:
                    raise AgFieldsJobConflict(
                        "An AgFields job is already active for this run "
                        f"(key={active['key']}, job_id={active['job_id']}, status={active['status']})."
                    )
                if job_key != AGFIELDS_RUN_WATERSHED_JOB_KEY:
                    prep.remove_timestamp(TaskEnum.run_ag_fields)
                queue = Queue(connection=redis_conn)
                job = queue.enqueue_call(func, args, timeout=RQ_TIMEOUT)
                prep.set_rq_job_id(job_key, job.id)
        finally:
            try:
                if lock_conn.get(submit_lock_key) == submit_owner:
                    lock_conn.delete(submit_lock_key)
            except redis.RedisError as exc:
                logger.warning(
                    "AgFields submit lock release failed for %s: %s",
                    runid,
                    exc,
                    extra={"runid": runid, "job_key": job_key},
                )
    return JSONResponse({"job_id": job.id}, status_code=202)


def _enqueue_watershed_jobs(
    wd: str,
    runid: str,
    schemes: tuple[AgFieldsRoutingScheme, ...],
    max_workers: int | None,
) -> JSONResponse:
    """Enqueue one or three independently tracked watershed jobs in serial order."""
    submit_owner = f"agfields_run_watershed:{uuid4().hex}"
    submit_lock_key = f"agfields:submit_lock:{runid}"
    prep = RedisPrep.getInstance(wd)
    ag_fields = AgFields.getInstance(wd)
    job_ids: dict[str, str] = {}
    with redis.Redis(
        **redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    ) as lock_conn:
        if not lock_conn.set(
            submit_lock_key,
            submit_owner,
            nx=True,
            ex=AGFIELDS_SUBMIT_LOCK_TTL_SECONDS,
        ):
            raise AgFieldsJobConflict("Another AgFields submission is in progress for this run.")
        try:
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
                active = _find_active_job(prep, redis_conn)
                if active is not None:
                    raise AgFieldsJobConflict(
                        "An AgFields job is already active for this run "
                        f"(key={active['key']}, job_id={active['job_id']}, status={active['status']})."
                    )
                states = _reconcile_interrupted_watershed_jobs(
                    ag_fields,
                    redis_conn,
                )
                running_schemes = [
                    scheme
                    for scheme, state in states.items()
                    if str(state["status"]).startswith("running")
                ]
                if running_schemes:
                    raise AgFieldsJobConflict(
                        "An AgFields watershed integration is already running for this run "
                        f"(schemes={','.join(running_schemes)})."
                    )
                planned_job_ids = {
                    scheme.value: str(uuid4())
                    for scheme in schemes
                }
                for scheme in schemes:
                    job_id = planned_job_ids[scheme.value]
                    job_key = AGFIELDS_RUN_WATERSHED_JOB_KEYS[scheme.value]
                    prep.set_rq_job_id(job_key, job_id)
                    if scheme is AgFieldsRoutingScheme.CONCEPT_2:
                        prep.set_rq_job_id(AGFIELDS_RUN_WATERSHED_JOB_KEY, job_id)
                ag_fields.set_watershed_integration_job_ids(planned_job_ids)

                queue = Queue(connection=redis_conn)
                previous_job_id: str | None = None
                for scheme in schemes:
                    dependency = (
                        Dependency(jobs=[previous_job_id], allow_failure=True)
                        if previous_job_id is not None
                        else None
                    )
                    job_id = planned_job_ids[scheme.value]
                    queue.enqueue_call(
                        run_ag_fields_watershed_rq,
                        args=(runid, max_workers, scheme.value),
                        timeout=RQ_TIMEOUT,
                        depends_on=dependency,
                        job_id=job_id,
                    )
                    job_ids[scheme.value] = job_id
                    previous_job_id = job_id
        finally:
            try:
                if lock_conn.get(submit_lock_key) == submit_owner:
                    lock_conn.delete(submit_lock_key)
            except redis.RedisError as exc:
                logger.warning(
                    "AgFields watershed submit lock release failed for %s: %s",
                    runid,
                    exc,
                    extra={"runid": runid},
                )
    first_job_id = job_ids[schemes[0].value]
    return JSONResponse(
        {"job_id": first_job_id, "job_ids": job_ids},
        status_code=202,
    )


def _mapping_summary(ag_fields: AgFields) -> dict[str, Any]:
    results = ag_fields.validate_rotation_lookup()
    used = [item for item in results if item.get("used")]
    mapped_count = sum(item.get("status") == "ok" for item in used)
    return {
        "crop_count": len(used),
        "mapped_count": mapped_count,
        "complete": bool(used) and mapped_count == len(used),
        "results": results,
    }


def _find_active_job(prep: RedisPrep, redis_conn: redis.Redis) -> dict[str, str] | None:
    for key in (
        AGFIELDS_BUILD_SUBFIELDS_JOB_KEY,
        AGFIELDS_PLANTDB_JOB_KEY,
        AGFIELDS_RUN_WEPP_JOB_KEY,
        *AGFIELDS_CURRENT_WATERSHED_JOB_KEYS,
        AGFIELDS_RUN_WATERSHED_JOB_KEY,
    ):
        job_id = prep.get_rq_job_id(key)
        if job_id is None:
            continue
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        status = str(job.get_status(refresh=False) or "").lower()
        if status in ACTIVE_RQ_JOB_STATUSES:
            return {"key": key, "job_id": job_id, "status": status}
    return None


def _reconcile_interrupted_watershed_jobs(
    ag_fields: AgFields,
    redis_conn: redis.Redis,
) -> dict[str, dict[str, Any]]:
    """Persist failure when a running scheme's matching RQ job is terminal."""
    states = ag_fields.get_watershed_integration_states()
    for scheme, state in states.items():
        persisted_status = str(state["status"])
        if not (
            persisted_status == "running"
            or persisted_status.startswith("running:")
        ):
            continue
        job_id = str(state.get("job_id") or "").strip()
        if not job_id:
            continue
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            rq_status = "missing"
        else:
            rq_status = str(job.get_status(refresh=False) or "").lower()
        if rq_status not in TERMINAL_RQ_JOB_STATUSES:
            continue
        if ag_fields.mark_watershed_integration_interrupted(
            scheme,
            job_id,
            rq_status,
        ):
            logger.warning(
                "Reconciled interrupted AgFields watershed job",
                extra={
                    "runid": Path(ag_fields.wd).name,
                    "scheme": scheme,
                    "job_id": job_id,
                    "rq_status": rq_status,
                },
            )
    return ag_fields.get_watershed_integration_states()


def _active_job_conflict_response(wd: str) -> JSONResponse | None:
    prep = RedisPrep.tryGetInstance(wd)
    ag_fields = AgFields.getInstance(wd)
    if prep is not None:
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            active = _find_active_job(prep, redis_conn)
            states = (
                ag_fields.get_watershed_integration_states()
                if active is not None
                else _reconcile_interrupted_watershed_jobs(ag_fields, redis_conn)
            )
        if active is not None:
            return error_response(
                "An AgFields job is active; wait for it to finish before changing AgFields inputs.",
                status_code=409,
                code="agfields_job_active",
                details=(
                    f"key={active['key']}, job_id={active['job_id']}, status={active['status']}"
                ),
            )
    else:
        states = ag_fields.get_watershed_integration_states()
    running_schemes = [
        scheme
        for scheme, state in states.items()
        if str(state["status"]).startswith("running")
    ]
    if running_schemes:
        return error_response(
            "An AgFields watershed integration is running; wait for it to finish "
            "before changing AgFields inputs.",
            status_code=409,
            code="agfields_job_active",
            details="schemes=" + ",".join(running_schemes),
        )
    return None


def _job_ids(prep: RedisPrep | None) -> tuple[dict[str, str | None], dict[str, str | None]]:
    keys = (
        AGFIELDS_BUILD_SUBFIELDS_JOB_KEY,
        AGFIELDS_PLANTDB_JOB_KEY,
        AGFIELDS_RUN_WEPP_JOB_KEY,
        *AGFIELDS_CURRENT_WATERSHED_JOB_KEYS,
        AGFIELDS_RUN_WATERSHED_JOB_KEY,
    )
    job_ids = {key: prep.get_rq_job_id(key) if prep is not None else None for key in keys}
    active_job_ids: dict[str, str | None] = {key: None for key in keys}
    if prep is None:
        return job_ids, active_job_ids

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        for key, job_id in job_ids.items():
            if job_id is None:
                continue
            try:
                job = Job.fetch(job_id, connection=redis_conn)
            except NoSuchJobError:
                continue
            if str(job.get_status(refresh=False) or "").lower() in ACTIVE_RQ_JOB_STATUSES:
                active_job_ids[key] = job_id
    return job_ids, active_job_ids


def _state_snapshot(wd: str) -> dict[str, Any]:
    ag_fields = AgFields.getInstance(wd)
    watershed_integrations = ag_fields.get_watershed_integration_states()
    if any(
        (
            str(state["status"]) == "running"
            or str(state["status"]).startswith("running:")
        )
        and bool(state.get("job_id"))
        for state in watershed_integrations.values()
    ):
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            watershed_integrations = _reconcile_interrupted_watershed_jobs(
                ag_fields,
                redis_conn,
            )
    readiness = ag_fields.get_readiness()
    staleness = ag_fields.get_staleness()
    mapping = _mapping_summary(ag_fields)
    inventory = ag_fields.get_plant_file_inventory()
    prep = RedisPrep.tryGetInstance(wd)
    job_ids, active_job_ids = _job_ids(prep)
    runs_dir = Path(ag_fields.ag_field_wepp_runs_dir)
    output_dir = Path(ag_fields.ag_field_wepp_output_dir)
    run_count = len(list(runs_dir.glob("p*.run")))
    output_count = len(list(output_dir.iterdir())) if output_dir.is_dir() else 0
    schema_complete = bool(
        ag_fields.geojson_is_valid
        and ag_fields.field_id_key
        and ag_fields.rotation_accessor
    )
    overlay_exists = Path(ag_fields.sub_fields_wgs_geojson).is_file()
    return {
        "boundary": {
            "filename": (
                ag_fields.field_boundaries_source_filename
                or ag_fields.field_boundaries_geojson
            ),
            "geojson_is_valid": ag_fields.geojson_is_valid,
            "geojson_hash": ag_fields.geojson_hash,
            "geojson_timestamp": ag_fields.geojson_timestamp,
            "field_columns": ag_fields.field_columns,
            "field_n": ag_fields.field_n,
        },
        "schema": {
            "field_id_key": ag_fields.field_id_key,
            "rotation_accessor": ag_fields.rotation_accessor,
            "complete": schema_complete,
        },
        "subfields": {
            "field_n": ag_fields.field_n,
            "sub_field_n": ag_fields.sub_field_n,
            "sub_field_fp_n": ag_fields.sub_field_fp_n,
            "overlay_exists": overlay_exists,
            "complete": overlay_exists and ag_fields.sub_field_n > 0 and not staleness["subfields"],
        },
        "mapping": mapping,
        "plant_files": {
            "valid_count": len(inventory["valid_files"]),
            "invalid_count": len(inventory["invalid_files"]),
        },
        "wepp": {
            "run_count": run_count,
            "output_count": output_count,
            "complete": run_count > 0 and not staleness["wepp_runs"],
            "wepp_bin": ag_fields.wepp_bin,
        },
        "watershed_integration": watershed_integrations["concept_2"],
        "watershed_integrations": watershed_integrations,
        "staleness": staleness,
        "readiness": readiness,
        "job_ids": job_ids,
        "active_job_ids": active_job_ids,
    }


@router.post(
    "/runs/{runid}/{config}/agfields/boundaries",
    summary="Upload AgFields boundaries",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates and persists field-boundary GeoJSON synchronously; no queue."
    ),
    operation_id=rq_operation_id("agfields_upload_boundaries"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Field boundaries validated and persisted.",
        extra={
            400: "Invalid upload or boundary geometry. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def upload_boundaries(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        ag_fields = AgFields.getInstance(wd)
        form = await request.form()
        upload = _extract_upload(form, "field_boundaries")
        if upload is None or not upload.filename:
            return error_response("field_boundaries upload is required", status_code=400, code="missing_upload_file")
        validation_result: dict[str, Any] = {}

        def _validate_boundary(path: Path) -> None:
            try:
                validation_result.update(
                    ag_fields.validate_field_boundary_geojson(
                        path,
                        source_filename=upload.filename,
                    )
                )
            except Exception as exc:  # broad-except: untrusted geospatial parser boundary
                logger.warning(
                    "rq-engine AgFields boundary validation rejected upload",
                    exc_info=True,
                    extra={"runid": runid, "config": config},
                )
                raise UploadError(f"Field boundary validation failed: {str(exc) or exc.__class__.__name__}") from exc

        saved_path = save_upload_file(
            upload,
            allowed_extensions=AGFIELDS_BOUNDARY_ALLOWED_EXTENSIONS,
            dest_dir=Path(ag_fields.ag_fields_dir),
            filename_transform=lambda value: f"field-boundaries-upload{Path(value).suffix.lower()}",
            overwrite=True,
            max_bytes=AGFIELDS_BOUNDARY_MAX_BYTES,
            post_save=_validate_boundary,
        )
        saved_path.unlink(missing_ok=True)
        _invalidate_ag_fields_preflight(wd)
        return JSONResponse(
            {
                "message": "Field boundaries uploaded and validated.",
                "result": {
                    "field_n": ag_fields.field_n,
                    "field_columns": ag_fields.field_columns,
                    "geojson_timestamp": ag_fields.geojson_timestamp,
                    "field_id_duplicates": validation_result.get("field_id_duplicates", []),
                },
            }
        )
    except UploadError as exc:
        return _upload_error_response(exc)
    except (FileNotFoundError, OSError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields boundary upload failed", extra={"runid": runid, "config": config})
        return error_response("Field boundary upload failed", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/schema",
    summary="Confirm AgFields schema",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates and persists field-id and rotation schema synchronously; no queue."
    ),
    operation_id=rq_operation_id("agfields_confirm_schema"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="AgFields schema confirmed.",
        extra={
            400: "Schema validation failed. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def confirm_schema(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        payload = await parse_request_payload(request)
        field_id_key = str(payload.get("field_id_key") or "").strip()
        rotation_accessor = str(payload.get("rotation_accessor") or "").strip()
        if not field_id_key or not rotation_accessor:
            return error_response("field_id_key and rotation_accessor are required", status_code=400)
        ag_fields = AgFields.getInstance(wd)
        ag_fields.confirm_schema(field_id_key, rotation_accessor)
        _invalidate_ag_fields_preflight(wd)
        return JSONResponse(
            {
                "message": "AgFields schema confirmed.",
                "result": {
                    "field_id_key": ag_fields.field_id_key,
                    "rotation_accessor": ag_fields.rotation_accessor,
                    "staleness": ag_fields.get_staleness(),
                },
            }
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields schema confirmation failed", extra={"runid": runid, "config": config})
        return error_response("Schema confirmation failed", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/build-subfields",
    summary="Build AgFields sub-fields",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates readiness and enqueues the AgFields sub-field build."
    ),
    operation_id=rq_operation_id("agfields_build_subfields"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=202,
        success_description="Sub-field build job enqueued.",
        extra={
            400: "Invalid build options. Returns the canonical error payload.",
            409: "Prerequisites are incomplete or a job is active. Returns the canonical error payload.",
        },
    ),
)
async def build_subfields(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        ag_fields = AgFields.getInstance(wd)
        if not (ag_fields.geojson_is_valid and ag_fields.field_id_key and ag_fields.rotation_accessor):
            return error_response("Confirm the field boundary schema before building sub-fields.", status_code=409)
        if not ag_fields.get_readiness()["watershed_abstraction"]:
            return error_response("Build the watershed subcatchments before building sub-fields.", status_code=409)
        payload = await parse_request_payload(request)
        minimum_area = float(payload.get("sub_field_min_area_threshold_m2", 0.0))
        if not math.isfinite(minimum_area) or minimum_area < 0.0:
            raise ValueError("sub_field_min_area_threshold_m2 must be a finite non-negative number.")
        return _enqueue_job(
            wd,
            AGFIELDS_BUILD_SUBFIELDS_JOB_KEY,
            build_ag_fields_subfields_rq,
            (runid, minimum_area),
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except AgFieldsJobConflict as exc:
        return error_response(str(exc), status_code=409, code="agfields_job_active")
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields build enqueue failed", extra={"runid": runid, "config": config})
        return error_response("Could not enqueue sub-field build", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/plant-database",
    summary="Upload AgFields plant database",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates a plant database archive and enqueues its processing."
    ),
    operation_id=rq_operation_id("agfields_upload_plant_database"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=202,
        success_description="Plant database job enqueued.",
        extra={
            400: "Invalid archive or upload. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def upload_plant_database(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        ag_fields = AgFields.getInstance(wd)
        form = await request.form()
        upload = _extract_upload(form, "plant_database")
        if upload is None or not upload.filename:
            return error_response("plant_database upload is required", status_code=400, code="missing_upload_file")
        archive_bytes = await read_upload_bytes_with_limit(
            upload=upload,
            max_bytes=AGFIELDS_PLANT_DB_MAX_BYTES,
        )
        with tempfile.TemporaryDirectory(prefix=".plant-archive-check-") as extraction_dir:
            extracted = validate_and_extract_zip_archive(
                archive_name=upload.filename,
                archive_bytes=archive_bytes,
                extraction_root=Path(extraction_dir),
                limits=AGFIELDS_PLANT_DB_LIMITS,
                member_policy=_plant_archive_member_policy,
                sanitize_metadata_sidecars=False,
            )
            if not any(path.suffix.lower() == ".man" for path in extracted.extracted_files):
                return error_response("Plant database archive contains no .man files.", status_code=400)

        filename = f"plant-db-{uuid4().hex}.zip"
        archive_path = Path(ag_fields.ag_fields_dir) / filename
        archive_path.write_bytes(archive_bytes)
        try:
            return _enqueue_job(
                wd,
                AGFIELDS_PLANTDB_JOB_KEY,
                process_ag_fields_plant_db_rq,
                (runid, filename),
            )
        except Exception:  # broad-except: cleanup staged archive before outer HTTP boundary
            archive_path.unlink(missing_ok=True)
            raise
    except ShapeConverterError as exc:
        return error_response(
            exc.message,
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )
    except AgFieldsJobConflict as exc:
        return error_response(str(exc), status_code=409, code="agfields_job_active")
    except OSError:
        logger.exception("rq-engine AgFields plant database save failed", extra={"runid": runid, "config": config})
        return error_response("Could not save plant database archive", status_code=500)
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields plant database enqueue failed", extra={"runid": runid, "config": config})
        return error_response("Could not enqueue plant database processing", status_code=500)


@router.get(
    "/runs/{runid}/{config}/agfields/plant-files",
    summary="Get AgFields plant files",
    description=(
        "Requires JWT Bearer `rq:status` scope and run access. "
        "Read-only plant-file inventory and validation response; no queue."
    ),
    operation_id=rq_operation_id("agfields_plant_file_inventory"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Plant-file inventory returned.",
    ),
)
async def plant_file_inventory(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_READ_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        return JSONResponse(AgFields.getInstance(get_wd(runid)).get_plant_file_inventory())
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields inventory read failed", extra={"runid": runid, "config": config})
        return error_response("Could not read plant file inventory", status_code=500)


@router.delete(
    "/runs/{runid}/{config}/agfields/plant-files/{filename}",
    summary="Delete an AgFields plant file",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Deletes one run-scoped plant file synchronously; no queue."
    ),
    operation_id=rq_operation_id("agfields_delete_plant_file"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Plant file deleted.",
        extra={
            400: "Invalid plant filename. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def delete_plant_file(runid: str, config: str, filename: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        ag_fields = AgFields.getInstance(wd)
        inventory = ag_fields.delete_plant_file(filename)
        _invalidate_ag_fields_preflight(wd)
        return JSONResponse(
            {
                "message": f"Deleted plant file {filename}.",
                "result": {
                    "inventory": inventory,
                    "mapping_results": ag_fields.validate_rotation_lookup(),
                },
            }
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields plant delete failed", extra={"runid": runid, "config": config})
        return error_response("Could not delete plant file", status_code=500)


@router.get(
    "/runs/{runid}/{config}/agfields/rotation-mapping",
    summary="Get AgFields rotation mapping",
    description=(
        "Requires JWT Bearer `rq:status` scope and run access. "
        "Read-only crop mapping and management-option response; no queue."
    ),
    operation_id=rq_operation_id("agfields_get_rotation_mapping"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Rotation mapping returned.",
    ),
)
async def get_rotation_mapping(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_READ_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        ag_fields = AgFields.getInstance(get_wd(runid))
        results = ag_fields.validate_rotation_lookup()
        return JSONResponse(
            {
                "rows": results,
                "unique_crops": sorted(
                    [item["crop_name"] for item in results if item.get("used")],
                    key=str.casefold,
                ),
                "unused_mappings": [item for item in results if not item.get("used")],
                "plant_files": ag_fields.get_plant_file_inventory(),
                "management_options": ag_fields.get_weppcloud_management_options(),
            }
        )
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields mapping read failed", extra={"runid": runid, "config": config})
        return error_response("Could not read rotation mapping", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/rotation-mapping",
    summary="Save AgFields rotation mapping",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates and persists crop mappings synchronously; no queue."
    ),
    operation_id=rq_operation_id("agfields_save_rotation_mapping"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Rotation mapping saved.",
        extra={
            400: "Mapping validation failed. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def save_rotation_mapping(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        payload = await request.json()
        if not isinstance(payload, dict):
            return error_response("Request body must be a JSON object", status_code=400)
        rows = payload.get("rows")
        if not isinstance(rows, list):
            return error_response("rows must be a JSON array", status_code=400)
        results = AgFields.getInstance(wd).write_rotation_lookup(rows)
        _invalidate_ag_fields_preflight(wd)
        return JSONResponse({"message": "Rotation mapping saved.", "result": {"rows": results}})
    except RotationLookupValidationError as exc:
        errors = [
            {
                "code": "invalid_mapping",
                "message": item["message"],
                "path": f"rows.{item['crop_name']}",
            }
            for item in exc.results
            if item.get("status") == "error"
        ]
        return error_response(
            "Rotation mapping validation failed",
            status_code=400,
            errors=errors,
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields mapping save failed", extra={"runid": runid, "config": config})
        return error_response("Could not save rotation mapping", status_code=500)


@router.get(
    "/runs/{runid}/{config}/agfields/management-options",
    summary="Get AgFields management options",
    description=(
        "Requires JWT Bearer `rq:status` scope and run access. "
        "Read-only WEPPcloud management option response; no queue."
    ),
    operation_id=rq_operation_id("agfields_management_options"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Management options returned.",
    ),
)
async def management_options(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_READ_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        return JSONResponse(
            {"management_options": AgFields.getInstance(get_wd(runid)).get_weppcloud_management_options()}
        )
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields management options failed", extra={"runid": runid, "config": config})
        return error_response("Could not read management options", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/run-wepp",
    summary="Run WEPP for AgFields",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates staged readiness and enqueues AgFields WEPP execution."
    ),
    operation_id=rq_operation_id("agfields_run_wepp"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=202,
        success_description="AgFields WEPP job enqueued.",
        extra={
            400: "Invalid run options. Returns the canonical error payload.",
            409: "Prerequisites are incomplete or a job is active. Returns the canonical error payload.",
        },
    ),
)
async def run_wepp(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        ag_fields = AgFields.getInstance(wd)
        state = _state_snapshot(wd)
        if not state["subfields"]["complete"]:
            return error_response("Build current sub-fields before running WEPP.", status_code=409)
        if not state["mapping"]["complete"]:
            return error_response("Map all crops to valid managements before running WEPP.", status_code=409)
        if not state["readiness"]["parent_wepp"]:
            return error_response("Run the watershed WEPP hillslopes before running AgFields WEPP.", status_code=409)
        payload = await parse_request_payload(request)
        raw_max_workers = payload.get("max_workers")
        max_workers = None if raw_max_workers in (None, "") else int(raw_max_workers)
        if max_workers is not None and max_workers < 1:
            raise ValueError("max_workers must be at least 1 when provided.")
        wepp_bin = str(payload.get("wepp_bin") or ag_fields.wepp_bin or "").strip()
        if wepp_bin not in get_linux_wepp_bin_opts():
            raise ValueError(f"Unknown WEPP executable: {wepp_bin}")
        return _enqueue_job(
            wd,
            AGFIELDS_RUN_WEPP_JOB_KEY,
            run_ag_fields_wepp_rq,
            (runid, max_workers, wepp_bin),
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except AgFieldsJobConflict as exc:
        return error_response(str(exc), status_code=409, code="agfields_job_active")
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields WEPP enqueue failed", extra={"runid": runid, "config": config})
        return error_response("Could not enqueue AgFields WEPP", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/run-watershed",
    summary="Run the integrated AgFields watershed",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Validates current sub-field and parent inputs, then enqueues one routing scheme "
        "or all three schemes serially. Omitted scheme defaults to concept_2."
    ),
    operation_id=rq_operation_id("agfields_run_watershed"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=202,
        success_description="AgFields watershed integration job enqueued.",
        extra={
            400: "Invalid run options. Returns the canonical error payload.",
            409: "Prerequisites are incomplete or a job is active. Returns the canonical error payload.",
        },
    ),
)
async def run_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        state = _state_snapshot(wd)
        if not state["wepp"]["complete"] or state["staleness"]["wepp_runs"]:
            return error_response(
                "Run current AgFields sub-field WEPP simulations before watershed integration.",
                status_code=409,
            )
        if not state["readiness"]["observed_climate"]:
            return error_response(
                "AgFields watershed integration requires a continuous observed climate.",
                status_code=409,
            )
        if not state["readiness"]["parent_wepp"]:
            return error_response(
                "Prepare all parent WEPP hillslope inputs before watershed integration.",
                status_code=409,
            )
        payload = await parse_request_payload(request)
        raw_max_workers = payload.get("max_workers")
        max_workers = validate_watershed_max_workers(
            None if raw_max_workers in (None, "") else raw_max_workers
        )
        schemes = expand_routing_scheme_request(payload.get("scheme"))
        return _enqueue_watershed_jobs(
            wd,
            runid,
            schemes,
            max_workers,
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except AgFieldsJobConflict as exc:
        return error_response(str(exc), status_code=409, code="agfields_job_active")
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception(
            "rq-engine AgFields watershed enqueue failed",
            extra={"runid": runid, "config": config},
        )
        return error_response("Could not enqueue AgFields watershed integration", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/clear-watershed",
    summary="Clear the integrated AgFields watershed",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Clears one fixed current-scheme tree, or all three current trees, and their state. "
        "Omitted scheme defaults to concept_2; legacy unscoped artifacts are preserved."
    ),
    operation_id=rq_operation_id("agfields_clear_watershed"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="AgFields watershed integration artifacts cleared.",
        extra={
            400: "The isolated path contract is invalid. Returns the canonical error payload.",
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def clear_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        payload = await parse_request_payload(request)
        requested_scheme = payload.get("scheme")
        schemes = expand_routing_scheme_request(requested_scheme)
        ag_fields = AgFields.getInstance(wd)
        states = ag_fields.get_watershed_integration_states()
        running = [
            scheme.value
            for scheme in schemes
            if str(states[scheme.value]["status"]).startswith("running")
        ]
        if running:
            return error_response(
                "AgFields watershed integration is running for: " + ", ".join(running),
                status_code=409,
                code="agfields_job_active",
            )
        for scheme in schemes:
            ag_fields.clear_watershed_integration(scheme)
        cleared = [scheme.value for scheme in schemes]
        return JSONResponse(
            {
                "message": "AgFields watershed integration artifacts cleared.",
                "cleared_schemes": cleared,
            }
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc), status_code=400)
    except AgFieldsNoDbLockedException as exc:
        return error_response(str(exc), status_code=409, code="agfields_job_active")
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception(
            "rq-engine AgFields watershed clear failed",
            extra={"runid": runid, "config": config},
        )
        return error_response("Could not clear AgFields watershed integration", status_code=500)


@router.post(
    "/runs/{runid}/{config}/agfields/clear",
    summary="Clear AgFields WEPP artifacts",
    description=(
        "Requires JWT Bearer `rq:enqueue` scope and run access. "
        "Clears regenerable AgFields runs and outputs synchronously; no queue."
    ),
    operation_id=rq_operation_id("agfields_clear_wepp"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="AgFields WEPP artifacts cleared.",
        extra={
            409: "An AgFields job is active. Returns the canonical error payload.",
        },
    ),
)
async def clear_wepp(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_ENQUEUE_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        wd = get_wd(runid)
        conflict = _active_job_conflict_response(wd)
        if conflict is not None:
            return conflict
        AgFields.getInstance(wd).clear_ag_field_wepp_artifacts()
        _invalidate_ag_fields_preflight(wd)
        return JSONResponse({"message": "AgFields WEPP runs and outputs cleared."})
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields clear failed", extra={"runid": runid, "config": config})
        return error_response("Could not clear AgFields WEPP artifacts", status_code=500)


@router.get(
    "/runs/{runid}/{config}/agfields/sub-fields.geojson",
    summary="Get AgFields sub-field overlay",
    description=(
        "Requires JWT Bearer `rq:status` scope and run access. "
        "Read-only current WGS84 sub-field GeoJSON response; no queue."
    ),
    operation_id=rq_operation_id("agfields_subfields_overlay"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="Sub-field GeoJSON returned.",
        extra={
            404: "Sub-field overlay is unavailable. Returns the canonical error payload.",
        },
    ),
)
async def subfields_overlay(runid: str, config: str, request: Request) -> Response:
    auth_error = _authorize(request, runid, RQ_READ_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        path = Path(AgFields.getInstance(get_wd(runid)).sub_fields_wgs_geojson)
        if not path.is_file():
            return error_response("Sub-fields overlay is not available.", status_code=404)
        return FileResponse(path, media_type="application/geo+json", filename="sub-fields.geojson")
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields overlay read failed", extra={"runid": runid, "config": config})
        return error_response("Could not read sub-fields overlay", status_code=500)


@router.get(
    "/runs/{runid}/{config}/agfields/state",
    summary="Get AgFields workflow state",
    description=(
        "Requires JWT Bearer `rq:status` scope and run access. "
        "Read-only staged workflow, readiness, staleness, and job state; no queue."
    ),
    operation_id=rq_operation_id("agfields_state"),
    tags=["rq-engine", "agfields"],
    responses=agent_route_responses(
        success_code=200,
        success_description="AgFields workflow state returned.",
    ),
)
async def state(runid: str, config: str, request: Request) -> JSONResponse:
    auth_error = _authorize(request, runid, RQ_READ_SCOPES)
    if auth_error is not None:
        return auth_error
    try:
        return JSONResponse(_state_snapshot(get_wd(runid)))
    except Exception:  # broad-except: HTTP boundary contract
        logger.exception("rq-engine AgFields state read failed", extra={"runid": runid, "config": config})
        return error_response("Could not read AgFields state", status_code=500)


__all__ = ["router"]
