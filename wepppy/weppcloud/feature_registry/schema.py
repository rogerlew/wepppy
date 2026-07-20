from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

VALID_MATURITY = {"stable", "preview", "experimental", "deprecated", "internal"}
VALID_INTERNAL_REASON = {"compute", "api_constrained", "beta", "publication_embargo"}
VALID_MIN_ROLE = {"user", "poweruser", "dev", "admin", "root"}
VALID_BACKEND = {"any", "wbt", "topaz"}

ROLE_AUDIENCES = {
    "user": frozenset({"User", "PowerUser", "Dev", "Admin", "Root"}),
    "poweruser": frozenset({"PowerUser", "Dev", "Admin", "Root"}),
    "dev": frozenset({"Dev", "Root"}),
    "admin": frozenset({"Admin", "Root"}),
    "root": frozenset({"Root"}),
}


class FeatureRegistryValidationError(ValueError):
    """Raised when feature/config registry payloads fail contract validation."""


@dataclass(frozen=True)
class FeatureSpec:
    id: str
    label: str
    maturity: str
    internal_reason: str | None
    embargo_until: str | None
    adr_reference: str | None
    min_role: str
    menu_min_role: str | None
    requires_backend: str
    requires_features: tuple[str, ...]
    section_template: str
    section_id: str
    section_class: str
    nav_label: str
    enable_dependencies: tuple[str, ...]
    disable_blockers: tuple[str, ...]


@dataclass(frozen=True)
class ConfigSpec:
    id: str
    label: str
    cfg_path: str
    maturity: str
    internal_reason: str | None
    embargo_until: str | None
    min_role: str
    requires_backend: str
    replaced_by: str | None


@dataclass(frozen=True)
class ConfigOverrideRule:
    id: str
    match_cfg_section: str
    match_cfg_option: str
    match_cfg_bool: bool
    set_maturity: str
    set_internal_reason: str | None
    set_embargo_until: str | None


@dataclass(frozen=True)
class ConfigRegistrySpec:
    configs: tuple[ConfigSpec, ...]
    overrides: tuple[ConfigOverrideRule, ...]


def _normalize_repo_relative_path(raw_path: str, context: str) -> Path:
    rel_path = Path(raw_path)
    if rel_path.is_absolute():
        raise FeatureRegistryValidationError(f"{context} must be a relative path")
    if ".." in rel_path.parts:
        raise FeatureRegistryValidationError(f"{context} must not contain '..' traversal")
    if "\\" in raw_path:
        raise FeatureRegistryValidationError(f"{context} must use '/' path separators")
    return rel_path


def _resolve_under_root(root: Path, rel_path: Path, context: str) -> Path:
    root_resolved = root.resolve()
    abs_path = (root_resolved / rel_path).resolve()
    if not abs_path.is_relative_to(root_resolved):
        raise FeatureRegistryValidationError(
            f"{context} must resolve under {root_resolved}"
        )
    return abs_path


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FeatureRegistryValidationError(f"{context} must be a mapping")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise FeatureRegistryValidationError(f"{context} must be a string")
    normalized = value.strip()
    if not normalized:
        raise FeatureRegistryValidationError(f"{context} must be non-empty")
    return normalized


def _require_enum(value: Any, context: str, allowed: set[str]) -> str:
    token = _require_string(value, context)
    if token not in allowed:
        raise FeatureRegistryValidationError(
            f"{context} must be one of {sorted(allowed)} (got {token!r})"
        )
    return token


def _require_string_list(value: Any, context: str) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if not isinstance(value, list):
        raise FeatureRegistryValidationError(f"{context} must be a list of strings")
    out: list[str] = []
    for idx, item in enumerate(value):
        out.append(_require_string(item, f"{context}[{idx}]"))
    return tuple(out)


def _optional_internal_reason(value: Any, *, context: str, maturity: str) -> str | None:
    if value is None:
        if maturity == "internal":
            raise FeatureRegistryValidationError(
                f"{context} must be set when maturity is 'internal'"
            )
        return None

    reason = _require_string(value, context)
    if reason not in VALID_INTERNAL_REASON:
        raise FeatureRegistryValidationError(
            f"{context} must be one of {sorted(VALID_INTERNAL_REASON)} (got {reason!r})"
        )
    if maturity != "internal":
        raise FeatureRegistryValidationError(
            f"{context} must be null unless maturity is 'internal'"
        )
    return reason


