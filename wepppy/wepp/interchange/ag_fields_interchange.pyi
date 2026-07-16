from os import PathLike
from pathlib import Path

AG_FIELDS_SCHEMA_VERSION: int
DATASET_KIND: str

__all__ = [
    "AG_FIELDS_SCHEMA_VERSION",
    "DATASET_KIND",
    "run_wepp_ag_fields_interchange",
]

def run_wepp_ag_fields_interchange(
    wepp_output_dir: Path | PathLike[str] | str,
    subfields_parquet_path: Path | PathLike[str] | str,
    *,
    start_year: int | None = ...,
) -> Path: ...
