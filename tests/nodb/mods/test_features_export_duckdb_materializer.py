from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame
from wepppy.nodb.mods.features_export.duckdb_materializer import (
    LayerCarrierInput,
    materialize_carrier_core,
    materialize_layer_attributes,
)
from wepppy.nodb.mods.features_export.geometry_carriers import (
    CanonicalGeometryCarrier,
    attach_geometry_once,
)
from wepppy.nodb.mods.features_export.join_planner import (
    JOIN_KEY_COLUMN,
    MaterializationContractError,
)

pytestmark = pytest.mark.unit


def test_materialize_layer_attributes_allows_non_unique_keys_when_enabled() -> None:
    merged, _ = materialize_layer_attributes(
        layer_id="wepp.temporal.events",
        carrier_layer="sbs_map-subcatchments",
        join_contract={"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
        sources=(
            DiscoveredSourceFrame(
                source_id="wepp_return_period_events",
                source_kind="parquet",
                required=True,
                dataframe=pd.DataFrame(
                    {
                        "topaz_id": [1, 1],
                        "runoff_volume_m3": [10.0, 20.0],
                    }
                ),
                units_by_column={"runoff_volume_m3": "m^3"},
            ),
        ),
        allow_non_unique_keys=True,
    )

    assert len(merged.index) == 2
    assert merged[JOIN_KEY_COLUMN].tolist() == ["1", "1"]
    assert merged["runoff_volume_m3"].tolist() == [10.0, 20.0]


def test_materialize_carrier_core_rejects_many_to_many_when_non_unique_enabled() -> None:
    with pytest.raises(MaterializationContractError, match="many-to-many"):
        materialize_carrier_core(
            carrier_label="baseline__sbs_map-subcatchments",
            layer_inputs=(
                LayerCarrierInput(
                    layer_id="wepp.temporal.events",
                    dataframe=pd.DataFrame(
                        {
                            JOIN_KEY_COLUMN: ["1", "1"],
                            "runoff_volume_m3": [10.0, 20.0],
                        }
                    ),
                    selected_columns=("runoff_volume_m3",),
                    unit_mapping={"runoff_volume_m3": "m^3"},
                ),
                LayerCarrierInput(
                    layer_id="wepp.summary.hillslopes",
                    dataframe=pd.DataFrame(
                        {
                            JOIN_KEY_COLUMN: ["1", "1"],
                            "soil_loss_kg_ha": [1.0, 2.0],
                        }
                    ),
                    selected_columns=("soil_loss_kg_ha",),
                    unit_mapping={"soil_loss_kg_ha": "kg/ha"},
                ),
            ),
            allow_non_unique_keys=True,
        )


def test_attach_geometry_once_allows_non_unique_core_keys_when_enabled() -> None:
    geometry_carrier = CanonicalGeometryCarrier(
        carrier_layer="sbs_map-subcatchments",
        geometry_relpath="dem/wbt/subcatchments.WGS.geojson",
        key_column="TopazID",
        dataframe=gpd.GeoDataFrame(
            {
                JOIN_KEY_COLUMN: ["1", "2", "3"],
                "TopazID": [1, 2, 3],
                "geometry": [Point(0.0, 0.0), Point(1.0, 1.0), Point(2.0, 2.0)],
            },
            geometry="geometry",
            crs="EPSG:4326",
        ),
    )
    core_table = pd.DataFrame(
        {
            JOIN_KEY_COLUMN: ["1", "1", "2"],
            "runoff_volume_m3": [10.0, 20.0, 30.0],
        }
    )

    merged = attach_geometry_once(
        core_table=core_table,
        geometry_carrier=geometry_carrier,
        allow_non_unique_keys=True,
    )

    assert len(merged.index) == 4
    assert merged.geometry.notna().all()
    assert merged[JOIN_KEY_COLUMN].tolist().count("3") == 1
    assert merged.loc[merged[JOIN_KEY_COLUMN] == "3", "runoff_volume_m3"].isna().all()


def test_materialize_layer_attributes_allows_empty_event_selection_when_enabled() -> None:
    merged, _ = materialize_layer_attributes(
        layer_id="wepp.temporal.events",
        carrier_layer="sbs_map-subcatchments",
        join_contract={"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
        sources=(
            DiscoveredSourceFrame(
                source_id="wepp_return_period_events",
                source_kind="parquet",
                required=True,
                dataframe=pd.DataFrame(
                    {
                        "topaz_id": [],
                        "runoff_volume_m3": [],
                    }
                ),
                units_by_column={"runoff_volume_m3": "m^3"},
            ),
        ),
        allow_non_unique_keys=True,
    )

    assert merged.empty
    assert JOIN_KEY_COLUMN in merged.columns


def test_materialize_carrier_core_allows_empty_inputs_when_enabled() -> None:
    result = materialize_carrier_core(
        carrier_label="baseline__sbs_map-subcatchments",
        layer_inputs=(
            LayerCarrierInput(
                layer_id="wepp.temporal.events",
                dataframe=pd.DataFrame(
                    {
                        JOIN_KEY_COLUMN: [],
                        "runoff_volume_m3": [],
                    }
                ),
                selected_columns=("runoff_volume_m3",),
                unit_mapping={"runoff_volume_m3": "m^3"},
            ),
        ),
        allow_non_unique_keys=True,
    )

    assert result.dataframe.empty
    assert JOIN_KEY_COLUMN in result.dataframe.columns
