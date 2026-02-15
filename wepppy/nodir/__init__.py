"""NoDir helpers.

This package is intentionally small and dependency-light. It hosts shared logic
needed across browse/query-engine/controllers without re-implementing
directory-vs-archive conventions in multiple places.
"""

from .parquet_sidecars import (
    logical_parquet_to_sidecar_relpath,
    sidecar_relpath_to_logical_parquet,
    pick_existing_parquet_path,
    pick_existing_parquet_relpath,
)

__all__ = [
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "pick_existing_parquet_path",
    "pick_existing_parquet_relpath",
]

