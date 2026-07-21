"""Config schema normalization + round-trip tests for PathCostEffective."""

from __future__ import annotations

import pytest

pytest.importorskip("pandas")

from wepppy.nodb.mods.path_ce.path_cost_effective import (
    _normalize_config,
    _solver_slope_range,
)
from wepppy.nodb.mods.path_ce.presets import PATH_CE_DEFAULT_TREATMENTS

pytestmark = pytest.mark.unit


def test_defaults():
    config = _normalize_config({})
    assert config["sdyd_threshold"] == 15.0
    assert config["sddc_threshold"] == 0.0
    assert config["slope_range"] == [None, None]
    assert config["severity_filter"] is None
    assert "render_reports" not in config
    assert config["treatments"] == [dict(t) for t in PATH_CE_DEFAULT_TREATMENTS]


def test_round_trip_stability():
    payload = {
        "sdyd_threshold": "2.5",
        "sddc_threshold": 40000,
        "slope_range": ["10", None],
        "severity_filter": ["high", "Moderate"],
        "treatments": [
            {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
             "unit_cost": "2475", "quantity": 2, "fixed_cost": 1500},
        ],
    }
    once = _normalize_config(payload)
    twice = _normalize_config(once)
    assert once == twice
    assert once["sdyd_threshold"] == 2.5
    assert once["slope_range"] == [10.0, None]
    assert once["severity_filter"] == ["High", "Moderate"]
    assert once["treatments"][0]["unit_cost"] == 2475.0


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"sdyd_threshold": -1}, "sdyd_threshold"),
        ({"sddc_threshold": float("inf")}, "sddc_threshold"),
        ({"slope_range": [30, 10]}, "min exceeds max"),
        ({"slope_range": [1, 2, 3]}, "slope_range"),
        ({"severity_filter": ["Extreme"]}, "severity_filter"),
        (
            {"treatments": [
                {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map", "unit_cost": -5}
            ]},
            "non-negative",
        ),
        (
            {"treatments": [
                {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map"},
                {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map"},
            ]},
            "unique",
        ),
        (
            {"treatments": [{"label": "0.5 tons/acre", "scenario": "mulch_60_sbs_map"}]},
            "does not match scenario",
        ),
        ({"treatments": []}, "at least one treatment"),
    ],
)
def test_invalid_payloads_raise(payload, match):
    with pytest.raises(ValueError, match=match):
        _normalize_config(payload)


def test_unknown_keys_are_dropped():
    # render_reports is retired (reports always render); stale nodb payloads drop it
    config = _normalize_config(
        {"mulch_costs": {"mulch_60_sbs_map": 1.0}, "bogus": 1, "render_reports": False}
    )
    assert "mulch_costs" not in config
    assert "bogus" not in config
    assert "render_reports" not in config


def test_solver_slope_range_substitutes_infinities():
    assert _solver_slope_range({"slope_range": [None, None]}) is None
    lo, hi = _solver_slope_range({"slope_range": [10.0, None]})
    assert lo == 10.0 and hi == float("inf")
    lo, hi = _solver_slope_range({"slope_range": [None, 35.0]})
    assert lo == float("-inf") and hi == 35.0
