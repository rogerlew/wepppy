from __future__ import annotations

import ast
import configparser
import hashlib
from io import StringIO
import json
from pathlib import Path

import pytest

import wepppy.nodb.project_config_capabilities as capability_module
import wepppy.nodb.config_builder.resolver as builder_resolver_module
import wepppy.nodb.project_config_snapshot as snapshot_module
from wepppy.nodb.config_builder import (
    BuilderConstraintError,
    BuilderSelections,
    resolve_builder_config,
)
from wepppy.nodb.config_builder.registry import load_registry
from wepppy.nodb.locales.capability_graph import CapabilityGraphError
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    LocaleAuthorityInvalidError,
    RunCapabilityMode,
    SOIL_BUILDER_MODES,
    capability_ids,
    model_tuple_allowed,
    model_tuple_binaries,
    resolve_run_capability_authority,
    runtime_value_allowed,
    soil_capability_modes,
)
from wepppy.nodb.project_config_reader import ProjectConfigStatus, ProjectConfigWarning

pytestmark = pytest.mark.unit


class FakeConfig:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def config_get_raw(self, _section: str, option: str, default: object = None) -> object:
        return self.values.get(option, default)

    def config_get_list(self, _section: str, option: str, default: object = None) -> object:
        return self.values.get(option, default)


class ParsedConfig:
    def __init__(self, text: str) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(text)
        self._configparser = parser

    def config_get_raw(
        self, section: str, option: str, default: object = None
    ) -> object:
        if not self._configparser.has_option(section, option):
            return default
        return self._configparser.get(section, option, raw=True)

    def config_get_list(
        self, section: str, option: str, default: object = None
    ) -> object:
        raw = self.config_get_raw(section, option, default)
        if not isinstance(raw, str):
            return raw
        return ast.literal_eval(raw)

def test_absent_capability_authority_preserves_legacy_behavior() -> None:
    config = FakeConfig({})
    assert capability_ids(config, "climate_datasets") is None
    assert runtime_value_allowed(config, "climate_datasets", "anything") is True


def test_semantic_soil_ids_map_to_runtime_modes() -> None:
    config = FakeConfig({
        "flattened": True,
        "soil_builders": ["gridded", "single_mukey"],
    })
    assert soil_capability_modes(config) == frozenset({0, 1})
    assert runtime_value_allowed(config, "soil_builders", 1, stable_to_runtime=SOIL_BUILDER_MODES)
    assert not runtime_value_allowed(config, "soil_builders", 2, stable_to_runtime=SOIL_BUILDER_MODES)


@pytest.mark.parametrize("value", [[], [""], [1], "vanilla_cligen"])
def test_malformed_capability_authority_fails_explicitly(value: object) -> None:
    with pytest.raises(ValueError, match="capabilities.climate_datasets"):
        capability_ids(FakeConfig({"climate_datasets": value}), "climate_datasets")


def test_legacy_builder_locales_share_the_builder_graph_hotpath() -> None:
    registry = load_registry()
    expected = {
        "us": "continental-us",
        "eu": "europe",
        "canada": "canada",
        "au": "australia",
        "earth": "global-earth",
    }

    for token, profile_id in expected.items():
        authority = resolve_run_capability_authority(
            ParsedConfig(f'[general]\nlocales = ["{token}"]\n'),
            registry=registry,
        )
        assert authority.mode is RunCapabilityMode.LEGACY_BUILDER
        assert authority.locale_profile == profile_id
        assert authority.runtime_tokens == (token,)
        assert authority.graph is not None
        assert authority.graph.locale_profiles == (profile_id,)


def test_missing_legacy_locale_uses_nonpersisting_continental_us_compatibility() -> None:
    authority = resolve_run_capability_authority(ParsedConfig("[general]\nname = old\n"))

    assert authority.mode is RunCapabilityMode.LEGACY_BUILDER
    assert authority.runtime_tokens == ("us",)
    assert authority.locale_profile == "continental-us"


@pytest.mark.parametrize(
    "value",
    ("[]", '["unknown"]', '["us", "eu"]', '["us", "us"]'),
)
def test_invalid_nonflattened_locale_fails_explicitly(value: str) -> None:
    with pytest.raises(LocaleAuthorityInvalidError):
        resolve_run_capability_authority(
            ParsedConfig(f"[general]\nlocales = {value}\n")
        )


