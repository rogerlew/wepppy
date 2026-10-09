import json
from types import SimpleNamespace

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


@pytest.mark.parametrize("spatial_mode", [0, 1, 2])
def test_historic_prism_accepts_calendar_bounds(spatial_mode) -> None:
    climate = SimpleNamespace(
        climate_mode=openet_ts.ClimateMode.Prism800m,
        climate_spatialmode=spatial_mode,
        observed_start_year="2019", observed_end_year="2021",
    )
    assert openet_ts.OpenET_TS._validate_climate(None, climate) == (2019, 2021)


@pytest.mark.parametrize("start,end", [(2021, 2019), (None, 2021), ("bad", 2021)])
def test_historic_prism_rejects_invalid_calendar_bounds(start, end) -> None:
    climate = SimpleNamespace(
        climate_mode=openet_ts.ClimateMode.Prism800m,
        observed_start_year=start, observed_end_year=end,
    )
    with pytest.raises(ValueError):
        openet_ts.OpenET_TS._validate_climate(None, climate)


def test_stochastic_mode_still_rejected() -> None:
    climate = SimpleNamespace(
        climate_mode=openet_ts.ClimateMode.Vanilla,
        observed_start_year=2019, observed_end_year=2021,
    )
    with pytest.raises(ValueError, match="requires observed climate"):
        openet_ts.OpenET_TS._validate_climate(None, climate)


@pytest.mark.parametrize("start,requested_start,expected", [
    (2019, None, "2019-01-01"), (2010, None, "2016-01-01"),
])
def test_prism_acquisition_preserves_year_range_and_start_clamp(
    tmp_path, monkeypatch, start, requested_start, expected,
) -> None:
    from contextlib import nullcontext

    climate = SimpleNamespace(
        climate_mode=openet_ts.ClimateMode.Prism800m,
        observed_start_year=start, observed_end_year=2021,
    )
    shape = tmp_path / "hills.json"
    shape.write_text("{}")
    monkeypatch.setattr(openet_ts.Climate, "getInstance", lambda wd: climate)
    monkeypatch.setattr(openet_ts.Watershed, "getInstance",
                        lambda wd: SimpleNamespace(subwta_shp=str(shape)))
    monkeypatch.setattr(openet_ts, "_load_api_key", lambda: "test-only")
    monkeypatch.setattr(openet_ts, "_load_subcatchments", lambda *a, **k: [("15", [])])
    calls = []

    def fetch(headers, dataset, variable, first, last, coords, topaz):
        calls.append((first, last, topaz))
        return openet_ts._parse_timeseries_rows(
            [{"Date": "2020-02-01", variable: 10.0}], topaz_id=topaz,
            dataset_key=dataset, dataset_id="OPENET_CONUS", variable=variable,
        )

    controller = SimpleNamespace(
        wd=str(tmp_path), _validate_climate=lambda c: openet_ts.OpenET_TS._validate_climate(None, c),
        _openet_start_year=None, _openet_end_year=None,
        openet_individual_dir=str(tmp_path / "individual"),
        locked=lambda: nullcontext(), _purge_cache=lambda: None, _fetch_one=fetch,
        logger=SimpleNamespace(info=lambda *a: None, warning=lambda *a: None),
    )
    openet_ts.OpenET_TS.acquire_timeseries(controller, start_year=requested_start, max_workers=1)
    assert calls == [(expected, "2021-12-31", "15")] * len(openet_ts.OPENET_VARIABLES)
    for path in (tmp_path / "individual").glob("*/15.parquet"):
        frame = openet_ts.pd.read_parquet(path)
        assert frame[["year", "month"]].values.tolist() == [[2020, 2]]
        assert frame["units"].tolist() == ["mm"]