def _optional_embargo_until(
    value: Any,
    *,
    context: str,
    maturity: str,
    internal_reason: str | None,
) -> str | None:
    if value is None:
        if maturity == "internal" and internal_reason == "publication_embargo":
            raise FeatureRegistryValidationError(
                f"{context} must be set when internal_reason is 'publication_embargo'"
            )
        return None

    embargo_until = _require_string(value, context)
    try:
        date.fromisoformat(embargo_until)
    except ValueError as exc:
        raise FeatureRegistryValidationError(
            f"{context} must be an ISO date in YYYY-MM-DD format (got {embargo_until!r})"
        ) from exc

    if maturity != "internal":
        raise FeatureRegistryValidationError(
            f"{context} must be null unless maturity is 'internal'"
        )
    if internal_reason != "publication_embargo":
        raise FeatureRegistryValidationError(
            f"{context} must be null unless internal_reason is 'publication_embargo'"
        )
    return embargo_until


def _validate_internal_min_role(*, min_role: str, maturity: str, context: str) -> None:
    if maturity == "internal" and min_role != "dev":
        raise FeatureRegistryValidationError(
            f"{context} must be 'dev' when maturity is 'internal'"
        )


def _optional_role(value: Any, context: str) -> str | None:
    if value is None:
        return None
    return _require_enum(value, context, VALID_MIN_ROLE)


def _validate_menu_role_audience(
    *,
    min_role: str,
    menu_min_role: str | None,
    context: str,
) -> None:
    if menu_min_role is None:
        return
    if not ROLE_AUDIENCES[min_role].issubset(ROLE_AUDIENCES[menu_min_role]):
        raise FeatureRegistryValidationError(
            f"{context} audience must include every {min_role!r} authorized role"
        )


def _expect_version(payload: Mapping[str, Any], context: str) -> None:
    version = payload.get("version")
    if version != 1:
        raise FeatureRegistryValidationError(f"{context}: expected version 1, got {version!r}")


def _validate_template_exists(registry_dir: Path, rel_template_path: str, context: str) -> None:
    templates_root = registry_dir.parent / "templates"
    rel_path = _normalize_repo_relative_path(rel_template_path, context)
    template_path = _resolve_under_root(templates_root, rel_path, context)
    if not template_path.is_file():
        raise FeatureRegistryValidationError(
            f"{context} references missing template path: {rel_template_path}"
        )


def _optional_adr_reference(value: Any, *, registry_dir: Path, context: str) -> str | None:
    if value is None:
        return None

    adr_reference = _require_string(value, context)
    rel_path = _normalize_repo_relative_path(adr_reference, context)
    expected_root = Path("docs") / "adrs"
    if not rel_path.is_relative_to(expected_root):
        raise FeatureRegistryValidationError(
            f"{context} must be under {expected_root.as_posix()}/"
        )

    repo_root = registry_dir.parents[2]
    abs_path = _resolve_under_root(repo_root, rel_path, context)
    if abs_path.suffix.lower() != ".md":
        raise FeatureRegistryValidationError(
            f"{context} must reference a markdown file under {expected_root.as_posix()}/"
        )
    if not abs_path.is_file():
        raise FeatureRegistryValidationError(
            f"{context} references missing ADR path: {adr_reference}"
        )
    return adr_reference


def _validate_cfg_path_exists(registry_dir: Path, cfg_path: str, context: str) -> None:
    repo_root = registry_dir.parents[2]
    rel_path = _normalize_repo_relative_path(cfg_path, context)
    expected_root = Path("wepppy") / "nodb" / "configs"
    if not rel_path.is_relative_to(expected_root):
        raise FeatureRegistryValidationError(
            f"{context} must be under {expected_root.as_posix()}/"
        )
    abs_path = _resolve_under_root(repo_root, rel_path, context)
    if not abs_path.is_file():
        raise FeatureRegistryValidationError(
            f"{context} references missing config path: {cfg_path}"
        )