def test_overlay_and_nonbuilder_locales_retain_catalog_compatibility() -> None:
    for value, profile_id in (
        ('["us", "portland"]', "continental-us"),
        ('["turkey"]', "turkey"),
        ('["rhem"]', "rhem"),
    ):
        authority = resolve_run_capability_authority(
            ParsedConfig(f"[general]\nlocales = {value}\n")
        )
        assert authority.mode is RunCapabilityMode.COMPATIBILITY
        assert authority.graph is None
        assert authority.locale_profile == profile_id


def test_flattened_v1_never_consults_live_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: pytest.fail("flattened v1 consulted live registry"),
    )
    authority = resolve_run_capability_authority(
        ParsedConfig(
            "[config]\nflattened = true\n"
            "[capabilities]\nschema_version = 1\n"
            '[general]\nlocales = ["unknown"]\n'
        )
    )

    assert authority.mode is RunCapabilityMode.COMPATIBILITY
    assert authority.graph is None
    assert authority.runtime_tokens == ()


def test_exact_schema_v1_named_preset_projects_only_climate_and_landuse(
    tmp_path: Path,
) -> None:
    candidate = snapshot_module.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
    )
    snapshot_module.materialize_preset_snapshot(tmp_path, candidate)
    config = ParsedConfig(candidate.config_bytes.decode("utf-8"))
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        str(tmp_path),
        "eu-disturbed.cfg",
        True,
        True,
        config_sha256=hashlib.sha256(candidate.config_bytes).hexdigest(),
    )

    authority = resolve_run_capability_authority(config)

    assert authority.mode is RunCapabilityMode.PRESET_PROJECTION
    assert authority.locale_profile == "europe"
    assert authority.runtime_tokens == ("eu",)
    assert authority.projected_domains == frozenset({"climate", "landuse"})
    assert authority.graph is not None
    assert authority.graph.climate_datasets == (
        "vanilla_cligen",
        "eobs_modified",
        "user_defined_cli",
    )
    assert authority.graph.landuse_datasets == (
        "corine-1990",
        "corine-2000",
        "corine-2006",
        "corine-2012",
        "corine-2018",
    )
    assert soil_capability_modes(config) == frozenset({0, 1, 2})


@pytest.mark.parametrize(
    ("preset_id", "profile_id", "climate_ids", "landuse_count"),
    [
        (
            "disturbed9002",
            "continental-us",
            (
                "vanilla_cligen",
                "prism_stochastic",
                "observed_daymet",
                "observed_gridmet",
                "dep_nexrad",
                "future_cmip5",
                "user_defined_cli",
            ),
            114,
        ),
        (
            "eu-disturbed",
            "europe",
            ("vanilla_cligen", "eobs_modified", "user_defined_cli"),
            5,
        ),
        (
            "canada",
            "canada",
            ("vanilla_cligen", "observed_daymet", "user_defined_cli"),
            29,
        ),
        (
            "au-disturbed",
            "australia",
            ("vanilla_cligen", "agdc", "user_defined_cli"),
            1,
        ),
        (
            "earth",
            "global-earth",
            ("vanilla_cligen", "user_defined_cli"),
            29,
        ),
    ],
)
def test_all_five_schema_v1_named_locale_presets_project_current_domains(
    tmp_path: Path,
    preset_id: str,
    profile_id: str,
    climate_ids: tuple[str, ...],
    landuse_count: int,
) -> None:
    candidate = snapshot_module.resolve_preset_snapshot(
        preset_id,
        {},
        source_revision="test-revision",
    )
    snapshot_module.materialize_preset_snapshot(tmp_path, candidate)
    config = ParsedConfig(candidate.config_bytes.decode("utf-8"))
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        str(tmp_path),
        f"{preset_id}.cfg",
        True,
        True,
        config_sha256=hashlib.sha256(candidate.config_bytes).hexdigest(),
    )

    authority = resolve_run_capability_authority(config)

    assert authority.mode is RunCapabilityMode.PRESET_PROJECTION
    assert authority.locale_profile == profile_id
    assert authority.projected_domains == frozenset({"climate", "landuse"})
    assert authority.graph is not None
    assert authority.graph.climate_datasets == climate_ids
    assert len(authority.graph.landuse_datasets) == landuse_count


