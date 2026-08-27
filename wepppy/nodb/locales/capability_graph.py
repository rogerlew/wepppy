"""Typed schema-v2 locale capability graph construction and validation."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping

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
    "CapabilityGraph",
    "CapabilityGraphError",
    "build_continental_us_capability_graph",
]

CAPABILITY_SCHEMA_VERSION = 2
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,127}$")
_MAX_VALUES = 4096
_MAX_SERIALIZED_BYTES = 4 * 1024 * 1024
_CLIMATE_IDS = (
    "vanilla_cligen",
    "prism_stochastic",
    "observed_daymet",
    "observed_gridmet",
)
_SOIL_BUILDERS = ("gridded", "single_mukey", "single_database")
_LANDUSE_METHODS = ("gridded", "single", "upload")
_DELINEATION_BACKENDS = ("topaz", "wbt")
_WATERSHED_REPRESENTATIONS = ("single-ofe", "multiple-ofe")
_CONTINENTAL_US_LOCALE_PROFILES = ("continental-us",)
_CONTINENTAL_US_DEM_SOURCES = ("usgs-ned1-2024", "usgs-ned13-2022")
_CONTINENTAL_US_SOIL_DATASETS = ("ssurgo-gnatsgso-2025",)
_CONTINENTAL_US_LANDUSE_DATASETS = ("nlcd-2019",)
_CONTINENTAL_US_CLIMATE_STATION_METHODS = ("auto", "distance", "multi_factor")
_CONTINENTAL_US_CLIMATE_SPATIAL_METHODS = ("single", "multiple", "interpolated")
_V2_KNOWN_CLIMATE_STATION_METHODS = frozenset({
    "auto", "distance", "multi_factor", "eu_heuristic", "au_heuristic", "user_defined",
})
_CONTINENTAL_US_CLIMATE_STATION_RELATIONS = MappingProxyType({
    catalog_id: _CONTINENTAL_US_CLIMATE_STATION_METHODS
    for catalog_id in _CLIMATE_IDS
})
_CONTINENTAL_US_CLIMATE_SPATIAL_RELATIONS = MappingProxyType({
    "vanilla_cligen": ("single", "multiple"),
    "prism_stochastic": ("single", "multiple"),
    "observed_daymet": _CONTINENTAL_US_CLIMATE_SPATIAL_METHODS,
    "observed_gridmet": _CONTINENTAL_US_CLIMATE_SPATIAL_METHODS,
})
_CONTINENTAL_US_CLIMATE_STATION_DEFAULTS = MappingProxyType({
    catalog_id: "auto" for catalog_id in _CLIMATE_IDS
})
_CONTINENTAL_US_CLIMATE_SPATIAL_DEFAULTS = MappingProxyType({
    catalog_id: "single" for catalog_id in _CLIMATE_IDS
})
_V2_KNOWN_MOD_IDS = frozenset({
    "ag_fields", "ash", "baer", "debris_flow", "disturbed", "general", "lt",
    "omni", "portland", "rangeland_cover", "rap", "rap_ts", "revegetation",
    "rhem", "rred", "seattle", "shrubland", "swat", "treatments", "treecanopy",
    "turkey",
})


class CapabilityGraphError(ValueError):
    """Raised when a capability graph is partial or contradictory."""


def _freeze_map(values: Mapping[str, tuple[str, ...]]) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def _freeze_defaults(values: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True, slots=True)
class CapabilityGraph:
    schema_version: int
    locale_profiles: tuple[str, ...]
    dem_sources: tuple[str, ...]
    climate_datasets: tuple[str, ...]
    climate_station_methods: tuple[str, ...]
    climate_spatial_methods: tuple[str, ...]
    soil_datasets: tuple[str, ...]
    soil_builders: tuple[str, ...]
    landuse_datasets: tuple[str, ...]
    landuse_methods: tuple[str, ...]
    delineation_backends: tuple[str, ...]
    watershed_representations: tuple[str, ...]
    wepp_binaries: tuple[str, ...]
    wepp_binary_revisions: Mapping[str, str]
    mods: tuple[str, ...]
    allowed_model_tuples: tuple[str, ...]
    climate_station_methods_by_dataset: Mapping[str, tuple[str, ...]]
    climate_spatial_methods_by_dataset: Mapping[str, tuple[str, ...]]
    climate_station_defaults: Mapping[str, str]
    climate_spatial_defaults: Mapping[str, str]
    landuse_methods_by_dataset: Mapping[str, tuple[str, ...]]
    landuse_method_defaults: Mapping[str, str]
    landuse_methods_by_representation: Mapping[str, tuple[str, ...]]
    soil_builders_by_dataset: Mapping[str, tuple[str, ...]]
    soil_builder_defaults: Mapping[str, str]
    mod_requires: Mapping[str, tuple[str, ...]]
    mod_conflicts: Mapping[str, tuple[str, ...]]
    defaults: Mapping[str, str]
    provider_revision: str

    def with_defaults(self, **updates: str) -> "CapabilityGraph":
        values = dict(self.defaults)
        values.update(updates)
        graph = replace(self, defaults=_freeze_defaults(values))
        graph.validate()
        return graph

    def validate(self) -> None:
        if self.schema_version != CAPABILITY_SCHEMA_VERSION:
            raise CapabilityGraphError("unsupported capability schema version")
        axes = {
            "locale_profiles": self.locale_profiles,
            "dem_sources": self.dem_sources,
            "climate_datasets": self.climate_datasets,
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
            if axis != "mods" and not values:
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
        closed_domain_axes = {
            "locale_profiles": set(_CONTINENTAL_US_LOCALE_PROFILES),
            "dem_sources": set(_CONTINENTAL_US_DEM_SOURCES),
            "climate_datasets": set(_CLIMATE_IDS),
            "climate_station_methods": set(_V2_KNOWN_CLIMATE_STATION_METHODS),
            "climate_spatial_methods": set(_CONTINENTAL_US_CLIMATE_SPATIAL_METHODS),
            "soil_builders": set(_SOIL_BUILDERS),
            "soil_datasets": set(_CONTINENTAL_US_SOIL_DATASETS),
            "landuse_datasets": set(_CONTINENTAL_US_LANDUSE_DATASETS),
            "landuse_methods": set(_LANDUSE_METHODS),
            "delineation_backends": set(_DELINEATION_BACKENDS),
            "watershed_representations": set(_WATERSHED_REPRESENTATIONS),
            "mods": set(_V2_KNOWN_MOD_IDS),
        }
        for axis, known_values in closed_domain_axes.items():
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
            "landuse_methods_by_representation",
            self.landuse_methods_by_representation,
            self.watershed_representations,
            self.landuse_methods,
        )
        self._validate_adjacency(
            "soil_builders", self.soil_builders_by_dataset,
            self.soil_datasets, self.soil_builders,
        )
        self._validate_defaults(
            "soil_builder_defaults", self.soil_builder_defaults,
            self.soil_builders_by_dataset,
        )
        if set(self.mod_requires) != set(self.mods) or set(self.mod_conflicts) != set(self.mods):
            raise CapabilityGraphError("mod relation keys must exhaust the mods axis")
        relation_axes = {
            "climate_dataset": self.climate_datasets,
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
            if set(self.mod_requires.get(mod, ())).intersection(
                self.mod_conflicts.get(mod, ())
            ):
                raise CapabilityGraphError("a mod relation must not both require and conflict")
        if re.fullmatch(r"[0-9a-f]{64}", self.provider_revision) is None:
            raise CapabilityGraphError("provider_revision must be a lowercase SHA-256 identity")
        if set(self.wepp_binary_revisions) != set(self.wepp_binaries):
            raise CapabilityGraphError("wepp_binary_revisions keys must exhaust the binary axis")
        role_revision_pattern = re.compile(
            r"^provider-v1:watershed=[0-9a-f]{64}:hillslope=[0-9a-f]{64}$"
        )
        if any(
            role_revision_pattern.fullmatch(revision) is None
            for revision in self.wepp_binary_revisions.values()
        ):
            raise CapabilityGraphError("wepp_binary_revisions contains an invalid role identity")

        if len(self.allowed_model_tuples) > _MAX_VALUES:
            raise CapabilityGraphError("allowed_model_tuples contains too many IDs")
        allowed_tuples: set[tuple[str, str, str]] = set()
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
            allowed_tuples.add((backend, representation, binary))
        if len(allowed_tuples) != len(self.allowed_model_tuples):
            raise CapabilityGraphError("allowed_model_tuples contains duplicates")
        for axis_values, index in (
            (self.delineation_backends, 0),
            (self.watershed_representations, 1),
            (self.wepp_binaries, 2),
        ):
            if any(not any(item[index] == value for item in allowed_tuples) for value in axis_values):
                raise CapabilityGraphError("an advertised model value has no valid tuple")
        default_tuple = (
            self.defaults.get("delineation_backend", ""),
            self.defaults.get("watershed_representation", ""),
            self.defaults.get("wepp_binary", ""),
        )
        if default_tuple not in allowed_tuples:
            raise CapabilityGraphError("capability defaults do not identify a valid model tuple")
        for key, axis in (
            ("locale_profile", self.locale_profiles),
            ("dem_source", self.dem_sources),
            ("climate_dataset", self.climate_datasets),
            ("soil_dataset", self.soil_datasets),
            ("landuse_dataset", self.landuse_datasets),
        ):
            if self.defaults.get(key) not in axis:
                raise CapabilityGraphError(f"capability default {key!r} is not advertised")
        self._validate_builder_profile_contract()
        serialized = json.dumps(self.as_config_sections(), sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _MAX_SERIALIZED_BYTES:
            raise CapabilityGraphError("serialized capability graph exceeds 4 MiB")

    @staticmethod
    def _validate_adjacency(
        name: str,
        relation: Mapping[str, tuple[str, ...]],
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
        defaults: Mapping[str, str],
        relation: Mapping[str, tuple[str, ...]],
    ) -> None:
        if set(defaults) != set(relation):
            raise CapabilityGraphError(f"{name} keys do not exhaust their source axis")
        if any(defaults[key] not in relation[key] for key in defaults):
            raise CapabilityGraphError(f"{name} contains a default outside its relation")

    def _validate_builder_profile_contract(self) -> None:
        """Validate against immutable schema-v2 rules, independent of live catalogs."""

        expected_axes = {
            "locale_profiles": _CONTINENTAL_US_LOCALE_PROFILES,
            "dem_sources": _CONTINENTAL_US_DEM_SOURCES,
            "climate_datasets": _CLIMATE_IDS,
            "climate_station_methods": _CONTINENTAL_US_CLIMATE_STATION_METHODS,
            "climate_spatial_methods": _CONTINENTAL_US_CLIMATE_SPATIAL_METHODS,
            "soil_datasets": _CONTINENTAL_US_SOIL_DATASETS,
            "soil_builders": _SOIL_BUILDERS,
            "landuse_datasets": _CONTINENTAL_US_LANDUSE_DATASETS,
            "landuse_methods": _LANDUSE_METHODS,
            "delineation_backends": _DELINEATION_BACKENDS,
            "watershed_representations": _WATERSHED_REPRESENTATIONS,
            "mods": (),
        }
        for axis, expected in expected_axes.items():
            if tuple(getattr(self, axis)) != tuple(expected):
                raise CapabilityGraphError(
                    f"{axis} is not authorized by the continental-us Builder profile"
                )

        if dict(self.climate_station_methods_by_dataset) != dict(
            _CONTINENTAL_US_CLIMATE_STATION_RELATIONS
        ):
            raise CapabilityGraphError(
                "climate station adjacency is not authorized by the continental-us profile"
            )
        if dict(self.climate_spatial_methods_by_dataset) != dict(
            _CONTINENTAL_US_CLIMATE_SPATIAL_RELATIONS
        ):
            raise CapabilityGraphError(
                "climate spatial adjacency is not authorized by the continental-us profile"
            )
        if dict(self.climate_station_defaults) != dict(
            _CONTINENTAL_US_CLIMATE_STATION_DEFAULTS
        ):
            raise CapabilityGraphError(
                "climate station defaults are not authorized by the continental-us profile"
            )
        if dict(self.climate_spatial_defaults) != dict(
            _CONTINENTAL_US_CLIMATE_SPATIAL_DEFAULTS
        ):
            raise CapabilityGraphError(
                "climate spatial defaults are not authorized by the continental-us profile"
            )
        if dict(self.landuse_methods_by_dataset) != {"nlcd-2019": _LANDUSE_METHODS}:
            raise CapabilityGraphError(
                "landuse dataset adjacency is not authorized by the continental-us profile"
            )
        if dict(self.landuse_methods_by_representation) != {
            "single-ofe": _LANDUSE_METHODS,
            "multiple-ofe": ("gridded", "upload"),
        }:
            raise CapabilityGraphError(
                "landuse representation adjacency is not authorized by the continental-us profile"
            )
        if dict(self.soil_builders_by_dataset) != {
            "ssurgo-gnatsgso-2025": _SOIL_BUILDERS
        }:
            raise CapabilityGraphError(
                "soil builder adjacency is not authorized by the continental-us profile"
            )
        if dict(self.landuse_method_defaults) != {"nlcd-2019": "gridded"}:
            raise CapabilityGraphError(
                "landuse method defaults are not authorized by the continental-us profile"
            )
        if dict(self.soil_builder_defaults) != {"ssurgo-gnatsgso-2025": "gridded"}:
            raise CapabilityGraphError(
                "soil builder defaults are not authorized by the continental-us profile"
            )

        expected_model_tuples = {
            (backend, "single-ofe", binary_id)
            for binary_id in self.wepp_binaries
            for backend in _DELINEATION_BACKENDS
        }
        expected_model_tuples.add(("wbt", "multiple-ofe", "wepp_260803"))
        observed_model_tuples = {
            tuple(token.split("|")) for token in self.allowed_model_tuples
        }
        if observed_model_tuples != expected_model_tuples:
            raise CapabilityGraphError(
                "model tuple is not authorized by the continental-us Builder profile"
            )

    def as_config_sections(self) -> dict[str, dict[str, CanonicalValue]]:
        """Return canonical config sections for project materialization."""

        return {
            "capabilities": {
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
            },
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


def build_continental_us_capability_graph(
    wepp_binaries: tuple[str, ...],
    wepp_binary_revisions: Mapping[str, str],
    *,
    climate_provider_tokens: Mapping[str, str] | None = None,
) -> CapabilityGraph:
    """Build the canonical Builder-exposed continental-US dependency graph."""

    profile = get_locale_profile("continental-us")
    if profile is None:
        raise CapabilityGraphError("continental-us locale profile is missing")
    climate_by_id = {item.catalog_id: item for item in iter_climate_datasets()}
    if any(catalog_id not in climate_by_id for catalog_id in _CLIMATE_IDS):
        raise CapabilityGraphError("continental-us climate descriptor is missing")
    if not wepp_binaries or "wepp_260803" not in wepp_binaries:
        raise CapabilityGraphError("WEPP provider is missing required default wepp_260803")
    if set(wepp_binary_revisions) != set(wepp_binaries):
        raise CapabilityGraphError("WEPP provider role identities do not exhaust binary values")

    station_relations = {
        catalog_id: climate_by_id[catalog_id].station_method_ids
        for catalog_id in _CLIMATE_IDS
    }
    spatial_relations = {
        catalog_id: climate_by_id[catalog_id].spatial_method_ids
        for catalog_id in _CLIMATE_IDS
    }
    configured_climate_tokens = (
        default_climate_provider_tokens()
        if climate_provider_tokens is None
        else dict(climate_provider_tokens)
    )
    provider_payload = {
        "locale": locale_catalog_revision(),
        "climate": climate_catalog_revision(configured_climate_tokens),
        "landcover": landcover_catalog_revision(),
        "dem_sources": {
            source_id: DEM_SOURCE_RUNTIME[source_id] for source_id in profile.dem_sources
        },
        "soil_sources": {
            source_id: SOIL_SOURCE_RUNTIME[source_id] for source_id in profile.soil_sources
        },
        "soil_builder_adapter": "soils-builder-runtime-map-v1",
        "delineation_adapters": {
            "topaz": "watershed-backend-contract-v1:topaz",
            "wbt": "weppcloud-wbt-adapter-v1:wbt",
        },
        "representation_adapter": "wepp-representation-contract-v1",
        "wepp_binaries": wepp_binaries,
        "wepp_binary_revisions": dict(wepp_binary_revisions),
    }
    provider_revision = hashlib.sha256(
        json.dumps(provider_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    model_tuples = tuple(
        f"{backend}|single-ofe|{binary_id}"
        for binary_id in wepp_binaries
        for backend in ("topaz", "wbt")
    ) + ("wbt|multiple-ofe|wepp_260803",)
    graph = CapabilityGraph(
        schema_version=CAPABILITY_SCHEMA_VERSION,
        locale_profiles=(profile.profile_id,),
        dem_sources=profile.dem_sources,
        climate_datasets=_CLIMATE_IDS,
        climate_station_methods=tuple(dict.fromkeys(
            method for values in station_relations.values() for method in values
        )),
        climate_spatial_methods=_CONTINENTAL_US_CLIMATE_SPATIAL_METHODS,
        soil_datasets=profile.soil_sources,
        soil_builders=_SOIL_BUILDERS,
        landuse_datasets=profile.landuse_sources,
        landuse_methods=_LANDUSE_METHODS,
        delineation_backends=_DELINEATION_BACKENDS,
        watershed_representations=_WATERSHED_REPRESENTATIONS,
        wepp_binaries=wepp_binaries,
        wepp_binary_revisions=MappingProxyType(dict(wepp_binary_revisions)),
        mods=(),
        allowed_model_tuples=model_tuples,
        climate_station_methods_by_dataset=_freeze_map(station_relations),
        climate_spatial_methods_by_dataset=_freeze_map(spatial_relations),
        climate_station_defaults=_freeze_defaults({
            catalog_id: climate_by_id[catalog_id].default_station_method_id
            for catalog_id in _CLIMATE_IDS
        }),
        climate_spatial_defaults=_freeze_defaults({
            catalog_id: climate_by_id[catalog_id].default_spatial_method_id
            for catalog_id in _CLIMATE_IDS
        }),
        landuse_methods_by_dataset=_freeze_map({"nlcd-2019": _LANDUSE_METHODS}),
        landuse_method_defaults=_freeze_defaults({"nlcd-2019": "gridded"}),
        landuse_methods_by_representation=_freeze_map({
            "single-ofe": _LANDUSE_METHODS,
            "multiple-ofe": ("gridded", "upload"),
        }),
        soil_builders_by_dataset=_freeze_map({
            "ssurgo-gnatsgso-2025": _SOIL_BUILDERS,
        }),
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
        provider_revision=provider_revision,
    )
    graph.validate()
    return graph
