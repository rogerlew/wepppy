import pytest

from wepppy.nodb.core.management_overrides import (
    apply_disturbed_management_overrides,
    is_forest_cover_disturbed_class,
    is_unburned_forest_disturbed_class,
    normalize_disturbed_class_for_management_lookup,
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
def test_unburned_forest_helper_includes_deciduous_and_mixed_classes() -> None:
    assert is_unburned_forest_disturbed_class("forest")
    assert is_unburned_forest_disturbed_class("young forest")
    assert is_unburned_forest_disturbed_class("deciduous forest")
    assert is_unburned_forest_disturbed_class("mixed forest")
    assert not is_unburned_forest_disturbed_class("forest high sev fire")
    assert not is_unburned_forest_disturbed_class("shrub")


@pytest.mark.unit
def test_forest_cover_helper_includes_burned_and_treatment_suffix_classes() -> None:
    assert is_forest_cover_disturbed_class("deciduous forest")
    assert is_forest_cover_disturbed_class("mixed forest")
    assert is_forest_cover_disturbed_class("forest high sev fire")
    assert is_forest_cover_disturbed_class("forest moderate sev fire-mulch_15")
    assert not is_forest_cover_disturbed_class("shrub high sev fire")


@pytest.mark.unit
def test_normalize_fire_mulch_uses_burned_base_lookup_class() -> None:
    lookup_class, lookup_label = normalize_disturbed_class_for_management_lookup(
        "forest moderate sev fire-mulch_30"
    )

    assert lookup_class == "forest moderate sev fire"
    assert lookup_label == "forest moderate sev fire"


@pytest.mark.unit
def test_normalize_pure_mulch_uses_mulch_lookup_class() -> None:
    lookup_class, lookup_label = normalize_disturbed_class_for_management_lookup("mulch_30")

    assert lookup_class == "mulch"
    assert lookup_label == "mulch"


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
