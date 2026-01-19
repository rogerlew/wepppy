from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("flask")

import wepppy.weppcloud.routes.nodb_api.omni_bp as omni_bp

pytestmark = pytest.mark.unit


def test_summarize_omni_contrast_outlet_metrics_uses_topaz_id_for_cumulative():
    df = pd.DataFrame({
        "key": [
            "Avg. Ann. water discharge from outlet",
            "Avg. Ann. total hillslope soil loss",
            "Avg. Ann. water discharge from outlet",
            "Avg. Ann. total hillslope soil loss",
        ],
        "value": [1.0, 2.0, 3.0, 4.0],
        "units": ["m^3/yr", "tonne/yr", "m^3/yr", "tonne/yr"],
        "contrast_topaz_id": [10, 10, 20, 20],
        "contrast_id": [1, 1, 2, 2],
        "contrast": ["c1", "c1", "c2", "c2"],
    })

    result = omni_bp._summarize_omni_contrast_outlet_metrics(df, "cumulative")

    assert [row["name"] for row in result] == ["10", "20"]
    assert result[0]["water_discharge"]["value"] == 1.0
    assert result[0]["soil_loss"]["value"] == 2.0


def test_summarize_omni_contrast_outlet_metrics_uses_contrast_id_for_user_defined():
    df = pd.DataFrame({
        "key": [
            "Avg. Ann. water discharge from outlet",
            "Avg. Ann. total hillslope soil loss",
        ],
        "value": [5.0, 6.0],
        "units": ["m^3/yr", "tonne/yr"],
        "contrast": ["Area A", "Area A"],
        "contrast_id": [7, 7],
    })

    result = omni_bp._summarize_omni_contrast_outlet_metrics(df, "user_defined_areas")

    assert len(result) == 1
    assert result[0]["name"] == "7"
    assert result[0]["water_discharge"]["value"] == 5.0
    assert result[0]["soil_loss"]["value"] == 6.0
