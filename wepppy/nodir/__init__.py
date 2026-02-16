"""NoDir helpers.

This package is intentionally small and dependency-light. It hosts shared logic
needed across browse/query-engine/controllers without re-implementing
directory-vs-archive conventions in multiple places.
"""

from .errors import NoDirError
from .fs import NoDirDirEntry, NoDirForm, ResolvedNoDirPath, listdir, open_read, resolve, stat
from .parquet_sidecars import (
    logical_parquet_to_sidecar_relpath,
    pick_existing_parquet_path,
    pick_existing_parquet_relpath,
    sidecar_relpath_to_logical_parquet,
)
from .paths import NoDirRoot, NoDirView, normalize_relpath, parse_external_subpath

__all__ = [
    "NoDirError",
    "NoDirDirEntry",
    "NoDirForm",
    "ResolvedNoDirPath",
    "NoDirRoot",
    "NoDirView",
    "normalize_relpath",
    "parse_external_subpath",
    "resolve",
    "listdir",
    "stat",
    "open_read",
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "pick_existing_parquet_path",
    "pick_existing_parquet_relpath",
]
