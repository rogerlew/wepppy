from __future__ import annotations

import pytest

from wepppy.nodb.mods.rusle.c_lookup import (
    load_rusle_c_lookup,
    normalize_disturbed_family,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw_disturbed_class", "expected"),
    [
        ("forest", "forest"),
        ("young forest", "forest"),
        ("deciduous forest", "forest"),
        ("mixed forest", "forest"),
        ("forest high sev fire-mulch_15", "forest"),
        ("shrub moderate sev fire", "shrub"),
        ("grass low sev fire", "tall_grass"),
        ("tall grass", "tall_grass"),
        ("short grass", "short_grass"),
        ("agriculture crops", "agriculture_crops"),
        ("mulch", "mulch"),
    ],
)
def test_normalize_disturbed_family_contract(raw_disturbed_class: str, expected: str) -> None:
    assert normalize_disturbed_family(raw_disturbed_class) == expected


def test_default_lookup_contains_required_static_matrix() -> None:
    lookup = load_rusle_c_lookup()

    assert lookup[("forest", "moderate")].resolved_c() == pytest.approx(0.09071795328941253)
    assert lookup[("shrub", "high")].resolved_c() == pytest.approx(0.30119421191220214)
    assert lookup[("tall_grass", "low")].resolved_c() == pytest.approx(0.09071795328941253)
    assert lookup[("bare", "unburned")].resolved_c() == pytest.approx(1.0)
    assert lookup[("short_grass", "unburned")].resolved_c() == pytest.approx(0.20189651799465538)
    assert lookup[("agriculture_crops", "unburned")].resolved_c() == pytest.approx(0.02732372244729257)
