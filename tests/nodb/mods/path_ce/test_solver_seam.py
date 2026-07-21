"""Tests for the wepppy solver seam contracts (ADR-0023).

The faithful core is hectare-based and positional; the wrapper must
(1) compute costs on acres ($/acre x acres), (2) align treatment vectors to
the frame's reduction-column order for any configured order or subset, and
(3) reject non-finite / malformed inputs before they reach PuLP.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pulp")
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from wepppy.nodb.mods.path_ce.path_ce_solver import (
    ACRES_PER_HECTARE,
    PathCESolverError,
    clean_solver_frame,
    convert_area_to_acres,
    prepare_solver_inputs,
    run_path_cost_effective_solver,
)

GOLDENS = Path(__file__).resolve().parents[3] / "data" / "path_ce" / "goldens"

pytestmark = pytest.mark.unit

TREATMENTS = ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
COST = [2475.0, 2475.0, 2475.0]
QTY = [0.5, 1.0, 2.0]
FIXED = [500.0, 1000.0, 1500.0]


def _austere_frame():
    return pd.read_parquet(GOLDENS / "prepared_frame_austere.parquet")


def test_wrapper_costs_are_acre_based():
    """Group 12 is the only treatable site; its cost must be acres x $/ac x qty."""
    frame = _austere_frame()
    result = run_path_cost_effective_solver(
        frame, TREATMENTS, COST, QTY, FIXED, sdyd_threshold=15, sddc_threshold=48.2
    )
    assert result.primary_status == 1
    assert sorted(int(x) for x in result.selected_hillslopes) == [12]
    assert [sorted(int(x) for x in t) for t in result.treatment_hillslopes] == [[12], [], []]

    area_ha = float(frame.loc[frame["contrast_id"] == 12, "area_sum"].iloc[0])
    expected = area_ha * ACRES_PER_HECTARE * 2475.0 * 0.5
    assert result.total_cost == pytest.approx(expected, rel=1e-9)
    assert result.total_fixed_cost == pytest.approx(500.0)
    # sanity: the hectare-based (upstream-defect) cost would be ~2.47x smaller
    assert result.total_cost > area_ha * 2475.0 * 0.5 * 2.0


def test_convert_area_to_acres_scales_only_area_column():
    frame = clean_solver_frame(_austere_frame())
    converted = convert_area_to_acres(frame)
    assert converted["area_sum"].tolist() == pytest.approx(
        (frame["area_sum"] * ACRES_PER_HECTARE).tolist()
    )
    unchanged = [c for c in frame.columns if c != "area_sum" and frame[c].dtype.kind in "if"]
    for c in unchanged:
        assert converted[c].tolist() == pytest.approx(frame[c].tolist(), nan_ok=True)


def _result_signature(result):
    return (
        result.primary_status,
        sorted(int(x) for x in result.selected_hillslopes),
        [sorted(int(x) for x in t) for t in sorted(result.treatment_hillslopes, key=len)],
        round(result.total_cost, 6),
        round(result.total_fixed_cost, 6),
        round(result.final_sddc, 6),
    )


def test_wrapper_is_invariant_to_treatment_order():
    frame = _austere_frame()
    kwargs = dict(sdyd_threshold=15, sddc_threshold=48.0)
    canonical = run_path_cost_effective_solver(frame, TREATMENTS, COST, QTY, FIXED, **kwargs)
    reversed_ = run_path_cost_effective_solver(
        frame, TREATMENTS[::-1], COST[::-1], QTY[::-1], FIXED[::-1], **kwargs
    )
    assert _result_signature(canonical) == _result_signature(reversed_)
    # result reports the aligned label order it actually ran with
    assert canonical.treatments == reversed_.treatments == TREATMENTS
    # same treatment gets the same hillslopes regardless of configured order
    canonical_map = dict(zip(canonical.treatments, canonical.treatment_hillslopes))
    reversed_map = dict(zip(reversed_.treatments, reversed_.treatment_hillslopes))
    for label in TREATMENTS:
        assert sorted(canonical_map[label]) == sorted(reversed_map[label])


def test_wrapper_supports_treatment_subset():
    frame = _austere_frame()
    result = run_path_cost_effective_solver(
        frame, ["2 tons/acre"], [2475.0], [2.0], [1500.0],
        sdyd_threshold=15, sddc_threshold=48.2,
    )
    assert sorted(int(x) for x in result.selected_hillslopes) == [12]
    area_ha = float(frame.loc[frame["contrast_id"] == 12, "area_sum"].iloc[0])
    assert result.total_cost == pytest.approx(area_ha * ACRES_PER_HECTARE * 2475.0 * 2.0, rel=1e-9)


def test_wrapper_rejects_unknown_treatment_label():
    with pytest.raises(PathCESolverError, match="no reduction columns.*available treatment labels"):
        run_path_cost_effective_solver(
            _austere_frame(), ["3 tons/acre"], [2475.0], [3.0], [2000.0],
            sdyd_threshold=15, sddc_threshold=48.2,
        )


def test_wrapper_rejects_duplicate_labels():
    with pytest.raises(PathCESolverError, match="unique"):
        run_path_cost_effective_solver(
            _austere_frame(), ["1 tons/acre", "1 tons/acre"], [1.0, 2.0], [1.0, 1.0], [0.0, 0.0],
            sdyd_threshold=15, sddc_threshold=48.2,
        )


@pytest.mark.parametrize(
    "bad_kwargs",
    [
        {"treatment_cost": [np.nan, 2475.0, 2475.0]},
        {"treatment_quantity": [0.5, np.inf, 2.0]},
        {"fixed_cost": [500.0, 1000.0, float("-inf")]},
    ],
)
def test_wrapper_rejects_nonfinite_treatment_metadata(bad_kwargs):
    kwargs = dict(zip(("treatment_cost", "treatment_quantity", "fixed_cost"), (COST, QTY, FIXED)))
    kwargs.update(bad_kwargs)
    with pytest.raises(PathCESolverError, match="finite"):
        run_path_cost_effective_solver(
            _austere_frame(), TREATMENTS, kwargs["treatment_cost"],
            kwargs["treatment_quantity"], kwargs["fixed_cost"],
            sdyd_threshold=15, sddc_threshold=48.2,
        )


def test_clean_solver_frame_tolerates_list_columns():
    frame = _austere_frame()
    assert any(
        frame[c].map(lambda v: isinstance(v, (list, np.ndarray))).any() for c in frame.columns
    ), "fixture should carry list-typed columns (topaz_ids)"
    cleaned = clean_solver_frame(frame)
    assert len(cleaned) == len(frame)
    assert not np.isinf(cleaned.select_dtypes(include=[np.number]).to_numpy(dtype=float)).any()


def test_wrapper_rejects_mismatched_treatment_metadata():
    with pytest.raises(PathCESolverError, match="matching lengths"):
        run_path_cost_effective_solver(
            _austere_frame(), TREATMENTS, COST, QTY, [500.0],
            sdyd_threshold=15, sddc_threshold=48.2,
        )


def test_wrapper_rejects_nonfinite_thresholds():
    with pytest.raises(PathCESolverError, match="finite"):
        run_path_cost_effective_solver(
            _austere_frame(), TREATMENTS, COST, QTY, FIXED,
            sdyd_threshold=float("nan"), sddc_threshold=48.2,
        )


def test_prepare_solver_inputs_prunes_and_reorders():
    frame, labels, costs, qtys, fixed, id_col, area_col = prepare_solver_inputs(
        _austere_frame(), ["2 tons/acre", "0.5 tons/acre"], [10.0, 20.0], [2.0, 0.5], [3.0, 4.0]
    )
    # reordered to frame column order (0.5 before 2)
    assert labels == ["0.5 tons/acre", "2 tons/acre"]
    assert costs == [20.0, 10.0] and qtys == [0.5, 2.0] and fixed == [4.0, 3.0]
    # unconfigured reduction columns pruned; configured ones kept
    kept = [c for c in frame.columns if c.startswith("Sddc reduction")]
    assert kept == ["Sddc reduction 0.5 tons/acre", "Sddc reduction 2 tons/acre"]
    assert not any(c == "Sddc reduction 1 tons/acre" for c in frame.columns)
    assert (id_col, area_col) == ("contrast_id", "area_sum")


def test_wrapper_secondary_path_matches_core_semantics():
    golden_path = GOLDENS / "solver_goldens_austere.json"
    with open(golden_path) as f:
        golden = json.load(f)
    case = next(c for c in golden["cases"] if c["primary_status"] == 0)
    result = run_path_cost_effective_solver(
        _austere_frame(), golden["treatments"], golden["treatment_cost"],
        golden["treatment_quantity"], golden["fixed_cost"],
        sdyd_threshold=case["sdyd_threshold"], sddc_threshold=case["sddc_threshold"],
    )
    # selection/feasibility identical to upstream (area scaling is uniform on
    # variable costs and does not change this fixture's forced structure)
    assert result.used_secondary
    assert sorted(int(x) for x in result.selected_hillslopes) == case["selected_hillslopes"]
    assert result.total_sddc_reduction == pytest.approx(case["total_sddc_reduction"], abs=1e-4)
