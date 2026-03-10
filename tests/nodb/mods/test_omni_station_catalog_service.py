from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_station_catalog_service import OmniStationCatalogService

pytestmark = pytest.mark.unit


class _StationOmniStub:
    def __init__(
        self,
        wd: Path,
        *,
        base_scenario: omni_module.OmniScenario = omni_module.OmniScenario.Undisturbed,
    ) -> None:
        self.wd = str(wd)
        self._base_scenario = base_scenario
        self.logger = logging.getLogger("tests.omni.station_catalog")
        self.sidecars: dict[int, dict[int | str, str]] = {}

    @property
    def base_scenario(self) -> omni_module.OmniScenario:
        return self._base_scenario

    def _load_contrast_sidecar(self, contrast_id: int):
        if contrast_id not in self.sidecars:
            raise FileNotFoundError(contrast_id)
        return self.sidecars[contrast_id]


def test_normalize_landuse_key_handles_null_and_numeric_values(tmp_path: Path) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    assert service.normalize_landuse_key(omni, None) is None
    assert service.normalize_landuse_key(omni, float("nan")) is None
    assert service.normalize_landuse_key(omni, 7) == "7"
    assert service.normalize_landuse_key(omni, 7.0) == "7"
    assert service.normalize_landuse_key(omni, 7.5) == "7.5"
    assert service.normalize_landuse_key(omni, "forest") == "forest"


def test_load_landuse_key_map_reads_topaz_id_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    parquet_path = tmp_path / "landuse" / "landuse.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.write_text("", encoding="ascii")

    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda path, columns: pd.DataFrame(
            [
                {"topaz_id": 1, "key": 10.0},
                {"topaz_id": 2, "key": "A"},
                {"topaz_id": "bad", "key": "B"},
                {"topaz_id": None, "key": "C"},
            ]
        ),
    )

    assert service.load_landuse_key_map(omni, str(tmp_path)) == {1: "10", 2: "A"}


def test_load_landuse_key_map_falls_back_to_topazid_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    parquet_path = tmp_path / "landuse" / "landuse.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.write_text("", encoding="ascii")

    read_calls: list[tuple[str, tuple[str, str]]] = []

    def _fake_read_parquet(path, columns):
        read_calls.append((str(path), tuple(columns)))
        if columns[0] == "topaz_id":
            raise ValueError("missing topaz_id")
        return pd.DataFrame(
            [
                {"TopazID": 9, "key": "forest"},
                {"TopazID": 10.0, "key": 2.0},
            ]
        )

    monkeypatch.setattr(pd, "read_parquet", _fake_read_parquet)

    assert service.load_landuse_key_map(omni, str(tmp_path)) == {9: "forest", 10: "2"}
    assert len(read_calls) == 2
    assert read_calls[0][1] == ("topaz_id", "key")
    assert read_calls[1][1] == ("TopazID", "key")


def test_load_landuse_key_map_logs_and_returns_none_on_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    parquet_path = tmp_path / "landuse" / "landuse.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.write_text("", encoding="ascii")

    monkeypatch.setattr(pd, "read_parquet", lambda path, columns: (_ for _ in ()).throw(OSError("read failed")))

    with caplog.at_level(logging.WARNING):
        assert service.load_landuse_key_map(omni, str(tmp_path)) is None

    assert "Failed to read landuse key parquet" in caplog.text
    assert str(tmp_path) in caplog.text


def test_contrast_landuse_skip_reason_reports_unchanged_when_maps_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    contrast_wd = tmp_path / omni_module.OMNI_REL_DIR / "scenarios" / "mulch" / "wepp" / "output"
    contrast_wd.mkdir(parents=True, exist_ok=True)
    contrast_wepp_path = contrast_wd / "H10"
    contrast_wepp_path.write_text("", encoding="ascii")

    omni.sidecars[1] = {10: str(contrast_wepp_path)}
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(
        service,
        "load_landuse_key_map",
        lambda _omni, landuse_wd: {10: "forest"} if "mulch" in landuse_wd else {10: "forest"},
    )

    cache: dict[str, dict[int, str] | None] = {}
    reason = service.contrast_landuse_skip_reason(
        omni,
        1,
        "undisturbed,10__to__mulch",
        landuse_cache=cache,
    )

    assert reason == "landuse_unchanged"
    assert "undisturbed" in cache
    assert "mulch" in cache


def test_contrast_landuse_skip_reason_returns_none_on_landuse_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    contrast_wd = tmp_path / omni_module.OMNI_REL_DIR / "scenarios" / "mulch" / "wepp" / "output"
    contrast_wd.mkdir(parents=True, exist_ok=True)
    contrast_wepp_path = contrast_wd / "H10"
    contrast_wepp_path.write_text("", encoding="ascii")

    omni.sidecars[2] = {10: str(contrast_wepp_path)}
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(
        service,
        "load_landuse_key_map",
        lambda _omni, landuse_wd: {10: "grass"} if "mulch" in landuse_wd else {10: "forest"},
    )

    assert service.contrast_landuse_skip_reason(omni, 2, "undisturbed,10__to__mulch") is None


