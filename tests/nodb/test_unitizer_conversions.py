"""Regression tests for unitizer conversion factors.

The ton→tonne factor was 25.4 (the inch→mm factor, a copy-paste defect)
until the PATH-CE v2 Phase 4 review caught it; these tests pin the corrected
factors and round-trip consistency for the categories PATH-CE exposes.
"""

from __future__ import annotations

import pytest

from wepppy.weppcloud.controllers_js.unitizer_map_builder import build_unitizer_map_data

pytestmark = pytest.mark.unit


def _conversion(map_data, category, from_unit, to_unit):
    for cat in map_data["categories"]:
        if cat["key"] != category:
            continue
        for conv in cat["conversions"]:
            if conv["from"] == from_unit and conv["to"] == to_unit:
                return conv
    raise AssertionError(f"conversion {from_unit}->{to_unit} not found in {category}")


@pytest.fixture(scope="module")
def map_data():
    return build_unitizer_map_data()


@pytest.mark.parametrize(
    "category,from_unit,to_unit,expected",
    [
        ("weight", "ton", "tonne", 0.90718474),
        ("weight", "tonne", "ton", 1.10231),
        ("weight-annual", "ton/yr", "tonne/yr", 0.90718474),
        ("weight-annual", "tonne/yr", "ton/yr", 1.10231),
        ("currency-area", "$/acre", "$/ha", 2.47105381467),
        ("currency-area", "$/ha", "$/acre", 0.40468564224),
    ],
)
def test_conversion_factors(map_data, category, from_unit, to_unit, expected):
    conv = _conversion(map_data, category, from_unit, to_unit)
    assert conv["scale"] == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize(
    "category,unit_a,unit_b",
    [
        ("weight", "ton", "tonne"),
        ("weight-annual", "ton/yr", "tonne/yr"),
        ("currency-area", "$/acre", "$/ha"),
    ],
)
def test_round_trip_consistency(map_data, category, unit_a, unit_b):
    forward = _conversion(map_data, category, unit_a, unit_b)["scale"]
    backward = _conversion(map_data, category, unit_b, unit_a)["scale"]
    assert forward * backward == pytest.approx(1.0, rel=1e-4)
