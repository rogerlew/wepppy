"""RQ worker entrypoints for the AgFields staged workflow."""

from __future__ import annotations

import inspect
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional

import redis
from rq import Queue, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.mods.ag_fields import AgFields, AgFieldsRunError, PlantFileProcessingError
from wepppy.nodb.mods.ag_fields.routing_schemes import (
    parse_routing_scheme,
    validate_watershed_max_workers,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.wepp.interchange import run_wepp_ag_fields_interchange
from wepppy.weppcloud.utils.helpers import get_wd


logger = logging.getLogger(__name__)

AGFIELDS_BUILD_SUBFIELDS_JOB_KEY = "agfields_build_subfields"
AGFIELDS_PLANTDB_JOB_KEY = "agfields_plantdb"
AGFIELDS_RUN_WEPP_JOB_KEY = "agfields_run_wepp"
AGFIELDS_RUN_WATERSHED_JOB_KEY = "agfields_run_watershed"
AGFIELDS_RUN_WATERSHED_SUITE_JOB_KEY = "agfields_run_watershed_suite"
AGFIELDS_RUN_WATERSHED_CONCEPT_1_JOB_KEY = "agfields_run_watershed_concept_1"
AGFIELDS_RUN_WATERSHED_CONCEPT_2_JOB_KEY = "agfields_run_watershed_concept_2"
AGFIELDS_RUN_WATERSHED_HYBRID_JOB_KEY = "agfields_run_watershed_hybrid"
AGFIELDS_RUN_WATERSHED_JOB_KEYS = {
    "concept_1": AGFIELDS_RUN_WATERSHED_CONCEPT_1_JOB_KEY,
    "concept_2": AGFIELDS_RUN_WATERSHED_CONCEPT_2_JOB_KEY,
    "hybrid": AGFIELDS_RUN_WATERSHED_HYBRID_JOB_KEY,
}

AGFIELDS_BUILD_SUBFIELDS_COMPLETED = "AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED"
AGFIELDS_PLANTDB_COMPLETED = "AGFIELDS_PLANTDB_TASK_COMPLETED"
AGFIELDS_RUN_WEPP_COMPLETED = "AGFIELDS_RUN_WEPP_TASK_COMPLETED"
AGFIELDS_RUN_WATERSHED_COMPLETED = "AGFIELDS_RUN_WATERSHED_TASK_COMPLETED"
AGFIELDS_SUITE_DISPATCH_LOCK_PREFIX = "agfields:suite_dispatch:"
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))


def _job_id() -> str:
    return str(getattr(get_current_job(), "id", "unknown"))


def _publish_result(channel: str, job_id: str, result: Dict[str, Any]) -> None:
    StatusMessenger.publish(
        channel,
        f"rq:{job_id} RESULT_JSON {json.dumps(result, sort_keys=True, separators=(',', ':'))}",
    )


def _publish_failure(channel: str, job_id: str, payload: Dict[str, Any]) -> None:
    StatusMessenger.publish(
        channel,
        f"rq:{job_id} EXCEPTION_JSON {json.dumps(payload, sort_keys=True, separators=(',', ':'))}",
    )


def _publish_completed(
    channel: str,
    job_id: str,
    func_name: str,
    runid: str,
    event_name: str,
) -> None:
    StatusMessenger.publish(channel, f"rq:{job_id} COMPLETED {func_name}({runid})")
    StatusMessenger.publish(channel, f"rq:{job_id} TRIGGER ag_fields {event_name}")


def _publish_exception(channel: str, job_id: str, func_name: str, runid: str) -> None:
    StatusMessenger.publish(channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")


def _invalidate_ag_fields_preflight(wd: str) -> RedisPrep:
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.run_ag_fields)
    return prep


