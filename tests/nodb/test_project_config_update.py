from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from configparser import RawConfigParser
import hashlib
import json
from pathlib import Path

import pytest

import wepppy.nodb.config_builder.resolver as builder_resolver
from wepppy.nodb.project_config_snapshot import (
    materialize_preset_snapshot,
    resolve_preset_snapshot,
)
from wepppy.nodb.config_builder.snapshot import resolve_builder_candidate
from wepppy.nodb.config_builder.schema import BuilderSelections
from wepppy.nodb.project_config_update import (
    JOURNAL_NAME,
    StaleConfigPreviewError,
    apply_project_config_update,
    preview_project_config_update,
    project_config_digest_warning,
    project_config_lifecycle_guard,
    project_config_update_enabled,
    recover_project_config_update,
    ConfigUpdateUnavailableError,
)
from wepppy.nodb.project_config_reader import load_project_config
from wepppy.project_config_serialization import parse_config_text, serialize_config

pytestmark = pytest.mark.unit


_HISTORICAL_V2_CONFIG = b'''[capabilities]
allowed_model_tuples = ["topaz|single-ofe|wepp_260803", "wbt|single-ofe|wepp_260803", "wbt|multiple-ofe|wepp_260803"]
climate_datasets = ["vanilla_cligen", "prism_stochastic", "observed_daymet", "observed_gridmet"]
climate_spatial_methods = ["single", "multiple", "interpolated"]
climate_station_methods = ["auto", "distance", "multi_factor"]
delineation_backends = ["topaz", "wbt"]
dem_sources = ["usgs-ned1-2024", "usgs-ned13-2022"]
landuse_datasets = ["nlcd-2019"]
landuse_methods = ["gridded", "single", "upload"]
locale_profiles = ["continental-us"]
mods = []
provider_revision = "5e60cccfa40a5f880179fffb4de8d9e8315c7ae3aec42dd4e0078b5a68e2272b"
schema_version = 2
soil_builders = ["gridded", "single_mukey", "single_database"]
soil_datasets = ["ssurgo-gnatsgso-2025"]
watershed_representations = ["single-ofe", "multiple-ofe"]
wepp_binaries = ["wepp_260803"]

[capabilities.climate_spatial_methods]
observed_daymet = ["single", "multiple", "interpolated"]
observed_gridmet = ["single", "multiple", "interpolated"]
prism_stochastic = ["single", "multiple"]
vanilla_cligen = ["single", "multiple"]

[capabilities.climate_spatial_defaults]
observed_daymet = "single"
observed_gridmet = "single"
prism_stochastic = "single"
vanilla_cligen = "single"

[capabilities.climate_station_methods]
observed_daymet = ["auto", "distance", "multi_factor"]
observed_gridmet = ["auto", "distance", "multi_factor"]
prism_stochastic = ["auto", "distance", "multi_factor"]
vanilla_cligen = ["auto", "distance", "multi_factor"]

[capabilities.climate_station_defaults]
observed_daymet = "auto"
observed_gridmet = "auto"
prism_stochastic = "auto"
vanilla_cligen = "auto"

[capabilities.landuse_methods]
nlcd-2019 = ["gridded", "single", "upload"]

[capabilities.landuse_method_defaults]
nlcd-2019 = "gridded"

[capabilities.landuse_methods_by_representation]
multiple-ofe = ["gridded", "upload"]
single-ofe = ["gridded", "single", "upload"]

[capabilities.soil_builders]
ssurgo-gnatsgso-2025 = ["gridded", "single_mukey", "single_database"]

[capabilities.soil_builder_defaults]
ssurgo-gnatsgso-2025 = "gridded"

[capabilities.wepp_binary_revisions]
wepp_260803 = "provider-v1:watershed=4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5:hillslope=86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7"

[capabilities.mod_requires]

[capabilities.mod_conflicts]

[capability_defaults]
climate_dataset = "vanilla_cligen"
delineation_backend = "wbt"
dem_source = "usgs-ned13-2022"
landuse_dataset = "nlcd-2019"
locale_profile = "continental-us"
soil_dataset = "ssurgo-gnatsgso-2025"
watershed_representation = "single-ofe"
wepp_binary = "wepp_260803"

[climate]
cligen_db = "2015_stations.db"

[config]
flattened = true
resolver_version = 1
schema_version = 1

[wepp]
bin = "wepp_260803"
multi_ofe = false
'''

