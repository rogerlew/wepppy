"""Parity tests for the vendored threshold sweep on the austere-inaction fixture.

Expected values were captured from Jackson's unmodified PATH_plot.py
(4e3b4a6) run on the same frame in the pinned environment; the vendored
module reproduced them exactly. The fixture's feasibility structure is
documented in docs/work-packages/20260720_path_ce_v2/artifacts/
2026-07-20_validation_run_austere.md (post-fire Sddc 48.3, max achievable
reduction 0.1, so the minimum primary-feasible integer threshold is 49).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pulp")
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from wepppy.nodb.mods.path_ce.path_ce_solver import clean_solver_frame
from wepppy.nodb.mods.path_ce.threshold_sweep import all_thresholds, find_threshold_ranges
import wepppy.nodb.mods.path_ce.threshold_sweep as threshold_sweep_module

GOLDENS = Path(__file__).resolve().parents[3] / "data" / "path_ce" / "goldens"

pytestmark = pytest.mark.unit


def load_golden(name: str) -> dict:
    with open(GOLDENS / name) as f:
        return json.load(f)

TREATMENTS = ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
COST = [2475.0, 2475.0, 2475.0]
QTY = [0.5, 1.0, 2.0]
FIXED = [500.0, 1000.0, 1500.0]


@pytest.fixture(scope="module")
def austere_frame():
    return clean_solver_frame(pd.read_parquet(GOLDENS / "prepared_frame_austere.parquet"))


def test_find_threshold_ranges_austere(austere_frame):
    sddc_rng, sdyd_rng, sddc_min_feasible, sdyd_max = find_threshold_ranges(
        austere_frame, TREATMENTS, COST, QTY, FIXED
    )
    assert sddc_rng == (49, 49)
    assert sdyd_rng == (0, 1)
    assert sddc_min_feasible == 49
    assert sdyd_max == 1


def test_find_threshold_ranges_uses_post_fire_when_post_treat_columns_are_absent(
    austere_frame, monkeypatch
):
    frame = austere_frame.drop(
        columns=[column for column in austere_frame.columns if column.startswith("Sdyd post-treat ")]
    )
    monkeypatch.setattr(
        threshold_sweep_module,
        "ce_select_sites_flexible",
        lambda **_kwargs: (1,),
    )

    _, sdyd_rng, _, _ = find_threshold_ranges(frame, TREATMENTS, COST, QTY, FIXED)

    assert sdyd_rng[0] == int(frame["Sdyd post-fire"].min())


def test_find_threshold_ranges_treats_solver_errors_as_infeasible(austere_frame, monkeypatch):
    def _solver_error(**_kwargs):
        raise threshold_sweep_module.PulpSolverError("CBC unavailable")

    monkeypatch.setattr(threshold_sweep_module, "ce_select_sites_flexible", _solver_error)

    sddc_rng, _, sddc_min_feasible, _ = find_threshold_ranges(
        austere_frame, TREATMENTS, COST, QTY, FIXED
    )

    assert sddc_min_feasible == sddc_rng[1]


def test_all_thresholds_austere(austere_frame):
    results_df = all_thresholds(
        austere_frame, TREATMENTS, COST, QTY, FIXED,
        sdyd_threshold_range=(0, 1), sddc_threshold_range=(49, 49),
        sdyd_threshold=1, sddc_threshold=49,
    )
    assert list(results_df["sdyd_threshold"]) == [0, 1]
    assert list(results_df["sddc_threshold"]) == [49, 49]
    assert list(results_df["model_primary_status"]) == [1, 1]
    # sdyd=0 forces group 12's positive-reduction treatment; sdyd=1 requires nothing
    assert results_df.loc[0, "total_cost"] == pytest.approx(830857.5)
    assert results_df.loc[0, "final_Sddc"] == pytest.approx(48.2)
    assert results_df.loc[1, "total_cost"] == pytest.approx(0.0)
    assert results_df.loc[1, "final_Sddc"] == pytest.approx(48.3)


def test_all_thresholds_includes_anchor_values(austere_frame):
    golden = load_golden("solver_goldens_austere.json")
    assert golden["upstream_commit"] == "4e3b4a6"
    results_df = all_thresholds(
        austere_frame, TREATMENTS, COST, QTY, FIXED,
        sdyd_threshold_range=(0, 1), sddc_threshold_range=(40, 49),
        sdyd_threshold=1, sddc_threshold=45,
    )
    assert 45 in set(results_df["sddc_threshold"])
    assert set(results_df["sdyd_threshold"]) == {0, 1}


def test_all_thresholds_records_solver_errors(austere_frame, monkeypatch):
    def _solver_error(**_kwargs):
        raise threshold_sweep_module.PulpSolverError("CBC unavailable")

    monkeypatch.setattr(threshold_sweep_module, "ce_select_sites_flexible", _solver_error)

    results_df = all_thresholds(
        austere_frame,
        TREATMENTS,
        COST,
        QTY,
        FIXED,
        sdyd_threshold_range=(0, 0),
        sddc_threshold_range=(49, 49),
        sdyd_threshold=0,
        sddc_threshold=49,
    )

    assert results_df.loc[0, "model_primary_status"] is None
    assert "PulpSolverError" in results_df.loc[0, "error"]
