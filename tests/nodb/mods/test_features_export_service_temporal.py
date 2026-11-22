from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.contracts import NormalizedTemporalEvent
from wepppy.nodb.mods.features_export.join_planner import MaterializationContractError
from wepppy.nodb.mods.features_export.tabular_temporal_layout import reshape_temporal_wide_to_long
from wepppy.nodb.mods.features_export.temporal_wide_materializer import materialize_temporal_layer_wide

pytestmark = pytest.mark.unit


def test_materialize_temporal_layer_wide_event_pivots_measures_to_one_row_per_key() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "2", "2"],
            "wepp_id": [1, 1, 2, 2],
            "date": ["2015-01-15", "2015-01-16", "2015-01-15", "2015-01-16"],
            "p_mm": [22.6, 15.7, 20.0, 14.0],
            "q_mm": [0.0, 0.0, 0.5, 0.4],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_wat",
        temporal_mode="event",
        selected_columns=("wepp_id", "date", "p_mm", "q_mm"),
        unit_mapping={"p_mm": "mm", "q_mm": "mm", "wepp_id": "non-unitized"},
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=NormalizedTemporalEvent(
            selector="date",
            dates=("2015-01-15", "2015-01-16"),
        ),
    )

    assert len(reshaped.frame.index) == 2
    assert reshaped.selected_columns == (
        "wepp_id",
        "p_mm_2015_01_15",
        "p_mm_2015_01_16",
        "q_mm_2015_01_15",
        "q_mm_2015_01_16",
    )
    assert reshaped.frame.loc[reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1", "p_mm_2015_01_15"].iloc[0] == pytest.approx(22.6)
    assert reshaped.frame.loc[reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1", "p_mm_2015_01_16"].iloc[0] == pytest.approx(15.7)


def test_materialize_temporal_layer_wide_event_prefers_terminal_ofe_slice() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1"],
            "wepp_id": [1, 1],
            "ofe_id": [1, 2],
            "date": ["2015-01-15", "2015-01-15"],
            "q_mm": [0.5, 1.25],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_wat",
        temporal_mode="event",
        selected_columns=("wepp_id", "date", "q_mm"),
        unit_mapping={"q_mm": "mm", "wepp_id": "non-unitized"},
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=NormalizedTemporalEvent(
            selector="date",
            dates=("2015-01-15",),
        ),
    )

    assert len(reshaped.frame.index) == 1
    assert reshaped.selected_columns == ("wepp_id", "q_mm_2015_01_15")
    assert reshaped.frame["q_mm_2015_01_15"].iloc[0] == pytest.approx(1.25)


def test_materialize_temporal_layer_wide_yearly_pivots_measures_to_year_columns() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "2", "2"],
            "wepp_id": [1, 1, 2, 2],
            "year": [2014, 2015, 2014, 2015],
            "sediment_kg": [10.0, 12.0, 8.0, 9.5],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_pass",
        temporal_mode="yearly",
        selected_columns=("wepp_id", "year", "sediment_kg"),
        unit_mapping={"sediment_kg": "kg", "wepp_id": "non-unitized"},
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert len(reshaped.frame.index) == 2
    assert reshaped.selected_columns == ("wepp_id", "sediment_kg_yr2014", "sediment_kg_yr2015")
    assert reshaped.frame.loc[reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "2", "sediment_kg_yr2015"].iloc[0] == pytest.approx(9.5)


def test_materialize_temporal_layer_wide_yearly_accepts_fire_year_column() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "2"],
            "wepp_id": [1, 1, 2],
            "fire_year": [2021, 2022, 2021],
            "ash_transport_tonne_ha": [5.0, 7.0, 3.5],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="ash.transport.hillslope_annuals",
        temporal_mode="yearly",
        selected_columns=("wepp_id", "fire_year", "ash_transport_tonne_ha"),
        unit_mapping={
            "wepp_id": "non-unitized",
            "ash_transport_tonne_ha": "tonne/ha",
        },
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert reshaped.selected_columns == (
        "wepp_id",
        "ash_transport_tonne_ha_yr2021",
        "ash_transport_tonne_ha_yr2022",
    )
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "ash_transport_tonne_ha_yr2021",
    ].iloc[0] == pytest.approx(5.0)
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "ash_transport_tonne_ha_yr2022",
    ].iloc[0] == pytest.approx(7.0)


