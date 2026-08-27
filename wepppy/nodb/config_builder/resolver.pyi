from typing import Mapping
from wepppy.nodb.config_builder.schema import BuilderDescription, BuilderSelections, Registry, ResolvedBuilderConfig
from wepppy.project_config_serialization import CanonicalValue

__all__ = ["ALLOWED_CELL_SIZES", "DEFAULT_SELECTIONS", "BuilderConstraintError", "describe_builder", "resolve_builder_config"]
ALLOWED_CELL_SIZES: tuple[int, ...]
DEFAULT_SELECTIONS: Mapping[str, str]

class BuilderConstraintError(ValueError):
    field: str
    code: str
    def __init__(self, field: str, code: str, message: str) -> None: ...

def describe_builder(registry: Registry | None = ...) -> BuilderDescription: ...
def resolve_builder_config(selections: BuilderSelections, *, registry: Registry | None = ..., base_config: Mapping[str, Mapping[str, CanonicalValue]] | None = ..., base_revision: str | None = ...) -> ResolvedBuilderConfig: ...
