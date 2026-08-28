from pathlib import Path
from typing import Mapping
from wepppy.nodb.config_builder.schema import BuilderDescription, BuilderSelections, Registry, ResolvedBuilderConfig
from wepppy.nodb.locales.capability_graph import CapabilityGraph
from wepppy.project_config_serialization import CanonicalValue

__all__ = ["ALLOWED_CELL_SIZES", "DEFAULT_SELECTIONS", "BuilderConstraintError", "describe_builder", "resolve_builder_capability_graph", "resolve_builder_config"]
ALLOWED_CELL_SIZES: tuple[int, ...]
DEFAULT_SELECTIONS: Mapping[str, str]

class BuilderConstraintError(ValueError):
    field: str
    code: str
    def __init__(self, field: str, code: str, message: str) -> None: ...

def describe_builder(registry: Registry | None = ...) -> BuilderDescription: ...
def resolve_builder_capability_graph(locale_id: str, *, registry: Registry | None = ..., registry_root: str | Path = ...) -> CapabilityGraph: ...
def resolve_builder_config(selections: BuilderSelections, *, registry: Registry | None = ..., base_config: Mapping[str, Mapping[str, CanonicalValue]] | None = ..., base_revision: str | None = ..., capability_schema_version: int = ..., capability_graph: CapabilityGraph | None = ...) -> ResolvedBuilderConfig: ...
