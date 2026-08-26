from __future__ import annotations

import pytest

from wepppy.nodb.project_config_capabilities import (
    SOIL_BUILDER_MODES,
    capability_ids,
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


def test_absent_capability_authority_preserves_legacy_behavior() -> None:
    config = FakeConfig({})
    assert capability_ids(config, "climate_datasets") is None
    assert runtime_value_allowed(config, "climate_datasets", "anything") is True


def test_semantic_soil_ids_map_to_runtime_modes() -> None:
    config = FakeConfig({"soil_builders": ["gridded", "single_mukey"]})
    assert soil_capability_modes(config) == frozenset({0, 1})
    assert runtime_value_allowed(config, "soil_builders", 1, stable_to_runtime=SOIL_BUILDER_MODES)
    assert not runtime_value_allowed(config, "soil_builders", 2, stable_to_runtime=SOIL_BUILDER_MODES)


@pytest.mark.parametrize("value", [[], [""], [1], "vanilla_cligen"])
def test_malformed_capability_authority_fails_explicitly(value: object) -> None:
    with pytest.raises(ValueError, match="capabilities.climate_datasets"):
        capability_ids(FakeConfig({"climate_datasets": value}), "climate_datasets")
