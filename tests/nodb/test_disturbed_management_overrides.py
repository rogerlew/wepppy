import pytest

from wepppy.nodb.core.management_overrides import (
    apply_disturbed_management_overrides,
    resolve_disturbed_scalar_replacements,
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


@pytest.mark.unit
def test_resolve_disturbed_scalar_replacements_accepts_extended_keys() -> None:
    rdmax, xmxlai = resolve_disturbed_scalar_replacements(
        disturbed_class="forest moderate sev fire",
        disturbed_class_str="forest moderate sev fire",
        replacements={
            "plant.data.rdmax": "0.77",
            "plant.data.xmxlai": "6.5",
        },
        cancov_override=None,
    )

    assert rdmax == "0.77"
    assert xmxlai == "6.5"


@pytest.mark.unit
def test_resolve_disturbed_scalar_replacements_prefers_legacy_keys_when_both_exist() -> None:
    rdmax, xmxlai = resolve_disturbed_scalar_replacements(
        disturbed_class="forest moderate sev fire",
        disturbed_class_str="forest moderate sev fire",
        replacements={
            "rdmax": "0.41",
            "xmxlai": "2.7",
            "plant.data.rdmax": "0.88",
            "plant.data.xmxlai": "7.3",
        },
        cancov_override=None,
    )

    assert rdmax == "0.41"
    assert xmxlai == "2.7"


@pytest.mark.unit
def test_resolve_disturbed_scalar_replacements_falls_back_when_legacy_values_blank() -> None:
    rdmax, xmxlai = resolve_disturbed_scalar_replacements(
        disturbed_class="forest moderate sev fire",
        disturbed_class_str="forest moderate sev fire",
        replacements={
            "rdmax": " ",
            "xmxlai": "",
            "plant.data.rdmax": "0.55",
            "plant.data.xmxlai": "4.9",
        },
        cancov_override=None,
    )

    assert rdmax == "0.55"
    assert xmxlai == "4.9"