@with_exception_logging
def build_ag_fields_subfields_rq(
    runid: str,
    sub_field_min_area_threshold_m2: float = 0.0,
) -> Dict[str, Any]:
    """Rasterize, abstract, and polygonize sub-fields in contractual order."""
    minimum_area = float(sub_field_min_area_threshold_m2)
    if not math.isfinite(minimum_area) or minimum_area < 0.0:
        raise ValueError("sub_field_min_area_threshold_m2 must be a finite non-negative number.")

    job_id = _job_id()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    try:
        wd = get_wd(runid)
        _invalidate_ag_fields_preflight(wd)
        clear_nodb_file_cache(runid, pup_relpath="ag_fields.nodb")
        ag_fields = AgFields.getInstance(wd)

        StatusMessenger.publish(status_channel, "Rasterizing field boundaries.")
        ag_fields.rasterize_field_boundaries_geojson()
        StatusMessenger.publish(status_channel, "Abstracting sub-fields.")
        ag_fields.periodot_abstract_sub_fields(minimum_area)
        StatusMessenger.publish(status_channel, "Polygonizing sub-fields.")
        ag_fields.polygonize_sub_fields()

        result: Dict[str, Any] = {
            "field_n": ag_fields.field_n,
            "sub_field_n": ag_fields.sub_field_n,
            "sub_field_fp_n": ag_fields.sub_field_fp_n,
        }
        _publish_result(status_channel, job_id, result)
        _publish_completed(
            status_channel,
            job_id,
            func_name,
            runid,
            AGFIELDS_BUILD_SUBFIELDS_COMPLETED,
        )
        return result
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception("AgFields build-subfields worker failed", extra={"runid": runid, "job_id": job_id})
        _publish_failure(status_channel, job_id, {"message": str(exc) or exc.__class__.__name__})
        _publish_exception(status_channel, job_id, func_name, runid)
        raise


@with_exception_logging
def process_ag_fields_plant_db_rq(runid: str, plant_db_zip_fn: str) -> Dict[str, Any]:
    """Process one server-staged AgFields plant management archive."""
    if not isinstance(plant_db_zip_fn, str) or not plant_db_zip_fn.strip():
        raise ValueError("plant_db_zip_fn is required.")

    job_id = _job_id()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    wd: Optional[str] = None
    try:
        wd = get_wd(runid)
        _invalidate_ag_fields_preflight(wd)
        clear_nodb_file_cache(runid, pup_relpath="ag_fields.nodb")
        ag_fields = AgFields.getInstance(wd)
        result = ag_fields.handle_plant_file_db_upload(plant_db_zip_fn)
        _publish_result(status_channel, job_id, result)
        _publish_completed(
            status_channel,
            job_id,
            func_name,
            runid,
            AGFIELDS_PLANTDB_COMPLETED,
        )
        return result
    except PlantFileProcessingError as exc:
        payload = {"filename": exc.filename, "message": str(exc)}
        logger.exception(
            "AgFields plant-db worker rejected an archive member",
            extra={"runid": runid, "job_id": job_id, "plant_filename": exc.filename},
        )
        _publish_failure(status_channel, job_id, payload)
        _publish_exception(status_channel, job_id, func_name, runid)
        raise
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception("AgFields plant-db worker failed", extra={"runid": runid, "job_id": job_id})
        _publish_failure(status_channel, job_id, {"message": str(exc) or exc.__class__.__name__})
        _publish_exception(status_channel, job_id, func_name, runid)
        raise
    finally:
        if wd is not None:
            archive_root = (Path(wd) / "ag_fields").resolve()
            archive_path = (archive_root / plant_db_zip_fn).resolve()
            if archive_root in archive_path.parents:
                try:
                    archive_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "AgFields plant-db worker could not remove staged archive %s: %s",
                        archive_path.name,
                        exc,
                        extra={"runid": runid, "job_id": job_id},
                    )