def test_schema_v1_digest_warning_stays_compatibility_without_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ParsedConfig(
        "[config]\nflattened = true\n"
        "[capabilities]\nschema_version = 1\n"
    )
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        "/tmp/not-consulted",
        "eu-disturbed.cfg",
        True,
        True,
        (ProjectConfigWarning("config_digest_mismatch", "run", "eu-disturbed.cfg"),),
    )
    monkeypatch.setattr(
        snapshot_module,
        "resolve_preset_locale_projection",
        lambda *_args, **_kwargs: pytest.fail("digest mismatch consulted projection"),
    )

    authority = resolve_run_capability_authority(config)

    assert authority.mode is RunCapabilityMode.COMPATIBILITY
    assert authority.graph is None


@pytest.mark.parametrize(
    "hostile_case",
    [
        "unknown_preset",
        "filename_mismatch",
        "parent_chain_mismatch",
        "non_allowlisted_override",
        "stored_locale_mismatch",
    ],
)
def test_hostile_schema_v1_preset_identity_retains_compatibility_without_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hostile_case: str,
) -> None:
    candidate = snapshot_module.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
    )
    config_path, manifest_path = snapshot_module.materialize_preset_snapshot(
        tmp_path,
        candidate,
    )
    manifest = json.loads(manifest_path.read_bytes())
    if hostile_case == "unknown_preset":
        unknown_path = tmp_path / "unknown-preset.cfg"
        config_path.rename(unknown_path)
        config_path = unknown_path
        manifest["source_preset"] = "unknown-preset"
        manifest["parent_chain"][1]["id"] = "unknown-preset"
        manifest["config"]["filename"] = config_path.name
    elif hostile_case == "filename_mismatch":
        manifest["source_preset"] = "earth"
        manifest["parent_chain"][1]["id"] = "earth"
    elif hostile_case == "parent_chain_mismatch":
        manifest["parent_chain"][1]["id"] = "earth"
    elif hostile_case == "non_allowlisted_override":
        manifest["selections"]["overrides"] = {
            "forged.option": {"source": "query", "value": "enabled"}
        }
    else:
        forged_bytes = config_path.read_bytes().replace(b'["eu"]', b'["us"]')
        config_path.write_bytes(forged_bytes)
        manifest["config"]["sha256"] = hashlib.sha256(forged_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    config = ParsedConfig(config_path.read_text(encoding="utf-8"))
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        str(tmp_path),
        config_path.name,
        True,
        True,
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: pytest.fail(
            f"{hostile_case} consulted the live registry"
        ),
    )

    authority = resolve_run_capability_authority(config)

    assert authority.mode is RunCapabilityMode.COMPATIBILITY
    assert authority.graph is None


def test_schema_v1_policy_failure_is_registry_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ParsedConfig(
        "[config]\nflattened = true\n"
        "[capabilities]\nschema_version = 1\n"
    )
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        "/tmp/policy-failure",
        "eu-disturbed.cfg",
        True,
        True,
        config_sha256="a" * 64,
    )

    def unavailable(*_args, **_kwargs):
        raise snapshot_module.PresetPolicyError("policy corpus unavailable")

    monkeypatch.setattr(snapshot_module, "resolve_preset_locale_projection", unavailable)

    with pytest.raises(BuilderRegistryUnavailableError, match="policy corpus unavailable"):
        resolve_run_capability_authority(config)


def test_schema_v1_live_provider_value_error_is_registry_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ParsedConfig(
        "[config]\nflattened = true\n"
        "[capabilities]\nschema_version = 1\n"
    )
    config.project_config_status = ProjectConfigStatus(
        "flattened",
        "/tmp/provider-failure",
        "eu-disturbed.cfg",
        True,
        True,
        config_sha256="a" * 64,
    )
    monkeypatch.setattr(
        snapshot_module,
        "resolve_preset_locale_projection",
        lambda *_args, **_kwargs: "europe",
    )
    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("climate provider defaults are incomplete")
        ),
    )

    with pytest.raises(BuilderRegistryUnavailableError, match="provider defaults"):
        resolve_run_capability_authority(config)


def test_schema_v1_soil_modes_remain_raw_without_live_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ParsedConfig(
        "[config]\nflattened = true\n"
        "[capabilities]\nschema_version = 1\n"
        "soil_builders = ['gridded', 'single_database']\n"
    )
    monkeypatch.setattr(
        capability_module,
        "resolve_run_capability_authority",
        lambda _config: pytest.fail("schema-v1 soil consulted live projection"),
    )

    assert soil_capability_modes(config) == frozenset({0, 2})


