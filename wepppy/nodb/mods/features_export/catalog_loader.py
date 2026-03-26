"""Layer catalog loading and schema validation for features export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import collections.abc as cabc

import yaml

from .contracts import (
    SUPPORTED_EVENT_SELECTORS,
    SUPPORTED_OUTPUT_SCOPES,
    SUPPORTED_TEMPORAL_MODES,
)

_LOCATOR_KINDS: frozenset[str] = frozenset({"nodb_ref", "relpath", "path_template"})
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
    layer = _require_mapping(raw_layer, layer_path)
    layer_id = _require_string(layer.get("layer_id"), f"{layer_path}.layer_id")
    family = _require_string(layer.get("family"), f"{layer_path}.family")
    scope_class = _require_string(layer.get("scope_class"), f"{layer_path}.scope_class")
    if scope_class not in _SCOPE_CLASS_VALUES:
        raise LayerCatalogValidationError(
            f"{source_name}: {layer_path}.scope_class must be one of {sorted(_SCOPE_CLASS_VALUES)}, "
            f"got {scope_class!r}."
        )

    geometry = _require_mapping(layer.get("geometry"), f"{layer_path}.geometry")
    _validate_locator(
        geometry.get("locator"),
        f"{layer_path}.geometry.locator",
        allowed_kinds=metadata.allowed_locator_kinds,
        source_name=source_name,
    )

    join = _require_mapping(layer.get("join"), f"{layer_path}.join")
    _require_string(join.get("primary_key"), f"{layer_path}.join.primary_key")

    sources = _require_sequence(layer.get("sources"), f"{layer_path}.sources")
    if not sources:
        raise LayerCatalogValidationError(f"{source_name}: {layer_path}.sources must be non-empty.")
    for index, source_value in enumerate(sources):
        source = _require_mapping(source_value, f"{layer_path}.sources[{index}]")
        _validate_locator(
            source.get("locator"),
            f"{layer_path}.sources[{index}].locator",
            allowed_kinds=metadata.allowed_locator_kinds,
            source_name=source_name,
        )

    dependencies = _require_sequence(layer.get("dependencies"), f"{layer_path}.dependencies")
    for index, dependency_value in enumerate(dependencies):
        dependency = _require_mapping(dependency_value, f"{layer_path}.dependencies[{index}]")
        _validate_locator(
            dependency.get("locator"),
            f"{layer_path}.dependencies[{index}].locator",
            allowed_kinds=metadata.allowed_locator_kinds,
            source_name=source_name,
        )

    if "table_profiles" in layer:
        _validate_table_profiles(
            layer.get("table_profiles"),
            f"{layer_path}.table_profiles",
            allowed_locator_kinds=metadata.allowed_locator_kinds,
            source_name=source_name,
        )

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
        raw=dict(layer),
    )


def _validate_table_profiles(
    value: object,
    path: str,
    *,
    allowed_locator_kinds: tuple[str, ...],
    source_name: str,
) -> None:
    profiles = _require_sequence(value, path)
    for index, profile_value in enumerate(profiles):
        profile = _require_mapping(profile_value, f"{path}[{index}]")
        geometry = _require_mapping(profile.get("geometry"), f"{path}[{index}].geometry")
        _validate_locator(
            geometry.get("locator"),
            f"{path}[{index}].geometry.locator",
            allowed_kinds=allowed_locator_kinds,
            source_name=source_name,
        )
        join = _require_mapping(profile.get("join"), f"{path}[{index}].join")
        _require_string(join.get("primary_key"), f"{path}[{index}].join.primary_key")


def _validate_locator(
    value: object,
    path: str,
    *,
    allowed_kinds: tuple[str, ...],
    source_name: str,
) -> None:
    locator = _require_mapping(value, path)
    keys = set(locator.keys())
    if keys != {"kind", "value"}:
        raise LayerCatalogValidationError(
            f"{source_name}: {path} must contain exactly keys 'kind' and 'value'; found {sorted(keys)!r}."
        )

    kind = _require_string(locator.get("kind"), f"{path}.kind")
    if kind not in allowed_kinds:
        raise LayerCatalogValidationError(
            f"{source_name}: {path}.kind must be one of {list(allowed_kinds)!r}, got {kind!r}."
        )
    _require_string(locator.get("value"), f"{path}.value")


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
