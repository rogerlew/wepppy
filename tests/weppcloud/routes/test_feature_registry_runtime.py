from __future__ import annotations

import configparser
import copy
from pathlib import Path

import pytest
import yaml

from wepppy.weppcloud.feature_registry import runtime as registry_runtime
from wepppy.weppcloud.feature_registry.schema import (
    FeatureRegistryValidationError,
    validate_config_registry_payload,
    validate_feature_registry_payload,
)
from wepppy.weppcloud.feature_registry.runtime import (
    build_header_mod_options,
    config_registry_by_id,
    feature_registry_by_id,
    load_config_registry,
    load_feature_registry,
)

pytestmark = [pytest.mark.routes, pytest.mark.unit]


class _User:
    def __init__(self, roles: set[str] | None = None) -> None:
        self._roles = set(roles or set())

    def has_role(self, role: str) -> bool:
        return role in self._roles


def test_feature_registry_loads_expected_entries() -> None:
    features = load_feature_registry()
    feature_ids = {entry.id for entry in features}

    assert "rap_ts" in feature_ids
    assert "openet_ts" in feature_ids
    assert "omni_contrasts" in feature_ids
    assert "rusle" in feature_ids


def test_config_registry_loads_expected_entries() -> None:
    configs = load_config_registry()
    config_ids = {entry.id for entry in configs}

    assert "disturbed9002" in config_ids
    assert "disturbed9002_wbt" in config_ids
    assert "disturbed9002-wbt-mofe" in config_ids
    assert "reveg" in config_ids


def test_build_header_mod_options_applies_role_and_backend_policy() -> None:
    user = _User(set())
    active_mods = {"disturbed", "openet_ts", "debris_flow", "rusle", "rap_ts"}

    options = build_header_mod_options(
        active_mods=active_mods,
        user=user,
        is_wbt=False,
        include_all=False,
    )
    option_ids = {entry["id"] for entry in options}

    assert "rap_ts" in option_ids
    assert "openet_ts" not in option_ids
    assert "debris_flow" not in option_ids
    assert "rusle" not in option_ids


def test_build_header_mod_options_include_all_overrides_policy() -> None:
    user = _User(set())

    options = build_header_mod_options(
        active_mods=set(),
        user=user,
        is_wbt=False,
        include_all=True,
    )
    option_ids = {entry["id"] for entry in options}

    assert "openet_ts" in option_ids
    assert "debris_flow" in option_ids
    assert "rusle" in option_ids


def test_build_header_mod_options_allows_internal_features_for_dev_role() -> None:
    user = _User({"Dev"})
    active_mods = {"omni"}

    options = build_header_mod_options(
        active_mods=active_mods,
        user=user,
        is_wbt=True,
        include_all=False,
    )
    option_ids = {entry["id"] for entry in options}

    assert "openet_ts" in option_ids
    assert "omni_contrasts" in option_ids


def test_config_registry_by_id_has_maturity_metadata() -> None:
    configs = config_registry_by_id()
    disturbed = configs["disturbed9002"]
    disturbed_wbt = configs["disturbed9002_wbt"]
    reveg = configs["reveg"]

    assert disturbed.maturity == "stable"
    assert disturbed_wbt.maturity == "preview"
    assert reveg.maturity == "experimental"


def test_multi_ofe_configs_are_forced_to_preview_maturity() -> None:
    configs = config_registry_by_id()
    repo_root = Path(__file__).resolve().parents[3]

    multi_ofe_ids: set[str] = set()
    for entry in configs.values():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(repo_root / entry.cfg_path, encoding="utf-8")
        try:
            token = parser.get("wepp", "multi_ofe")
        except (configparser.NoSectionError, configparser.NoOptionError):
            continue

        normalized = token.strip().lower()
        if normalized in {"", "none", "null"}:
            continue
        if normalized in configparser.ConfigParser.BOOLEAN_STATES and configparser.ConfigParser.BOOLEAN_STATES[normalized]:
            multi_ofe_ids.add(entry.id)
            assert entry.maturity == "preview"

    assert "reveg-mofe" in multi_ofe_ids
    assert "reveg-10m-mofe" in multi_ofe_ids
    assert "disturbed9002-wbt-mofe" in multi_ofe_ids


def test_config_registry_declares_multi_ofe_preview_override_rule() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    registry_path = repo_root / "wepppy/weppcloud/feature_registry/config_registry.yaml"
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    assert isinstance(payload, dict)
    overrides = payload.get("overrides")
    assert isinstance(overrides, list)

    matched = [
        rule
        for rule in overrides
        if isinstance(rule, dict)
        and isinstance(rule.get("when"), dict)
        and isinstance(rule["when"].get("cfg_bool"), dict)
        and rule["when"]["cfg_bool"].get("section") == "wepp"
        and rule["when"]["cfg_bool"].get("option") == "multi_ofe"
        and rule["when"]["cfg_bool"].get("equals") is True
        and isinstance(rule.get("set"), dict)
        and rule["set"].get("maturity") == "preview"
    ]
    assert matched


def test_registry_maps_are_immutable() -> None:
    feature_map = feature_registry_by_id()
    config_map = config_registry_by_id()

    with pytest.raises(TypeError):
        feature_map["new-feature"] = object()
    with pytest.raises(TypeError):
        config_map["new-config"] = object()


