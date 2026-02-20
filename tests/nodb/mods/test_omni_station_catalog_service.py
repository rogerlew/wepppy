from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_station_catalog_service import OmniStationCatalogService

pytestmark = pytest.mark.unit


class _DummyOmni:
    def _normalize_landuse_key_impl(self, value):
        return f"key:{value}"

    def _load_landuse_key_map_impl(self, landuse_wd: str):
        return {1: landuse_wd}

    def _contrast_landuse_skip_reason_impl(self, contrast_id, contrast_name, *, landuse_cache=None):
        return f"{contrast_id}:{contrast_name}:{bool(landuse_cache)}"

    def _normalize_scenario_key_impl(self, name):
        return f"scenario:{name}"

    def _loss_pw0_path_for_scenario_impl(self, scenario_name):
        return f"/tmp/{scenario_name}/loss_pw0.txt"

    def _interchange_class_data_path_for_scenario_impl(self, scenario_name):
        return f"/tmp/{scenario_name}/loss_pw0.all_years.class_data.parquet"

    def _year_set_for_scenario_impl(self, scenario_name):
        if scenario_name == "missing":
            return None
        return {2001, 2002}

    def _scenario_signature_impl(self, scenario_def):
        return f"sig:{scenario_def['type']}"

    def _scenario_dependency_target_impl(self, scenario, scenario_def):
        return scenario_def.get("base_scenario", str(scenario))

    def _contrast_dependencies_impl(self, contrast_name):
        return {"c1": {"loss_path": f"/tmp/{contrast_name}.txt", "sha1": "abc"}}

    def _contrast_scenario_keys_impl(self, contrast_name):
        return ("undisturbed", contrast_name)


def test_station_catalog_service_routes_to_impl_methods() -> None:
    service = OmniStationCatalogService()
    omni = _DummyOmni()

    assert service.normalize_landuse_key(omni, 4) == "key:4"
    assert service.load_landuse_key_map(omni, "/run") == {1: "/run"}
    assert service.contrast_landuse_skip_reason(omni, 2, "c2", landuse_cache={}) == "2:c2:False"
    assert service.normalize_scenario_key(omni, "uniform_low") == "scenario:uniform_low"
    assert service.loss_pw0_path_for_scenario(omni, "uniform_low") == "/tmp/uniform_low/loss_pw0.txt"
    assert service.interchange_class_data_path_for_scenario(
        omni,
        "uniform_low",
    ) == "/tmp/uniform_low/loss_pw0.all_years.class_data.parquet"
    assert service.year_set_for_scenario(omni, "uniform_low") == {2001, 2002}
    assert service.year_set_for_scenario(omni, "missing") is None
    assert service.scenario_signature(omni, {"type": "uniform_low"}) == "sig:uniform_low"
    assert service.scenario_dependency_target(
        omni,
        omni_module.OmniScenario.Mulch,
        {"base_scenario": "uniform_low"},
    ) == "uniform_low"
    assert service.contrast_dependencies(omni, "undisturbed__to__mulch") == {
        "c1": {"loss_path": "/tmp/undisturbed__to__mulch.txt", "sha1": "abc"}
    }
    assert service.contrast_scenario_keys(omni, "mulch") == ("undisturbed", "mulch")


def _new_detached_omni(tmp_path: Path) -> omni_module.Omni:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    return omni


def test_facade_station_catalog_methods_delegate_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path)

    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "normalize_landuse_key",
        lambda instance, value: f"delegated-key:{value}",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "load_landuse_key_map",
        lambda instance, landuse_wd: {7: landuse_wd},
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "contrast_landuse_skip_reason",
        lambda instance, contrast_id, contrast_name, *, landuse_cache=None: "landuse_unchanged",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "normalize_scenario_key",
        lambda instance, name: f"delegated-scenario:{name}",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "loss_pw0_path_for_scenario",
        lambda instance, scenario_name: f"/delegated/{scenario_name}/loss_pw0.txt",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "interchange_class_data_path_for_scenario",
        lambda instance, scenario_name: f"/delegated/{scenario_name}/class_data.parquet",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "year_set_for_scenario",
        lambda instance, scenario_name: {1999},
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "scenario_signature",
        lambda instance, scenario_def: "delegated-signature",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "scenario_dependency_target",
        lambda instance, scenario, scenario_def: "delegated-target",
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "contrast_dependencies",
        lambda instance, contrast_name: {"x": {"loss_path": "/tmp/x", "sha1": "1"}},
    )
    monkeypatch.setattr(
        omni_module._OMNI_STATION_CATALOG_SERVICE,
        "contrast_scenario_keys",
        lambda instance, contrast_name: ("a", "b"),
    )

    assert omni._normalize_landuse_key(1) == "delegated-key:1"
    assert omni._load_landuse_key_map("/run") == {7: "/run"}
    assert omni._contrast_landuse_skip_reason(1, "c1") == "landuse_unchanged"
    assert omni._normalize_scenario_key("uniform_low") == "delegated-scenario:uniform_low"
    assert omni._loss_pw0_path_for_scenario("uniform_low") == "/delegated/uniform_low/loss_pw0.txt"
    assert omni._interchange_class_data_path_for_scenario("uniform_low") == "/delegated/uniform_low/class_data.parquet"
    assert omni._year_set_for_scenario("uniform_low") == {1999}
    assert omni._scenario_signature({"type": "uniform_low"}) == "delegated-signature"
    assert omni._scenario_dependency_target(omni_module.OmniScenario.UniformLow, {}) == "delegated-target"
    assert omni._contrast_dependencies("u__to__m") == {"x": {"loss_path": "/tmp/x", "sha1": "1"}}
    assert omni._contrast_scenario_keys("u__to__m") == ("a", "b")
