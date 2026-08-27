from __future__ import annotations

import ast
import configparser
from dataclasses import replace
from pathlib import Path
import re
from types import MappingProxyType

import pytest

from wepp_runner.wepp_runner import get_linux_wepp_bin_opts
import wepppy.nodb.locales.capability_graph as capability_graph_module
from wepppy.nodb.config_builder import BuilderSelections, resolve_builder_config
from wepppy.nodb.config_builder.registry import load_registry
from wepppy.nodb.locales import (
    CapabilityGraphError,
    LocaleClassification,
    LocaleSupportState,
    build_continental_us_capability_graph,
    build_locale_capability_graph,
    iter_landcover_catalog,
    iter_locale_profiles,
    resolve_locale_composition,
)
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
    default_climate_provider_tokens,
    get_climate_station_database,
)
from wepppy.nodb.locales.landuse_catalog import (
    get_landcover_entry,
    landcover_catalog_id,
    landcover_catalog_revision,
)
from wepppy.nodb.locales.locale_profiles import (
    DEM_SOURCE_RUNTIME,
    SHIPPED_MOD_IDS,
    SOIL_SOURCE_RUNTIME,
)
from wepppy.nodb.project_config_capabilities import (
    LANDUSE_METHOD_MODES,
    SOIL_BUILDER_MODES,
    capability_authority,
    capability_ids,
    resolve_landuse_runtime_dataset,
    resolve_named_preset_capabilities,
)

pytestmark = pytest.mark.unit


def _binary_revisions(binary_ids: tuple[str, ...]) -> dict[str, str]:
    return {
        binary_id: f"provider-v1:watershed={'a' * 64}:hillslope={'b' * 64}"
        for binary_id in binary_ids
    }


class ParsedConfig:
    def __init__(self, text: str) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(text)
        self._configparser = parser

    def config_get_raw(self, section: str, option: str, default: object = None) -> object:
        if not self._configparser.has_option(section, option):
            return default
        return self._configparser.get(section, option, raw=True)

    def config_get_list(self, section: str, option: str, default: object = None) -> object:
        raw = self.config_get_raw(section, option, default)
        if not isinstance(raw, str):
            return raw
        return ast.literal_eval(raw)


