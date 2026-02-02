import pytest

from wepppy.nodb.core.management_overrides import (
    apply_disturbed_management_overrides,
)


class DummyManagement:
    def __init__(self) -> None:
        self.plant_data = {
            "decfct": 0.65,
            "dropfc": 0.98,
        }
        self.ini_data = {
            "cancov": 0.4,
        }
        self.set_calls = []

    def __setitem__(self, attr: str, value: float | int) -> int:
        if attr.startswith("plant.data."):
            key = attr[11:]
            self.plant_data[key] = float(value)
        elif attr.startswith("ini.data."):
            key = attr[9:]
            self.ini_data[key] = float(value)
        else:
            raise AssertionError(f"Unexpected attr {attr}")
        self.set_calls.append((attr, value))
        return 0


@pytest.mark.unit
def test_agriculture_rows_skip_blank_overrides() -> None:
    management = DummyManagement()
    replacements = {
        "plant.data.decfct": "",
        "plant.data.dropfc": "  ",
        "ini.data.cancov": "",
    }

    apply_disturbed_management_overrides(management, replacements)

    assert management.plant_data["decfct"] == 0.65
    assert management.plant_data["dropfc"] == 0.98
    assert management.ini_data["cancov"] == 0.4
    assert management.set_calls == []


@pytest.mark.unit
def test_static_overrides_set_plant_decay_drop_factors() -> None:
    management = DummyManagement()
    replacements = {
        "plant.data.decfct": "1",
        "plant.data.dropfc": 1,
    }

    apply_disturbed_management_overrides(management, replacements)

    assert management.plant_data["decfct"] == 1.0
    assert management.plant_data["dropfc"] == 1.0
