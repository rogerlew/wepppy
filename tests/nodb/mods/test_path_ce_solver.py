from __future__ import annotations

import pandas as pd
import pytest

pulp = pytest.importorskip("pulp")

from wepppy.nodb.mods.path_ce.path_ce_solver import PathCESolverError, run_path_cost_effective_solver

pytestmark = pytest.mark.unit


def _build_solver_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "wepp_id": [101, 102],
            "slope_deg": [5.0, 15.0],
            "Burn severity": ["High", "High"],
            "NTU post-fire": [10.0, 5.0],
            "Sdyd post-fire": [5.0, 3.0],
            "area": [1.0, 2.0],
            "NTU reduction T1": [3.0, 1.0],
            "NTU reduction T2": [4.0, 0.0],
            "Sdyd reduction T1": [4.0, 2.0],
            "Sdyd reduction T2": [1.0, 3.0],
            "Sdyd post-treat T1": [1.0, 1.0],
            "Sdyd post-treat T2": [4.0, 0.0],
        }
    )


def test_run_path_cost_effective_solver_raises_for_treatment_metadata_length_mismatch():
    data = _build_solver_input()

    with pytest.raises(PathCESolverError, match="Treatment metadata must have matching lengths"):
        run_path_cost_effective_solver(
            data=data,
            treatments=["T1", "T2"],
            treatment_cost=[100.0, 50.0],
            treatment_quantity=[1.0, 1.0],
            fixed_cost=[10.0],
            sdyd_threshold=1.0,
            sddc_threshold=1000.0,
        )


def test_run_path_cost_effective_solver_raises_when_filters_remove_all_rows():
    data = _build_solver_input()

    with pytest.raises(PathCESolverError, match="No hillslopes available after applying filters"):
        run_path_cost_effective_solver(
            data=data,
            treatments=["T1"],
            treatment_cost=[100.0],
            treatment_quantity=[1.0],
            fixed_cost=[10.0],
            sdyd_threshold=1.0,
            sddc_threshold=1000.0,
            slope_range=(100.0, None),
        )


def test_run_path_cost_effective_solver_uses_secondary_result_when_primary_not_optimal(monkeypatch):
    data = _build_solver_input()

    from wepppy.nodb.mods.path_ce import path_ce_solver

    monkeypatch.setattr(path_ce_solver.LpProblem, "solve", lambda self: 0)

    secondary_allocations = {"T1": [1.0, 0.0], "T2": [0.0, 0.0]}
    secondary_b_solution = {"T1": 1.0, "T2": 0.0}

    monkeypatch.setattr(
        path_ce_solver,
        "_run_secondary_model",
        lambda **kwargs: (secondary_allocations, secondary_b_solution, "Optimal"),
    )

    result = run_path_cost_effective_solver(
        data=data,
        treatments=["T1", "T2"],
        treatment_cost=[100.0, 50.0],
        treatment_quantity=[1.0, 1.0],
        fixed_cost=[10.0, 5.0],
        sdyd_threshold=1.0,
        sddc_threshold=1000.0,
    )

    assert result.used_secondary is True
    assert result.status == "Optimal"
    assert result.selected_hillslopes == [101]
    assert result.treatment_hillslopes == {"T1": [101], "T2": []}
    assert result.total_cost == pytest.approx(100.0)
    assert result.total_fixed_cost == pytest.approx(10.0)
    assert result.total_sddc_reduction == pytest.approx(3.0)
    assert result.final_sddc == pytest.approx(12.0)

    assert list(result.hillslopes_sdyd["wepp_id"]) == [101, 102]
    assert float(result.hillslopes_sdyd.loc[0, "final_Sdyd"]) == pytest.approx(1.0)
    assert float(result.hillslopes_sdyd.loc[1, "final_Sdyd"]) == pytest.approx(3.0)
    assert list(result.untreatable_sdyd["wepp_id"]) == [102]


def test_run_path_cost_effective_solver_raises_when_primary_not_optimal_and_secondary_missing(monkeypatch):
    data = _build_solver_input()

    from wepppy.nodb.mods.path_ce import path_ce_solver

    monkeypatch.setattr(path_ce_solver.LpProblem, "solve", lambda self: 0)
    monkeypatch.setattr(path_ce_solver, "_run_secondary_model", lambda **kwargs: None)

    with pytest.raises(PathCESolverError, match="No feasible solution found"):
        run_path_cost_effective_solver(
            data=data,
            treatments=["T1", "T2"],
            treatment_cost=[100.0, 50.0],
            treatment_quantity=[1.0, 1.0],
            fixed_cost=[10.0, 5.0],
            sdyd_threshold=1.0,
            sddc_threshold=1000.0,
        )