_HISTORICAL_V2_PARENT_CHAIN = [
    {"id": "shared-defaults", "kind": "defaults", "revision": "pre-wp12c-defaults"},
    {"id": "continental-us", "kind": "locale", "revision": "locale-profile-WP12B-1"},
    {"id": "usgs-ned13-2022", "kind": "dem", "revision": "dem-database-adapter-v1:ned13-2022"},
    {"id": "wbt", "kind": "delineation", "revision": "weppcloud-wbt-adapter-v1:wbt"},
    {"id": "single-ofe", "kind": "representation", "revision": "wepp-representation-contract-v1:single-ofe"},
    {"id": "wepp_260803", "kind": "wepp_binary", "revision": "pre-wp12c-wepp-provider"},
    {"id": "ssurgo-gnatsgso-2025", "kind": "soil", "revision": "soils-database-adapter-v1:ssurgo-gnatsgso-2025"},
    {"id": "nlcd-2019", "kind": "landuse", "revision": "pre-wp12c-nlcd-provider"},
    {"id": "vanilla_cligen", "kind": "climate", "revision": "pre-wp12c-climate-provider"},
    {"id": "continental-us-capabilities", "kind": "capability", "revision": "pre-wp12c-provider-v2"},
]


def _historical_v2_builder_project(tmp_path: Path) -> tuple[Path, Path]:
    config_path = tmp_path / "config.cfg"
    manifest_path = tmp_path / "config-manifest.json"
    config_path.write_bytes(_HISTORICAL_V2_CONFIG)
    manifest = {
        "schema_version": 1,
        "resolver_version": 1,
        "source_kind": "builder",
        "source_preset": None,
        "source_revision": "pre-wp12c-fixture",
        "resolved_at": "2026-08-26T00:00:00Z",
        "parent_chain": _HISTORICAL_V2_PARENT_CHAIN,
        "selections": {
            "locale": "continental-us",
            "dem": "usgs-ned13-2022",
            "delineation_backend": "wbt",
            "watershed_representation": "single-ofe",
            "wepp_binary": "wepp_260803",
            "soil": "ssurgo-gnatsgso-2025",
            "landuse": "nlcd-2019",
            "climate": "vanilla_cligen",
            "capability_profile": "continental-us-capabilities",
            "mods": [],
            "cellsize": 10,
            "cellsize_source": "dem_default",
        },
        "config": {
            "filename": "config.cfg",
            "sha256": hashlib.sha256(_HISTORICAL_V2_CONFIG).hexdigest(),
        },
        "amendments": [],
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return config_path, manifest_path


def _old_preset_project(tmp_path: Path) -> tuple[Path, tuple[str, str]]:
    candidate = resolve_preset_snapshot(
        "disturbed9002_wbt",
        {},
        source_revision="deployment-a",
        resolved_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    materialize_preset_snapshot(tmp_path, candidate)
    config_path = tmp_path / candidate.config_filename
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    target = ("unitizer", "is_english")
    assert target[0] in config and target[1] in config[target[0]]
    del config[target[0]][target[1]]
    if not config[target[0]]:
        del config[target[0]]
    old_bytes = serialize_config(config)
    config_path.write_bytes(old_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(old_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return config_path, target


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.iterdir()
        if path.is_file() and path.name in {"config-manifest.json", "disturbed9002_wbt.cfg"}
    }


def test_update_flag_is_strict_and_default_off() -> None:
    assert project_config_update_enabled({}) is False
    assert project_config_update_enabled({"WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED": "true"}) is True
    with pytest.raises(ValueError, match="strict boolean"):
        project_config_update_enabled({"WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED": "sometimes"})


def test_preview_is_read_only_and_lists_complete_registered_delta(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    before = _snapshot(tmp_path)

    preview = preview_project_config_update(tmp_path)

    assert preview.available is True
    assert preview.preview_id and preview.preview_id.startswith("pcu1-")
    assert preview.digest_warning is False
    assert preview.declared_digest == preview.current_digest
    assert [(item.section, item.option) for item in preview.additions] == [target]
    assert preview.additions[0].source_id in {"shared-defaults", "disturbed9002_wbt"}
    assert _snapshot(tmp_path) == before
    assert not (tmp_path / ".config-amendment.lock").exists()


def test_apply_adds_missing_value_preserves_existing_and_records_provenance(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    before = parse_config_text(config_path.read_text(encoding="utf-8"))
    preview = preview_project_config_update(tmp_path)

    result = apply_project_config_update(
        tmp_path,
        preview.preview_id or "",
        trigger_section=target[0],
        trigger_option=target[1],
        application_revision="worker-revision-a",
        resolved_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
    )

    after = parse_config_text(config_path.read_text(encoding="utf-8"))
    for section, options in before.items():
        for option, value in options.items():
            assert after[section][option] == value
    assert target[1] in after[target[0]]
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    amendment = manifest["amendments"][-1]
    assert result.sequence == amendment["sequence"] == 1
    assert amendment["application_revision"] == "worker-revision-a"
    assert amendment["reason"] == "missing_registered_attribute_merge"
    assert amendment["additions"][0]["source_revision"]
    assert manifest["config"]["sha256"] == result.resulting_digest
    assert not (tmp_path / JOURNAL_NAME).exists()
    assert preview_project_config_update(tmp_path).available is False


def test_digest_mismatch_is_recorded_from_actual_config_not_blocked(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    actual_prior = hashlib.sha256(config_path.read_bytes()).hexdigest()
    preview = preview_project_config_update(tmp_path)
    assert preview.digest_warning is True
    assert preview.declared_digest == "0" * 64
    assert project_config_digest_warning(tmp_path) is True

    result = apply_project_config_update(
        tmp_path, preview.preview_id or "", trigger_section=target[0],
        trigger_option=target[1], application_revision="worker-revision-a",
    )

    amended = json.loads(manifest_path.read_text(encoding="utf-8"))["amendments"][-1]
    assert result.prior_digest == amended["prior_sha256"] == actual_prior
    assert amended["resulting_sha256"] == result.resulting_digest


def test_stale_preview_rejects_without_mutation(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    config.setdefault("user", {})["retained"] = "value"
    config_path.write_bytes(serialize_config(config))
    before = _snapshot(tmp_path)

    with pytest.raises(StaleConfigPreviewError):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
        )

    assert _snapshot(tmp_path) == before


def test_arbitrary_trigger_rejects_complete_batch_without_mutation(tmp_path: Path) -> None:
    _config_path, _target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)
    before = _snapshot(tmp_path)
    with pytest.raises(ConfigUpdateUnavailableError, match="Trigger"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section="misspelled",
            trigger_option="attribute", application_revision="worker-revision-a",
        )
    assert _snapshot(tmp_path) == before


def test_builder_preview_uses_only_recorded_active_component_chain(tmp_path: Path) -> None:
    selections = BuilderSelections(
        locale="continental-us", dem="usgs-ned13-2022", delineation_backend="wbt",
        watershed_representation="single-ofe", soil="ssurgo-gnatsgso-2025",
        wepp_binary="wepp_260803",
        landuse="nlcd-2019", climate="vanilla_cligen",
    )
    candidate = resolve_builder_candidate(
        selections, resolved_at=datetime(2026, 8, 1, tzinfo=timezone.utc)
    )
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    config_path = tmp_path / "config.cfg"
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    owned = sorted(
        (key, writer) for key, writer in candidate.resolved.effective_writers.items()
        if writer not in {"shared-defaults", "resolver-v1", "selection:cellsize", "selection:mods"}
        and key[0] != "capability_defaults"
        and not key[0].startswith("capabilities")
        and key != ("climate", "cligen_db")
    )
    (section, option), expected_writer = owned[0]
    del config[section][option]
    old_bytes = serialize_config(config)
    config_path.write_bytes(old_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(old_bytes).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    preview = preview_project_config_update(tmp_path)

    addition = next(item for item in preview.additions if (item.section, item.option) == (section, option))
    assert addition.source_id == expected_writer


def test_frozen_pre_wp12c_v2_reopens_previews_and_applies_without_recomposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest_path = _historical_v2_builder_project(tmp_path)
    before_config = config_path.read_bytes()
    before_manifest = manifest_path.read_bytes()
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "1")

    loaded = load_project_config(
        wd=tmp_path,
        config_token="config",
        parent_wd=None,
        config_dir=tmp_path / "missing",
        defaults_resolver=lambda _wd=None: str(tmp_path / "missing-defaults.cfg"),
        parser_factory=RawConfigParser,
        run_id="historical-v2-builder",
    )

    assert loaded.status.mode == "flattened"
    assert loaded.status.manifest_valid is True
    assert loaded.parser.getint("capabilities", "schema_version") == 2
    assert config_path.read_bytes() == before_config
    assert manifest_path.read_bytes() == before_manifest

    monkeypatch.setattr(
        builder_resolver,
        "_historical_capability_graph_for_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("historical update consulted the live capability graph")
        ),
    )
    preview = preview_project_config_update(tmp_path)

    assert preview.available is True
    assert all(not item.section.startswith("capabilities") for item in preview.additions)
    assert all(item.section != "capability_defaults" for item in preview.additions)
    assert config_path.read_bytes() == before_config
    assert manifest_path.read_bytes() == before_manifest

    trigger = preview.additions[0]
    apply_project_config_update(
        tmp_path,
        preview.preview_id or "",
        trigger_section=trigger.section,
        trigger_option=trigger.option,
        application_revision="wp12c-frozen-v2-test",
    )

    resulting_config = config_path.read_text(encoding="utf-8")
    resulting_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "climate_station_databases" not in resulting_config
    assert "climate_station_database" not in resulting_manifest["selections"]
    assert resulting_manifest["parent_chain"] == _HISTORICAL_V2_PARENT_CHAIN


def test_schema_v3_update_uses_stored_graph_and_never_recomposes_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    selections = BuilderSelections(
        locale="europe", dem="europe-eudem-v1-1", delineation_backend="wbt",
        watershed_representation="single-ofe", wepp_binary="wepp_260803",
        soil="esdac-europe", landuse="corine-2018", climate="vanilla_cligen",
        climate_station_database="cligen-stations-ghcn",
        capability_profile="europe-capabilities",
    )
    candidate = resolve_builder_candidate(selections)
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    config_path = tmp_path / "config.cfg"
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    del config["unitizer"]["is_english"]
    old_bytes = serialize_config(config)
    config_path.write_bytes(old_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(old_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        builder_resolver,
        "_capability_graph_for_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("schema-v3 update consulted the live capability graph")
        ),
    )

    preview = preview_project_config_update(tmp_path)

    assert [(item.section, item.option) for item in preview.additions] == [
        ("unitizer", "is_english")
    ]
    apply_project_config_update(
        tmp_path,
        preview.preview_id or "",
        trigger_section="unitizer",
        trigger_option="is_english",
        application_revision="wp12c-frozen-v3-test",
    )
    resulting = parse_config_text(config_path.read_text(encoding="utf-8"))
    for section, options in config.items():
        if section.startswith("capabilities") or section == "capability_defaults":
            assert resulting[section] == options


def test_partial_stored_v3_graph_blocks_preview_without_writes(tmp_path: Path) -> None:
    selections = BuilderSelections(
        locale="europe", dem="europe-eudem-v1-1", delineation_backend="wbt",
        watershed_representation="single-ofe", wepp_binary="wepp_260803",
        soil="esdac-europe", landuse="corine-2018", climate="vanilla_cligen",
        climate_station_database="cligen-stations-ghcn",
        capability_profile="europe-capabilities",
    )
    candidate = resolve_builder_candidate(selections)
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    config_path = tmp_path / "config.cfg"
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    del config["capabilities.climate_station_methods"]["eobs_modified"]
    hostile_bytes = serialize_config(config)
    config_path.write_bytes(hostile_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(hostile_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    before = (config_path.read_bytes(), manifest_path.read_bytes())

    with pytest.raises(ConfigUpdateUnavailableError, match="authority is invalid"):
        preview_project_config_update(tmp_path)

    assert (config_path.read_bytes(), manifest_path.read_bytes()) == before


def test_pre_binary_builder_manifest_remains_runnable_but_update_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_bytes = serialize_config({
        "config": {"flattened": True, "resolver_version": 1, "schema_version": 1},
        "wepp": {"bin": "wepp_dcc52a6", "multi_ofe": False},
    })
    (tmp_path / "config.cfg").write_bytes(config_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = {
        "schema_version": 1,
        "resolver_version": 1,
        "source_kind": "builder",
        "source_preset": None,
        "source_revision": "pre-binary-builder",
        "resolved_at": "2026-08-26T22:00:00Z",
        "parent_chain": [
            {"kind": "defaults", "id": "shared-defaults", "revision": "old-defaults"},
            {"kind": "locale", "id": "continental-us", "revision": "1"},
            {"kind": "dem", "id": "usgs-ned13-2022", "revision": "1"},
            {"kind": "delineation", "id": "wbt", "revision": "1"},
            {"kind": "representation", "id": "single-ofe", "revision": "1"},
        ],
        "selections": {
            "locale": "continental-us", "dem": "usgs-ned13-2022",
            "delineation_backend": "wbt", "watershed_representation": "single-ofe",
            "soil": "ssurgo-gnatsgso-2025", "landuse": "nlcd-2019",
            "climate": "vanilla_cligen", "capability_profile": "continental-us-capabilities",
            "mods": [], "cellsize": 10, "cellsize_source": "dem_default",
        },
        "config": {"filename": "config.cfg", "sha256": hashlib.sha256(config_bytes).hexdigest()},
        "amendments": [],
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "1")
    loaded = load_project_config(
        wd=tmp_path,
        config_token="config",
        parent_wd=None,
        config_dir=tmp_path / "missing",
        defaults_resolver=lambda _wd=None: str(tmp_path / "missing-defaults.cfg"),
        parser_factory=RawConfigParser,
        run_id="pre-binary-builder",
    )
    assert loaded.status.manifest_valid is True
    assert loaded.parser.get("wepp", "bin") == '"wepp_dcc52a6"'
    with pytest.raises(ConfigUpdateUnavailableError, match="selections are incomplete"):
        preview_project_config_update(tmp_path)


def test_invalid_recorded_chain_produces_no_preview_or_write(tmp_path: Path) -> None:
    _old_preset_project(tmp_path)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parent_chain"][1]["id"] = "unregistered-preset"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    before = _snapshot(tmp_path)
    with pytest.raises(ConfigUpdateUnavailableError, match="parent chain"):
        preview_project_config_update(tmp_path)
    assert _snapshot(tmp_path) == before


def test_concurrent_applies_produce_one_amendment(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def apply_once():
        return apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(apply_once) for _index in range(2)]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except ConfigUpdateUnavailableError:
            outcomes.append(None)
    assert sum(item is not None for item in outcomes) == 1
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["amendments"]) == 1


def test_lifecycle_guard_blocks_update_until_copy_window_finishes(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with project_config_lifecycle_guard(tmp_path):
            future = executor.submit(
                apply_project_config_update,
                tmp_path,
                preview.preview_id or "",
                trigger_section=target[0],
                trigger_option=target[1],
                application_revision="wp10-test",
            )
            with pytest.raises(FutureTimeoutError):
                future.result(timeout=0.1)
        result = future.result(timeout=5)

    assert result.applied is True
    assert not (tmp_path / JOURNAL_NAME).exists()


def test_reader_recovers_interrupted_replacement_before_serving(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def fail_after_config(stage: str) -> None:
        if stage == "config_replaced":
            raise RuntimeError("worker stopped")

    with pytest.raises(RuntimeError, match="worker stopped"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
            fault_hook=fail_after_config,
        )

    result = load_project_config(
        wd=tmp_path, config_token="disturbed9002_wbt", parent_wd=None,
        config_dir=tmp_path, defaults_resolver=lambda _wd: str(tmp_path / "unused.cfg"),
        parser_factory=RawConfigParser, run_id="run-1",
    )

    assert result.parser.has_option(target[0], target[1])
    assert result.status.updates_enabled is True
    assert not (tmp_path / JOURNAL_NAME).exists()


@pytest.mark.parametrize(
    ("stage", "expected_applied"),
    [("journal_committed", False), ("config_replaced", True), ("manifest_replaced", True)],
)
def test_crash_recovery_returns_one_consistent_pair(
    tmp_path: Path, stage: str, expected_applied: bool,
) -> None:
    config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def fail_at(current: str) -> None:
        if current == stage:
            raise RuntimeError(f"fault at {stage}")

    with pytest.raises(RuntimeError, match="fault at"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
            fault_hook=fail_at,
        )
    assert (tmp_path / JOURNAL_NAME).exists()

    assert recover_project_config_update(tmp_path) is True

    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    assert (target[0] in config and target[1] in config[target[0]]) is expected_applied
    assert bool(manifest["amendments"]) is expected_applied
    assert manifest["config"]["sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert not (tmp_path / JOURNAL_NAME).exists()
