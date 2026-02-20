from __future__ import annotations

import logging
from pathlib import Path

import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_scaling_service import OmniScalingService

pytestmark = pytest.mark.unit


class _DummyOmni:
    def __init__(self, tmp_path: Path) -> None:
        self.wd = str(tmp_path)
        self.logger = logging.getLogger("tests.omni.scaling")
        self._contrast_order_reduction_passes = None

    def config_get_int(self, section: str, key: str, default: int) -> int:
        return default


def test_normalize_selection_mode_aliases() -> None:
    service = OmniScalingService()

    assert service.normalize_selection_mode(None) == "cumulative"
    assert service.normalize_selection_mode("stream_order_pruning") == "stream_order"
    assert service.normalize_selection_mode("stream-order-pruning") == "stream_order"
    assert service.normalize_selection_mode("user-defined-hillslope-group") == "user_defined_hillslope_groups"
    assert service.normalize_selection_mode("cumulative") == "cumulative"


def test_normalize_hillslope_limit_validates_and_clamps(tmp_path: Path) -> None:
    service = OmniScalingService()
    omni = _DummyOmni(tmp_path)

    limit, cap = service.normalize_hillslope_limit(
        omni,
        selection_mode="cumulative",
        contrast_hillslope_limit=500,
    )
    assert limit == 100
    assert cap == 100

    with pytest.raises(ValueError, match="must be >= 1"):
        service.normalize_hillslope_limit(
            omni,
            selection_mode="cumulative",
            contrast_hillslope_limit=0,
        )

    with pytest.raises(ValueError, match="must be an integer"):
        service.normalize_hillslope_limit(
            omni,
            selection_mode="cumulative",
            contrast_hillslope_limit="bad",
        )


def test_normalize_filter_inputs_parses_slope_and_int_sets() -> None:
    service = OmniScalingService()

    hill_min, hill_max, burns, topaz = service.normalize_filter_inputs(
        contrast_hill_min_slope="30",
        contrast_hill_max_slope="70",
        contrast_select_burn_severities="1,2,3",
        contrast_select_topaz_ids=["10", 20],
    )

    assert hill_min == 0.3
    assert hill_max == 0.7
    assert burns == {1, 2, 3}
    assert topaz == {10, 20}

    with pytest.raises(ValueError, match="must be <="):
        service.normalize_filter_inputs(
            contrast_hill_min_slope=0.9,
            contrast_hill_max_slope=0.1,
            contrast_select_burn_severities=None,
            contrast_select_topaz_ids=None,
        )


def test_resolve_order_reduction_passes_normalizes_zero_and_rejects_negative(tmp_path: Path) -> None:
    service = OmniScalingService()
    omni = _DummyOmni(tmp_path)

    omni._contrast_order_reduction_passes = 0
    assert service.resolve_order_reduction_passes(omni) == 1

    omni._contrast_order_reduction_passes = -1
    with pytest.raises(ValueError, match=">= 1"):
        service.resolve_order_reduction_passes(omni)


def test_apply_advanced_filters_applies_topaz_slope_and_burn_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniScalingService()
    omni = _DummyOmni(tmp_path)

    class DummyWatershed:
        @staticmethod
        def hillslope_slope(topaz_id: str) -> float:
            return {"101": 0.2, "102": 0.4, "103": 0.6}[str(topaz_id)]

    class DummyLanduse:
        @staticmethod
        def identify_burn_class(topaz_id: str) -> str:
            return {"101": "Low", "102": "Moderate", "103": "High"}[str(topaz_id)]

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())

    records = [
        omni_module.ObjectiveParameter("101", "201", 10.0),
        omni_module.ObjectiveParameter("102", "202", 9.0),
        omni_module.ObjectiveParameter("103", "203", 8.0),
    ]

    filtered, total = service.apply_advanced_filters(
        omni,
        watershed=DummyWatershed(),
        control_scenario="uniform_high",
        obj_param_descending=records,
        contrast_hill_min_slope=0.3,
        contrast_hill_max_slope=None,
        contrast_select_burn_severities={2, 3},
        contrast_select_topaz_ids={102, 103},
    )

    assert [item.topaz_id for item in filtered] == ["102", "103"]
    assert total == 17.0


def test_apply_advanced_filters_rejects_unknown_burn_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniScalingService()
    omni = _DummyOmni(tmp_path)

    class DummyWatershed:
        @staticmethod
        def hillslope_slope(topaz_id: str) -> float:
            return 0.4

    class DummyLanduse:
        @staticmethod
        def identify_burn_class(topaz_id: str) -> str:
            return "Extreme"

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())

    records = [omni_module.ObjectiveParameter("101", "201", 10.0)]

    with pytest.raises(ValueError, match="Unknown burn class"):
        service.apply_advanced_filters(
            omni,
            watershed=DummyWatershed(),
            control_scenario="uniform_high",
            obj_param_descending=records,
            contrast_hill_min_slope=None,
            contrast_hill_max_slope=None,
            contrast_select_burn_severities={1},
            contrast_select_topaz_ids=None,
        )


def test_normalize_filter_inputs_rejects_malformed_numeric_values() -> None:
    service = OmniScalingService()

    with pytest.raises(ValueError, match="must be a number"):
        service.normalize_filter_inputs(
            contrast_hill_min_slope="not-a-number",
            contrast_hill_max_slope=None,
            contrast_select_burn_severities=None,
            contrast_select_topaz_ids=None,
        )

    with pytest.raises(ValueError, match="entries must be integers"):
        service.normalize_filter_inputs(
            contrast_hill_min_slope=None,
            contrast_hill_max_slope=None,
            contrast_select_burn_severities="1,2,bad",
            contrast_select_topaz_ids=None,
        )