def test_schema_rejects_absolute_config_paths() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["cfg_path"] = "/etc/hosts"

    with pytest.raises(FeatureRegistryValidationError, match="relative path"):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_parent_traversal_config_paths() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["cfg_path"] = "../escape.cfg"

    with pytest.raises(FeatureRegistryValidationError, match="must not contain '..' traversal"):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_backslash_config_paths() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["cfg_path"] = r"wepppy\nodb\configs\disturbed9002.cfg"

    with pytest.raises(FeatureRegistryValidationError, match="must use '/' path separators"):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_absolute_template_paths() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["section_template"] = "/etc/hosts"

    with pytest.raises(FeatureRegistryValidationError, match="relative path"):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_parent_traversal_template_paths() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["section_template"] = "../templates/controls/rap_ts_pure.htm"

    with pytest.raises(FeatureRegistryValidationError, match="must not contain '..' traversal"):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_validates_enable_dependency_references() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["enable_dependencies"] = ["does-not-exist"]

    with pytest.raises(FeatureRegistryValidationError, match="enable dependency references unknown"):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_validates_requires_feature_references() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["requires_features"] = ["does-not-exist"]

    with pytest.raises(FeatureRegistryValidationError, match="requires unknown prerequisite feature"):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_validates_disable_blocker_references() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["disable_blockers"] = ["does-not-exist"]

    with pytest.raises(FeatureRegistryValidationError, match="references unknown disable blocker"):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_validates_replaced_by_references() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["replaced_by"] = "does-not-exist"

    with pytest.raises(FeatureRegistryValidationError, match="replaced_by references unknown config"):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_requires_embargo_until_for_publication_embargo_feature() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["maturity"] = "internal"
    mutated["features"][0]["internal_reason"] = "publication_embargo"
    mutated["features"][0]["embargo_until"] = None
    mutated["features"][0]["min_role"] = "dev"

    with pytest.raises(
        FeatureRegistryValidationError,
        match="must be set when internal_reason is 'publication_embargo'",
    ):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_accepts_publication_embargo_with_embargo_until_config() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["maturity"] = "internal"
    mutated["configs"][0]["internal_reason"] = "publication_embargo"
    mutated["configs"][0]["embargo_until"] = "2027-05-22"
    mutated["configs"][0]["min_role"] = "dev"

    spec = validate_config_registry_payload(mutated, registry_dir=registry_dir)

    assert spec.configs[0].internal_reason == "publication_embargo"
    assert spec.configs[0].embargo_until == "2027-05-22"


def test_schema_rejects_invalid_embargo_until_format_config() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["maturity"] = "internal"
    mutated["configs"][0]["internal_reason"] = "publication_embargo"
    mutated["configs"][0]["embargo_until"] = "05/22/2027"
    mutated["configs"][0]["min_role"] = "dev"

    with pytest.raises(
        FeatureRegistryValidationError,
        match="must be an ISO date in YYYY-MM-DD format",
    ):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_embargo_until_without_publication_embargo_config() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["configs"][0]["maturity"] = "internal"
    mutated["configs"][0]["internal_reason"] = "compute"
    mutated["configs"][0]["embargo_until"] = "2027-05-22"
    mutated["configs"][0]["min_role"] = "dev"

    with pytest.raises(
        FeatureRegistryValidationError,
        match="must be null unless internal_reason is 'publication_embargo'",
    ):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_override_publication_embargo_without_embargo_until() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "config_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["overrides"].append(
        {
            "id": "embargo-missing-date",
            "when": {
                "cfg_bool": {
                    "section": "wepp",
                    "option": "multi_ofe",
                    "equals": True,
                }
            },
            "set": {
                "maturity": "internal",
                "internal_reason": "publication_embargo",
            },
        }
    )

    with pytest.raises(
        FeatureRegistryValidationError,
        match="set.embargo_until must be set when internal_reason is 'publication_embargo'",
    ):
        validate_config_registry_payload(mutated, registry_dir=registry_dir)


def test_schema_rejects_internal_feature_with_non_dev_min_role() -> None:
    registry_dir = Path(registry_runtime.__file__).resolve().parent
    payload = yaml.safe_load((registry_dir / "feature_registry.yaml").read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["features"][0]["maturity"] = "internal"
    mutated["features"][0]["internal_reason"] = "compute"
    mutated["features"][0]["embargo_until"] = None
    mutated["features"][0]["min_role"] = "admin"

    with pytest.raises(
        FeatureRegistryValidationError,
        match="must be 'dev' when maturity is 'internal'",
    ):
        validate_feature_registry_payload(mutated, registry_dir=registry_dir)


def test_override_bool_tokens_are_strict() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_dict({"wepp": {"multi_ofe": "trueish"}})

    with pytest.raises(FeatureRegistryValidationError, match="Invalid boolean token"):
        registry_runtime._read_cfg_bool_option(
            parser,
            "wepp",
            "multi_ofe",
            cfg_path="wepppy/nodb/configs/test.cfg",
        )


def test_yaml_parse_errors_are_wrapped_as_validation_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad_yaml_path = tmp_path / "feature_registry_bad.yaml"
    bad_yaml_path.write_text("version: 1\nfeatures: [\n", encoding="utf-8")
    monkeypatch.setattr(registry_runtime, "_FEATURE_REGISTRY_PATH", bad_yaml_path)

    registry_runtime.invalidate_registry_caches()
    with pytest.raises(FeatureRegistryValidationError, match="Failed to load registry YAML"):
        registry_runtime.load_feature_registry()
    registry_runtime.invalidate_registry_caches()
