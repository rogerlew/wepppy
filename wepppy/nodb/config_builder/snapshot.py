"""Builder payload validation and schema-v1 project artifact construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from types import MappingProxyType
from typing import Mapping

from wepppy.nodb.config_builder.registry import load_registry
from wepppy.nodb.config_builder.resolver import BuilderConstraintError, resolve_builder_config
from wepppy.nodb.config_builder.schema import BuilderSelections, Registry, ResolvedBuilderConfig
from wepppy.nodb.project_config_snapshot import PresetSnapshotCandidate
from wepppy.project_config_sanitization import assert_materialization_safe, scan_manifest_text

__all__ = ["BUILDER_WRITER_FLAG", "BuilderCandidate", "builder_writer_enabled", "parse_builder_selections", "resolve_builder_candidate"]

BUILDER_WRITER_FLAG = "WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})
_REQUIRED = frozenset({
    "locale",
    "dem",
    "delineation_backend",
    "watershed_representation",
    "wepp_binary",
    "soil",
    "landuse",
    "climate",
    "climate_station_database",
})
_OPTIONAL = frozenset({"mods", "capability_profile", "cellsize_override"})


@dataclass(frozen=True, slots=True)
class BuilderCandidate:
    resolved: ResolvedBuilderConfig
    artifact: PresetSnapshotCandidate
    review: Mapping[str, object]


def builder_writer_enabled(environ: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    raw = source.get(BUILDER_WRITER_FLAG, "").strip().casefold()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ValueError(f"{BUILDER_WRITER_FLAG} must be a strict boolean")


def parse_builder_selections(payload: object) -> BuilderSelections:
    if not isinstance(payload, dict):
        raise BuilderConstraintError("selections", "invalid_type", "Selections must be an object")
    unknown = set(payload) - _REQUIRED - _OPTIONAL
    missing = _REQUIRED - set(payload)
    if unknown:
        raise BuilderConstraintError("selections", "unknown_field", f"Unknown selection fields: {sorted(unknown)}")
    if missing:
        field = sorted(missing)[0]
        raise BuilderConstraintError(field, "missing_required_field", f"{field} is required")
    for field in _REQUIRED:
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise BuilderConstraintError(field, "invalid_type", f"{field} must be a stable ID")
    mods = payload.get("mods", [])
    if not isinstance(mods, list) or not all(isinstance(item, str) for item in mods):
        raise BuilderConstraintError("mods", "invalid_type", "mods must be an array of stable IDs")
    override = payload.get("cellsize_override")
    if override is not None and (isinstance(override, bool) or not isinstance(override, int)):
        raise BuilderConstraintError("cellsize_override", "invalid_type", "cellsize_override must be an integer")
    profile = payload.get("capability_profile", f"{payload['locale']}-capabilities")
    if not isinstance(profile, str) or not profile:
        raise BuilderConstraintError("capability_profile", "invalid_type", "capability_profile must be a stable ID")
    return BuilderSelections(
        locale=payload["locale"], dem=payload["dem"], delineation_backend=payload["delineation_backend"],
        watershed_representation=payload["watershed_representation"], wepp_binary=payload["wepp_binary"], soil=payload["soil"],
        landuse=payload["landuse"], climate=payload["climate"],
        climate_station_database=payload["climate_station_database"], mods=tuple(mods),
        capability_profile=profile, cellsize_override=override,
    )


def resolve_builder_candidate(
    selections: BuilderSelections,
    *,
    registry: Registry | None = None,
    resolved_at: datetime | None = None,
) -> BuilderCandidate:
    resolved_registry = load_registry() if registry is None else registry
    deployment_revision = str(os.getenv("RQ_ENGINE_DEPLOYMENT_REVISION") or "dev").strip() or "dev"
    resolved = resolve_builder_config(selections, registry=resolved_registry)
    assert_materialization_safe(resolved.config_bytes.decode("utf-8"))
    review = {
        "locale": selections.locale, "dem": selections.dem,
        "dem_default_cellsize": resolved.dem_default_cellsize,
        "cellsize": resolved.effective_cellsize, "cellsize_source": resolved.cellsize_source,
        "delineation_backend": selections.delineation_backend,
        "watershed_representation": selections.watershed_representation,
        "wepp_binary": selections.wepp_binary,
        "soil": selections.soil, "landuse": selections.landuse, "climate": selections.climate,
        "climate_station_database": selections.climate_station_database,
        "mods": list(selections.mods),
        "capabilities": dict(resolved.config.get("capabilities", {})),
        "config_filename": "config.cfg",
    }
    timestamp = (resolved_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 1, "resolver_version": 1, "source_kind": "builder", "source_preset": None,
        "source_revision": deployment_revision, "resolved_at": timestamp,
        "parent_chain": [{"kind": item.kind, "id": item.component_id, "revision": item.revision} for item in resolved.parent_chain],
        "selections": review | {"capability_profile": selections.capability_profile},
        "config": {"filename": "config.cfg", "sha256": hashlib.sha256(resolved.config_bytes).hexdigest()},
        "amendments": [],
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if scan_manifest_text(manifest_bytes.decode(), source="config-manifest.json"):
        raise BuilderConstraintError("selections", "unsafe_materialization", "Generated manifest is unsafe")
    artifact = PresetSnapshotCandidate("config", "config.cfg", resolved.config_bytes, manifest_bytes, MappingProxyType({}), deployment_revision)
    return BuilderCandidate(resolved, artifact, MappingProxyType(review))