def _selections() -> BuilderSelections:
    return BuilderSelections(
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


def _resolved_parser() -> ParsedConfig:
    resolved = resolve_builder_config(_selections())
    return ParsedConfig(resolved.config_bytes.decode("utf-8"))


def _historical_parser() -> ParsedConfig:
    resolved = resolve_builder_config(_selections(), capability_schema_version=2)
    return ParsedConfig(resolved.config_bytes.decode("utf-8"))


def test_locale_catalog_classifies_every_shipped_runtime_token() -> None:
    profiles = iter_locale_profiles()
    known_tokens = {profile.runtime_token.casefold() for profile in profiles}
    observed_tokens: set[str] = set()
    for config_path in Path("wepppy/nodb/configs").glob("*.cfg"):
        text = config_path.read_text(encoding="utf-8")
        match = re.search(r"^locales\s*=\s*(\[[^\n]*\])", text, re.MULTILINE)
        if match:
            observed_tokens.update(str(item).casefold() for item in ast.literal_eval(match.group(1)))

    assert observed_tokens <= known_tokens
    assert known_tokens - observed_tokens == {"canada"}
    assert len(profiles) == 17
    assert sum(profile.support_state is LocaleSupportState.BUILDER_EXPOSED for profile in profiles) == 5
    assert next(
        profile for profile in profiles if profile.classification is LocaleClassification.NON_BUILDER_FAMILY
    ).profile_id == "rhem"


def test_shipped_config_data_and_dependency_boundaries_are_closed() -> None:
    observed_dem: set[str] = set()
    observed_soil: set[str | None] = set()
    observed_landuse: set[str] = set()
    observed_backends: set[str] = set()
    observed_mods: set[str] = set()
    for config_path in Path("wepppy/nodb/configs").glob("*.cfg"):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read(config_path, encoding="utf-8")
        for section, option, target in (
            ("general", "dem_db", observed_dem),
            ("landuse", "nlcd_db", observed_landuse),
            ("watershed", "delineation_backend", observed_backends),
        ):
            if parser.has_option(section, option):
                raw = parser.get(section, option)
                try:
                    value = ast.literal_eval(raw)
                except (SyntaxError, ValueError):
                    value = raw.strip()
                target.add(str(value))
        if parser.has_option("soils", "ssurgo_db"):
            raw = parser.get("soils", "ssurgo_db")
            try:
                soil_value = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                soil_value = raw.strip()
            observed_soil.add(None if soil_value is None or str(soil_value) == "None" else str(soil_value))
        if parser.has_option("nodb", "mods"):
            raw_mods = ast.literal_eval(parser.get("nodb", "mods"))
            observed_mods.update(str(item) for item in raw_mods)

    assert observed_dem == set(DEM_SOURCE_RUNTIME.values())
    assert observed_soil == {
        SOIL_SOURCE_RUNTIME[key]
        for key in (
            "ssurgo-gnatsgso-2025", "alaska-gsmsoil", "hawaii-ssurgo",
            "usvi-soils", "isric-global", "chile-soils", "portland-soils",
            "none-soil-provider",
        )
    }
    assert {landcover_catalog_id(value) for value in observed_landuse} <= {
        entry.catalog_id for entry in iter_landcover_catalog()
    }
    assert observed_backends == {"topaz", "wbt"}
    assert observed_mods == set(SHIPPED_MOD_IDS)
    assert set(CLIMATE_STATION_METHOD_RUNTIME) == {
        "auto", "distance", "multi_factor", "eu_heuristic", "au_heuristic", "user_defined"
    }
    assert set(CLIMATE_SPATIAL_METHOD_RUNTIME) == {"single", "multiple", "interpolated"}
    assert set(LANDUSE_METHOD_MODES) == {
        "gridded", "single", "rred_unburned", "rred_burned", "upload"
    }
    assert set(SOIL_BUILDER_MODES) == {"gridded", "single_mukey", "single_database"}


def test_locale_composition_normalizes_continental_us_and_overlay_order() -> None:
    continental = resolve_locale_composition(["us"])
    assert continental.base.profile_id == "continental-us"
    assert continental.runtime_tokens == ("us",)

    tenerife = resolve_locale_composition(["tenerife", "eu"])
    assert tuple(profile.profile_id for profile in tenerife.profiles) == ("europe", "tenerife")
    assert tenerife.runtime_tokens == ("eu", "tenerife")


def test_landcover_catalog_is_complete_and_uses_canonical_runtime_aliases() -> None:
    catalog = iter_landcover_catalog()
    by_id = {entry.catalog_id: entry for entry in catalog}

    assert len(catalog) == 164
    assert "emapr-vote-1984" in by_id
    assert "emapr-vote-1983" not in by_id
    assert by_id["corine-2018"].runtime_value == "eu/CORINE_LandCover/2018"
    assert by_id["australia-landuse-2010-2011"].runtime_value == (
        "au/landuse_201011/lu10v5ua"
    )
    assert by_id["nlcd-2019"].support_state == "builder_exposed"


def test_generated_config_round_trips_as_complete_schema_v3_authority() -> None:
    authority = capability_authority(_resolved_parser())

    assert authority is not None
    assert authority.schema_version == 3
    assert authority.locale_profiles == ("continental-us",)
    assert authority.defaults["locale_profile"] == "continental-us"
    assert authority.defaults["delineation_backend"] == "wbt"
    assert authority.defaults["wepp_binary"] == "wepp_260803"
    assert authority.climate_station_databases == (
        "cligen-stations-legacy",
        "cligen-stations-2015",
        "cligen-stations-ghcn",
    )
    assert authority.defaults["climate_station_database"] == "cligen-stations-2015"
    assert authority.wepp_binaries == tuple(dict.fromkeys(get_linux_wepp_bin_opts()))
    assert authority.landuse_methods_by_representation["multiple-ofe"] == (
        "gridded",
        "upload",
    )


def test_historical_schema_v2_round_trip_never_adds_station_database_axis() -> None:
    resolved = resolve_builder_config(_selections(), capability_schema_version=2)
    authority = capability_authority(ParsedConfig(resolved.config_bytes.decode("utf-8")))

    assert authority is not None
    assert authority.schema_version == 2
    assert authority.climate_station_databases == ()
    assert "climate_station_databases" not in authority.as_config_sections()["capabilities"]
    assert "climate_station_database" not in authority.defaults


@pytest.mark.parametrize(
    (
        "profile_id",
        "runtime_token",
        "climates",
        "station_databases",
        "default_landuse",
    ),
    (
        (
            "continental-us",
            "us",
            (
                "vanilla_cligen",
                "prism_stochastic",
                "observed_daymet",
                "observed_gridmet",
            ),
            (
                "cligen-stations-legacy",
                "cligen-stations-2015",
                "cligen-stations-ghcn",
            ),
            "nlcd-2019",
        ),
        (
            "europe",
            "eu",
            ("vanilla_cligen", "eobs_modified"),
            ("cligen-stations-ghcn",),
            "corine-2018",
        ),
        (
            "canada",
            "canada",
            ("vanilla_cligen", "observed_daymet"),
            ("cligen-stations-ghcn",),
            "c3s-landcover-2020",
        ),
        (
            "australia",
            "au",
            ("vanilla_cligen", "agdc"),
            ("cligen-stations-ghcn",),
            "australia-landuse-2010-2011",
        ),
        (
            "global-earth",
            "earth",
            ("vanilla_cligen",),
            ("cligen-stations-ghcn",),
            "c3s-landcover-2020",
        ),
    ),
)
def test_schema_v3_profile_graphs_and_default_configs_match_authority(
    profile_id: str,
    runtime_token: str,
    climates: tuple[str, ...],
    station_databases: tuple[str, ...],
    default_landuse: str,
) -> None:
    binary_ids = ("wepp_260803", "latest")
    graph = build_locale_capability_graph(
        profile_id, binary_ids, _binary_revisions(binary_ids)
    )

    assert graph.schema_version == 3
    assert graph.climate_datasets == climates
    assert graph.climate_station_databases == station_databases
    assert graph.defaults["climate_dataset"] == "vanilla_cligen"
    assert graph.defaults["landuse_dataset"] == default_landuse
    assert graph.defaults["delineation_backend"] == "wbt"
    assert graph.defaults["watershed_representation"] == "single-ofe"
    assert graph.defaults["wepp_binary"] == "wepp_260803"
    profile = next(item for item in iter_locale_profiles() if item.profile_id == profile_id)
    assert graph.dem_sources == profile.dem_sources
    assert graph.soil_datasets == profile.soil_sources
    assert graph.landuse_datasets == profile.landuse_sources

    defaults = graph.defaults
    resolved = resolve_builder_config(BuilderSelections(
        locale=profile_id,
        dem=defaults["dem_source"],
        delineation_backend=defaults["delineation_backend"],
        watershed_representation=defaults["watershed_representation"],
        wepp_binary=defaults["wepp_binary"],
        soil=defaults["soil_dataset"],
        landuse=defaults["landuse_dataset"],
        climate=defaults["climate_dataset"],
        climate_station_database=defaults["climate_station_database"],
        capability_profile=f"{profile_id}-capabilities",
    ))
    assert resolved.config["general"]["locales"] == [runtime_token]
    assert resolved.config["general"]["dem_db"] == DEM_SOURCE_RUNTIME[defaults["dem_source"]]
    soil_runtime = SOIL_SOURCE_RUNTIME[defaults["soil_dataset"]]
    if soil_runtime is not None:
        assert resolved.config["soils"]["ssurgo_db"] == soil_runtime
    landcover = get_landcover_entry(defaults["landuse_dataset"])
    assert landcover is not None
    if profile_id != "australia":
        assert resolved.config["landuse"]["nlcd_db"] == landcover.runtime_value
    station_database = get_climate_station_database(defaults["climate_station_database"])
    assert station_database is not None
    assert resolved.config["climate"]["cligen_db"] == station_database.selector
    assert resolved.config["landuse"]["enable_landuse_change"] is True
    assert resolved.config["capabilities"]["schema_version"] == 3
    assert resolved.config["capability_defaults"]["climate_dataset"] == (
        "vanilla_cligen"
    )
    stored_authority = capability_authority(
        ParsedConfig(resolved.config_bytes.decode("utf-8"))
    )
    assert stored_authority is not None
    assert stored_authority.locale_profiles == (profile_id,)


def test_locale_dispatched_providers_do_not_own_runtime_selector_writes() -> None:
    components = load_registry().components

    for soil_id in ("esdac-europe", "asris-australia"):
        component = components[soil_id]
        assert ("soils", "ssurgo_db") not in component.owns
        assert all(write.key != ("soils", "ssurgo_db") for write in component.writes)

    australia = components["australia-landuse-2010-2011"]
    assert ("landuse", "nlcd_db") not in australia.owns
    assert all(write.key != ("landuse", "nlcd_db") for write in australia.writes)


@pytest.mark.parametrize(
    "profile_id",
    ("continental-us", "europe", "canada", "australia", "global-earth"),
)
def test_schema_v3_reader_rejects_hostile_climate_method_broadening(
    profile_id: str,
) -> None:
    binary_ids = ("wepp_260803",)
    graph = build_locale_capability_graph(
        profile_id, binary_ids, _binary_revisions(binary_ids)
    )
    source = graph.climate_datasets[0]
    hostile_relations = {
        **graph.climate_station_methods_by_dataset,
        source: (*graph.climate_station_methods_by_dataset[source], "user_defined"),
    }
    hostile = replace(
        graph,
        climate_station_methods=(*graph.climate_station_methods, "user_defined"),
        climate_station_methods_by_dataset=MappingProxyType(hostile_relations),
    )

    with pytest.raises(CapabilityGraphError, match=r"climate[_ ]station"):
        hostile.validate()


@pytest.mark.parametrize(
    "profile_id",
    ("continental-us", "europe", "canada", "australia", "global-earth"),
)
def test_schema_v3_parser_rejects_hostile_climate_method_broadening(
    profile_id: str,
) -> None:
    binary_ids = ("wepp_260803",)
    graph = build_locale_capability_graph(
        profile_id, binary_ids, _binary_revisions(binary_ids)
    )
    defaults = graph.defaults
    resolved = resolve_builder_config(BuilderSelections(
        locale=profile_id,
        dem=defaults["dem_source"],
        delineation_backend=defaults["delineation_backend"],
        watershed_representation=defaults["watershed_representation"],
        wepp_binary=defaults["wepp_binary"],
        soil=defaults["soil_dataset"],
        landuse=defaults["landuse_dataset"],
        climate=defaults["climate_dataset"],
        climate_station_database=defaults["climate_station_database"],
        capability_profile=f"{profile_id}-capabilities",
    ))
    config = ParsedConfig(resolved.config_bytes.decode("utf-8"))
    methods = ast.literal_eval(
        config._configparser.get("capabilities", "climate_station_methods")
    )
    methods.append("user_defined")
    config._configparser.set(
        "capabilities", "climate_station_methods", repr(methods)
    )
    source = graph.climate_datasets[0]
    relation = ast.literal_eval(
        config._configparser.get("capabilities.climate_station_methods", source)
    )
    relation.append("user_defined")
    config._configparser.set(
        "capabilities.climate_station_methods", source, repr(relation)
    )

    with pytest.raises(ValueError, match=r"climate[_ ]station"):
        capability_authority(config)


@pytest.mark.parametrize(
    ("stable_id", "selector"),
    (
        ("cligen-stations-legacy", "legacy"),
        ("cligen-stations-2015", "2015_stations.db"),
        ("cligen-stations-ghcn", "ghcn_stations.db"),
    ),
)
def test_schema_v3_station_database_selection_is_bound_to_exact_runtime_selector(
    stable_id: str, selector: str,
) -> None:
    selections = replace(_selections(), climate_station_database=stable_id)
    resolved = resolve_builder_config(selections)
    config = ParsedConfig(resolved.config_bytes.decode("utf-8"))

    authority = capability_authority(config)

    assert authority is not None
    assert authority.defaults["climate_station_database"] == stable_id
    assert config.config_get_raw("climate", "cligen_db") == f'"{selector}"'


@pytest.mark.parametrize(
    "hostile_selector",
    (
        "unknown-catalog",
        "legacy-2015",
        "tenerife_stations.db",
        "au_stations.db",
    ),
)
def test_schema_v3_station_database_runtime_mismatch_fails_closed(
    hostile_selector: str,
) -> None:
    config = _resolved_parser()
    config._configparser.set("climate", "cligen_db", f'"{hostile_selector}"')

    with pytest.raises(ValueError, match="does not match"):
        capability_authority(config)


def test_model_tuple_matrix_covers_every_advertised_value_without_cross_product() -> None:
    binary_ids = tuple(dict.fromkeys(get_linux_wepp_bin_opts()))
    graph = build_continental_us_capability_graph(
        binary_ids,
        _binary_revisions(binary_ids),
    )
    tuples = {tuple(token.split("|")) for token in graph.allowed_model_tuples}

    assert ("wbt", "multiple-ofe", "wepp_260803") in tuples
    assert all(
        backend != "topaz" or representation != "multiple-ofe"
        for backend, representation, _binary in tuples
    )
    assert {item[0] for item in tuples} == set(graph.delineation_backends)
    assert {item[1] for item in tuples} == set(graph.watershed_representations)
    assert {item[2] for item in tuples} == set(graph.wepp_binaries)


def test_stored_schema_v2_graph_validation_is_independent_of_live_catalogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary_ids = ("wepp_260803",)
    graph = build_continental_us_capability_graph(
        binary_ids,
        _binary_revisions(binary_ids),
    )

    def _live_catalog_access_is_forbidden(*_args, **_kwargs):
        raise AssertionError("stored graph validation consulted a live catalog")

    monkeypatch.setattr(
        capability_graph_module,
        "get_locale_profile",
        _live_catalog_access_is_forbidden,
    )
    monkeypatch.setattr(
        capability_graph_module,
        "iter_climate_datasets",
        _live_catalog_access_is_forbidden,
    )

    graph.validate()


def test_provider_revision_binds_every_advertised_binary_role_identity() -> None:
    binary_ids = ("wepp_260803", "wepp_dcc52a6")
    revisions = _binary_revisions(binary_ids)
    baseline = build_continental_us_capability_graph(binary_ids, revisions)
    changed_revisions = dict(revisions)
    changed_revisions["wepp_dcc52a6"] = (
        f"provider-v1:watershed={'c' * 64}:hillslope={'b' * 64}"
    )
    changed = build_continental_us_capability_graph(binary_ids, changed_revisions)

    assert baseline.provider_revision != changed.provider_revision
    assert baseline.wepp_binary_revisions == revisions


def test_provider_revision_binds_configured_climate_tokens_and_landcover_adapter() -> None:
    binary_ids = ("wepp_260803",)
    revisions = _binary_revisions(binary_ids)
    tokens = dict(default_climate_provider_tokens())
    baseline = build_continental_us_capability_graph(
        binary_ids, revisions, climate_provider_tokens=tokens
    )
    tokens["daymet_observed"] = "daymet/test-revision"
    changed = build_continental_us_capability_graph(
        binary_ids, revisions, climate_provider_tokens=tokens
    )

    assert baseline.provider_revision != changed.provider_revision
    assert landcover_catalog_revision("landuse-catalog-adapter-v1") != (
        landcover_catalog_revision("landuse-catalog-adapter-v2")
    )


@pytest.mark.parametrize(
    ("relation_token", "message"),
    [
        ("unknown:thing", "unknown relation axis"),
        ("wepp_binary:not-a-binary", "unknown relation target"),
        ("wepp_260803", "malformed relation token"),
    ],
)
def test_mod_dependency_tokens_use_closed_axis_and_target_grammar(
    relation_token: str,
    message: str,
) -> None:
    binary_ids = tuple(dict.fromkeys(get_linux_wepp_bin_opts()))
    graph = build_continental_us_capability_graph(
        binary_ids,
        _binary_revisions(binary_ids),
    )
    hostile = replace(
        graph,
        mods=("disturbed",),
        mod_requires=MappingProxyType({"disturbed": (relation_token,)}),
        mod_conflicts=MappingProxyType({"disturbed": ()}),
    )

    with pytest.raises(CapabilityGraphError, match=message):
        hostile.validate()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda parser: parser.remove_section("capabilities.mod_requires"), "sections must be complete"),
        (lambda parser: parser.set("capabilities", "unknown_axis", "[]"), "no unknown axes"),
        (lambda parser: parser.set("capabilities", "climate_datasets", "[]"), "must not be empty"),
        (
            lambda parser: parser.set(
                "capabilities", "climate_datasets", '["vanilla_cligen", "vanilla_cligen"]'
            ),
            "must not contain duplicates",
        ),
        (lambda parser: parser.set("capabilities", "schema_version", "3"), "complete"),
        (
            lambda parser: parser.set("capabilities", "provider_revision", '"' + "A" * 64 + '"'),
            "SHA-256",
        ),
        (
            lambda parser: parser.set(
                "capabilities.climate_station_methods", "orphan_dataset", '["auto"]'
            ),
            "keys must exhaust",
        ),
    ],
)
def test_schema_v2_hostile_mutations_fail_closed(mutation, message: str) -> None:
    config = _historical_parser()
    mutation(config._configparser)

    with pytest.raises(ValueError, match=message):
        capability_authority(config)