def test_normalize_and_path_helpers_resolve_base_and_scenario_paths(tmp_path: Path) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    base_loss_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    base_loss_path.parent.mkdir(parents=True, exist_ok=True)
    base_loss_path.write_text("", encoding="ascii")

    assert service.normalize_scenario_key(omni, None) == "undisturbed"
    assert service.normalize_scenario_key(omni, omni_module.OmniScenario.UniformLow) == "uniform_low"
    assert service.contrast_scenario_keys(omni, "None,1__to__mulch") == ("undisturbed", "mulch")

    assert service.loss_pw0_path_for_scenario(omni, None) == str(base_loss_path)
    assert service.loss_pw0_path_for_scenario(omni, "mulch").endswith(
        "_pups/omni/scenarios/mulch/wepp/output/interchange/loss_pw0.out.parquet"
    )

    base_interchange_path = (
        tmp_path
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.all_years.class_data.parquet"
    )
    base_interchange_path.parent.mkdir(parents=True, exist_ok=True)
    base_interchange_path.write_text("", encoding="ascii")

    assert service.interchange_class_data_path_for_scenario(omni, None) == str(base_interchange_path)
    assert service.interchange_class_data_path_for_scenario(omni, "mulch").endswith(
        "_pups/omni/scenarios/mulch/wepp/output/interchange/loss_pw0.all_years.class_data.parquet"
    )


def test_year_set_for_scenario_reads_and_normalizes_years(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    class_data_path = tmp_path / "class_data.parquet"
    class_data_path.write_text("", encoding="ascii")

    monkeypatch.setattr(
        service,
        "interchange_class_data_path_for_scenario",
        lambda _omni, _scenario_name: str(class_data_path),
    )
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda path, columns: pd.DataFrame({"year": [2001, 2002.0, 2002, None]}),
    )

    assert service.year_set_for_scenario(omni, "mulch") == {2001, 2002}


def test_signature_and_dependency_helpers_are_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    signature = service.scenario_signature(
        omni,
        {"value": 2, "type": omni_module.OmniScenario.UniformLow},
    )
    parsed_signature = json.loads(signature)
    assert parsed_signature["type"] == "uniform_low"
    assert parsed_signature["value"] == 2

    assert service.scenario_dependency_target(
        omni,
        omni_module.OmniScenario.Mulch,
        {"base_scenario": "uniform_low"},
    ) == "uniform_low"
    assert service.scenario_dependency_target(
        omni,
        omni_module.OmniScenario.UniformLow,
        {},
    ) == "undisturbed"

    monkeypatch.setattr(
        service,
        "loss_pw0_path_for_scenario",
        lambda _omni, scenario_name: f"/loss/{scenario_name}.txt",
    )
    monkeypatch.setattr(omni_module, "_hash_file_sha1", lambda path: f"sha:{path}")

    dependencies = service.contrast_dependencies(omni, "None,10__to__mulch")

    assert dependencies == {
        "undisturbed": {"loss_path": "/loss/undisturbed.txt", "sha1": "sha:/loss/undisturbed.txt"},
        "mulch": {"loss_path": "/loss/mulch.txt", "sha1": "sha:/loss/mulch.txt"},
    }


def test_contrast_dependencies_use_interchange_loss_out_paths(tmp_path: Path) -> None:
    service = OmniStationCatalogService()
    omni = _StationOmniStub(tmp_path)

    base_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    mulch_path = (
        tmp_path
        / "_pups"
        / "omni"
        / "scenarios"
        / "mulch"
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.out.parquet"
    )
    base_path.parent.mkdir(parents=True, exist_ok=True)
    mulch_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text("base", encoding="ascii")
    mulch_path.write_text("mulch", encoding="ascii")

    dependencies = service.contrast_dependencies(omni, "None,10__to__mulch")

    assert dependencies["undisturbed"]["loss_path"] == str(base_path)
    assert dependencies["mulch"]["loss_path"] == str(mulch_path)
    assert dependencies["undisturbed"]["sha1"] == omni_module._hash_file_sha1(str(base_path))
    assert dependencies["mulch"]["sha1"] == omni_module._hash_file_sha1(str(mulch_path))


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
    assert omni._normalize_landuse_key_impl(2) == "delegated-key:2"
    assert omni._load_landuse_key_map("/run") == {7: "/run"}
    assert omni._load_landuse_key_map_impl("/run-impl") == {7: "/run-impl"}
    assert omni._contrast_landuse_skip_reason(1, "c1") == "landuse_unchanged"
    assert omni._contrast_landuse_skip_reason_impl(2, "c2") == "landuse_unchanged"
    assert omni._normalize_scenario_key("uniform_low") == "delegated-scenario:uniform_low"
    assert omni._normalize_scenario_key_impl("uniform_high") == "delegated-scenario:uniform_high"
    assert omni._loss_pw0_path_for_scenario("uniform_low") == "/delegated/uniform_low/loss_pw0.txt"
    assert omni._loss_pw0_path_for_scenario_impl("uniform_high") == "/delegated/uniform_high/loss_pw0.txt"
    assert (
        omni._interchange_class_data_path_for_scenario("uniform_low")
        == "/delegated/uniform_low/class_data.parquet"
    )
    assert (
        omni._interchange_class_data_path_for_scenario_impl("uniform_high")
        == "/delegated/uniform_high/class_data.parquet"
    )
    assert omni._year_set_for_scenario("uniform_low") == {1999}
    assert omni._year_set_for_scenario_impl("uniform_low") == {1999}
    assert omni._scenario_signature({"type": "uniform_low"}) == "delegated-signature"
    assert omni._scenario_signature_impl({"type": "uniform_low"}) == "delegated-signature"
    assert omni._scenario_dependency_target(omni_module.OmniScenario.UniformLow, {}) == "delegated-target"
    assert omni._scenario_dependency_target_impl(omni_module.OmniScenario.UniformLow, {}) == "delegated-target"
    assert omni._contrast_dependencies("u__to__m") == {"x": {"loss_path": "/tmp/x", "sha1": "1"}}
    assert omni._contrast_dependencies_impl("u__to__m") == {"x": {"loss_path": "/tmp/x", "sha1": "1"}}
    assert omni._contrast_scenario_keys("u__to__m") == ("a", "b")
    assert omni._contrast_scenario_keys_impl("u__to__m") == ("a", "b")
