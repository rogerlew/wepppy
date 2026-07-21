"""Tests for the PATH-CE treatment-vector contract in presets.py."""

from __future__ import annotations

import pytest

from wepppy.nodb.mods.path_ce.presets import (
    PATH_CE_DEFAULT_TREATMENTS,
    default_treatments,
    label_for_scenario,
    normalize_treatment,
    solver_vectors,
)

pytestmark = pytest.mark.unit


def test_default_treatments_match_upstream_report_defaults():
    labels, costs, qtys, fixed = solver_vectors(PATH_CE_DEFAULT_TREATMENTS)
    assert labels == ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
    assert costs == [2475.0, 2475.0, 2475.0]
    assert qtys == [0.5, 1.0, 2.0]
    assert fixed == [500.0, 1000.0, 1500.0]


def test_labels_match_data_prep_scenario_rate_derivation():
    # data_prep derives labels as f"{n/30:g} tons/acre" from mulch_{n}_sbs_map
    for t in PATH_CE_DEFAULT_TREATMENTS:
        n = int(t["scenario"].split("_")[1])
        assert t["label"] == f"{n / 30.0:g} tons/acre"


def test_default_treatments_returns_fresh_copies():
    a = default_treatments()
    a[0]["unit_cost"] = 1.0
    assert PATH_CE_DEFAULT_TREATMENTS[0]["unit_cost"] == 2475.0
    assert default_treatments()[0]["unit_cost"] == 2475.0


def test_normalize_treatment_coerces_numerics():
    t = normalize_treatment(
        {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
         "unit_cost": "10", "quantity": 2, "fixed_cost": None}
    )
    assert t == {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
                 "unit_cost": 10.0, "quantity": 2.0, "fixed_cost": 0.0}


def test_label_for_scenario_derivation():
    assert label_for_scenario("mulch_15_sbs_map") == "0.5 tons/acre"
    assert label_for_scenario("mulch_30_sbs_map") == "1 tons/acre"
    assert label_for_scenario("mulch_60_sbs_map") == "2 tons/acre"
    assert label_for_scenario("sbs_map") is None
    assert label_for_scenario("undisturbed") is None


@pytest.mark.parametrize(
    "bad,match",
    [
        ({"label": "", "scenario": "mulch_60_sbs_map"}, "non-empty string"),
        ({"label": "2 tons/acre", "scenario": ""}, "non-empty string"),
        ({"label": None, "scenario": "mulch_60_sbs_map"}, "non-empty string"),
        ({"label": "2 tons/acre", "scenario": "mulch_60_sbs_map", "unit_cost": "abc"}, "numeric"),
        ({"label": "2 tons/acre", "scenario": "mulch_60_sbs_map", "quantity": -1}, "non-negative"),
        ({"label": "2 tons/acre", "scenario": "mulch_60_sbs_map", "fixed_cost": float("nan")}, "finite"),
        # label/scenario mismatch: would silently solve with another treatment's effects
        ({"label": "0.5 tons/acre", "scenario": "mulch_60_sbs_map"}, "does not match scenario"),
        # non-mulch scenarios are not derivable by the current pipeline
        ({"label": "custom", "scenario": "thin_forest"}, "unsupported treatment scenario"),
    ],
)
def test_normalize_treatment_rejects_invalid(bad, match):
    with pytest.raises((ValueError, TypeError), match=match):
        normalize_treatment(bad)


def test_solver_vectors_rejects_duplicate_labels():
    dupes = [dict(PATH_CE_DEFAULT_TREATMENTS[0]), dict(PATH_CE_DEFAULT_TREATMENTS[0])]
    with pytest.raises(ValueError, match="unique"):
        solver_vectors(dupes)


def test_solver_vectors_rejects_empty():
    with pytest.raises(ValueError, match="at least one"):
        solver_vectors([])
