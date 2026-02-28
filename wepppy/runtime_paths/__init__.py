"""Directory-only runtime path helpers replacing legacy NoDir package."""

from .errors import NoDirError
from .fs import NoDirDirEntry, NoDirForm, ResolvedNoDirPath, listdir, open_read, resolve, stat
from .materialize import materialize_file, materialize_path_if_archive
from .mutations import mutate_root, mutate_roots, preflight_root_forms
from .parquet_sidecars import (
    logical_parquet_to_sidecar_relpath,
    pick_existing_parquet_path,
    pick_existing_parquet_relpath,
    sidecar_relpath_to_logical_parquet,
)
from .paths import NODIR_ROOTS, NoDirRoot, NoDirView, normalize_relpath, parse_external_subpath, split_nodir_root
from .projections import (
    ProjectionHandle,
    ProjectionMode,
    abort_mutation_projection,
    acquire_root_projection,
    commit_mutation_projection,
    release_root_projection,
    with_root_projection,
)
from .thaw_freeze import (
    NoDirMaintenanceLock,
    acquire_maintenance_lock,
    freeze,
    freeze_locked,
    maintenance_lock,
    maintenance_lock_key,
    release_maintenance_lock,
    thaw,
    thaw_locked,
)

__all__ = [
    "NoDirError",
    "NoDirDirEntry",
    "NoDirForm",
    "ResolvedNoDirPath",
    "NoDirRoot",
    "NoDirView",
    "NODIR_ROOTS",
    "normalize_relpath",
    "parse_external_subpath",
    "split_nodir_root",
    "resolve",
    "listdir",
    "stat",
    "open_read",
    "materialize_file",
    "materialize_path_if_archive",
    "preflight_root_forms",
    "mutate_root",
    "mutate_roots",
    "ProjectionMode",
    "ProjectionHandle",
    "acquire_root_projection",
    "release_root_projection",
    "with_root_projection",
    "commit_mutation_projection",
    "abort_mutation_projection",
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "pick_existing_parquet_path",
    "pick_existing_parquet_relpath",
    "NoDirMaintenanceLock",
    "maintenance_lock_key",
    "acquire_maintenance_lock",
    "release_maintenance_lock",
    "maintenance_lock",
    "thaw_locked",
    "thaw",
    "freeze_locked",
    "freeze",
]
