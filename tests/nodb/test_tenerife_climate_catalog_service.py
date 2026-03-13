from __future__ import annotations

import types

import pytest

from wepppy.nodb.core.climate_station_catalog_service import ClimateStationCatalogService


pytestmark = pytest.mark.unit


class _ClimateStub:
    def __init__(
        self,
        *,
        locales: tuple[str, ...],
        mods: tuple[str, ...] = (),
        uses_tenerife_station_catalog: bool,
    ) -> None:
        self.locales = list(locales)
        self.ron_instance = types.SimpleNamespace(mods=list(mods))
        self.uses_tenerife_station_catalog = uses_tenerife_station_catalog


def test_tenerife_available_catalog_is_runtime_constrained() -> None:
    service = ClimateStationCatalogService()
    climate = _ClimateStub(
        locales=("tenerife", "eu"),
        uses_tenerife_station_catalog=True,
    )

    datasets = service.available_catalog_datasets(climate)

    assert {dataset.catalog_id for dataset in datasets} == {"vanilla_cligen", "user_defined_cli"}
    by_id = {dataset.catalog_id: dataset for dataset in datasets}

    vanilla = by_id["vanilla_cligen"]
    assert vanilla.spatial_modes == (0,)
    assert vanilla.default_spatial_mode == 0
    assert vanilla.station_modes == (-1, 0)

    user_defined = by_id["user_defined_cli"]
    assert user_defined.spatial_modes == (0,)
    assert user_defined.default_spatial_mode == 0
    assert user_defined.station_modes == (4,)


def test_tenerife_resolve_catalog_rejects_unsupported_modes() -> None:
    service = ClimateStationCatalogService()
    climate = _ClimateStub(
        locales=("tenerife", "eu"),
        uses_tenerife_station_catalog=True,
    )

    assert service.resolve_catalog_dataset(climate, "prism_stochastic") is None

    vanilla = service.resolve_catalog_dataset(climate, "vanilla_cligen")
    assert vanilla is not None
    assert vanilla.spatial_modes == (0,)
    assert vanilla.station_modes == (-1, 0)

    user_defined = service.resolve_catalog_dataset(climate, "user_defined_cli")
    assert user_defined is not None
    assert user_defined.spatial_modes == (0,)
    assert user_defined.station_modes == (4,)


def test_non_tenerife_catalog_remains_unchanged() -> None:
    service = ClimateStationCatalogService()
    climate = _ClimateStub(
        locales=("us",),
        uses_tenerife_station_catalog=False,
    )

    prism = service.resolve_catalog_dataset(climate, "prism_stochastic")
    assert prism is not None
    assert prism.climate_mode == 5
    assert prism.spatial_modes == (0, 1)
    assert prism.station_modes == (-1, 0, 1)
