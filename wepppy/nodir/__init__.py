"""NoDir helpers.

This package is intentionally small and dependency-light. It hosts shared logic
needed across browse/query-engine/controllers without re-implementing
directory-vs-archive conventions in multiple places.
"""

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
from .paths import NoDirRoot, NoDirView, normalize_relpath, parse_external_subpath
from .projections import (
    ProjectionHandle,
    ProjectionMode,
    abort_mutation_projection,
    acquire_root_projection,
    commit_mutation_projection,
    release_root_projection,
    with_root_projection,
)
from .state import (
    NoDirArchiveFingerprint,
    NoDirStateName,
    NoDirStatePayload,
    NODIR_STATE_SCHEMA_VERSION,
    NODIR_TRANSITION_STATES,
    archive_fingerprint_from_path,
    freeze_temp_path,
    is_transitioning_locked,
    read_state,
    state_path,
    thaw_temp_path,
    write_state,
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
    "normalize_relpath",
    "parse_external_subpath",
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
    "NoDirStateName",
    "NoDirArchiveFingerprint",
    "NoDirStatePayload",
    "NODIR_STATE_SCHEMA_VERSION",
    "NODIR_TRANSITION_STATES",
    "state_path",
    "thaw_temp_path",
    "freeze_temp_path",
    "archive_fingerprint_from_path",
    "read_state",
    "write_state",
    "is_transitioning_locked",
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