def validate_feature_registry_payload(
    payload: Mapping[str, Any],
    *,
    registry_dir: Path,
) -> tuple[FeatureSpec, ...]:
    root = _require_mapping(payload, "feature_registry")
    _expect_version(root, "feature_registry")

    raw_entries = root.get("features")
    if not isinstance(raw_entries, list):
        raise FeatureRegistryValidationError("feature_registry.features must be a list")
    internal_prerequisites = set(
        _require_string_list(
            root.get("internal_prerequisites"),
            "feature_registry.internal_prerequisites",
        )
    )

    entries: list[FeatureSpec] = []
    seen_ids: set[str] = set()

    for idx, raw in enumerate(raw_entries):
        context = f"feature_registry.features[{idx}]"
        item = _require_mapping(raw, context)

        feature_id = _require_string(item.get("id"), f"{context}.id")
        if feature_id in seen_ids:
            raise FeatureRegistryValidationError(f"{context}.id duplicates {feature_id!r}")
        seen_ids.add(feature_id)

        label = _require_string(item.get("label"), f"{context}.label")
        maturity = _require_enum(item.get("maturity"), f"{context}.maturity", VALID_MATURITY)
        internal_reason = _optional_internal_reason(
            item.get("internal_reason"),
            context=f"{context}.internal_reason",
            maturity=maturity,
        )
        embargo_until = _optional_embargo_until(
            item.get("embargo_until"),
            context=f"{context}.embargo_until",
            maturity=maturity,
            internal_reason=internal_reason,
        )
        adr_reference = _optional_adr_reference(
            item.get("adr_reference"),
            registry_dir=registry_dir,
            context=f"{context}.adr_reference",
        )
        min_role = _require_enum(item.get("min_role"), f"{context}.min_role", VALID_MIN_ROLE)
        _validate_internal_min_role(
            min_role=min_role,
            maturity=maturity,
            context=f"{context}.min_role",
        )
        menu_min_role = _optional_role(
            item.get("menu_min_role"),
            f"{context}.menu_min_role",
        )
        _validate_menu_role_audience(
            min_role=min_role,
            menu_min_role=menu_min_role,
            context=f"{context}.menu_min_role",
        )
        requires_backend = _require_enum(
            item.get("requires_backend"),
            f"{context}.requires_backend",
            VALID_BACKEND,
        )
        requires_features = _require_string_list(
            item.get("requires_features"),
            f"{context}.requires_features",
        )
        section_template = _require_string(item.get("section_template"), f"{context}.section_template")
        _validate_template_exists(registry_dir, section_template, f"{context}.section_template")

        section_id = _require_string(
            item.get("section_id", feature_id.replace("_", "-")),
            f"{context}.section_id",
        )
        section_class = _require_string(
            item.get("section_class", "wc-stack"),
            f"{context}.section_class",
        )
        nav_label = _require_string(item.get("nav_label", label), f"{context}.nav_label")

        enable_dependencies = _require_string_list(
            item.get("enable_dependencies"),
            f"{context}.enable_dependencies",
        )
        disable_blockers = _require_string_list(
            item.get("disable_blockers"),
            f"{context}.disable_blockers",
        )

        entries.append(
            FeatureSpec(
                id=feature_id,
                label=label,
                maturity=maturity,
                internal_reason=internal_reason,
                embargo_until=embargo_until,
                adr_reference=adr_reference,
                min_role=min_role,
                menu_min_role=menu_min_role,
                requires_backend=requires_backend,
                requires_features=requires_features,
                section_template=section_template,
                section_id=section_id,
                section_class=section_class,
                nav_label=nav_label,
                enable_dependencies=enable_dependencies,
                disable_blockers=disable_blockers,
            )
        )

    known_ids = {entry.id for entry in entries}
    for entry in entries:
        for dep_id in entry.requires_features:
            if dep_id in known_ids or dep_id in internal_prerequisites:
                continue
            raise FeatureRegistryValidationError(
                f"feature {entry.id!r} requires unknown prerequisite feature {dep_id!r}"
            )

        for dep_id in entry.enable_dependencies:
            if dep_id in known_ids or dep_id in internal_prerequisites:
                continue
            raise FeatureRegistryValidationError(
                f"feature {entry.id!r} enable dependency references unknown feature {dep_id!r}"
            )

        for blocker in entry.disable_blockers:
            if blocker not in known_ids:
                raise FeatureRegistryValidationError(
                    f"feature {entry.id!r} references unknown disable blocker {blocker!r}"
                )

    return tuple(entries)


