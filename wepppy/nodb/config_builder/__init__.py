"""Declarative project-configuration registry and deterministic resolver."""

from wepppy.nodb.config_builder.registry import (
    DEFAULT_PROFILES_ROOT,
    RegistryError,
    load_registry,
)
from wepppy.nodb.config_builder.resolver import (
    ALLOWED_CELL_SIZES,
    BuilderConstraintError,
    describe_builder,
    resolve_builder_capability_graph,
    resolve_builder_config,
)
from wepppy.nodb.config_builder.schema import (
    BuilderDescription,
    BuilderSelections,
    ComponentDefinition,
    ComponentKind,
    ComponentSummary,
    ConfigProvenance,
    ConfigWrite,
    Registry,
    ResolvedBuilderConfig,
)

__all__ = [
    "ALLOWED_CELL_SIZES",
    "DEFAULT_PROFILES_ROOT",
    "BuilderConstraintError",
    "BuilderDescription",
    "BuilderSelections",
    "ComponentDefinition",
    "ComponentKind",
    "ComponentSummary",
    "ConfigProvenance",
    "ConfigWrite",
    "Registry",
    "RegistryError",
    "ResolvedBuilderConfig",
    "describe_builder",
    "load_registry",
    "resolve_builder_capability_graph",
    "resolve_builder_config",
]
