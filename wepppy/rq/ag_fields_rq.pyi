from typing import Any, Dict, Optional

__all__: list[str] = [
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

AGFIELDS_BUILD_SUBFIELDS_JOB_KEY: str
AGFIELDS_PLANTDB_JOB_KEY: str
AGFIELDS_RUN_WEPP_JOB_KEY: str
AGFIELDS_RUN_WATERSHED_JOB_KEY: str
AGFIELDS_SUITE_DISPATCH_LOCK_PREFIX: str
AGFIELDS_RUN_WATERSHED_SUITE_JOB_KEY: str
AGFIELDS_RUN_WATERSHED_CONCEPT_1_JOB_KEY: str
AGFIELDS_RUN_WATERSHED_CONCEPT_2_JOB_KEY: str
AGFIELDS_RUN_WATERSHED_HYBRID_JOB_KEY: str
AGFIELDS_RUN_WATERSHED_JOB_KEYS: dict[str, str]

def build_ag_fields_subfields_rq(
    runid: str,
    sub_field_min_area_threshold_m2: float = ...,
) -> Dict[str, Any]: ...
def process_ag_fields_plant_db_rq(runid: str, plant_db_zip_fn: str) -> Dict[str, Any]: ...
def run_ag_fields_wepp_rq(
    runid: str,
    max_workers: Optional[int] = ...,
    wepp_bin: Optional[str] = ...,
) -> Dict[str, Any]: ...
def run_ag_fields_watershed_rq(
    runid: str,
    max_workers: Optional[int] = ...,
    scheme: Optional[str] = ...,
    publish_completion_trigger: bool = ...,
) -> Dict[str, Any]: ...
def run_ag_fields_watershed_suite_rq(
    runid: str,
    max_workers: Optional[int],
    planned_job_ids: Dict[str, str],
    finalizer_job_id: str,
) -> Dict[str, Any]: ...
def finalize_ag_fields_watershed_suite_rq(
    runid: str,
    planned_job_ids: Dict[str, str],
) -> Dict[str, Any]: ...