@with_exception_logging
def run_ag_fields_wepp_rq(
    runid: str,
    max_workers: Optional[int] = None,
    wepp_bin: Optional[str] = None,
) -> Dict[str, Any]:
    """Run WEPP for each current AgFields sub-field."""
    if max_workers is not None:
        max_workers = int(max_workers)
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1 when provided.")

    job_id = _job_id()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    try:
        wd = get_wd(runid)
        prep = _invalidate_ag_fields_preflight(wd)
        clear_nodb_file_cache(runid, pup_relpath="ag_fields.nodb")
        ag_fields = AgFields.getInstance(wd)
        if wepp_bin is not None:
            ag_fields.wepp_bin = wepp_bin
        result: Dict[str, Any] = dict(
            ag_fields.run_wepp_ag_fields(max_workers=max_workers)
        )
        source_signature = ag_fields.wepp_source_signature
        if not source_signature:
            raise RuntimeError("AgFields raw WEPP run did not publish a source signature")
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} PHASE_JSON "
            + json.dumps(
                {"phase": "interchange", "message": "Publishing AgFields interchange."},
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        climate = Climate.getInstance(wd)
        interchange_dir = run_wepp_ag_fields_interchange(
            ag_fields.ag_field_wepp_output_dir,
            ag_fields.subfields_parquet_path,
            start_year=climate.calendar_start_year,
        )
        ag_fields.mark_wepp_ag_fields_interchange_complete(source_signature)
        result["interchange_relpath"] = str(interchange_dir.relative_to(Path(wd)))
        prep.timestamp(TaskEnum.run_ag_fields)
        _publish_result(status_channel, job_id, result)
        _publish_completed(
            status_channel,
            job_id,
            func_name,
            runid,
            AGFIELDS_RUN_WEPP_COMPLETED,
        )
        return result
    except AgFieldsRunError as exc:
        payload = {
            "field_id": exc.field_id,
            "sub_field_id": exc.sub_field_id,
            "message": str(exc),
        }
        logger.exception(
            "AgFields WEPP worker failed",
            extra={
                "runid": runid,
                "job_id": job_id,
                "field_id": exc.field_id,
                "sub_field_id": exc.sub_field_id,
                "error_message": str(exc),
            },
        )
        _publish_failure(status_channel, job_id, payload)
        _publish_exception(status_channel, job_id, func_name, runid)
        raise
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception("AgFields WEPP worker failed", extra={"runid": runid, "job_id": job_id})
        _publish_failure(status_channel, job_id, {"message": str(exc) or exc.__class__.__name__})
        _publish_exception(status_channel, job_id, func_name, runid)
        raise


@with_exception_logging
def run_ag_fields_watershed_rq(
    runid: str,
    max_workers: Optional[int] = None,
    scheme: Optional[str] = None,
    publish_completion_trigger: bool = True,
) -> Dict[str, Any]:
    """Run exactly one isolated AgFields watershed routing scheme."""
    max_workers = validate_watershed_max_workers(max_workers)
    parsed_scheme = parse_routing_scheme(scheme)

    job_id = _job_id()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(
        status_channel,
        f"rq:{job_id} STARTED {func_name}({runid},scheme={parsed_scheme.value})",
    )

    try:
        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="ag_fields.nodb")
        ag_fields = AgFields.getInstance(wd)

        def publish_phase(phase: str) -> None:
            payload = json.dumps(
                {"phase": phase, "scheme": parsed_scheme.value},
                sort_keys=True,
                separators=(",", ":"),
            )
            StatusMessenger.publish(status_channel, f"rq:{job_id} PHASE_JSON {payload}")

        result = ag_fields.run_watershed_integration(
            max_workers=max_workers,
            phase_callback=publish_phase,
            scheme=parsed_scheme.value,
        )
        result["scheme"] = parsed_scheme.value
        _publish_result(status_channel, job_id, result)
        if publish_completion_trigger:
            _publish_completed(
                status_channel,
                job_id,
                func_name,
                runid,
                AGFIELDS_RUN_WATERSHED_COMPLETED,
            )
        else:
            StatusMessenger.publish(
                status_channel,
                f"rq:{job_id} COMPLETED {func_name}({runid})",
            )
        return result
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception(
            "AgFields watershed worker failed",
            extra={"runid": runid, "job_id": job_id, "scheme": parsed_scheme.value},
        )
        _publish_failure(
            status_channel,
            job_id,
            {
                "message": str(exc) or exc.__class__.__name__,
                "scheme": parsed_scheme.value,
            },
        )
        _publish_exception(status_channel, job_id, func_name, runid)
        raise


