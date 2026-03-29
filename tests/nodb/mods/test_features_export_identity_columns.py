from __future__ import annotations

import pandas as pd
import pytest

from wepppy.nodb.mods.features_export.identity_columns import normalize_identity_output_columns

pytestmark = pytest.mark.unit


def test_normalize_identity_output_columns_coalesces_aliases_and_orders_columns() -> None:
    frame = pd.DataFrame(
        {
            "TopazID": [101, 102],
            "topaz_id": [None, 202],
            "WeppID": [41, 42],
            "metric_mm": [1.5, 2.0],
        }
    )

    normalized_frame, selected_columns, unit_mapping = normalize_identity_output_columns(
        frame=frame,
        selected_columns=("TopazID", "WeppID", "metric_mm"),
        unit_mapping={"TopazID": "non-unitized", "WeppID": "non-unitized", "metric_mm": "mm"},
        geometry_name=None,
        consolidated_join_key_column="__join_key__",
    )

    assert selected_columns == ("topaz_id", "wepp_id", "metric_mm")
    assert "TopazID" not in normalized_frame.columns
    assert "WeppID" not in normalized_frame.columns
    assert normalized_frame["topaz_id"].tolist() == [101, 202]
    assert normalized_frame["wepp_id"].tolist() == [41, 42]
    assert unit_mapping["topaz_id"] == "non-unitized"
    assert unit_mapping["wepp_id"] == "non-unitized"


def test_normalize_identity_output_columns_adds_missing_canonical_columns() -> None:
    frame = pd.DataFrame({"chn_id": [1, 2], "value": [10.0, 11.0]})

    normalized_frame, selected_columns, unit_mapping = normalize_identity_output_columns(
        frame=frame,
        selected_columns=("chn_id", "value"),
        unit_mapping={"chn_id": "non-unitized", "value": "non-unitized"},
        geometry_name=None,
        consolidated_join_key_column="__join_key__",
    )

    assert selected_columns[:2] == ("topaz_id", "wepp_id")
    assert "topaz_id" in normalized_frame.columns
    assert "wepp_id" in normalized_frame.columns
    assert normalized_frame["topaz_id"].isna().all()
    assert normalized_frame["wepp_id"].isna().all()
    assert unit_mapping["topaz_id"] == "non-unitized"
    assert unit_mapping["wepp_id"] == "non-unitized"

