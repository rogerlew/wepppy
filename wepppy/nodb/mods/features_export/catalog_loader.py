"""Layer catalog loading and schema validation for features export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import collections.abc as cabc

import yaml

from wepppy.project_assets import WEPP_LOSS_HILL, get_asset

from .contracts import (
    SUPPORTED_EVENT_SELECTORS,
    SUPPORTED_OUTPUT_SCOPES,
    SUPPORTED_TEMPORAL_MODES,
)

_LOCATOR_KINDS: frozenset[str] = frozenset({"nodb_ref", "relpath", "path_template"})
_OMNI_PROJECTION_PREFIXES = {
    "scenario": "_pups/omni/scenarios/{scenario_id}",
    "contrast": "_pups/omni/contrasts/{contrast_id}",
}
_SCOPE_CLASS_VALUES: frozenset[str] = frozenset({"scope_aware", "scope_invariant"})
_CATALOG_STATUSES: frozenset[str] = frozenset({"draft", "active", "deprecated"})


class LayerCatalogValidationError(ValueError):
    """Raised when `layer_catalog.yaml` violates the expected contract."""


@dataclass(frozen=True)
class CatalogMetadata:
    catalog_version: str
    schema_version: int | str
    updated_at_utc: str
    owner: str
    status: str
    allowed_locator_kinds: tuple[str, ...]
    temporal_modes: tuple[str, ...]
    event_selectors: tuple[str, ...]
    path_template_vars: dict[str, object]


@dataclass(frozen=True)
class CatalogLayer:
    layer_id: str
    family: str
    scope_class: str
    temporal_supported_modes: tuple[str, ...]
    temporal_mode_rules: dict[str, dict[str, object]]
    raw: dict[str, object]


@dataclass(frozen=True)
class LayerCatalog:
    metadata: CatalogMetadata
    layers: tuple[CatalogLayer, ...]
    layer_index: dict[str, CatalogLayer]

    def get_layer(self, layer_id: str) -> CatalogLayer | None:
        return self.layer_index.get(layer_id)


def default_catalog_path() -> Path:
    return Path(__file__).resolve().with_name("layer_catalog.yaml")


def load_layer_catalog(path: str | Path | None = None) -> LayerCatalog:
    catalog_path = Path(path) if path is not None else default_catalog_path()
    try:
        text = catalog_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LayerCatalogValidationError(
            f"Failed to read layer catalog at {catalog_path}: {exc}"
        ) from exc

    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise LayerCatalogValidationError(f"Invalid YAML in catalog {catalog_path}: {exc}") from exc

    return parse_layer_catalog(payload, source_name=str(catalog_path))


def parse_layer_catalog(payload: object, *, source_name: str = "<memory>") -> LayerCatalog:
    root = _require_mapping(payload, "$")

    metadata_map = _require_mapping(root.get("metadata"), "$.metadata")
    layers_list = _require_sequence(root.get("layers"), "$.layers")
    if not layers_list:
        raise LayerCatalogValidationError(f"{source_name}: $.layers must be a non-empty array.")

    metadata = _parse_metadata(metadata_map, source_name=source_name)

    parsed_layers: list[CatalogLayer] = []
    layer_index: dict[str, CatalogLayer] = {}
    for index, layer_value in enumerate(layers_list):
        layer = _parse_layer(
            layer_value,
            layer_path=f"$.layers[{index}]",
            metadata=metadata,
            source_name=source_name,
        )
        if layer.layer_id in layer_index:
            raise LayerCatalogValidationError(
                f"{source_name}: duplicate layer_id {layer.layer_id!r} in $.layers."
            )
        parsed_layers.append(layer)
        layer_index[layer.layer_id] = layer

    return LayerCatalog(metadata=metadata, layers=tuple(parsed_layers), layer_index=layer_index)


def _parse_metadata(raw: cabc.Mapping[str, object], *, source_name: str) -> CatalogMetadata:
    catalog_version = _require_string(raw.get("catalog_version"), "$.metadata.catalog_version")
    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, (int, str)):
        raise LayerCatalogValidationError(
            f"{source_name}: $.metadata.schema_version must be an integer or string."
        )
    updated_at_utc = _require_string(raw.get("updated_at_utc"), "$.metadata.updated_at_utc")
    owner = _require_string(raw.get("owner"), "$.metadata.owner")
    status = _require_string(raw.get("status"), "$.metadata.status")
    if status not in _CATALOG_STATUSES:
        raise LayerCatalogValidationError(
            f"{source_name}: $.metadata.status must be one of {sorted(_CATALOG_STATUSES)}, got {status!r}."
        )

    resolver = _require_mapping(raw.get("resolver_contract"), "$.metadata.resolver_contract")
    allowed_locator_kinds = _require_string_array(
        resolver.get("allowed_locator_kinds"),
        "$.metadata.resolver_contract.allowed_locator_kinds",
    )
    if set(allowed_locator_kinds) != _LOCATOR_KINDS:
        raise LayerCatalogValidationError(
            f"{source_name}: $.metadata.resolver_contract.allowed_locator_kinds must be exactly "
            f"{sorted(_LOCATOR_KINDS)}, got {allowed_locator_kinds!r}."
        )

    path_template_vars = _require_mapping(
        resolver.get("path_template_vars"), "$.metadata.resolver_contract.path_template_vars"
    )
    _validate_scope_root_contract(path_template_vars, source_name=source_name)

    temporal_modes = _require_string_array(
        resolver.get("temporal_modes"), "$.metadata.resolver_contract.temporal_modes"
    )
    if set(temporal_modes) != set(SUPPORTED_TEMPORAL_MODES):
        raise LayerCatalogValidationError(
            f"{source_name}: $.metadata.resolver_contract.temporal_modes must be exactly "
            f"{list(SUPPORTED_TEMPORAL_MODES)!r}, got {temporal_modes!r}."
        )

    event_selectors = _require_string_array(
        resolver.get("event_selectors"), "$.metadata.resolver_contract.event_selectors"
    )
    if set(event_selectors) != set(SUPPORTED_EVENT_SELECTORS):
        raise LayerCatalogValidationError(
            f"{source_name}: $.metadata.resolver_contract.event_selectors must be exactly "
            f"{list(SUPPORTED_EVENT_SELECTORS)!r}, got {event_selectors!r}."
        )

    return CatalogMetadata(
        catalog_version=catalog_version,
        schema_version=schema_version,
        updated_at_utc=updated_at_utc,
        owner=owner,
        status=status,
        allowed_locator_kinds=tuple(allowed_locator_kinds),
        temporal_modes=tuple(temporal_modes),
        event_selectors=tuple(event_selectors),
        path_template_vars=dict(path_template_vars),
    )


def _validate_scope_root_contract(path_template_vars: cabc.Mapping[str, object], *, source_name: str) -> None:
    scope_root = _require_mapping(
        path_template_vars.get("scope_root"),
        "$.metadata.resolver_contract.path_template_vars.scope_root",
    )
    scope_values = _require_mapping(
        scope_root.get("values"),
        "$.metadata.resolver_contract.path_template_vars.scope_root.values",
    )

    for scope in SUPPORTED_OUTPUT_SCOPES:
        if scope not in scope_values:
            raise LayerCatalogValidationError(
                f"{source_name}: scope_root.values must include key {scope!r}."
            )

    baseline_value = scope_values.get("baseline")
    roads_value = scope_values.get("roads")
    if baseline_value != "output" or roads_value != "roads/output":
        raise LayerCatalogValidationError(
            f"{source_name}: scope_root.values must map baseline=output and roads=roads/output, "
            f"got baseline={baseline_value!r}, roads={roads_value!r}."
        )


def _parse_layer(
    raw_layer: object,
    *,
    layer_path: str,
    metadata: CatalogMetadata,
    source_name: str,
) -> CatalogLayer:
    layer = dict(_require_mapping(raw_layer, layer_path))
    layer_id = _require_string(layer.get("layer_id"), f"{layer_path}.layer_id")
    family = _require_string(layer.get("family"), f"{layer_path}.family")
    scope_class = _require_string(layer.get("scope_class"), f"{layer_path}.scope_class")
    if scope_class not in _SCOPE_CLASS_VALUES:
        raise LayerCatalogValidationError(
            f"{source_name}: {layer_path}.scope_class must be one of {sorted(_SCOPE_CLASS_VALUES)}, "
            f"got {scope_class!r}."
        )

    def parse_locator_owner(value: object, path: str) -> dict[str, object]:
        owner = dict(_require_mapping(value, path))
        owner["locator"] = _parse_locator(
            owner.get("locator"), f"{path}.locator",
            allowed_kinds=metadata.allowed_locator_kinds, source_name=source_name,
        )
        return owner

    layer["geometry"] = parse_locator_owner(layer.get("geometry"), f"{layer_path}.geometry")

    join = _require_mapping(layer.get("join"), f"{layer_path}.join")
    _require_string(join.get("primary_key"), f"{layer_path}.join.primary_key")

    sources = _require_sequence(layer.get("sources"), f"{layer_path}.sources")
    if not sources:
        raise LayerCatalogValidationError(f"{source_name}: {layer_path}.sources must be non-empty.")
    layer["sources"] = [
        parse_locator_owner(source, f"{layer_path}.sources[{index}]")
        for index, source in enumerate(sources)
    ]

    dependencies = _require_sequence(layer.get("dependencies"), f"{layer_path}.dependencies")
    layer["dependencies"] = [
        parse_locator_owner(dependency, f"{layer_path}.dependencies[{index}]")
        for index, dependency in enumerate(dependencies)
    ]

    if "table_profiles" in layer:
        profiles = []
        for index, value in enumerate(_require_sequence(layer["table_profiles"], f"{layer_path}.table_profiles")):
            path = f"{layer_path}.table_profiles[{index}]"
            profile = dict(_require_mapping(value, path))
            profile["geometry"] = parse_locator_owner(profile.get("geometry"), f"{path}.geometry")
            join = _require_mapping(profile.get("join"), f"{path}.join")
            _require_string(join.get("primary_key"), f"{path}.join.primary_key")
            profiles.append(profile)
        layer["table_profiles"] = profiles

    temporal = _require_mapping(layer.get("temporal"), f"{layer_path}.temporal")
    supported_modes = _require_string_array(
        temporal.get("supported_modes"), f"{layer_path}.temporal.supported_modes"
    )
    invalid_modes = sorted(set(supported_modes) - set(metadata.temporal_modes))
    if invalid_modes:
        raise LayerCatalogValidationError(
            f"{source_name}: {layer_path}.temporal.supported_modes contains unsupported modes {invalid_modes!r}."
        )

    raw_mode_rules = _require_mapping(temporal.get("mode_rules"), f"{layer_path}.temporal.mode_rules")
    mode_rules: dict[str, dict[str, object]] = {}
    for mode_name, rule_value in raw_mode_rules.items():
        if not isinstance(mode_name, str):
            raise LayerCatalogValidationError(
                f"{source_name}: {layer_path}.temporal.mode_rules keys must be strings."
            )
        if mode_name not in metadata.temporal_modes:
            raise LayerCatalogValidationError(
                f"{source_name}: {layer_path}.temporal.mode_rules contains unsupported mode {mode_name!r}."
            )
        if mode_name not in supported_modes:
            raise LayerCatalogValidationError(
                f"{source_name}: {layer_path}.temporal.mode_rules includes mode {mode_name!r} that is "
                f"absent from supported_modes."
            )

        rule = _require_mapping(rule_value, f"{layer_path}.temporal.mode_rules.{mode_name}")
        if mode_name == "event":
            selector_support = _require_string_array(
                rule.get("selector_support"),
                f"{layer_path}.temporal.mode_rules.event.selector_support",
            )
            invalid_selectors = sorted(set(selector_support) - set(metadata.event_selectors))
            if invalid_selectors:
                raise LayerCatalogValidationError(
                    f"{source_name}: {layer_path}.temporal.mode_rules.event.selector_support has "
                    f"unsupported selectors {invalid_selectors!r}."
                )
        elif "year_selection_supported" in rule and not isinstance(
            rule["year_selection_supported"], bool
        ):
            raise LayerCatalogValidationError(
                f"{source_name}: {layer_path}.temporal.mode_rules.{mode_name}.year_selection_supported "
                "must be boolean when provided."
            )

        mode_rules[mode_name] = dict(rule)

    for mode_name in supported_modes:
        if mode_name not in mode_rules:
            raise LayerCatalogValidationError(
                f"{source_name}: {layer_path}.temporal.mode_rules is missing required entry for mode "
                f"{mode_name!r}."
            )

    return CatalogLayer(
        layer_id=layer_id,
        family=family,
        scope_class=scope_class,
        temporal_supported_modes=tuple(supported_modes),
        temporal_mode_rules=mode_rules,
        raw=layer,
    )


def _parse_locator(
    value: object,
    path: str,
    *,
    allowed_kinds: tuple[str, ...],
    source_name: str,
) -> cabc.Mapping[str, object]:
    locator = _require_mapping(value, path)
    keys = set(locator.keys())
    if "asset_id" in keys:
        if keys - {"asset_id", "projection"}:
            raise LayerCatalogValidationError(f"{source_name}: {path} mixes an asset reference with extra keys.")
        asset_id = _require_string(locator["asset_id"], f"{path}.asset_id")
        try:
            asset = get_asset(asset_id)
        except KeyError as exc:
            raise LayerCatalogValidationError(f"{source_name}: {path} has unknown asset {asset_id!r}.") from exc

        template = asset.path_template
        if "projection" in keys:
            projection = _require_string(locator["projection"], f"{path}.projection")
            if asset != WEPP_LOSS_HILL or projection not in _OMNI_PROJECTION_PREFIXES:
                raise LayerCatalogValidationError(
                    f"{source_name}: {path} has unsupported projection {projection!r} for {asset_id!r}."
                )
            template = f"{_OMNI_PROJECTION_PREFIXES[projection]}/{asset.relative_path()}"
        locator = {"kind": "path_template" if "{" in template else "relpath", "value": template}

    if set(locator) != {"kind", "value"}:
        raise LayerCatalogValidationError(
            f"{source_name}: {path} must contain exactly keys 'kind' and 'value'; found {sorted(keys)!r}."
        )

    kind = _require_string(locator.get("kind"), f"{path}.kind")
    if kind not in allowed_kinds:
        raise LayerCatalogValidationError(
            f"{source_name}: {path}.kind must be one of {list(allowed_kinds)!r}, got {kind!r}."
        )
    _require_string(locator.get("value"), f"{path}.value")
    return locator


def _require_mapping(value: object, path: str) -> cabc.Mapping[str, object]:
    if not isinstance(value, cabc.Mapping):
        raise LayerCatalogValidationError(f"{path} must be an object/mapping.")
    return value


def _require_sequence(value: object, path: str) -> list[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise LayerCatalogValidationError(f"{path} must be an array.")
    return value


def _require_string_array(value: object, path: str) -> list[str]:
    values = _require_sequence(value, path)
    normalized: list[str] = []
    for index, entry in enumerate(values):
        normalized.append(_require_string(entry, f"{path}[{index}]"))
    return normalized


def _require_string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise LayerCatalogValidationError(f"{path} must be a string.")
    token = value.strip()
    if not token:
        raise LayerCatalogValidationError(f"{path} must be a non-empty string.")
    return token


__all__ = [
    "CatalogLayer",
    "CatalogMetadata",
    "LayerCatalog",
    "LayerCatalogValidationError",
    "default_catalog_path",
    "load_layer_catalog",
    "parse_layer_catalog",
]
