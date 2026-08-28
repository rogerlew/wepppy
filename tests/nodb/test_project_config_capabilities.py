from __future__ import annotations

import ast
import configparser
from io import StringIO

import pytest

import wepppy.nodb.project_config_capabilities as capability_module
import wepppy.nodb.config_builder.resolver as builder_resolver_module
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
