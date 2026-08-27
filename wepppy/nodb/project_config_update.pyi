from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping
from wepppy.nodb.config_builder.schema import Registry

CONFIG_UPDATE_FLAG: str
MANIFEST_NAME: str
JOURNAL_NAME: str
LOCK_NAME: str

class ConfigUpdateError(ValueError): ...
class ConfigUpdateUnavailableError(ConfigUpdateError): ...
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

@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    applied: bool
    sequence: int | None
    prior_digest: str
    resulting_digest: str
    additions: tuple[ConfigUpdateAddition, ...]

def project_config_update_enabled(environ: Mapping[str, str] | None = ...) -> bool: ...
def project_config_digest_warning(working_directory: str | Path) -> bool: ...
def preview_project_config_update(working_directory: str | Path, *, registry: Registry | None = ..., registry_root: str | Path = ..., configs_root: str | Path = ...) -> ConfigUpdatePreview: ...
def recover_project_config_update(working_directory: str | Path) -> bool: ...
def apply_project_config_update(working_directory: str | Path, preview_id: str, *, trigger_section: str, trigger_option: str, application_revision: str, registry: Registry | None = ..., registry_root: str | Path = ..., configs_root: str | Path = ..., resolved_at: datetime | None = ..., fault_hook: Callable[[str], None] | None = ...) -> ConfigUpdateResult: ...

__all__ = [
    "CONFIG_UPDATE_FLAG",
    "ConfigUpdateAddition",
    "ConfigUpdateError",
    "ConfigUpdatePreview",
    "ConfigUpdateResult",
    "ConfigUpdateUnavailableError",
    "StaleConfigPreviewError",
    "apply_project_config_update",
    "preview_project_config_update",
    "project_config_digest_warning",
    "project_config_update_enabled",
    "recover_project_config_update",
]