def test_graph_rejects_oversized_tuples_orphan_methods_and_unknown_domains() -> None:
    binary_ids = ("wepp_260803",)
    graph = build_continental_us_capability_graph(binary_ids, _binary_revisions(binary_ids))

    with pytest.raises(CapabilityGraphError, match="too many"):
        replace(graph, allowed_model_tuples=(graph.allowed_model_tuples[0],) * 4097).validate()
    with pytest.raises(CapabilityGraphError, match="orphaned"):
        replace(
            graph,
            climate_station_methods=(*graph.climate_station_methods, "user_defined"),
        ).validate()
    with pytest.raises(CapabilityGraphError, match="unknown domain ID"):
        replace(graph, delineation_backends=("topaz", "wbt", "invented")).validate()
    with pytest.raises(CapabilityGraphError, match="invalid role identity"):
        replace(
            graph,
            wepp_binary_revisions=MappingProxyType({"wepp_260803": "forged"}),
        ).validate()


@pytest.mark.parametrize(
    ("axis", "hostile_id", "relation_sections", "default_key"),
    (
        ("dem_sources", "hostile_dem", (), "dem_source"),
        (
            "climate_datasets",
            "hostile_climate",
            (
                "capabilities.climate_station_methods",
                "capabilities.climate_spatial_methods",
                "capabilities.climate_station_defaults",
                "capabilities.climate_spatial_defaults",
            ),
            "climate_dataset",
        ),
        (
            "soil_datasets",
            "hostile_soil",
            ("capabilities.soil_builders", "capabilities.soil_builder_defaults"),
            "soil_dataset",
        ),
        (
            "landuse_datasets",
            "hostile_landuse",
            ("capabilities.landuse_methods", "capabilities.landuse_method_defaults"),
            "landuse_dataset",
        ),
    ),
)
def test_schema_v2_reader_rejects_closed_domain_dataset_ids(
    axis: str,
    hostile_id: str,
    relation_sections: tuple[str, ...],
    default_key: str,
) -> None:
    config = _historical_parser()
    parser = config._configparser
    parser.set("capabilities", axis, f'["{hostile_id}"]')
    parser.set("capability_defaults", default_key, f'"{hostile_id}"')
    for section in relation_sections:
        options = tuple(parser.options(section))
        value = parser.get(section, options[0])
        for option in options:
            parser.remove_option(section, option)
        parser.set(section, hostile_id, value)

    with pytest.raises(ValueError, match=f"{axis} is not authorized"):
        capability_authority(config)


