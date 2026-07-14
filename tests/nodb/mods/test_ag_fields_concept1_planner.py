from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from wepppy.nodb.mods.ag_fields.concept1_planner import (
    Concept1PlanningError,
    _integer_grid,
    _normalize_subfield_grid,
    build_parent_plan,
)


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_ordered_field_and_downstream_background_fit_exactly() -> None:
    plan = build_parent_plan(
        source_ids=np.array([10, 10, 0, 0]),
        discharge_ranks=np.array([4.0, 3.0, 2.0, 1.0]),
        cell_area_m2=100.0,
    )

    assert plan.selected.overall_assignment_agreement == 1.0
    assert plan.selected.field_cell_agreement == 1.0
    assert plan.selected.max_field_area_error_fraction == 0.0
    assert plan.selected.modeled_downstream_background_fraction == 0.5
    assert [(row.source_id, row.start_index, row.end_index) for row in plan.selected.segments] == [
        (10, 0, 2),
        (0, 2, 4),
    ]


def test_side_by_side_rank_pattern_exposes_fit_loss_under_ofe_limit() -> None:
    plan = build_parent_plan(
        source_ids=np.array([10, 20, 10, 20, 10, 20]),
        discharge_ranks=np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0]),
        cell_area_m2=100.0,
        max_ofes=2,
    )

    assert plan.selected.ofe_count == 2
    assert plan.selected.overall_assignment_agreement < 1.0
    assert plan.selected.fragmented_field_count == 2
    assert plan.selected.missing_field_source_count == 0
    assert plan.selected.zero_overlap_field_source_count == 0


def test_constrained_merge_keeps_a_small_field_between_background_runs() -> None:
    plan = build_parent_plan(
        source_ids=np.array([0, 0, 0, 10, 0, 0, 0]),
        discharge_ranks=np.arange(7.0, 0.0, -1.0),
        cell_area_m2=100.0,
        max_ofes=2,
    )

    assert plan.selected.missing_field_source_count == 0
    assert plan.selected.zero_overlap_field_source_count == 0
    assert plan.selected.field_cell_agreement == 1.0


def test_residual_plan_preserves_original_profile_positions_and_area() -> None:
    plan = build_parent_plan(
        source_ids=np.array([10, 20, 20, 0]),
        discharge_ranks=np.array([4.0, 3.0, 2.0, 1.0]),
        cell_area_m2=100.0,
        ignored_source_ids={20},
    )

    assert plan.selected.overall_assignment_agreement == 1.0
    assert plan.selected.max_field_area_error_fraction == 0.0
    assert [(row.source_id, row.start_index, row.end_index) for row in plan.selected.segments] == [
        (10, 0, 2),
        (0, 2, 4),
    ]


def test_rejects_complete_connected_coverage_as_no_residual_source() -> None:
    with pytest.raises(Concept1PlanningError, match="at least one active raster cell"):
        build_parent_plan(
            source_ids=np.array([10, 10]),
            discharge_ranks=np.array([2.0, 1.0]),
            cell_area_m2=100.0,
            ignored_source_ids={10},
        )


def test_tied_discharge_ranks_preserve_input_order() -> None:
    plan = build_parent_plan(
        source_ids=np.array([20, 10, 0]),
        discharge_ranks=np.array([1.0, 1.0, 0.0]),
        cell_area_m2=100.0,
    )

    assert plan.ordered_source_ids[:2] == (20, 10)


def test_rejects_non_finite_discharge_rank() -> None:
    with pytest.raises(Concept1PlanningError, match="non-finite"):
        build_parent_plan(
            source_ids=np.array([10, 0]),
            discharge_ranks=np.array([1.0, np.nan]),
            cell_area_m2=100.0,
        )


def test_subfield_nonfinite_nodata_can_normalize_to_background() -> None:
    resource = SimpleNamespace(data=np.array([[1.0, np.nan, 0.0]]))

    values = _integer_grid(resource, "subfield map", nonfinite_value=0)

    assert values.tolist() == [[1, 0, 0]]


def test_subfield_finite_nodata_normalizes_to_background() -> None:
    resource = SimpleNamespace(data=np.array([[1, -2147483648, 0]], dtype=np.int32))

    values = _normalize_subfield_grid(resource)

    assert values.tolist() == [[1, 0, 0]]
