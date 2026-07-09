from typing import Any, Dict, Optional

__all__: list[str] = [
    "AGFIELDS_BUILD_SUBFIELDS_JOB_KEY",
    "AGFIELDS_PLANTDB_JOB_KEY",
    "AGFIELDS_RUN_WEPP_JOB_KEY",
    "build_ag_fields_subfields_rq",
    "process_ag_fields_plant_db_rq",
    "run_ag_fields_wepp_rq",
]

AGFIELDS_BUILD_SUBFIELDS_JOB_KEY: str
AGFIELDS_PLANTDB_JOB_KEY: str
AGFIELDS_RUN_WEPP_JOB_KEY: str

def build_ag_fields_subfields_rq(
    runid: str,
    sub_field_min_area_threshold_m2: float = ...,
) -> Dict[str, Any]: ...
def process_ag_fields_plant_db_rq(runid: str, plant_db_zip_fn: str) -> Dict[str, Any]: ...
def run_ag_fields_wepp_rq(runid: str, max_workers: Optional[int] = ...) -> Dict[str, Any]: ...
