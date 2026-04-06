"""Dependency tracking helpers for features export WP-2."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import string

from .catalog_loader import CatalogLayer, LayerCatalog
from .contracts import DEFAULT_SWAT_RUN_ID, ResolvedExportPlan, ResolvedLayerPlan

_SUPPORTED_LOCATOR_KINDS: frozenset[str] = frozenset({"nodb_ref", "relpath", "path_template"})
_SUPPORTED_CONTENT_HASH_MODES: frozenset[str] = frozenset({"none", "sha256"})

NodbRefResolver = cabc.Callable[[str, str, str], str | Path]


class DependencyResolutionError(ValueError):
    """Raised when dependency locator resolution fails."""


@dataclass(frozen=True)
class DependencyEntry:
    """Canonical dependency record used for cache-fingerprint computation."""

    relpath: str
    exists: bool
    size: int | None
    mtime_ns: int | None
    content_hash_marker: str | None = None
    content_hash_value: str | None = None
    layer_id: str | None = None
    output_layer_id: str | None = None
    dependency_role: str = "dependency"
    dependency_id: str | None = None

    def sort_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.relpath,
            self.output_layer_id or "",
            self.layer_id or "",
            self.dependency_role,
            self.dependency_id or "",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "relpath": self.relpath,
            "exists": self.exists,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "content_hash_marker": self.content_hash_marker,
            "content_hash_value": self.content_hash_value,
            "layer_id": self.layer_id,
            "output_layer_id": self.output_layer_id,
            "dependency_role": self.dependency_role,
            "dependency_id": self.dependency_id,
        }


@dataclass(frozen=True)
class DependencySnapshot:
    """Resolved dependency snapshot used as cache-key input."""

    catalog_signature: str
    entries: tuple[DependencyEntry, ...]
    fingerprint: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "catalog_signature": self.catalog_signature,
            "entries": [entry.to_mapping() for entry in self.entries],
            "fingerprint": self.fingerprint,
        }


def build_catalog_signature(catalog: LayerCatalog) -> str:
    """Return a stable fingerprint of catalog version metadata."""

    payload = {
        "catalog_version": catalog.metadata.catalog_version,
        "schema_version": catalog.metadata.schema_version,
        "updated_at_utc": catalog.metadata.updated_at_utc,
        "owner": catalog.metadata.owner,
        "status": catalog.metadata.status,
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_payload.encode("utf-8")).hexdigest()


def build_dependency_snapshot(
    plan: ResolvedExportPlan,
    catalog: LayerCatalog,
    wd: str | Path,
    *,
    nodb_ref_resolver: NodbRefResolver | None = None,
    table_names_by_output_layer_id: cabc.Mapping[str, cabc.Sequence[str]] | None = None,
    include_unitizer_dependency: bool = True,
    content_hash_mode: str = "none",
    template_context_overrides: cabc.Mapping[str, object] | None = None,
) -> DependencySnapshot:
    """Build dependency entries and deterministic fingerprint for a resolved plan."""

    if content_hash_mode not in _SUPPORTED_CONTENT_HASH_MODES:
        raise DependencyResolutionError(
            f"Unsupported content_hash_mode {content_hash_mode!r}; "
            f"expected one of {sorted(_SUPPORTED_CONTENT_HASH_MODES)}."
        )

    wd_path = Path(wd).resolve()
    entries: list[DependencyEntry] = []

    for layer_plan in sorted(plan.layers, key=lambda item: item.output_layer_id):
        layer = catalog.get_layer(layer_plan.layer_id)
        if layer is None:
            raise DependencyResolutionError(
                f"Resolved layer {layer_plan.layer_id!r} is missing from catalog index."
            )
        entries.extend(
            _resolve_layer_entries(
                layer_plan,
                layer,
                plan=plan,
                catalog=catalog,
                wd_path=wd_path,
                nodb_ref_resolver=nodb_ref_resolver,
                table_names_by_output_layer_id=table_names_by_output_layer_id,
                content_hash_mode=content_hash_mode,
                template_context_overrides=template_context_overrides,
            )
        )

    if include_unitizer_dependency and plan.request.units == "project":
        entries.append(
            _build_entry_for_relpath(
                relpath="unitizer.nodb",
                wd_path=wd_path,
                layer_id=None,
                output_layer_id=None,
                dependency_role="unitizer",
                dependency_id="unitizer.preferences",
                content_hash_mode=content_hash_mode,
            )
        )

    ordered_entries = tuple(sorted(entries, key=DependencyEntry.sort_key))
    catalog_signature = build_catalog_signature(catalog)
    fingerprint = dependency_fingerprint(
        ordered_entries,
        catalog_signature=catalog_signature,
    )
    return DependencySnapshot(
        catalog_signature=catalog_signature,
        entries=ordered_entries,
        fingerprint=fingerprint,
    )


def dependency_fingerprint(
    entries: cabc.Sequence[DependencyEntry],
    *,
    catalog_signature: str,
) -> str:
    """Compute deterministic dependency fingerprint from canonical entry JSON."""

    payload = {
        "catalog_signature": catalog_signature,
        "entries": [entry.to_mapping() for entry in entries],
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_payload.encode("utf-8")).hexdigest()


def _resolve_layer_entries(
    layer_plan: ResolvedLayerPlan,
    layer: CatalogLayer,
    *,
    plan: ResolvedExportPlan,
    catalog: LayerCatalog,
    wd_path: Path,
    nodb_ref_resolver: NodbRefResolver | None,
    table_names_by_output_layer_id: cabc.Mapping[str, cabc.Sequence[str]] | None,
    content_hash_mode: str,
    template_context_overrides: cabc.Mapping[str, object] | None,
) -> list[DependencyEntry]:
    raw_layer = layer.raw
    contexts = _build_template_contexts(
        layer_plan,
        layer,
        plan=plan,
        catalog=catalog,
        table_names_by_output_layer_id=table_names_by_output_layer_id,
        template_context_overrides=template_context_overrides,
    )

    entries: list[DependencyEntry] = []
    locator_records = _iter_layer_locator_records(raw_layer)
    for context in contexts:
        for role, dependency_id, locator in locator_records:
            kind, value = _parse_locator(locator, locator_context=f"{layer.layer_id}.{role}.{dependency_id}")
            relpath = _resolve_locator_to_relpath(
                kind=kind,
                value=value,
                wd_path=wd_path,
                context=context,
                nodb_ref_resolver=nodb_ref_resolver,
                layer_id=layer.layer_id,
                output_layer_id=layer_plan.output_layer_id,
            )
            entries.append(
                _build_entry_for_relpath(
                    relpath=relpath,
                    wd_path=wd_path,
                    layer_id=layer.layer_id,
                    output_layer_id=layer_plan.output_layer_id,
                    dependency_role=role,
                    dependency_id=dependency_id,
                    content_hash_mode=content_hash_mode,
                )
            )

    return entries


def _iter_layer_locator_records(
    raw_layer: cabc.Mapping[str, object],
) -> tuple[tuple[str, str, object], ...]:
    records: list[tuple[str, str, object]] = []

    geometry = _require_mapping(raw_layer.get("geometry"), context="layer.geometry")
    records.append(("geometry", "geometry", geometry.get("locator")))

    for source in _require_sequence(raw_layer.get("sources"), context="layer.sources"):
        source_map = _require_mapping(source, context="layer.sources[]")
        source_id = _require_string(source_map.get("source_id"), context="layer.sources[].source_id")
        records.append(("source", source_id, source_map.get("locator")))

    for dependency in _require_sequence(raw_layer.get("dependencies"), context="layer.dependencies"):
        dependency_map = _require_mapping(dependency, context="layer.dependencies[]")
        dep_id = _require_string(dependency_map.get("dep_id"), context="layer.dependencies[].dep_id")
        records.append(("dependency", dep_id, dependency_map.get("locator")))

    return tuple(records)


def _build_template_contexts(
    layer_plan: ResolvedLayerPlan,
    layer: CatalogLayer,
    *,
    plan: ResolvedExportPlan,
    catalog: LayerCatalog,
    table_names_by_output_layer_id: cabc.Mapping[str, cabc.Sequence[str]] | None,
    template_context_overrides: cabc.Mapping[str, object] | None,
) -> tuple[dict[str, str], ...]:
    base_context = _build_base_template_context(
        layer_plan,
        plan=plan,
        catalog=catalog,
        template_context_overrides=template_context_overrides,
    )

    requires_table_name = _layer_requires_template_var(layer, "table_name")
    if not requires_table_name:
        return (base_context,)

    table_names = _resolve_table_names_for_layer(
        layer_plan,
        table_names_by_output_layer_id=table_names_by_output_layer_id,
    )
    if not table_names:
        raise DependencyResolutionError(
            f"Layer {layer_plan.output_layer_id!r} requires table_name selector resolution, "
            "but no table names were provided."
        )

    contexts: list[dict[str, str]] = []
    for table_name in table_names:
        context = dict(base_context)
        context["table_name"] = table_name
        contexts.append(context)
    return tuple(contexts)


def _build_base_template_context(
    layer_plan: ResolvedLayerPlan,
    *,
    plan: ResolvedExportPlan,
    catalog: LayerCatalog,
    template_context_overrides: cabc.Mapping[str, object] | None,
) -> dict[str, str]:
    context: dict[str, str] = {}

    path_template_vars = catalog.metadata.path_template_vars
    scope_root = path_template_vars.get("scope_root")
    if isinstance(scope_root, cabc.Mapping):
        values = scope_root.get("values")
        if isinstance(values, cabc.Mapping) and layer_plan.scope in values:
            resolved_scope_root = values[layer_plan.scope]
            if isinstance(resolved_scope_root, str) and resolved_scope_root:
                context["scope_root"] = resolved_scope_root

    if layer_plan.context == "scenario" and layer_plan.selector_id is not None:
        context["scenario_id"] = layer_plan.selector_id
    elif plan.request.scenario is not None:
        context["scenario_id"] = plan.request.scenario

    if layer_plan.context == "contrast" and layer_plan.selector_id is not None:
        context["contrast_id"] = layer_plan.selector_id
    elif plan.request.contrast_id is not None:
        context["contrast_id"] = plan.request.contrast_id
    if plan.request.swat_run_id and plan.request.swat_run_id != DEFAULT_SWAT_RUN_ID:
        context["swat_run_id"] = plan.request.swat_run_id

    crs_token_var = path_template_vars.get("crs_token")
    if isinstance(crs_token_var, cabc.Mapping):
        values = crs_token_var.get("values")
        if isinstance(values, cabc.Mapping):
            resolved_crs_token = values.get(plan.request.crs)
            if isinstance(resolved_crs_token, str) and resolved_crs_token:
                context["crs_token"] = resolved_crs_token

    if template_context_overrides is not None:
        for key, value in template_context_overrides.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            context[key_text] = str(value)

    return context


def _layer_requires_template_var(layer: CatalogLayer, variable_name: str) -> bool:
    token = "{" + variable_name + "}"
    for _, _, locator in _iter_layer_locator_records(layer.raw):
        if isinstance(locator, cabc.Mapping):
            value = locator.get("value")
            if isinstance(value, str) and token in value:
                return True
    return False


def _resolve_table_names_for_layer(
    layer_plan: ResolvedLayerPlan,
    *,
    table_names_by_output_layer_id: cabc.Mapping[str, cabc.Sequence[str]] | None,
) -> tuple[str, ...]:
    if table_names_by_output_layer_id is None:
        return ()

    table_names = table_names_by_output_layer_id.get(layer_plan.output_layer_id)
    if table_names is None:
        table_names = table_names_by_output_layer_id.get(layer_plan.layer_id)
    if table_names is None:
        return ()

    normalized_names: list[str] = []
    seen: set[str] = set()
    for name in table_names:
        if not isinstance(name, str) or not name.strip():
            raise DependencyResolutionError(
                f"Resolved table names for {layer_plan.output_layer_id!r} must be non-empty strings."
            )
        token = name.strip()
        if token not in seen:
            seen.add(token)
            normalized_names.append(token)
    return tuple(sorted(normalized_names))


def _parse_locator(locator: object, *, locator_context: str) -> tuple[str, str]:
    locator_map = _require_mapping(locator, context=f"{locator_context}.locator")
    if set(locator_map.keys()) != {"kind", "value"}:
        raise DependencyResolutionError(
            f"{locator_context}.locator must contain exactly keys 'kind' and 'value'."
        )

    kind = _require_string(locator_map.get("kind"), context=f"{locator_context}.locator.kind")
    value = _require_string(locator_map.get("value"), context=f"{locator_context}.locator.value")

    if kind not in _SUPPORTED_LOCATOR_KINDS:
        raise DependencyResolutionError(
            f"Unsupported locator kind {kind!r} at {locator_context}; "
            f"expected one of {sorted(_SUPPORTED_LOCATOR_KINDS)}."
        )

    return kind, value


def _resolve_locator_to_relpath(
    *,
    kind: str,
    value: str,
    wd_path: Path,
    context: cabc.Mapping[str, str],
    nodb_ref_resolver: NodbRefResolver | None,
    layer_id: str,
    output_layer_id: str,
) -> str:
    if kind == "relpath":
        return _normalize_relpath(value, wd_path)

    if kind == "path_template":
        expanded = _expand_path_template(value, context, layer_id=layer_id, output_layer_id=output_layer_id)
        return _normalize_relpath(expanded, wd_path)

    if kind == "nodb_ref":
        if nodb_ref_resolver is None:
            raise DependencyResolutionError(
                "nodb_ref locator requires an explicit nodb_ref_resolver callback."
            )
        controller, attribute = _parse_nodb_ref(value)
        resolved_path = nodb_ref_resolver(str(wd_path), controller, attribute)
        if not isinstance(resolved_path, (str, Path)):
            raise DependencyResolutionError(
                "nodb_ref_resolver must return a str or Path for "
                f"nodb:{controller}.{attribute}; got {type(resolved_path).__name__}."
            )
        return _normalize_relpath(str(resolved_path), wd_path)

    raise DependencyResolutionError(f"Unsupported locator kind {kind!r}.")


def _parse_nodb_ref(value: str) -> tuple[str, str]:
    if not value.startswith("nodb:"):
        raise DependencyResolutionError(
            f"nodb_ref locator value must start with 'nodb:', received {value!r}."
        )

    token = value[len("nodb:") :]
    if "." not in token:
        raise DependencyResolutionError(
            "nodb_ref locator value must use 'nodb:<controller>.<attribute>' format."
        )

    controller, attribute = token.split(".", 1)
    if not controller.strip() or not attribute.strip():
        raise DependencyResolutionError(
            "nodb_ref locator value must include non-empty controller and attribute tokens."
        )

    return controller.strip(), attribute.strip()


def _expand_path_template(
    value: str,
    context: cabc.Mapping[str, str],
    *,
    layer_id: str,
    output_layer_id: str,
) -> str:
    formatter = string.Formatter()
    required_fields = [
        field_name
        for _, field_name, _, _ in formatter.parse(value)
        if field_name is not None and field_name != ""
    ]
    missing_fields = sorted(set(field for field in required_fields if field not in context))
    if missing_fields:
        raise DependencyResolutionError(
            f"Unresolved path_template variable(s) {missing_fields!r} for layer "
            f"{layer_id!r} ({output_layer_id!r})."
        )

    try:
        return value.format_map(dict(context))
    except KeyError as exc:
        missing = str(exc)
        raise DependencyResolutionError(
            f"Failed to resolve path_template {value!r}; missing variable {missing}."
        ) from exc


def _normalize_relpath(path_value: str, wd_path: Path) -> str:
    candidate = Path(path_value)
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
    else:
        resolved = (wd_path / candidate).resolve(strict=False)

    allowed_roots = _allowed_dependency_roots(wd_path)
    for allowed_root in allowed_roots:
        try:
            resolved.relative_to(allowed_root)
        except ValueError:
            continue
        return Path(os.path.relpath(resolved, wd_path)).as_posix()

    allowed_tokens = ", ".join(str(path) for path in allowed_roots)
    raise DependencyResolutionError(
        f"Resolved dependency path {resolved} escapes allowed roots ({allowed_tokens}) "
        f"for working directory {wd_path}."
    )


def _allowed_dependency_roots(wd_path: Path) -> tuple[Path, ...]:
    roots: list[Path] = [wd_path]
    parent_run_root = _find_parent_run_root(wd_path)
    if parent_run_root is not None:
        resolved_parent = parent_run_root.resolve(strict=False)
        if resolved_parent not in roots:
            roots.append(resolved_parent)
    return tuple(roots)


def _find_parent_run_root(wd_path: Path) -> Path | None:
    """Infer parent run root when wd points at a child `_pups` workspace."""

    parts = wd_path.parts
    for pups_index in range(len(parts) - 1, -1, -1):
        if parts[pups_index] != "_pups":
            continue
        if pups_index <= 1:
            continue

        tail = parts[pups_index + 1 :]
        if len(tail) != 3:
            continue
        if tail[0] != "omni" or tail[1] not in {"scenarios", "contrasts"}:
            continue

        parent_root = Path(*parts[:pups_index])
        if parent_root == Path(parent_root.anchor):
            continue
        return parent_root

    return None


def _build_entry_for_relpath(
    *,
    relpath: str,
    wd_path: Path,
    layer_id: str | None,
    output_layer_id: str | None,
    dependency_role: str,
    dependency_id: str,
    content_hash_mode: str,
) -> DependencyEntry:
    abs_path = wd_path / relpath
    exists = abs_path.exists()
    size: int | None = None
    mtime_ns: int | None = None
    content_hash_marker: str | None = None
    content_hash_value: str | None = None

    if exists:
        stat_result = abs_path.stat()
        size = stat_result.st_size
        mtime_ns = stat_result.st_mtime_ns

        if content_hash_mode == "sha256" and abs_path.is_file():
            content_hash_marker = "sha256"
            content_hash_value = _hash_file_sha256(abs_path)

    return DependencyEntry(
        relpath=relpath,
        exists=exists,
        size=size,
        mtime_ns=mtime_ns,
        content_hash_marker=content_hash_marker,
        content_hash_value=content_hash_value,
        layer_id=layer_id,
        output_layer_id=output_layer_id,
        dependency_role=dependency_role,
        dependency_id=dependency_id,
    )


def _hash_file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping(value: object, *, context: str) -> cabc.Mapping[str, object]:
    if not isinstance(value, cabc.Mapping):
        raise DependencyResolutionError(f"{context} must be a mapping.")
    return value


def _require_sequence(value: object, *, context: str) -> tuple[object, ...]:
    if not isinstance(value, list):
        raise DependencyResolutionError(f"{context} must be an array.")
    return tuple(value)


def _require_string(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DependencyResolutionError(f"{context} must be a non-empty string.")
    return value.strip()


__all__ = [
    "DependencyEntry",
    "DependencyResolutionError",
    "DependencySnapshot",
    "build_catalog_signature",
    "build_dependency_snapshot",
    "dependency_fingerprint",
]
