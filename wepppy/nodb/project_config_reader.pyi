from configparser import RawConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

__all__ = [
    "PROJECT_CONFIG_READER_FLAG",
    "ProjectConfigAuthorityError",
    "ProjectConfigError",
    "ProjectConfigLoadResult",
    "ProjectConfigSchemaError",
    "ProjectConfigStatus",
    "ProjectConfigWarning",
    "load_project_config",
    "project_config_reader_enabled",
]
PROJECT_CONFIG_READER_FLAG: str

class ProjectConfigError(ValueError): ...
class ProjectConfigSchemaError(ProjectConfigError): ...
class ProjectConfigAuthorityError(ProjectConfigError): ...

@dataclass(frozen=True, slots=True)
class ProjectConfigWarning:
    code: str
    run_id: str
    config_filename: str
    declared_digest: str | None = ...
    observed_digest: str | None = ...

@dataclass(frozen=True, slots=True)
class ProjectConfigStatus:
    mode: str
    authority_root: str | None
    config_filename: str | None
    manifest_valid: bool
    updates_enabled: bool
    warnings: tuple[ProjectConfigWarning, ...] = ...

@dataclass(frozen=True, slots=True)
class ProjectConfigLoadResult:
    parser: RawConfigParser
    status: ProjectConfigStatus

def project_config_reader_enabled(environ: dict[str, str] | None = ...) -> bool: ...
def load_project_config(
    *,
    wd: str | Path,
    config_token: str,
    parent_wd: str | Path | None,
    config_dir: str | Path,
    defaults_resolver: Callable[[str | Path | None], str],
    parser_factory: Callable[..., RawConfigParser],
    run_id: str,
) -> ProjectConfigLoadResult: ...
def log_project_config_warning(warning: ProjectConfigWarning) -> None: ...
