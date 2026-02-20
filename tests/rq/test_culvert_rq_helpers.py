from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.culvert_rq_helpers as helpers

pytestmark = pytest.mark.unit


def test_load_payload_json_validates_missing_invalid_and_non_object(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        helpers._load_payload_json(missing_path)

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ValueError):
        helpers._load_payload_json(invalid_path)

    list_payload_path = tmp_path / "list.json"
    list_payload_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError):
        helpers._load_payload_json(list_payload_path)

    valid_payload_path = tmp_path / "payload.json"
    valid_payload_path.write_text(json.dumps({"schema": "v1"}), encoding="utf-8")
    assert helpers._load_payload_json(valid_payload_path) == {"schema": "v1"}


def test_map_order_reduction_passes_applies_cellsize_and_threshold_mapping() -> None:
    assert helpers._map_order_reduction_passes(cellsize_m=None, flow_accum_threshold=None) is None
    assert helpers._map_order_reduction_passes(cellsize_m=0.5, flow_accum_threshold=100) == 3
    assert helpers._map_order_reduction_passes(cellsize_m=2.0, flow_accum_threshold=100) == 2
    assert helpers._map_order_reduction_passes(cellsize_m=5.0, flow_accum_threshold=100) == 1
    # threshold increases effective cell size: 2m with threshold 900 -> 6m => 1 pass
    assert helpers._map_order_reduction_passes(cellsize_m=2.0, flow_accum_threshold=900) == 1


def test_minimum_watershed_area_error_respects_threshold_and_type_name() -> None:
    feature = SimpleNamespace(properties={"area_sqm": 12.0}, area_m2=12.0)
    assert (
        helpers._minimum_watershed_area_error(
            run_id="11",
            watershed_feature=feature,
            minimum_watershed_area_m2=10.0,
        )
        is None
    )

    error = helpers._minimum_watershed_area_error(
        run_id="11",
        watershed_feature=feature,
        minimum_watershed_area_m2=20.0,
        error_type_name="CustomMinAreaError",
    )
    assert error is not None
    assert error["type"] == "CustomMinAreaError"
    assert "Point_ID 11" in error["message"]


def test_select_watershed_label_prefers_named_properties_then_feature_id() -> None:
    named_feature = SimpleNamespace(properties={"watershed_name": "Upper Fork"}, id="fallback")
    assert helpers._select_watershed_label(named_feature) == "Upper Fork"

    id_only_feature = SimpleNamespace(properties={}, id="ws-42")
    assert helpers._select_watershed_label(id_only_feature) == "ws-42"

    assert helpers._select_watershed_label(None) is None
