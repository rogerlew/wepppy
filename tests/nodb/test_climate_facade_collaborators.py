from __future__ import annotations

import contextlib
import logging
import types
from pathlib import Path

import pytest

import wepppy.nodb.core.climate as climate_module
from wepppy.nodb.core.climate import Climate

pytestmark = pytest.mark.unit


def _new_detached_climate(tmp_path: Path, logger_name: str) -> Climate:
    climate = Climate.__new__(Climate)
    climate.wd = str(tmp_path)
    climate.logger = logging.getLogger(logger_name)
    climate._logger = climate.logger
    return climate


def test_parse_inputs_delegates_to_input_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _new_detached_climate(tmp_path, "tests.nodb.climate.facade.parse")
    captured: dict[str, object] = {}

    def _fake_parse(instance: Climate, kwds: dict[str, object]) -> None:
        captured["instance"] = instance
        captured["kwds"] = kwds

    monkeypatch.setattr(climate_module._CLIMATE_INPUT_PARSER, "parse_inputs", _fake_parse)

    payload = {"climate_mode": "0"}
    climate.parse_inputs(payload)

    assert captured == {"instance": climate, "kwds": payload}


def test_build_delegates_to_build_router(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _new_detached_climate(tmp_path, "tests.nodb.climate.facade.build")
    captured: dict[str, object] = {}

    def _fake_build(instance: Climate, *, verbose: bool = False, attrs=None) -> None:
        captured["instance"] = instance
        captured["verbose"] = verbose
        captured["attrs"] = attrs

    monkeypatch.setattr(climate_module._CLIMATE_BUILD_ROUTER, "build", _fake_build)

    climate.build(verbose=True, attrs={"k": "v"})

    assert captured == {
        "instance": climate,
        "verbose": True,
        "attrs": {"k": "v"},
    }


def test_catalog_station_facade_methods_delegate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _new_detached_climate(tmp_path, "tests.nodb.climate.facade.station")

    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "available_catalog_datasets",
        lambda instance, include_hidden=False: [
            type("_D", (), {"to_mapping": lambda self: {"catalog_id": "a"}})(),
        ],
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "resolve_catalog_dataset",
        lambda instance, catalog_id, include_hidden=False: {"catalog_id": catalog_id},
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "find_closest_stations",
        lambda instance, num_stations=10: [{"id": "A"}],
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "find_heuristic_stations",
        lambda instance, num_stations=10: [{"id": "B"}],
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "find_eu_heuristic_stations",
        lambda instance, num_stations=10: [{"id": "EU"}],
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "find_au_heuristic_stations",
        lambda instance, num_stations=None: [{"id": "AU"}],
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_STATION_CATALOG_SERVICE,
        "climatestation_meta",
        lambda instance: {"name": "meta"},
    )

    assert climate.available_catalog_datasets() and climate.catalog_datasets_payload() == [{"catalog_id": "a"}]
    assert climate._resolve_catalog_dataset("dataset-x") == {"catalog_id": "dataset-x"}
    assert climate.find_closest_stations() == [{"id": "A"}]
    assert climate.find_heuristic_stations() == [{"id": "B"}]
    assert climate.find_eu_heuristic_stations() == [{"id": "EU"}]
    assert climate.find_au_heuristic_stations() == [{"id": "AU"}]
    assert climate.climatestation_meta == {"name": "meta"}


def test_scaling_and_artifact_wrappers_delegate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _new_detached_climate(tmp_path, "tests.nodb.climate.facade.scaling")
    captured: list[tuple[str, object]] = []

    monkeypatch.setattr(
        climate_module._CLIMATE_SCALING_SERVICE,
        "scale_precip",
        lambda instance, scale_factor: captured.append(("scale_precip", scale_factor)),
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_SCALING_SERVICE,
        "scale_precip_monthlies",
        lambda instance, factors, scale_func: captured.append(("scale_monthlies", tuple(factors))),
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_SCALING_SERVICE,
        "spatial_scale_precip",
        lambda instance, fn: captured.append(("scale_spatial", fn)),
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_ARTIFACT_EXPORT_SERVICE,
        "export_cli_parquet",
        lambda instance: "parquet-path",
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_ARTIFACT_EXPORT_SERVICE,
        "export_cli_precip_frequency_csv",
        lambda instance, parquet_path: captured.append(("export_freq", parquet_path)) or "freq-path",
    )
    monkeypatch.setattr(
        climate_module._CLIMATE_ARTIFACT_EXPORT_SERVICE,
        "download_noaa_atlas14_intensity",
        lambda instance: captured.append(("atlas14", None)) or "atlas-path",
    )

    climate._scale_precip(1.5)
    climate._scale_precip_monthlies([1.0] * 12, lambda *_args, **_kwargs: None)
    climate._spatial_scale_precip("scale-map.tif")

    assert climate._export_cli_parquet() == "parquet-path"
    assert climate._export_cli_precip_frequency_csv(Path("p.parquet")) == "freq-path"
    assert climate._download_noaa_atlas14_intensity() == "atlas-path"

    assert ("scale_precip", 1.5) in captured
    assert ("scale_monthlies", tuple([1.0] * 12)) in captured
    assert ("scale_spatial", "scale-map.tif") in captured
    assert ("export_freq", Path("p.parquet")) in captured
    assert ("atlas14", None) in captured


def test_gridmet_multiple_build_delegates_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _new_detached_climate(tmp_path, "tests.nodb.climate.facade.gridmet_multiple")
    captured: dict[str, object] = {}

    @contextlib.contextmanager
    def _noop_locked(_self):
        yield

    def _set_attrs(attrs):
        captured["attrs"] = attrs

    def _fake_build(
        instance: Climate,
        *,
        build_observed_gridmet_interpolated_fn,
        ncpu: int,
    ) -> None:
        captured["instance"] = instance
        captured["build_fn"] = build_observed_gridmet_interpolated_fn
        captured["ncpu"] = ncpu

    climate.locked = types.MethodType(_noop_locked, climate)
    climate.set_attrs = _set_attrs
    monkeypatch.setattr(climate_module._CLIMATE_GRIDMET_MULTIPLE_BUILD_SERVICE, "build", _fake_build)

    climate._build_climate_observed_gridmet_multiple(attrs={"mode": "gridmet"})

    assert captured["instance"] is climate
    assert captured["attrs"] == {"mode": "gridmet"}
    assert captured["build_fn"] is climate_module.build_observed_gridmet_interpolated
    assert captured["ncpu"] == climate_module.NCPU