def test_materialize_temporal_layer_wide_yearly_sums_numeric_like_object_slices() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "1", "2"],
            "wepp_id": [1, 1, 1, 2],
            "year": [2014, 2014, 2015, 2014],
            "sediment_kg": ["10.0", "12.5", "3.0", "8.0"],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_pass",
        temporal_mode="yearly",
        selected_columns=("wepp_id", "year", "sediment_kg"),
        unit_mapping={"sediment_kg": "kg", "wepp_id": "non-unitized"},
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "sediment_kg_yr2014", "sediment_kg_yr2015")
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "sediment_kg_yr2014",
    ].iloc[0] == pytest.approx(22.5)


def test_materialize_temporal_layer_wide_yearly_rejects_conflicting_non_numeric_slices() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1"],
            "wepp_id": [1, 1],
            "year": [2014, 2014],
            "soil_class": ["A", "B"],
        }
    )

    with pytest.raises(MaterializationContractError) as exc_info:
        materialize_temporal_layer_wide(
            frame=frame,
            layer_id="wepp.interchange.hill_pass",
            temporal_mode="yearly",
            selected_columns=("wepp_id", "year", "soil_class"),
            unit_mapping={"soil_class": "non-unitized", "wepp_id": "non-unitized"},
            join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
            event_selector=None,
        )

    assert "conflicting non-numeric values" in str(exc_info.value)


def test_materialize_temporal_layer_wide_yearly_treats_event_column_as_control() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "1"],
            "wepp_id": [1, 1, 1],
            "year": [2014, 2014, 2015],
            "event": ["E1", "E2", "E3"],
            "sediment_kg": [10.0, 12.5, 3.0],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_pass",
        temporal_mode="yearly",
        selected_columns=("wepp_id", "year", "event", "sediment_kg"),
        unit_mapping={
            "event": "non-unitized",
            "sediment_kg": "kg",
            "wepp_id": "non-unitized",
        },
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "sediment_kg_yr2014", "sediment_kg_yr2015")
    assert "event_yr2014" not in reshaped.frame.columns
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "sediment_kg_yr2014",
    ].iloc[0] == pytest.approx(22.5)


def test_materialize_temporal_layer_wide_annual_average_means_selected_years() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "1", "2", "2"],
            "wepp_id": [1, 1, 1, 2, 2],
            "year": [2014, 2014, 2015, 2014, 2015],
            "runoff_mm": [10.0, 12.0, 8.0, 4.0, 6.0],
            "sim_day_index": [1, 2, 3, 10, 11],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="wepp.interchange.hill_pass",
        temporal_mode="annual_average",
        selected_columns=("wepp_id", "year", "runoff_mm", "sim_day_index"),
        unit_mapping={
            "wepp_id": "non-unitized",
            "runoff_mm": "mm",
            "sim_day_index": "non-unitized",
        },
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "runoff_mm", "sim_day_index")
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "runoff_mm",
    ].iloc[0] == pytest.approx(15.0)
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "sim_day_index",
    ].iloc[0] == pytest.approx(3.0)
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "2",
        "runoff_mm",
    ].iloc[0] == pytest.approx(5.0)
    assert "runoff_mm_yr2014" not in reshaped.frame.columns


def test_materialize_temporal_layer_wide_annual_average_without_year_column_averages_rows() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "2"],
            "wepp_id": [1, 1, 2],
            "ash_transport_tonne_ha": [10.0, 14.0, 20.0],
        }
    )

    reshaped = materialize_temporal_layer_wide(
        frame=frame,
        layer_id="ash.transport.hillslope_annuals",
        temporal_mode="annual_average",
        selected_columns=("wepp_id", "ash_transport_tonne_ha"),
        unit_mapping={
            "wepp_id": "non-unitized",
            "ash_transport_tonne_ha": "tonne/ha",
        },
        join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "ash_transport_tonne_ha")
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "1",
        "ash_transport_tonne_ha",
    ].iloc[0] == pytest.approx(12.0)
    assert reshaped.frame.loc[
        reshaped.frame[service._CONSOLIDATED_JOIN_KEY_COLUMN] == "2",
        "ash_transport_tonne_ha",
    ].iloc[0] == pytest.approx(20.0)


