from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, ContextManager, Mapping
from wepppy.nodb.config_builder.schema import Registry

CONFIG_UPDATE_FLAG: str
CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION: str
CAPABILITY_REFRESH_WARNING: str
MANIFEST_NAME: str
JOURNAL_NAME: str
LOCK_NAME: str

class ConfigUpdateError(ValueError): ...
class ConfigUpdateAcknowledgmentError(ConfigUpdateError): ...
class ConfigUpdateUnavailableError(ConfigUpdateError): ...
class ConfigUpdateRegistryError(ConfigUpdateUnavailableError): ...
class StaleConfigPreviewError(ConfigUpdateError): ...

@dataclass(frozen=True, slots=True)
class ConfigUpdateAddition:
    section: str
    option: str
    value: str
    source_id: str
    source_revision: str

@dataclass(frozen=True, slots=True)
class ConfigUpdatePreview:
    available: bool
    preview_id: str | None
    additions: tuple[ConfigUpdateAddition, ...]
    config_filename: str
    current_digest: str
    declared_digest: str | None
    digest_warning: bool
    resulting_digest: str = ...
    update_kind: str = ...
    capability_refresh: Mapping[str, object] | None = ...

@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    applied: bool
    sequence: int | None
    prior_digest: str
    resulting_digest: str
    additions: tuple[ConfigUpdateAddition, ...]
    recovered: bool = ...
    update_kind: str = ...

@dataclass(frozen=True, slots=True)
class ConfigUpdateStatus:
    current_digest: str
    last_update: Mapping[str, object] | None
    config_filename: str | None = ...

def project_config_update_enabled(environ: Mapping[str, str] | None = ...) -> bool: ...
def project_config_digest_warning(working_directory: str | Path) -> bool: ...
def project_config_update_reconciliation(working_directory: str | Path, preview_id: str) -> ConfigUpdateResult | None: ...
def project_config_update_status(working_directory: str | Path) -> ConfigUpdateStatus: ...
def project_config_lifecycle_guard(working_directory: str | Path) -> ContextManager[None]: ...
def preview_project_config_update(working_directory: str | Path, *, registry: Registry | None = ..., registry_root: str | Path = ..., configs_root: str | Path = ..., application_revision: str = ...) -> ConfigUpdatePreview: ...
def project_config_update_preview_guard(working_directory: str | Path, *, registry: Registry | None = ..., registry_root: str | Path = ..., configs_root: str | Path = ..., application_revision: str = ...) -> ContextManager[ConfigUpdatePreview]: ...
def recover_project_config_update(working_directory: str | Path) -> bool: ...
def apply_project_config_update(working_directory: str | Path, preview_id: str, *, trigger_section: str | None = ..., trigger_option: str | None = ..., application_revision: str, capability_acknowledgment_accepted: bool = ..., capability_acknowledgment_revision: str | None = ..., registry: Registry | None = ..., registry_root: str | Path = ..., configs_root: str | Path = ..., resolved_at: datetime | None = ..., fault_hook: Callable[[str], None] | None = ...) -> ConfigUpdateResult: ...

__all__ = [
    "CONFIG_UPDATE_FLAG",
    "CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION",
    "CAPABILITY_REFRESH_WARNING",
    "ConfigUpdateAcknowledgmentError",
    "ConfigUpdateAddition",
    "ConfigUpdateError",
    "ConfigUpdatePreview",
    "ConfigUpdateRegistryError",
    "ConfigUpdateResult",
    "ConfigUpdateStatus",
    "ConfigUpdateUnavailableError",
    "StaleConfigPreviewError",
    "apply_project_config_update",
    "preview_project_config_update",
    "project_config_digest_warning",
    "project_config_lifecycle_guard",
    "project_config_update_preview_guard",
    "project_config_update_reconciliation",
    "project_config_update_status",
    "project_config_update_enabled",
    "recover_project_config_update",
]