def test_graph_rejects_known_non_builder_values_and_incompatible_edges() -> None:
    binary_ids = ("wepp_260803",)
    graph = build_continental_us_capability_graph(
        binary_ids, _binary_revisions(binary_ids)
    )

    with pytest.raises(CapabilityGraphError, match="not authorized"):
        replace(
            graph,
            dem_sources=("australia-srtm-1s",),
            defaults=MappingProxyType({**graph.defaults, "dem_source": "australia-srtm-1s"}),
        ).validate()
    with pytest.raises(CapabilityGraphError):
        replace(graph, climate_datasets=("future_cmip5",)).validate()
    with pytest.raises(CapabilityGraphError, match="climate spatial adjacency"):
        replace(
            graph,
            climate_spatial_methods_by_dataset=MappingProxyType({
                **graph.climate_spatial_methods_by_dataset,
                "vanilla_cligen": ("single", "multiple", "interpolated"),
            }),
        ).validate()
    with pytest.raises(CapabilityGraphError, match="landuse representation adjacency"):
        replace(
            graph,
            landuse_methods_by_representation=MappingProxyType({
                "single-ofe": ("gridded", "single", "upload"),
                "multiple-ofe": ("gridded", "single", "upload"),
            }),
        ).validate()
    with pytest.raises(CapabilityGraphError, match="model tuple"):
        replace(
            graph,
            allowed_model_tuples=(
                *graph.allowed_model_tuples,
                "topaz|multiple-ofe|wepp_260803",
            ),
        ).validate()


