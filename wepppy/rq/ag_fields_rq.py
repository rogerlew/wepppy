"""RQ worker entrypoints for the AgFields staged workflow."""

from __future__ import annotations

import inspect
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, Optional

from rq import get_current_job

from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.mods.ag_fields import AgFields, AgFieldsRunError, PlantFileProcessingError
from wepppy.nodb.mods.ag_fields.routing_schemes import (
    parse_routing_scheme,
    validate_watershed_max_workers,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd


logger = logging.getLogger(__name__)

AGFIELDS_BUILD_SUBFIELDS_JOB_KEY = "agfields_build_subfields"
AGFIELDS_PLANTDB_JOB_KEY = "agfields_plantdb"
AGFIELDS_RUN_WEPP_JOB_KEY = "agfields_run_wepp"
AGFIELDS_RUN_WATERSHED_JOB_KEY = "agfields_run_watershed"
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
        result = ag_fields.run_wepp_ag_fields(max_workers=max_workers)
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


__all__ = [
    "AGFIELDS_BUILD_SUBFIELDS_JOB_KEY",
    "AGFIELDS_PLANTDB_JOB_KEY",
    "AGFIELDS_RUN_WEPP_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_CONCEPT_1_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_CONCEPT_2_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_HYBRID_JOB_KEY",
    "AGFIELDS_RUN_WATERSHED_JOB_KEYS",
    "build_ag_fields_subfields_rq",
    "process_ag_fields_plant_db_rq",
    "run_ag_fields_wepp_rq",
    "run_ag_fields_watershed_rq",
]
