import json

import pytest

from wepppy.nodb.mods.openet import openet_ts

pytestmark = pytest.mark.unit


def test_parse_timeseries_rows_handles_units_and_filters() -> None:
    rows = [
        {"Date": "2023-06-01", "et_ensemble_mad (mm)": 35.0},
        {"Date": "2023-07-01", "et_ensemble_mad (mm)": -9999},
        {"Date": "bad", "et_ensemble_mad (mm)": 10.0},
    ]

    df = openet_ts._parse_timeseries_rows(
        rows,
        topaz_id="12",
        dataset_key="ensemble",
        dataset_id="OPENET_CONUS",
        variable="et_ensemble_mad",
    )

    assert len(df) == 1
    row = df.iloc[0]
    assert row["topaz_id"] == "12"
    assert row["year"] == 2023
    assert row["month"] == 6
    assert row["units"] == "mm"
    assert row["value"] == 35.0


def test_parse_timeseries_rows_accepts_variable_without_units() -> None:
    rows = [
        {"Date": "2023-06-01", "et_eemetric": 31.0},
    ]

    df = openet_ts._parse_timeseries_rows(
        rows,
        topaz_id="23",
        dataset_key="eemetric",
        dataset_id="OPENET_CONUS",
        variable="et_eemetric",
    )

    assert len(df) == 1
    row = df.iloc[0]
    assert row["units"] == "mm"
    assert row["value"] == 31.0


def test_load_subcatchments_skips_channels(tmp_path) -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"TopazID": "14"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"TopazID": "15"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 2], [2, 2], [0, 0]]],
                },
            },
        ],
    }

    geojson_path = tmp_path / "subcatchments.json"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    selections = openet_ts._load_subcatchments(str(geojson_path))

    assert selections == [("15", [[[0, 0], [0, 2], [2, 2], [0, 0]]])]
