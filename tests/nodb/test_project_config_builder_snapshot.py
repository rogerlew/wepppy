from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from wepppy.nodb.config_builder.resolver import BuilderConstraintError
from wepppy.nodb.config_builder.snapshot import builder_writer_enabled, parse_builder_selections, resolve_builder_candidate
from wepppy.project_config_serialization import parse_config_text
from wepppy.nodb.base import CaseSensitiveRawConfigParser
from wepppy.nodb.project_config_reader import load_project_config, project_config_manifest_source_kind
from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot

pytestmark = pytest.mark.unit


def _payload(**updates):
    payload = {"locale": "continental-us", "dem": "usgs-ned13-2022", "delineation_backend": "wbt", "watershed_representation": "single-ofe", "wepp_binary": "wepp_260803", "soil": "ssurgo-gnatsgso-2025", "landuse": "nlcd-2019", "climate": "vanilla_cligen", "climate_station_database": "cligen-stations-2015", "mods": []}
    payload.update(updates)
    return payload


def test_builder_flag_is_strict_and_default_off() -> None:
    assert not builder_writer_enabled({})
    assert builder_writer_enabled({"WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED": "yes"})
    with pytest.raises(ValueError):
        builder_writer_enabled({"WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED": "maybe"})


def test_builder_candidate_has_fixed_token_manifest_and_review() -> None:
    candidate = resolve_builder_candidate(parse_builder_selections(_payload()), resolved_at=datetime(2026, 8, 26, tzinfo=timezone.utc))
    config = parse_config_text(candidate.artifact.config_bytes.decode())
    manifest = json.loads(candidate.artifact.manifest_bytes)
    assert candidate.artifact.config_filename == "config.cfg"
    assert config["general"]["cellsize"] == 10
    assert config["wepp"]["bin"] == "wepp_260803"
    assert config["wepp"]["multi_ofe"] is False
    assert manifest["source_kind"] == "builder"
    assert manifest["source_preset"] is None
    assert manifest["selections"]["cellsize_source"] == "dem_default"
    assert manifest["selections"]["wepp_binary"] == "wepp_260803"
    assert manifest["selections"]["climate_station_database"] == "cligen-stations-2015"
    assert manifest["config"]["filename"] == "config.cfg"
    assert manifest["source_revision"] == "dev"


def test_builder_pair_reopens_without_shared_fallback(tmp_path, monkeypatch) -> None:
    candidate = resolve_builder_candidate(parse_builder_selections(_payload()))
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "1")
    result = load_project_config(
        wd=tmp_path,
        config_token="config",
        parent_wd=None,
        config_dir=tmp_path / "missing",
        defaults_resolver=lambda _wd=None: str(tmp_path / "missing-defaults.cfg"),
        parser_factory=CaseSensitiveRawConfigParser,
        run_id="builder-fixture",
    )
    assert result.status.mode == "flattened"
    assert result.status.manifest_valid is True
    assert project_config_manifest_source_kind(tmp_path, "config.cfg") == "builder"

    (tmp_path / "config-manifest.json").write_text("not-json\n", encoding="utf-8")
    assert project_config_manifest_source_kind(tmp_path, "config.cfg") is None


def test_payload_rejects_unknown_fields_and_invalid_cellsize() -> None:
    with pytest.raises(BuilderConstraintError) as unknown:
        parse_builder_selections(_payload(config="evil"))
    assert unknown.value.code == "unknown_field"
    with pytest.raises(BuilderConstraintError) as invalid:
        resolve_builder_candidate(parse_builder_selections(_payload(cellsize_override=17)))
    assert invalid.value.field == "cellsize_override"


@pytest.mark.parametrize("locale", ["continental-us", "europe", "canada", "australia", "global-earth"])
def test_builder_always_materializes_disturbed_and_compatible_mapping(locale):
    from dataclasses import replace
    from wepppy.nodb.config_builder.resolver import resolve_builder_capability_graph
    from wepppy.nodb.config_builder.schema import BuilderSelections
    from wepppy.wepp.management import load_map

    graph = resolve_builder_capability_graph(locale)
    defaults = graph.defaults
    selections = BuilderSelections(
        locale=locale, dem=defaults["dem_source"], soil=defaults["soil_dataset"],
        landuse=defaults["landuse_dataset"], climate=defaults["climate_dataset"],
        climate_station_database=defaults["climate_station_database"],
        capability_profile=f"{locale}-capabilities", delineation_backend="wbt",
        watershed_representation="single-ofe", wepp_binary=defaults["wepp_binary"],
    )
    required = {f"{cover} {severity} sev fire" for cover in ("forest", "shrub", "grass")
                for severity in ("low", "moderate", "high")}
    for source in graph.landuse_datasets:
        candidate = resolve_builder_candidate(replace(selections, landuse=source))
        config = parse_config_text(candidate.artifact.config_bytes.decode())
        assert config["nodb"]["mods"] == ["disturbed"]
        assert json.loads(candidate.artifact.manifest_bytes)["selections"]["mods"] == []
        mapping = load_map(config["landuse"]["mapping"])
        assert required <= {entry["DisturbedClass"] for entry in mapping.values()}, source
        assert candidate.resolved.effective_writers[("landuse", "mapping")] == source


@pytest.mark.parametrize("representation", ["single-ofe", "multiple-ofe"])
@pytest.mark.parametrize("climate_id", ["vanilla_cligen", "observed_prism_800m"])
def test_single_inputs_are_independent_creation_capabilities(representation, climate_id):
    candidate = resolve_builder_candidate(parse_builder_selections(_payload(
        single_user_defined_uploads=True, watershed_representation=representation,
        climate=climate_id,
    )))
    config = parse_config_text(candidate.artifact.config_bytes.decode())
    manifest = json.loads(candidate.artifact.manifest_bytes)
    assert config["nodb"]["mods"] == []
    assert config["nodb"]["single_user_defined_uploads"] is True
    assert config["watershed"]["mofe_buffer"] is False
    assert manifest["selections"]["single_user_defined_uploads"] is True
    assert config["capabilities"]["wepp_binaries"] == ["wepp_260803"]
    assert "observed_prism_800m" in config["capabilities"]["climate_datasets"]
    for section in ("capabilities.landuse_methods", "capabilities.soil_builders",
                    "capabilities.landuse_methods_by_representation"):
        assert all("single-user-defined" in methods for methods in config[section].values())
    ordinary = resolve_builder_candidate(parse_builder_selections(_payload()))
    normal_config = parse_config_text(ordinary.artifact.config_bytes.decode())
    assert normal_config["nodb"]["mods"] == ["disturbed"]
    assert "single-user-defined" not in normal_config["capabilities"]["soil_builders"]
    assert config["landuse"].get("mode") == normal_config["landuse"].get("mode")
    assert config["soils"].get("mode") == normal_config["soils"].get("mode")


@pytest.mark.parametrize("value", [None, 0, 1, "true", "false", [], {}])
def test_single_input_builder_boolean_is_not_coerced(value):
    with pytest.raises(BuilderConstraintError, match="must be a boolean"):
        parse_builder_selections(_payload(single_user_defined_uploads=value))


def test_single_input_native_binary_is_explicit():
    with pytest.raises(BuilderConstraintError, match="require wepp_260803"):
        resolve_builder_candidate(parse_builder_selections(_payload(
            single_user_defined_uploads=True, wepp_binary="latest",
        )))