def _release_deferred_job_if_ready(queue: Queue, dependent_job: Job) -> None:
    """Release a failure-tolerant dependent whose prerequisites are terminal."""
    if dependent_job.get_status(refresh=True) != JobStatus.DEFERRED:
        return
    if not dependent_job.dependencies_are_met():
        return

    DeferredJobRegistry(queue=queue).remove(dependent_job)
    queue._enqueue_job(dependent_job)


@with_exception_logging
def finalize_ag_fields_watershed_suite_rq(
    runid: str,
    planned_job_ids: Dict[str, str],
) -> Dict[str, Any]:
    """Publish one terminal suite summary after every scheme job is terminal."""
    job_id = _job_id()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    try:
        statuses: Dict[str, str] = {}
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            for scheme, child_job_id in planned_job_ids.items():
                try:
                    child_job = Job.fetch(child_job_id, connection=redis_conn)
                except NoSuchJobError:
                    statuses[scheme] = "missing"
                    continue
                statuses[scheme] = str(child_job.get_status(refresh=False) or "unknown").lower()

        result: Dict[str, Any] = {
            "job_ids": dict(planned_job_ids),
            "statuses": statuses,
        }
        _publish_result(status_channel, job_id, result)
        _publish_completed(
            status_channel,
            job_id,
            func_name,
            runid,
            AGFIELDS_RUN_WATERSHED_COMPLETED,
        )
        return result
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception(
            "AgFields watershed suite finalizer failed",
            extra={"runid": runid, "job_id": job_id},
        )
        _publish_failure(status_channel, job_id, {"message": str(exc) or exc.__class__.__name__})
        _publish_exception(status_channel, job_id, func_name, runid)
        raise