def test_materialize_temporal_layer_wide_annual_average_rejects_conflicting_non_numeric_year_values() -> None:
    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "1", "1"],
            "wepp_id": [1, 1, 1],
            "year": [2014, 2015, 2016],
            "soil_class": ["A", "A", "B"],
        }
    )

    with pytest.raises(MaterializationContractError) as exc_info:
        materialize_temporal_layer_wide(
            frame=frame,
            layer_id="wepp.interchange.hill_pass",
            temporal_mode="annual_average",
            selected_columns=("wepp_id", "year", "soil_class"),
            unit_mapping={"soil_class": "non-unitized", "wepp_id": "non-unitized"},
            join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
            event_selector=None,
        )

    assert "Annual-average materialization found conflicting non-numeric values across years." in str(
        exc_info.value
    )


def test_reshape_temporal_wide_to_long_event_restores_date_rows() -> None:
    frame = gpd.GeoDataFrame(
        {
            "topaz_id": [1, 2],
            "p_mm_2015_01_15": [22.6, 20.0],
            "p_mm_2015_01_16": [15.7, 14.0],
            "q_mm_2015_01_15": [0.0, 0.5],
            "q_mm_2015_01_16": [0.0, 0.4],
            "geometry": [Point(0.0, 0.0), Point(1.0, 1.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    reshaped = reshape_temporal_wide_to_long(
        frame=frame,
        selected_columns=(
            "topaz_id",
            "p_mm_2015_01_15",
            "p_mm_2015_01_16",
            "q_mm_2015_01_15",
            "q_mm_2015_01_16",
        ),
        unit_mapping={
            "topaz_id": "non-unitized",
            "p_mm_2015_01_15": "mm",
            "p_mm_2015_01_16": "mm",
            "q_mm_2015_01_15": "mm",
            "q_mm_2015_01_16": "mm",
        },
        temporal_mode="event",
        event_selector=NormalizedTemporalEvent(selector="date", dates=("2015-01-15", "2015-01-16")),
    )

    assert reshaped.selected_columns == ("topaz_id", "date", "p_mm", "q_mm")
    assert len(reshaped.frame.index) == 4
    assert sorted(reshaped.frame["date"].dropna().unique().tolist()) == ["2015-01-15", "2015-01-16"]
    assert reshaped.frame.loc[0, "p_mm"] == pytest.approx(22.6)
    assert reshaped.frame.loc[1, "p_mm"] == pytest.approx(20.0)


def test_reshape_temporal_wide_to_long_yearly_restores_year_rows() -> None:
    frame = gpd.GeoDataFrame(
        {
            "wepp_id": [1, 2],
            "soil_loss_kg_yr2014": [10.0, 8.0],
            "soil_loss_kg_yr2015": [12.0, 9.5],
            "geometry": [Point(0.0, 0.0), Point(1.0, 1.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    reshaped = reshape_temporal_wide_to_long(
        frame=frame,
        selected_columns=("wepp_id", "soil_loss_kg_yr2014", "soil_loss_kg_yr2015"),
        unit_mapping={
            "wepp_id": "non-unitized",
            "soil_loss_kg_yr2014": "kg",
            "soil_loss_kg_yr2015": "kg",
        },
        temporal_mode="yearly",
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "year", "soil_loss_kg")
    assert sorted(reshaped.frame["year"].dropna().unique().tolist()) == [2014, 2015]
    assert len(reshaped.frame.index) == 4


def test_reshape_temporal_wide_to_long_supports_non_geometry_frames() -> None:
    frame = pd.DataFrame(
        {
            "wepp_id": [1, 2],
            "soil_loss_kg_yr2014": [10.0, 8.0],
            "soil_loss_kg_yr2015": [12.0, 9.5],
        }
    )

    reshaped = reshape_temporal_wide_to_long(
        frame=frame,
        selected_columns=("wepp_id", "soil_loss_kg_yr2014", "soil_loss_kg_yr2015"),
        unit_mapping={
            "wepp_id": "non-unitized",
            "soil_loss_kg_yr2014": "kg",
            "soil_loss_kg_yr2015": "kg",
        },
        temporal_mode="yearly",
        event_selector=None,
    )

    assert reshaped.selected_columns == ("wepp_id", "year", "soil_loss_kg")
    assert "geometry" not in reshaped.frame.columns
    assert sorted(reshaped.frame["year"].dropna().unique().tolist()) == [2014, 2015]
    assert len(reshaped.frame.index) == 4