def validate_config_registry_payload(
    payload: Mapping[str, Any],
    *,
    registry_dir: Path,
) -> ConfigRegistrySpec:
    root = _require_mapping(payload, "config_registry")
    _expect_version(root, "config_registry")

    raw_entries = root.get("configs")
    if not isinstance(raw_entries, list):
        raise FeatureRegistryValidationError("config_registry.configs must be a list")

    entries: list[ConfigSpec] = []
    seen_ids: set[str] = set()

    for idx, raw in enumerate(raw_entries):
        context = f"config_registry.configs[{idx}]"
        item = _require_mapping(raw, context)

        config_id = _require_string(item.get("id"), f"{context}.id")
        if config_id in seen_ids:
            raise FeatureRegistryValidationError(f"{context}.id duplicates {config_id!r}")
        seen_ids.add(config_id)

        label = _require_string(item.get("label"), f"{context}.label")
        cfg_path = _require_string(item.get("cfg_path"), f"{context}.cfg_path")
        _validate_cfg_path_exists(registry_dir, cfg_path, f"{context}.cfg_path")

        maturity = _require_enum(item.get("maturity"), f"{context}.maturity", VALID_MATURITY)
        internal_reason = _optional_internal_reason(
            item.get("internal_reason"),
            context=f"{context}.internal_reason",
            maturity=maturity,
        )
        embargo_until = _optional_embargo_until(
            item.get("embargo_until"),
            context=f"{context}.embargo_until",
            maturity=maturity,
            internal_reason=internal_reason,
        )
        min_role = _require_enum(item.get("min_role"), f"{context}.min_role", VALID_MIN_ROLE)
        _validate_internal_min_role(
            min_role=min_role,
            maturity=maturity,
            context=f"{context}.min_role",
        )
        requires_backend = _require_enum(
            item.get("requires_backend"),
            f"{context}.requires_backend",
            VALID_BACKEND,
        )

        replaced_by_raw = item.get("replaced_by")
        replaced_by = None
        if replaced_by_raw is not None:
            replaced_by = _require_string(replaced_by_raw, f"{context}.replaced_by")

        entries.append(
            ConfigSpec(
                id=config_id,
                label=label,
                cfg_path=cfg_path,
                maturity=maturity,
                internal_reason=internal_reason,
                embargo_until=embargo_until,
                min_role=min_role,
                requires_backend=requires_backend,
                replaced_by=replaced_by,
            )
        )

    known_ids = {entry.id for entry in entries}
    for entry in entries:
        if entry.replaced_by and entry.replaced_by not in known_ids:
            raise FeatureRegistryValidationError(
                f"config {entry.id!r} replaced_by references unknown config {entry.replaced_by!r}"
            )

    raw_overrides = root.get("overrides", [])
    if raw_overrides is None:
        raw_overrides = []
    if not isinstance(raw_overrides, list):
        raise FeatureRegistryValidationError("config_registry.overrides must be a list when present")

    overrides: list[ConfigOverrideRule] = []
    seen_override_ids: set[str] = set()
    for idx, raw in enumerate(raw_overrides):
        context = f"config_registry.overrides[{idx}]"
        item = _require_mapping(raw, context)

        override_id = _require_string(item.get("id"), f"{context}.id")
        if override_id in seen_override_ids:
            raise FeatureRegistryValidationError(
                f"{context}.id duplicates {override_id!r}"
            )
        seen_override_ids.add(override_id)

        when = _require_mapping(item.get("when"), f"{context}.when")
        allowed_when_keys = {"cfg_bool"}
        unknown_when_keys = set(when.keys()) - allowed_when_keys
        if unknown_when_keys:
            raise FeatureRegistryValidationError(
                f"{context}.when has unsupported keys: {sorted(unknown_when_keys)}"
            )
        cfg_bool = _require_mapping(when.get("cfg_bool"), f"{context}.when.cfg_bool")
        allowed_cfg_bool_keys = {"section", "option", "equals"}
        unknown_cfg_bool_keys = set(cfg_bool.keys()) - allowed_cfg_bool_keys
        if unknown_cfg_bool_keys:
            raise FeatureRegistryValidationError(
                f"{context}.when.cfg_bool has unsupported keys: {sorted(unknown_cfg_bool_keys)}"
            )
        match_cfg_section = _require_string(cfg_bool.get("section"), f"{context}.when.cfg_bool.section")
        match_cfg_option = _require_string(cfg_bool.get("option"), f"{context}.when.cfg_bool.option")
        match_cfg_bool = cfg_bool.get("equals")
        if not isinstance(match_cfg_bool, bool):
            raise FeatureRegistryValidationError(
                f"{context}.when.cfg_bool.equals must be a boolean"
            )

        set_map = _require_mapping(item.get("set"), f"{context}.set")
        allowed_set_keys = {"maturity", "internal_reason", "embargo_until"}
        unknown_set_keys = set(set_map.keys()) - allowed_set_keys
        if unknown_set_keys:
            raise FeatureRegistryValidationError(
                f"{context}.set has unsupported keys: {sorted(unknown_set_keys)}"
            )
        set_maturity = _require_enum(set_map.get("maturity"), f"{context}.set.maturity", VALID_MATURITY)
        set_internal_reason = _optional_internal_reason(
            set_map.get("internal_reason"),
            context=f"{context}.set.internal_reason",
            maturity=set_maturity,
        )
        set_embargo_until = _optional_embargo_until(
            set_map.get("embargo_until"),
            context=f"{context}.set.embargo_until",
            maturity=set_maturity,
            internal_reason=set_internal_reason,
        )

        overrides.append(
            ConfigOverrideRule(
                id=override_id,
                match_cfg_section=match_cfg_section,
                match_cfg_option=match_cfg_option,
                match_cfg_bool=match_cfg_bool,
                set_maturity=set_maturity,
                set_internal_reason=set_internal_reason,
                set_embargo_until=set_embargo_until,
            )
        )

    return ConfigRegistrySpec(configs=tuple(entries), overrides=tuple(overrides))