@with_exception_logging
def run_ag_fields_watershed_suite_rq(
    runid: str,
    max_workers: Optional[int],
    planned_job_ids: Dict[str, str],
    finalizer_job_id: str,
) -> Dict[str, Any]:
    """Dispatch three serial scheme children and an always-released finalizer."""
    max_workers = validate_watershed_max_workers(max_workers)
    expected_schemes = tuple(AGFIELDS_RUN_WATERSHED_JOB_KEYS)
    normalized_job_ids = {
        str(scheme): str(job_id).strip()
        for scheme, job_id in planned_job_ids.items()
    }
    if tuple(normalized_job_ids) != expected_schemes:
        raise ValueError(
            "planned_job_ids must contain concept_1, concept_2, and hybrid in routing order."
        )
    if any(not job_id for job_id in normalized_job_ids.values()):
        raise ValueError("Every planned AgFields watershed child job id is required.")
    if len(set(normalized_job_ids.values())) != len(normalized_job_ids):
        raise ValueError("AgFields watershed child job ids must be distinct.")
    normalized_finalizer_job_id = str(finalizer_job_id).strip()
    if not normalized_finalizer_job_id:
        raise ValueError("The AgFields watershed suite finalizer job id is required.")
    if normalized_finalizer_job_id in normalized_job_ids.values():
        raise ValueError("The AgFields watershed suite finalizer job id must be distinct.")

    parent_job = get_current_job()
    if parent_job is None:
        raise RuntimeError("AgFields watershed suite requires an active RQ parent job.")
    parent_job_id = str(parent_job.id)
    dispatch_lock_key = f"{AGFIELDS_SUITE_DISPATCH_LOCK_PREFIX}{parent_job_id}"
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:ag_fields"
    StatusMessenger.publish(
        status_channel,
        f"rq:{parent_job_id} STARTED {func_name}({runid})",
    )

    try:
        tree_meta = {
            f"jobs:{order},scheme:{scheme}": child_job_id
            for order, (scheme, child_job_id) in enumerate(normalized_job_ids.items())
        }
        tree_meta[
            "jobs:3,func:finalize_ag_fields_watershed_suite_rq"
        ] = normalized_finalizer_job_id

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        clear_nodb_file_cache(runid, pup_relpath="ag_fields.nodb")
        ag_fields = AgFields.getInstance(wd)

        scheme_jobs: list[Job] = []
        previous_job_id: str | None = None
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            with redis_conn.lock(dispatch_lock_key, timeout=30, blocking_timeout=30):
                parent_job.refresh()
                if parent_job.meta.get("cancel_requested"):
                    raise RuntimeError("AgFields watershed suite was canceled before child dispatch.")
                parent_job.meta.update(tree_meta)
                parent_job.meta["runid"] = runid
                parent_job.meta["child_dispatch_lock_key"] = dispatch_lock_key
                parent_job.save()

                for scheme, child_job_id in normalized_job_ids.items():
                    prep.set_rq_job_id(AGFIELDS_RUN_WATERSHED_JOB_KEYS[scheme], child_job_id)
                prep.set_rq_job_id(
                    AGFIELDS_RUN_WATERSHED_JOB_KEY,
                    normalized_job_ids["concept_2"],
                )
                ag_fields.set_watershed_integration_job_ids(normalized_job_ids)

                queue = Queue(connection=redis_conn)
                for order, (scheme, child_job_id) in enumerate(normalized_job_ids.items()):
                    dependency = (
                        Dependency(jobs=[previous_job_id], allow_failure=True)
                        if previous_job_id is not None
                        else None
                    )
                    child_job = queue.enqueue_call(
                        run_ag_fields_watershed_rq,
                        args=(runid, max_workers, scheme, False),
                        timeout=RQ_TIMEOUT,
                        depends_on=dependency,
                        job_id=child_job_id,
                        meta={
                            "runid": runid,
                            "agfields_scheme": scheme,
                            "parent_job_id": parent_job_id,
                            **(
                                {"auth_actor": parent_job.meta["auth_actor"]}
                                if isinstance(parent_job.meta.get("auth_actor"), dict)
                                else {}
                            ),
                        },
                    )
                    if dependency is not None:
                        _release_deferred_job_if_ready(queue, child_job)
                    scheme_jobs.append(child_job)
                    previous_job_id = child_job.id

                finalizer_dependency = Dependency(
                    jobs=[child_job.id for child_job in scheme_jobs],
                    allow_failure=True,
                )
                finalizer_job = queue.enqueue_call(
                    finalize_ag_fields_watershed_suite_rq,
                    args=(runid, normalized_job_ids),
                    timeout=RQ_TIMEOUT,
                    depends_on=finalizer_dependency,
                    job_id=normalized_finalizer_job_id,
                    meta={
                        "runid": runid,
                        "parent_job_id": parent_job_id,
                        **(
                            {"auth_actor": parent_job.meta["auth_actor"]}
                            if isinstance(parent_job.meta.get("auth_actor"), dict)
                            else {}
                        ),
                    },
                )
                _release_deferred_job_if_ready(queue, finalizer_job)

        result: Dict[str, Any] = {
            "job_ids": normalized_job_ids,
            "finalizer_job_id": finalizer_job.id,
            "schemes": list(expected_schemes),
        }
        _publish_result(status_channel, parent_job_id, result)
        StatusMessenger.publish(
            status_channel,
            f"rq:{parent_job_id} COMPLETED {func_name}({runid})",
        )
        return result
    except Exception as exc:  # broad-except: RQ task boundary preserves terminal status contract
        logger.exception(
            "AgFields watershed suite dispatch failed",
            extra={"runid": runid, "job_id": parent_job_id},
        )
        _publish_failure(
            status_channel,
            parent_job_id,
            {"message": str(exc) or exc.__class__.__name__},
        )
        _publish_exception(status_channel, parent_job_id, func_name, runid)
        raise


__all__ = [
    "AGFIELDS_BUILD_SUBFIELDS_JOB_KEY",
    "AGFIELDS_PLANTDB_JOB_KEY",
    "AGFIELDS_RUN_WEPP_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_JOB_KEY",
    "AGFIELDS_SUITE_DISPATCH_LOCK_PREFIX",
    "AGFIELDS_RUN_WATERSHED_SUITE_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_CONCEPT_1_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_CONCEPT_2_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_HYBRID_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_JOB_KEYS",
    "build_ag_fields_subfields_rq",
    "process_ag_fields_plant_db_rq",
    "run_ag_fields_wepp_rq",
    "run_ag_fields_watershed_rq",
    "run_ag_fields_watershed_suite_rq",
    "finalize_ag_fields_watershed_suite_rq",
]
