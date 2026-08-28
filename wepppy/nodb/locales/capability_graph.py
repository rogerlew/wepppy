"""Immutable locale capability graph construction and stored validation."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
import typing

from wepppy.nodb.locales.climate_catalog import (
    climate_catalog_revision,
    default_climate_provider_tokens,
    iter_climate_datasets,
)
from wepppy.nodb.locales.landuse_catalog import landcover_catalog_revision
from wepppy.nodb.locales.locale_profiles import (
    DEM_SOURCE_RUNTIME,
    SOIL_SOURCE_RUNTIME,
    get_locale_profile,
    locale_catalog_revision,
)
from wepppy.project_config_serialization import CanonicalValue

__all__ = [
    "CAPABILITY_SCHEMA_VERSION",
    "HISTORICAL_CAPABILITY_SCHEMA_VERSION",
    "CapabilityGraph",
    "CapabilityGraphError",
    "build_continental_us_capability_graph",
    "build_locale_capability_graph",
    "capability_structure_payload",
    "capability_structure_sha256",
]

HISTORICAL_CAPABILITY_SCHEMA_VERSION = 2
CAPABILITY_SCHEMA_VERSION = 3
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,127}$")
_MAX_VALUES = 4096
_MAX_SERIALIZED_BYTES = 4 * 1024 * 1024
_SOIL_BUILDERS = ("gridded", "single_mukey", "single_database")
_LANDUSE_METHODS = ("gridded", "single", "upload")
_DELINEATION_BACKENDS = ("topaz", "wbt")
_WATERSHED_REPRESENTATIONS = ("single-ofe", "multiple-ofe")
_KNOWN_STATION_METHODS = frozenset(
    {"auto", "distance", "multi_factor", "eu_heuristic", "au_heuristic", "user_defined"}
)
_KNOWN_SPATIAL_METHODS = frozenset({"single", "multiple", "interpolated"})
_KNOWN_STATION_DATABASES = frozenset(
    {"cligen-stations-legacy", "cligen-stations-2015", "cligen-stations-ghcn"}
)
_KNOWN_MOD_IDS = frozenset({
    "ag_fields", "ash", "baer", "debris_flow", "disturbed", "general", "lt",
    "omni", "portland", "rangeland_cover", "rap", "rap_ts", "revegetation",
    "rhem", "rred", "seattle", "shrubland", "swat", "treatments", "treecanopy",
    "turkey",
})

_V2_CLIMATE_IDS = (
    "vanilla_cligen",
    "prism_stochastic",
    "observed_daymet",
    "observed_gridmet",
)
_V2_STATION_METHODS = ("auto", "distance", "multi_factor")
_V2_SPATIAL_METHODS = ("single", "multiple", "interpolated")
_V2_STATION_RELATIONS = MappingProxyType({
    climate_id: _V2_STATION_METHODS for climate_id in _V2_CLIMATE_IDS
})
_V2_SPATIAL_RELATIONS = MappingProxyType({
    "vanilla_cligen": ("single", "multiple"),
    "prism_stochastic": ("single", "multiple"),
    "observed_daymet": _V2_SPATIAL_METHODS,
    "observed_gridmet": _V2_SPATIAL_METHODS,
})

_CLIMATE_STATION_RELATIONS: typing.Mapping[str, tuple[str, ...]] = MappingProxyType({
    "vanilla_cligen": ("auto", "distance", "multi_factor"),
    "prism_stochastic": ("auto", "distance", "multi_factor"),
    "observed_daymet": ("auto", "distance", "multi_factor"),
    "observed_gridmet": ("auto", "distance", "multi_factor"),
    "eobs_modified": ("auto", "distance", "multi_factor", "eu_heuristic"),
    "agdc": ("auto", "distance"),
})
_CLIMATE_SPATIAL_RELATIONS: typing.Mapping[str, tuple[str, ...]] = MappingProxyType({
    "vanilla_cligen": ("single", "multiple"),
    "prism_stochastic": ("single", "multiple"),
    "observed_daymet": ("single", "multiple", "interpolated"),
    "observed_gridmet": ("single", "multiple", "interpolated"),
    "eobs_modified": ("single", "multiple"),
    "agdc": ("single", "multiple"),
})
_CLIMATE_STATION_DEFAULTS: typing.Mapping[str, str] = MappingProxyType({
    source: "auto" for source in _CLIMATE_STATION_RELATIONS
})
_CLIMATE_SPATIAL_DEFAULTS: typing.Mapping[str, str] = MappingProxyType({
    "vanilla_cligen": "single",
    "prism_stochastic": "single",
    "observed_daymet": "single",
    "observed_gridmet": "single",
    "eobs_modified": "multiple",
    "agdc": "single",
})


@dataclass(frozen=True, slots=True)
class _ProfileContract:
    profile_id: str
    dem_sources: tuple[str, ...]
    soil_sources: tuple[str, ...]
    landuse_sources: tuple[str, ...]
    climate_sources: tuple[str, ...]
    climate_station_databases: tuple[str, ...]
    default_dem: str
    default_soil: str
    default_landuse: str
    default_station_database: str


_C3S_IDS = tuple(f"c3s-landcover-{year}" for year in range(2020, 1991, -1))
_PROFILE_CONTRACTS: typing.Mapping[str, _ProfileContract] = MappingProxyType({
    "continental-us": _ProfileContract(
        "continental-us",
        ("usgs-ned1-2024", "usgs-ned13-2022"),
        ("ssurgo-gnatsgso-2025",),
        tuple(
            [f"nlcd-ever-forest-{year}" for year in range(2024, 1984, -1)]
            + [f"nlcd-{year}" for year in range(2024, 1984, -1)]
            + [f"emapr-vote-{year}" for year in range(2017, 1983, -1)]
        ),
        (*_V2_CLIMATE_IDS, "dep_nexrad", "future_cmip5", "user_defined_cli"),
        ("cligen-stations-legacy", "cligen-stations-2015", "cligen-stations-ghcn"),
        "usgs-ned1-2024",
        "ssurgo-gnatsgso-2025",
        "nlcd-2019",
        "cligen-stations-2015",
    ),
    "europe": _ProfileContract(
        "europe",
        ("europe-eudem-v1-1",),
        ("esdac-europe",),
        ("corine-1990", "corine-2000", "corine-2006", "corine-2012", "corine-2018"),
        ("vanilla_cligen", "eobs_modified", "user_defined_cli"),
        ("cligen-stations-ghcn",),
        "europe-eudem-v1-1",
        "esdac-europe",
        "corine-2018",
        "cligen-stations-ghcn",
    ),
    "canada": _ProfileContract(
        "canada",
        ("copernicus-dem-30",),
        ("isric-global",),
        _C3S_IDS,
        ("vanilla_cligen", "observed_daymet", "user_defined_cli"),
        ("cligen-stations-ghcn",),
        "copernicus-dem-30",
        "isric-global",
        "c3s-landcover-2020",
        "cligen-stations-ghcn",
    ),
    "australia": _ProfileContract(
        "australia",
        ("australia-srtm-1s",),
        ("asris-australia",),
        ("australia-landuse-2010-2011",),
        ("vanilla_cligen", "agdc", "user_defined_cli"),
        ("cligen-stations-ghcn",),
        "australia-srtm-1s",
        "asris-australia",
        "australia-landuse-2010-2011",
        "cligen-stations-ghcn",
    ),
    "global-earth": _ProfileContract(
        "global-earth",
        ("copernicus-dem-30",),
        ("isric-global",),
        _C3S_IDS,
        ("vanilla_cligen", "user_defined_cli"),
        ("cligen-stations-ghcn",),
        "copernicus-dem-30",
        "isric-global",
        "c3s-landcover-2020",
        "cligen-stations-ghcn",
    ),
})


class CapabilityGraphError(ValueError):
    """Raised when a capability graph is partial or contradictory."""


@dataclass(frozen=True, slots=True)
class _CapabilityStructureRecord:
    schema_version: int
    locale_profile: str
    structure_sha256: str
    canonical_payload: str
    first_reader_revision: str


_StructureCatalog = typing.Mapping[
    tuple[int, str],
    typing.Mapping[str, _CapabilityStructureRecord],
]


def _freeze_map(values: typing.Mapping[str, tuple[str, ...]]) -> typing.Mapping[str, tuple[str, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def _freeze_defaults(values: typing.Mapping[str, str]) -> typing.Mapping[str, str]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True, slots=True)
class CapabilityGraph:
    schema_version: int
    locale_profiles: tuple[str, ...]
    dem_sources: tuple[str, ...]
    climate_datasets: tuple[str, ...]
    climate_station_databases: tuple[str, ...]
    climate_station_methods: tuple[str, ...]
    climate_spatial_methods: tuple[str, ...]
    soil_datasets: tuple[str, ...]
    soil_builders: tuple[str, ...]
    landuse_datasets: tuple[str, ...]
    landuse_methods: tuple[str, ...]
    delineation_backends: tuple[str, ...]
    watershed_representations: tuple[str, ...]
    wepp_binaries: tuple[str, ...]
    wepp_binary_revisions: typing.Mapping[str, str]
    mods: tuple[str, ...]
    allowed_model_tuples: tuple[str, ...]
    climate_station_methods_by_dataset: typing.Mapping[str, tuple[str, ...]]
    climate_spatial_methods_by_dataset: typing.Mapping[str, tuple[str, ...]]
    climate_station_defaults: typing.Mapping[str, str]
    climate_spatial_defaults: typing.Mapping[str, str]
    landuse_methods_by_dataset: typing.Mapping[str, tuple[str, ...]]
    landuse_method_defaults: typing.Mapping[str, str]
    landuse_methods_by_representation: typing.Mapping[str, tuple[str, ...]]
    soil_builders_by_dataset: typing.Mapping[str, tuple[str, ...]]
    soil_builder_defaults: typing.Mapping[str, str]
    mod_requires: typing.Mapping[str, tuple[str, ...]]
    mod_conflicts: typing.Mapping[str, tuple[str, ...]]
    defaults: typing.Mapping[str, str]
    provider_revision: str

    def with_defaults(self, **updates: str) -> "CapabilityGraph":
        values = dict(self.defaults)
        values.update(updates)
        graph = replace(self, defaults=_freeze_defaults(values))
        graph.validate()
        return graph

    def validate(self) -> None:
        if self.schema_version not in {
            HISTORICAL_CAPABILITY_SCHEMA_VERSION,
            CAPABILITY_SCHEMA_VERSION,
        }:
            raise CapabilityGraphError("unsupported capability schema version")
        axes = {
            "locale_profiles": self.locale_profiles,
            "dem_sources": self.dem_sources,
            "climate_datasets": self.climate_datasets,
            "climate_station_databases": self.climate_station_databases,
            "climate_station_methods": self.climate_station_methods,
            "climate_spatial_methods": self.climate_spatial_methods,
            "soil_datasets": self.soil_datasets,
            "soil_builders": self.soil_builders,
            "landuse_datasets": self.landuse_datasets,
            "landuse_methods": self.landuse_methods,
            "delineation_backends": self.delineation_backends,
            "watershed_representations": self.watershed_representations,
            "wepp_binaries": self.wepp_binaries,
            "mods": self.mods,
        }
        for axis, values in axes.items():
            may_be_empty = axis == "mods" or (
                axis == "climate_station_databases"
                and self.schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
            )
            if not may_be_empty and not values:
                raise CapabilityGraphError(f"{axis} must not be empty")
            if len(values) > _MAX_VALUES or len(set(values)) != len(values):
                raise CapabilityGraphError(f"{axis} contains too many or duplicate IDs")
            if any(_ID_RE.fullmatch(value) is None for value in values):
                raise CapabilityGraphError(f"{axis} contains an invalid stable ID")
        if any(
            value != "latest" and re.fullmatch(r"wepp_[a-z0-9][a-z0-9_-]{0,122}", value) is None
            for value in self.wepp_binaries
        ):
            raise CapabilityGraphError("wepp_binaries contains an unknown domain ID")
        known_domains = {
            "climate_station_databases": _KNOWN_STATION_DATABASES,
            "climate_station_methods": _KNOWN_STATION_METHODS,
            "climate_spatial_methods": _KNOWN_SPATIAL_METHODS,
            "soil_builders": frozenset(_SOIL_BUILDERS),
            "landuse_methods": frozenset(_LANDUSE_METHODS),
            "delineation_backends": frozenset(_DELINEATION_BACKENDS),
            "watershed_representations": frozenset(_WATERSHED_REPRESENTATIONS),
            "mods": _KNOWN_MOD_IDS,
        }
        for axis, known_values in known_domains.items():
            if not set(axes[axis]).issubset(known_values):
                raise CapabilityGraphError(f"{axis} contains an unknown domain ID")

        self._validate_adjacency(
            "climate_station_methods", self.climate_station_methods_by_dataset,
            self.climate_datasets, self.climate_station_methods,
        )
        self._validate_adjacency(
            "climate_spatial_methods", self.climate_spatial_methods_by_dataset,
            self.climate_datasets, self.climate_spatial_methods,
        )
        self._validate_defaults(
            "climate_station_defaults", self.climate_station_defaults,
            self.climate_station_methods_by_dataset,
        )
        self._validate_defaults(
            "climate_spatial_defaults", self.climate_spatial_defaults,
            self.climate_spatial_methods_by_dataset,
        )
        self._validate_adjacency(
            "landuse_methods", self.landuse_methods_by_dataset,
            self.landuse_datasets, self.landuse_methods,
        )
        self._validate_defaults(
            "landuse_method_defaults", self.landuse_method_defaults,
            self.landuse_methods_by_dataset,
        )
        self._validate_adjacency(
            "landuse_methods_by_representation", self.landuse_methods_by_representation,
            self.watershed_representations, self.landuse_methods,
        )
        self._validate_adjacency(
            "soil_builders", self.soil_builders_by_dataset,
            self.soil_datasets, self.soil_builders,
        )
        self._validate_defaults(
            "soil_builder_defaults", self.soil_builder_defaults,
            self.soil_builders_by_dataset,
        )
        self._validate_mod_relations()
        self._validate_provider_and_model_policy()
        for key, axis_values in (
            ("locale_profile", self.locale_profiles),
            ("dem_source", self.dem_sources),
            ("climate_dataset", self.climate_datasets),
            ("soil_dataset", self.soil_datasets),
            ("landuse_dataset", self.landuse_datasets),
        ):
            if self.defaults.get(key) not in axis_values:
                raise CapabilityGraphError(f"capability default {key!r} is not advertised")
        if self.schema_version == CAPABILITY_SCHEMA_VERSION:
            if self.defaults.get("climate_station_database") not in self.climate_station_databases:
                raise CapabilityGraphError(
                    "capability default 'climate_station_database' is not advertised"
                )
        elif "climate_station_database" in self.defaults:
            raise CapabilityGraphError("schema-v2 must not contain a station-database default")
        expected_default_keys = {
            "locale_profile", "dem_source", "climate_dataset", "soil_dataset",
            "landuse_dataset", "delineation_backend", "watershed_representation",
            "wepp_binary",
        }
        if self.schema_version == CAPABILITY_SCHEMA_VERSION:
            expected_default_keys.add("climate_station_database")
        if set(self.defaults) != expected_default_keys:
            raise CapabilityGraphError("capability default keys do not match the schema")
        _validate_cataloged_structure(self)
        serialized = json.dumps(self.as_config_sections(), sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _MAX_SERIALIZED_BYTES:
            raise CapabilityGraphError("serialized capability graph exceeds 4 MiB")

    @staticmethod
    def _validate_adjacency(
        name: str,
        relation: typing.Mapping[str, tuple[str, ...]],
        keys: tuple[str, ...],
        targets: tuple[str, ...],
    ) -> None:
        if set(relation) != set(keys):
            raise CapabilityGraphError(f"{name} keys do not exhaust their source axis")
        for values in relation.values():
            if not values or len(values) > _MAX_VALUES or len(set(values)) != len(values):
                raise CapabilityGraphError(f"{name} contains an empty or duplicate relation")
            if not set(values).issubset(targets):
                raise CapabilityGraphError(f"{name} references an unknown target")
        used_targets = {value for values in relation.values() for value in values}
        if used_targets != set(targets):
            raise CapabilityGraphError(f"{name} leaves an advertised target orphaned")

    @staticmethod
    def _validate_defaults(
        name: str,
        defaults: typing.Mapping[str, str],
        relation: typing.Mapping[str, tuple[str, ...]],
    ) -> None:
        if set(defaults) != set(relation):
            raise CapabilityGraphError(f"{name} keys do not exhaust their source axis")
        if any(defaults[key] not in relation[key] for key in defaults):
            raise CapabilityGraphError(f"{name} contains a default outside its relation")

    def _validate_mod_relations(self) -> None:
        if set(self.mod_requires) != set(self.mods) or set(self.mod_conflicts) != set(self.mods):
            raise CapabilityGraphError("mod relation keys must exhaust the mods axis")
        relation_axes = {
            "climate_dataset": self.climate_datasets,
            "climate_station_database": self.climate_station_databases,
            "climate_station_method": self.climate_station_methods,
            "climate_spatial_method": self.climate_spatial_methods,
            "landuse_dataset": self.landuse_datasets,
            "landuse_method": self.landuse_methods,
            "soil_dataset": self.soil_datasets,
            "soil_builder": self.soil_builders,
            "delineation_backend": self.delineation_backends,
            "watershed_representation": self.watershed_representations,
            "wepp_binary": self.wepp_binaries,
            "mod": self.mods,
        }
        if self.schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION:
            relation_axes.pop("climate_station_database")
        for relation_name, relation in (
            ("mod_requires", self.mod_requires),
            ("mod_conflicts", self.mod_conflicts),
        ):
            for values in relation.values():
                if (
                    (relation_name == "mod_requires" and not values)
                    or len(values) > _MAX_VALUES
                    or len(set(values)) != len(values)
                ):
                    raise CapabilityGraphError(f"{relation_name} contains too many or duplicate IDs")
                for token in values:
                    parts = token.split(":")
                    if len(parts) != 2:
                        raise CapabilityGraphError(
                            f"{relation_name} contains a malformed relation token"
                        )
                    axis, target = parts
                    if axis not in relation_axes:
                        raise CapabilityGraphError(
                            f"{relation_name} references an unknown relation axis"
                        )
                    if _ID_RE.fullmatch(target) is None or target not in relation_axes[axis]:
                        raise CapabilityGraphError(
                            f"{relation_name} references an unknown relation target"
                        )
        if any(f"mod:{mod}" in self.mod_conflicts.get(mod, ()) for mod in self.mods):
            raise CapabilityGraphError("a mod must not conflict with itself")
        for mod in self.mods:
            if set(self.mod_requires.get(mod, ())).intersection(self.mod_conflicts.get(mod, ())):
                raise CapabilityGraphError("a mod relation must not both require and conflict")

    def _validate_provider_and_model_policy(self) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", self.provider_revision) is None:
            raise CapabilityGraphError("provider_revision must be a lowercase SHA-256 identity")
        if set(self.wepp_binary_revisions) != set(self.wepp_binaries):
            raise CapabilityGraphError("wepp_binary_revisions keys must exhaust the binary axis")
        role_pattern = re.compile(
            r"^provider-v1:watershed=[0-9a-f]{64}:hillslope=[0-9a-f]{64}$"
        )
        if any(role_pattern.fullmatch(value) is None for value in self.wepp_binary_revisions.values()):
            raise CapabilityGraphError("wepp_binary_revisions contains an invalid role identity")
        if len(self.allowed_model_tuples) > _MAX_VALUES:
            raise CapabilityGraphError("allowed_model_tuples contains too many IDs")
        allowed: set[tuple[str, str, str]] = set()
        for token in self.allowed_model_tuples:
            parts = tuple(token.split("|"))
            if len(parts) != 3:
                raise CapabilityGraphError("allowed_model_tuples contains a malformed tuple")
            backend, representation, binary = parts
            if (
                backend not in self.delineation_backends
                or representation not in self.watershed_representations
                or binary not in self.wepp_binaries
            ):
                raise CapabilityGraphError("allowed_model_tuples references an unknown ID")
            allowed.add((backend, representation, binary))
        if len(allowed) != len(self.allowed_model_tuples):
            raise CapabilityGraphError("allowed_model_tuples contains duplicates")
        for values, index in (
            (self.delineation_backends, 0),
            (self.watershed_representations, 1),
            (self.wepp_binaries, 2),
        ):
            if any(not any(item[index] == value for item in allowed) for value in values):
                raise CapabilityGraphError("an advertised model value has no valid tuple")
        default_tuple = (
            self.defaults.get("delineation_backend", ""),
            self.defaults.get("watershed_representation", ""),
            self.defaults.get("wepp_binary", ""),
        )
        if default_tuple not in allowed:
            raise CapabilityGraphError("capability defaults do not identify a valid model tuple")
        expected_model = {
            (backend, "single-ofe", binary)
            for binary in self.wepp_binaries
            for backend in _DELINEATION_BACKENDS
        }
        expected_model.add(("wbt", "multiple-ofe", "wepp_260803"))
        if allowed != expected_model:
            raise CapabilityGraphError("model tuple set violates the Builder binary policy")

    def as_config_sections(self) -> dict[str, dict[str, CanonicalValue]]:
        """Return canonical config sections for project materialization."""

        capabilities: dict[str, CanonicalValue] = {
            "schema_version": self.schema_version,
            "locale_profiles": list(self.locale_profiles),
            "dem_sources": list(self.dem_sources),
            "climate_datasets": list(self.climate_datasets),
            "climate_station_methods": list(self.climate_station_methods),
            "climate_spatial_methods": list(self.climate_spatial_methods),
            "soil_datasets": list(self.soil_datasets),
            "soil_builders": list(self.soil_builders),
            "landuse_datasets": list(self.landuse_datasets),
            "landuse_methods": list(self.landuse_methods),
            "delineation_backends": list(self.delineation_backends),
            "watershed_representations": list(self.watershed_representations),
            "wepp_binaries": list(self.wepp_binaries),
            "mods": list(self.mods),
            "allowed_model_tuples": list(self.allowed_model_tuples),
            "provider_revision": self.provider_revision,
        }
        if self.schema_version == CAPABILITY_SCHEMA_VERSION:
            capabilities["climate_station_databases"] = list(self.climate_station_databases)
        return {
            "capabilities": capabilities,
            "capabilities.climate_station_methods": {
                key: list(value) for key, value in self.climate_station_methods_by_dataset.items()
            },
            "capabilities.climate_spatial_methods": {
                key: list(value) for key, value in self.climate_spatial_methods_by_dataset.items()
            },
            "capabilities.climate_station_defaults": dict(self.climate_station_defaults),
            "capabilities.climate_spatial_defaults": dict(self.climate_spatial_defaults),
            "capabilities.landuse_methods": {
                key: list(value) for key, value in self.landuse_methods_by_dataset.items()
            },
            "capabilities.landuse_method_defaults": dict(self.landuse_method_defaults),
            "capabilities.landuse_methods_by_representation": {
                key: list(value) for key, value in self.landuse_methods_by_representation.items()
            },
            "capabilities.soil_builders": {
                key: list(value) for key, value in self.soil_builders_by_dataset.items()
            },
            "capabilities.soil_builder_defaults": dict(self.soil_builder_defaults),
            "capabilities.wepp_binary_revisions": dict(self.wepp_binary_revisions),
            "capabilities.mod_requires": {
                key: list(value) for key, value in self.mod_requires.items()
            },
            "capabilities.mod_conflicts": {
                key: list(value) for key, value in self.mod_conflicts.items()
            },
            "capability_defaults": dict(self.defaults),
        }


def capability_structure_payload(graph: CapabilityGraph) -> dict[str, object]:
    """Return the selection/provider-independent structural contract payload."""

    allowed_model_pairs = sorted({
        (backend, representation)
        for backend, representation, _binary in (
            tuple(token.split("|")) for token in graph.allowed_model_tuples
        )
    })
    return {
        "schema_version": graph.schema_version,
        "locale_profile": graph.locale_profiles[0] if len(graph.locale_profiles) == 1 else "",
        "axes": {
            "dem_sources": list(graph.dem_sources),
            "climate_datasets": list(graph.climate_datasets),
            "climate_station_databases": list(graph.climate_station_databases),
            "climate_station_methods": list(graph.climate_station_methods),
            "climate_spatial_methods": list(graph.climate_spatial_methods),
            "soil_datasets": list(graph.soil_datasets),
            "soil_builders": list(graph.soil_builders),
            "landuse_datasets": list(graph.landuse_datasets),
            "landuse_methods": list(graph.landuse_methods),
            "delineation_backends": list(graph.delineation_backends),
            "watershed_representations": list(graph.watershed_representations),
            "mods": list(graph.mods),
        },
        "relations": {
            "climate_station_methods": {
                key: list(values)
                for key, values in graph.climate_station_methods_by_dataset.items()
            },
            "climate_spatial_methods": {
                key: list(values)
                for key, values in graph.climate_spatial_methods_by_dataset.items()
            },
            "landuse_methods": {
                key: list(values) for key, values in graph.landuse_methods_by_dataset.items()
            },
            "landuse_methods_by_representation": {
                key: list(values)
                for key, values in graph.landuse_methods_by_representation.items()
            },
            "soil_builders": {
                key: list(values) for key, values in graph.soil_builders_by_dataset.items()
            },
            "mod_requires": {
                key: list(values) for key, values in graph.mod_requires.items()
            },
            "mod_conflicts": {
                key: list(values) for key, values in graph.mod_conflicts.items()
            },
        },
        "method_defaults": {
            "climate_station": dict(graph.climate_station_defaults),
            "climate_spatial": dict(graph.climate_spatial_defaults),
            "landuse": dict(graph.landuse_method_defaults),
            "soil": dict(graph.soil_builder_defaults),
        },
        "allowed_model_pairs": allowed_model_pairs,
    }


def _canonical_structure_payload(payload: typing.Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def capability_structure_sha256(graph: CapabilityGraph) -> str:
    """Return the deterministic structural identity for one capability graph."""

    canonical = _canonical_structure_payload(capability_structure_payload(graph))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _structure_record(
    payload: typing.Mapping[str, object],
    *,
    first_reader_revision: str,
    expected_sha256: str | None = None,
) -> _CapabilityStructureRecord:
    schema_version = payload.get("schema_version")
    locale_profile = payload.get("locale_profile")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise CapabilityGraphError("capability structure schema_version must be an integer")
    if not isinstance(locale_profile, str) or _ID_RE.fullmatch(locale_profile) is None:
        raise CapabilityGraphError("capability structure locale_profile must be a stable ID")
    canonical = _canonical_structure_payload(payload)
    calculated_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if expected_sha256 is not None and expected_sha256 != calculated_sha256:
        raise CapabilityGraphError("capability structure payload hash does not match its catalog")
    return _CapabilityStructureRecord(
        schema_version=schema_version,
        locale_profile=locale_profile,
        structure_sha256=calculated_sha256,
        canonical_payload=canonical,
        first_reader_revision=first_reader_revision,
    )


def _build_structure_catalog(
    payloads: tuple[typing.Mapping[str, object], ...],
) -> _StructureCatalog:
    """Build an isolated catalog for structural-reader tests."""

    mutable: dict[tuple[int, str], dict[str, _CapabilityStructureRecord]] = {}
    for payload in payloads:
        record = _structure_record(payload, first_reader_revision="test-only")
        key = (record.schema_version, record.locale_profile)
        records = mutable.setdefault(key, {})
        if record.structure_sha256 in records:
            raise CapabilityGraphError("duplicate capability structure identity")
        records[record.structure_sha256] = record
    return MappingProxyType({
        key: MappingProxyType(records) for key, records in mutable.items()
    })


def _load_structure_catalog() -> _StructureCatalog:
    catalog_path = Path(__file__).with_name("capability_structures") / "catalog.json"
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise CapabilityGraphError("unsupported capability structure catalog schema")
    entries = raw.get("structures")
    if not isinstance(entries, list) or not entries:
        raise CapabilityGraphError("capability structure catalog must not be empty")

    mutable: dict[tuple[int, str], dict[str, _CapabilityStructureRecord]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise CapabilityGraphError("capability structure catalog entry must be an object")
        payload = entry.get("payload")
        expected_sha256 = entry.get("structure_sha256")
        first_reader_revision = entry.get("first_reader_revision")
        if (
            not isinstance(payload, dict)
            or not isinstance(expected_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
            or not isinstance(first_reader_revision, str)
            or not first_reader_revision
        ):
            raise CapabilityGraphError("capability structure catalog entry is malformed")
        record = _structure_record(
            payload,
            first_reader_revision=first_reader_revision,
            expected_sha256=expected_sha256,
        )
        key = (record.schema_version, record.locale_profile)
        records = mutable.setdefault(key, {})
        if record.structure_sha256 in records:
            raise CapabilityGraphError("duplicate capability structure identity")
        records[record.structure_sha256] = record
    return MappingProxyType({
        key: MappingProxyType(records) for key, records in mutable.items()
    })


def _validate_cataloged_structure(
    graph: CapabilityGraph,
    catalog: _StructureCatalog | None = None,
) -> None:
    selected_catalog = _PRODUCTION_STRUCTURE_CATALOG if catalog is None else catalog
    if len(graph.locale_profiles) != 1:
        raise CapabilityGraphError("capability graph must identify exactly one locale profile")
    key = (graph.schema_version, graph.locale_profiles[0])
    records = selected_catalog.get(key, {})
    payload = capability_structure_payload(graph)
    canonical = _canonical_structure_payload(payload)
    structure_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    record = records.get(structure_sha256)
    if record is None or record.canonical_payload != canonical:
        raise CapabilityGraphError(
            f"unknown capability structure for schema {graph.schema_version} "
            f"locale {graph.locale_profiles[0]!r}"
        )


_PRODUCTION_STRUCTURE_CATALOG = _load_structure_catalog()


def _provider_revision(
    profile_id: str,
    wepp_binaries: tuple[str, ...],
    wepp_binary_revisions: typing.Mapping[str, str],
    climate_provider_tokens: typing.Mapping[str, str] | None,
) -> str:
    profile = get_locale_profile(profile_id)
    if profile is None:
        raise CapabilityGraphError(f"{profile_id} locale profile is missing")
    configured_tokens = (
        default_climate_provider_tokens()
        if climate_provider_tokens is None
        else dict(climate_provider_tokens)
    )
    payload = {
        "locale": locale_catalog_revision(),
        "climate": climate_catalog_revision(configured_tokens),
        "landcover": landcover_catalog_revision(),
        "profile_id": profile_id,
        "dem_sources": {
            source_id: DEM_SOURCE_RUNTIME[source_id] for source_id in profile.dem_sources
        },
        "soil_sources": {
            source_id: SOIL_SOURCE_RUNTIME[source_id] for source_id in profile.soil_sources
        },
        "soil_builder_adapter": "soils-builder-runtime-map-v2",
        "delineation_adapters": {
            "topaz": "watershed-backend-contract-v1:topaz",
            "wbt": "weppcloud-wbt-adapter-v1:wbt",
        },
        "representation_adapter": "wepp-representation-contract-v1",
        "wepp_binaries": wepp_binaries,
        "wepp_binary_revisions": dict(wepp_binary_revisions),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _model_tuples(wepp_binaries: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        f"{backend}|single-ofe|{binary_id}"
        for binary_id in wepp_binaries
        for backend in _DELINEATION_BACKENDS
    ) + ("wbt|multiple-ofe|wepp_260803",)


def _validate_wepp_provider(
    wepp_binaries: tuple[str, ...],
    wepp_binary_revisions: typing.Mapping[str, str],
) -> None:
    if not wepp_binaries or "wepp_260803" not in wepp_binaries:
        raise CapabilityGraphError("WEPP provider is missing required default wepp_260803")
    if set(wepp_binary_revisions) != set(wepp_binaries):
        raise CapabilityGraphError("WEPP provider role identities do not exhaust binary values")


def build_continental_us_capability_graph(
    wepp_binaries: tuple[str, ...],
    wepp_binary_revisions: typing.Mapping[str, str],
    *,
    climate_provider_tokens: typing.Mapping[str, str] | None = None,
) -> CapabilityGraph:
    """Build the frozen historical Continental-US schema-v2 graph."""

    _validate_wepp_provider(wepp_binaries, wepp_binary_revisions)
    climate_by_id = {item.catalog_id: item for item in iter_climate_datasets()}
    graph = CapabilityGraph(
        schema_version=HISTORICAL_CAPABILITY_SCHEMA_VERSION,
        locale_profiles=("continental-us",),
        dem_sources=("usgs-ned1-2024", "usgs-ned13-2022"),
        climate_datasets=_V2_CLIMATE_IDS,
        climate_station_databases=(),
        climate_station_methods=_V2_STATION_METHODS,
        climate_spatial_methods=_V2_SPATIAL_METHODS,
        soil_datasets=("ssurgo-gnatsgso-2025",),
        soil_builders=_SOIL_BUILDERS,
        landuse_datasets=("nlcd-2019",),
        landuse_methods=_LANDUSE_METHODS,
        delineation_backends=_DELINEATION_BACKENDS,
        watershed_representations=_WATERSHED_REPRESENTATIONS,
        wepp_binaries=wepp_binaries,
        wepp_binary_revisions=MappingProxyType(dict(wepp_binary_revisions)),
        mods=(),
        allowed_model_tuples=_model_tuples(wepp_binaries),
        climate_station_methods_by_dataset=_freeze_map(dict(_V2_STATION_RELATIONS)),
        climate_spatial_methods_by_dataset=_freeze_map(dict(_V2_SPATIAL_RELATIONS)),
        climate_station_defaults=_freeze_defaults({source: "auto" for source in _V2_CLIMATE_IDS}),
        climate_spatial_defaults=_freeze_defaults({source: "single" for source in _V2_CLIMATE_IDS}),
        landuse_methods_by_dataset=_freeze_map({"nlcd-2019": _LANDUSE_METHODS}),
        landuse_method_defaults=_freeze_defaults({"nlcd-2019": "gridded"}),
        landuse_methods_by_representation=_freeze_map({
            "single-ofe": _LANDUSE_METHODS,
            "multiple-ofe": ("gridded", "upload"),
        }),
        soil_builders_by_dataset=_freeze_map({"ssurgo-gnatsgso-2025": _SOIL_BUILDERS}),
        soil_builder_defaults=_freeze_defaults({"ssurgo-gnatsgso-2025": "gridded"}),
        mod_requires=_freeze_map({}),
        mod_conflicts=_freeze_map({}),
        defaults=_freeze_defaults({
            "locale_profile": "continental-us",
            "dem_source": "usgs-ned1-2024",
            "climate_dataset": "vanilla_cligen",
            "landuse_dataset": "nlcd-2019",
            "soil_dataset": "ssurgo-gnatsgso-2025",
            "delineation_backend": "wbt",
            "watershed_representation": "single-ofe",
            "wepp_binary": "wepp_260803",
        }),
        provider_revision=_provider_revision(
            "continental-us", wepp_binaries, wepp_binary_revisions, climate_provider_tokens
        ),
    )
    if any(source not in climate_by_id for source in graph.climate_datasets):
        raise CapabilityGraphError("continental-us climate descriptor is missing")
    graph.validate()
    return graph


def build_locale_capability_graph(
    profile_id: str,
    wepp_binaries: tuple[str, ...],
    wepp_binary_revisions: typing.Mapping[str, str],
    *,
    climate_provider_tokens: typing.Mapping[str, str] | None = None,
) -> CapabilityGraph:
    """Build the current schema-v3 graph for one exposed locale profile."""

    _validate_wepp_provider(wepp_binaries, wepp_binary_revisions)
    contract = _PROFILE_CONTRACTS.get(profile_id)
    profile = get_locale_profile(profile_id)
    if contract is None or profile is None or profile.support_state.value != "builder_exposed":
        raise CapabilityGraphError(f"locale profile {profile_id!r} is not Builder-exposed")
    if (
        profile.dem_sources != contract.dem_sources
        or profile.soil_sources != contract.soil_sources
        or profile.landuse_sources != contract.landuse_sources
        or profile.climate_sources != contract.climate_sources
        or profile.climate_station_databases != contract.climate_station_databases
    ):
        raise CapabilityGraphError(f"locale profile {profile_id!r} differs from its schema-v3 contract")
    climate_by_id = {item.catalog_id: item for item in iter_climate_datasets()}
    if any(source not in climate_by_id for source in contract.climate_sources):
        raise CapabilityGraphError(f"{profile_id} climate descriptor is missing")
    station_relations = {
        source: climate_by_id[source].station_method_ids for source in contract.climate_sources
    }
    spatial_relations = {
        source: climate_by_id[source].spatial_method_ids for source in contract.climate_sources
    }
    station_methods = tuple(dict.fromkeys(
        method for source in contract.climate_sources for method in station_relations[source]
    ))
    spatial_methods = tuple(dict.fromkeys(
        method for source in contract.climate_sources for method in spatial_relations[source]
    ))
    soil_builders = _SOIL_BUILDERS if profile_id == "continental-us" else ("gridded",)
    graph = CapabilityGraph(
        schema_version=CAPABILITY_SCHEMA_VERSION,
        locale_profiles=(profile_id,),
        dem_sources=contract.dem_sources,
        climate_datasets=contract.climate_sources,
        climate_station_databases=contract.climate_station_databases,
        climate_station_methods=station_methods,
        climate_spatial_methods=spatial_methods,
        soil_datasets=contract.soil_sources,
        soil_builders=soil_builders,
        landuse_datasets=contract.landuse_sources,
        landuse_methods=_LANDUSE_METHODS,
        delineation_backends=_DELINEATION_BACKENDS,
        watershed_representations=_WATERSHED_REPRESENTATIONS,
        wepp_binaries=wepp_binaries,
        wepp_binary_revisions=MappingProxyType(dict(wepp_binary_revisions)),
        mods=(),
        allowed_model_tuples=_model_tuples(wepp_binaries),
        climate_station_methods_by_dataset=_freeze_map(station_relations),
        climate_spatial_methods_by_dataset=_freeze_map(spatial_relations),
        climate_station_defaults=_freeze_defaults({
            source: climate_by_id[source].default_station_method_id
            for source in contract.climate_sources
        }),
        climate_spatial_defaults=_freeze_defaults({
            source: climate_by_id[source].default_spatial_method_id
            for source in contract.climate_sources
        }),
        landuse_methods_by_dataset=_freeze_map({
            source: _LANDUSE_METHODS for source in contract.landuse_sources
        }),
        landuse_method_defaults=_freeze_defaults({
            source: "gridded" for source in contract.landuse_sources
        }),
        landuse_methods_by_representation=_freeze_map({
            "single-ofe": _LANDUSE_METHODS,
            "multiple-ofe": ("gridded", "upload"),
        }),
        soil_builders_by_dataset=_freeze_map({
            source: soil_builders for source in contract.soil_sources
        }),
        soil_builder_defaults=_freeze_defaults({
            source: "gridded" for source in contract.soil_sources
        }),
        mod_requires=_freeze_map({}),
        mod_conflicts=_freeze_map({}),
        defaults=_freeze_defaults({
            "locale_profile": profile_id,
            "dem_source": contract.default_dem,
            "climate_dataset": "vanilla_cligen",
            "climate_station_database": contract.default_station_database,
            "soil_dataset": contract.default_soil,
            "landuse_dataset": contract.default_landuse,
            "delineation_backend": "wbt",
            "watershed_representation": "single-ofe",
            "wepp_binary": "wepp_260803",
        }),
        provider_revision=_provider_revision(
            profile_id, wepp_binaries, wepp_binary_revisions, climate_provider_tokens
        ),
    )
    graph.validate()
    return graph