def test_graph_rejects_directly_contradictory_mod_relations() -> None:
    binary_ids = ("wepp_260803",)
    graph = build_continental_us_capability_graph(binary_ids, _binary_revisions(binary_ids))
    hostile = replace(
        graph,
        mods=("disturbed",),
        mod_requires=MappingProxyType({"disturbed": ("wepp_binary:wepp_260803",)}),
        mod_conflicts=MappingProxyType({"disturbed": ("wepp_binary:wepp_260803",)}),
    )
    with pytest.raises(CapabilityGraphError, match="both require and conflict"):
        hostile.validate()


def test_schema_v1_only_constrains_present_axes() -> None:
    config = ParsedConfig(
        "[capabilities]\n"
        'climate_datasets = ["vanilla_cligen"]\n'
        "mods = []\n"
    )

    assert capability_authority(config) is None
    assert capability_ids(config, "climate_datasets") == frozenset({"vanilla_cligen"})
    assert capability_ids(config, "soil_builders") is None
    assert capability_ids(config, "mods") == frozenset()


def test_explicit_schema_v1_is_rejected_instead_of_inferred_as_v2() -> None:
    config = ParsedConfig(
        "[capabilities]\n"
        "schema_version = 1\n"
        'climate_datasets = ["vanilla_cligen"]\n'
    )

    with pytest.raises(ValueError, match="unsupported capabilities.schema_version: 1"):
        capability_authority(config)


def test_schema_v1_present_empty_mandatory_axis_is_invalid() -> None:
    config = ParsedConfig("[capabilities]\nclimate_datasets = []\n")
    with pytest.raises(ValueError, match="must not be empty"):
        capability_ids(config, "climate_datasets")


def test_schema_v1_landuse_axis_restricts_runtime_resolution() -> None:
    config = ParsedConfig(
        "[capabilities]\n"
        'landuse_datasets = ["nlcd-2019"]\n'
    )

    assert resolve_landuse_runtime_dataset(config, "nlcd-2019") == "nlcd/2019"
    assert resolve_landuse_runtime_dataset(config, "nlcd/2019") == "nlcd/2019"
    assert resolve_landuse_runtime_dataset(config, "nlcd/2018") is None


def test_named_preset_capability_snapshot_reads_only_nodb_mods() -> None:
    snapshot = resolve_named_preset_capabilities({
        "general": {"locales": ["us"]},
        "nodb": {"mods": ["disturbed"]},
        "unrelated_section": {"enabled": True},
    })

    assert snapshot["mods"] == ["disturbed"]