def test_flattened_v3_uses_only_stored_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selections = BuilderSelections(
        locale="continental-us",
        dem="usgs-ned1-2024",
        delineation_backend="wbt",
        watershed_representation="single-ofe",
        wepp_binary="wepp_260803",
        soil="ssurgo-gnatsgso-2025",
        landuse="nlcd-2019",
        climate="vanilla_cligen",
        mods=(),
    )
    resolved = resolve_builder_config(selections)
    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: pytest.fail("stored v3 consulted live registry"),
    )

    authority = resolve_run_capability_authority(
        ParsedConfig(resolved.config_bytes.decode("utf-8"))
    )

    assert authority.mode is RunCapabilityMode.STORED
    assert authority.graph is not None
    assert authority.graph.schema_version == 3
    assert authority.runtime_tokens == ("us",)


@pytest.mark.parametrize(
    ("profile_id", "expected_runtime_token"),
    (("australia", "au"), ("europe", "eu")),
)
def test_stored_graph_runtime_tokens_ignore_incongruent_flattened_locales(
    profile_id: str,
    expected_runtime_token: str,
) -> None:
    graph = builder_resolver_module.resolve_builder_capability_graph(profile_id)
    defaults = graph.defaults
    resolved = resolve_builder_config(
        BuilderSelections(
            locale=profile_id,
            dem=defaults["dem_source"],
            delineation_backend=defaults["delineation_backend"],
            watershed_representation=defaults["watershed_representation"],
            wepp_binary=defaults["wepp_binary"],
            soil=defaults["soil_dataset"],
            landuse=defaults["landuse_dataset"],
            climate=defaults["climate_dataset"],
            climate_station_database=defaults.get("climate_station_database"),
            capability_profile=f"{profile_id}-capabilities",
        ),
    )
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(resolved.config_bytes.decode("utf-8"))
    parser.set("general", "locales", '["us"]')
    output = StringIO()
    parser.write(output)

    authority = resolve_run_capability_authority(ParsedConfig(output.getvalue()))

    assert authority.mode is RunCapabilityMode.STORED
    assert authority.locale_profile == profile_id
    assert authority.runtime_tokens == (expected_runtime_token,)


def test_historical_stored_graph_exposes_its_canonical_runtime_token() -> None:
    resolved = resolve_builder_config(
        BuilderSelections(
            locale="continental-us",
            dem="usgs-ned1-2024",
            delineation_backend="wbt",
            watershed_representation="single-ofe",
            wepp_binary="wepp_260803",
            soil="ssurgo-gnatsgso-2025",
            landuse="nlcd-2019",
            climate="vanilla_cligen",
            mods=(),
        ),
        capability_schema_version=2,
    )
    authority = resolve_run_capability_authority(
        ParsedConfig(resolved.config_bytes.decode("utf-8"))
    )

    assert authority.mode is RunCapabilityMode.STORED
    assert authority.runtime_tokens == ("us",)


def test_legacy_builder_registry_failure_is_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(*_args, **_kwargs):
        raise BuilderConstraintError("locale", "test", "registry unavailable")

    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        _unavailable,
    )
    with pytest.raises(BuilderRegistryUnavailableError, match="continental-us"):
        resolve_run_capability_authority(
            ParsedConfig('[general]\nlocales = ["us"]\n')
        )


def test_legacy_builder_graph_validation_failure_is_registry_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _invalid_graph(*_args, **_kwargs):
        raise CapabilityGraphError("provider graph is invalid")

    monkeypatch.setattr(
        builder_resolver_module,
        "build_locale_capability_graph",
        _invalid_graph,
    )

    with pytest.raises(BuilderRegistryUnavailableError, match="provider graph is invalid"):
        resolve_run_capability_authority(
            ParsedConfig('[general]\nlocales = ["us"]\n')
        )


def test_legacy_model_tuple_helpers_do_not_consult_live_builder_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capability_module,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: pytest.fail("legacy model helper consulted live graph"),
    )
    config = ParsedConfig('[general]\nlocales = ["us"]\n')

    assert model_tuple_allowed(config, "topaz", "single-ofe", "legacy-bin") is True
    assert model_tuple_binaries(config, "topaz", "single-ofe") is None
