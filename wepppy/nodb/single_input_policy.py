"""Creation-time policy for independently uploaded management and soil sources."""
from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

__all__ = [
    "EXCLUDED_FEATURES", "SUPPORTED_BINARY", "SingleInputPolicyError",
    "single_input_uploads_enabled", "require_feature_allowed",
    "require_single_input_policy", "single_input_capability_graph", "require_wepp_input_policy",
]

SUPPORTED_BINARY = "wepp_260803"
EXCLUDED_FEATURES = frozenset({
    "disturbed", "baer", "treatments", "omni", "omni_contrasts", "path_ce",
    "debris_flow", "rusle", "postfire_debris_flow", "revegetation", "rred",
})


class SingleInputPolicyError(ValueError):
    """A request conflicts with immutable project input capabilities."""


def single_input_uploads_enabled(config) -> bool:
    getter = getattr(config, "config_get_str", None)
    if getter is None:
        return False
    value = getter("nodb", "single_user_defined_uploads", None)
    if value is None:
        return False
    token = str(value).strip().lower()
    if token not in {"true", "false"}:
        raise SingleInputPolicyError("The single-input upload project policy is invalid.")
    return token == "true"


def require_feature_allowed(config, feature: str) -> None:
    if single_input_uploads_enabled(config) and feature in EXCLUDED_FEATURES:
        raise SingleInputPolicyError(
            f"{feature} is unavailable when single landuse and soils upload is enabled."
        )


def require_single_input_policy(config, *, watershed=None, require_enabled=False) -> None:
    enabled = single_input_uploads_enabled(config)
    if require_enabled and not enabled:
        raise SingleInputPolicyError("Single User-Defined inputs are not enabled for this project.")
    if not enabled:
        return
    if EXCLUDED_FEATURES.intersection(config.mods):
        raise SingleInputPolicyError("The project contains modules incompatible with single-input uploads.")
    if config.config_get_str("wepp", "bin", None) != SUPPORTED_BINARY:
        raise SingleInputPolicyError(f"Single User-Defined inputs require {SUPPORTED_BINARY}.")
    if watershed is not None and watershed.mofe_buffer:
        raise SingleInputPolicyError("Buffer OFEs are disabled for single-input upload projects.")


def single_input_capability_graph(graph):
    """Add source methods without changing dataset defaults; restrict native readers."""
    method = "single-user-defined"
    add = lambda values: tuple(dict.fromkeys((*values, method)))
    relation = lambda values: MappingProxyType({key: add(value) for key, value in values.items()})
    mods = tuple(item for item in graph.mods if item not in EXCLUDED_FEATURES)
    defaults = dict(graph.defaults)
    defaults["wepp_binary"] = SUPPORTED_BINARY
    result = replace(
        graph,
        landuse_methods=add(graph.landuse_methods),
        soil_builders=add(graph.soil_builders),
        landuse_methods_by_dataset=relation(graph.landuse_methods_by_dataset),
        landuse_methods_by_representation=relation(graph.landuse_methods_by_representation),
        soil_builders_by_dataset=relation(graph.soil_builders_by_dataset),
        wepp_binaries=(SUPPORTED_BINARY,),
        wepp_binary_revisions=MappingProxyType({SUPPORTED_BINARY: graph.wepp_binary_revisions[SUPPORTED_BINARY]}),
        allowed_model_tuples=tuple(value for value in graph.allowed_model_tuples if value.endswith("|" + SUPPORTED_BINARY)),
        mods=mods,
        mod_requires=MappingProxyType({key: value for key, value in graph.mod_requires.items() if key in mods}),
        mod_conflicts=MappingProxyType({key: tuple(item for item in value if item in mods) for key, value in graph.mod_conflicts.items() if key in mods}),
        defaults=MappingProxyType(defaults),
    )
    result.validate()
    return result


def require_wepp_input_policy(wepp, *, binary=None, reveg=False):
    if not single_input_uploads_enabled(wepp):
        return
    require_single_input_policy(wepp, watershed=wepp.watershed_instance)
    if (wepp.wepp_bin if binary is None else binary) != SUPPORTED_BINARY:
        raise SingleInputPolicyError(f"Single User-Defined inputs require {SUPPORTED_BINARY}.")
    if reveg:
        raise SingleInputPolicyError("Revegetation is disabled for single-input upload projects.")
