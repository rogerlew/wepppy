from __future__ import annotations

import pytest

from wepppy.nodb.mods.rusle.k_compare import ComparisonThresholds, compare_k_modes_to_reference


pytestmark = pytest.mark.unit


def test_compare_k_modes_to_reference_metrics_and_flags() -> None:
    reference = [
        {"point_id": "p1", "value": 0.20, "is_nodata": False},
        {"point_id": "p2", "value": 0.30, "is_nodata": False},
        {"point_id": "p3", "value": 0.40, "is_nodata": False},
    ]
    nomograph = [
        {"point_id": "p1", "value": 0.22, "is_nodata": False},
        {"point_id": "p2", "value": 0.60, "is_nodata": False},
        {"point_id": "p3", "value": 0.39, "is_nodata": False},
    ]
    epic = [
        {"point_id": "p1", "value": 0.21, "is_nodata": False},
        {"point_id": "p2", "value": 0.31, "is_nodata": False},
        {"point_id": "p3", "value": 0.38, "is_nodata": False},
    ]

    summary = compare_k_modes_to_reference(
        reference_samples=reference,
        nomograph_samples=nomograph,
        epic_samples=epic,
        thresholds=ComparisonThresholds(abs_error_warn=0.10, rel_error_warn=0.40),
    )

    nomograph_metrics = summary["modes"]["polaris_nomograph"]["metrics"]
    epic_metrics = summary["modes"]["polaris_epic"]["metrics"]

    assert nomograph_metrics["count"] == 3
    assert epic_metrics["count"] == 3
    assert "p2" in summary["modes"]["polaris_nomograph"]["flagged_point_ids"]
    assert summary["modes"]["polaris_epic"]["flagged_point_ids"] == []


def test_compare_k_modes_to_reference_handles_empty_overlap() -> None:
    summary = compare_k_modes_to_reference(
        reference_samples=[{"point_id": "p1", "value": 0.2, "is_nodata": False}],
        nomograph_samples=[{"point_id": "p2", "value": 0.2, "is_nodata": False}],
        epic_samples=[{"point_id": "p3", "value": 0.2, "is_nodata": False}],
    )

    assert summary["modes"]["polaris_nomograph"]["metrics"]["count"] == 0
    assert summary["modes"]["polaris_epic"]["metrics"]["count"] == 0
