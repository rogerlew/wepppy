from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.contracts import (
    LayerColumnSelection,
    NormalizedExportRequest,
    NormalizedTemporalEvent,
    NormalizedTemporalRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.dependency_tracker import DependencySnapshot
from wepppy.nodb.mods.features_export.join_planner import MaterializationContractError

pytestmark = pytest.mark.unit


def test_build_materialized_execution_plan_consolidates_carrier_layers() -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=(
            "watershed.subcatchments",
            "wepp.summary.hillslopes",
            "wepp.temporal.events",
            "omni.scenarios.hillslopes",
        ),
        crs="wgs",
        output_scopes=("baseline", "roads"),
        scenarios=("thinned",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.summary.hillslopes",
                family="wepp_summary",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.summary.hillslopes",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.temporal.events",
                family="wepp_temporal",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.temporal.events",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.summary.hillslopes",
                family="wepp_summary",
                scope_class="scope_aware",
                scope="roads",
                output_layer_id="roads__wepp.summary.hillslopes",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="omni.scenarios.hillslopes",
                family="omni_scenarios",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="scenario-thinned__shared__omni.scenarios.hillslopes",
                context="scenario",
                selector_id="thinned",
                carrier_layer="sbs_map-subcatchments",
            ),
        ),
        warnings=(),
    )

    materialized_plan, grouped = service._build_materialized_execution_plan(plan, runid="minus-farce")

    assert [layer.output_layer_id for layer in materialized_plan.layers] == [
        "minus-farce-roads-sbs_map-subcatchments",
        "minus-farce-sbs_map-subcatchments",
        "minus-farce-scenario-thinned-sbs_map-subcatchments",
    ]
    assert [layer.layer_id for layer in grouped["minus-farce-sbs_map-subcatchments"]] == [
        "watershed.subcatchments",
        "wepp.summary.hillslopes",
        "wepp.temporal.events",
    ]
    assert [layer.layer_id for layer in grouped["minus-farce-roads-sbs_map-subcatchments"]] == [
        "wepp.summary.hillslopes",
    ]
    assert [layer.layer_id for layer in grouped["minus-farce-scenario-thinned-sbs_map-subcatchments"]] == [
        "omni.scenarios.hillslopes",
    ]


def test_build_materialized_execution_plan_wepp_six_inputs_collapse_to_two_carriers() -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=(
            "wepp.summary.hillslopes",
            "wepp.summary.channels",
            "wepp.temporal.events",
            "wepp.interchange.hill_pass",
            "wepp.interchange.hill_element",
            "wepp.interchange.hill_wat",
        ),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="wepp.summary.hillslopes",
                family="wepp_summary",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.summary.hillslopes",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.summary.channels",
                family="wepp_summary",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.summary.channels",
                context="base",
                carrier_layer="chan_map-channels",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.temporal.events",
                family="wepp_temporal",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.temporal.events",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.interchange.hill_pass",
                family="wepp_interchange",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.interchange.hill_pass",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.interchange.hill_element",
                family="wepp_interchange",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.interchange.hill_element",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
            ResolvedLayerPlan(
                layer_id="wepp.interchange.hill_wat",
                family="wepp_interchange",
                scope_class="scope_aware",
                scope="baseline",
                output_layer_id="baseline__wepp.interchange.hill_wat",
                context="base",
                carrier_layer="sbs_map-subcatchments",
            ),
        ),
        warnings=(),
    )

    materialized_plan, grouped = service._build_materialized_execution_plan(plan, runid="minus-farce")

    assert [layer.output_layer_id for layer in materialized_plan.layers] == [
        "minus-farce-chan_map-channels",
        "minus-farce-sbs_map-subcatchments",
    ]
    assert [layer.layer_id for layer in grouped["minus-farce-chan_map-channels"]] == [
        "wepp.summary.channels",
    ]
    assert [layer.layer_id for layer in grouped["minus-farce-sbs_map-subcatchments"]] == [
        "wepp.interchange.hill_element",
        "wepp.interchange.hill_pass",
        "wepp.interchange.hill_wat",
        "wepp.summary.hillslopes",
        "wepp.temporal.events",
    ]


def test_build_materialized_layer_payload_rejects_multi_source_passthrough_group() -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
    )
    source_a = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments__a",
    )
    source_b = ResolvedLayerPlan(
        layer_id="wepp.summary.hillslopes",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.hillslopes",
    )
    frame = gpd.GeoDataFrame(
        {"value": [1.0], "geometry": [Point(0, 0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_results = (
        service._LayerFrameResult(
            layer=source_a,
            frame=frame.copy(),
            selected_columns=("value",),
            unit_mapping={"value": "m3"},
            warnings=(),
        ),
        service._LayerFrameResult(
            layer=source_b,
            frame=frame.copy(),
            selected_columns=("value",),
            unit_mapping={"value": "m3"},
            warnings=(),
        ),
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._build_materialized_layer_payload(
            layer,
            source_results=source_results,
            use_tabular_payload=False,
        )

    assert exc_info.value.code == "materialization_error"
    assert "source_count=2" in exc_info.value.details


def test_build_materialized_layer_payload_tabular_skips_feature_collection_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
    )
    source = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments__source",
    )
    frame = gpd.GeoDataFrame(
        {"TopazID": [1, 2], "metric": [4.0, 5.0], "geometry": [Point(0, 0), Point(1, 1)]},
        geometry="geometry",
        crs="EPSG:4326",
    )

    def _raise_if_called(*args, **kwargs):
        raise AssertionError("feature-collection serializer should not be called for tabular payloads")

    monkeypatch.setattr(service, "_serialize_feature_collection_payload", _raise_if_called)

    payload, column_metadata = service._build_materialized_layer_payload(
        layer,
        source_results=(
            service._LayerFrameResult(
                layer=source,
                frame=frame,
                selected_columns=("TopazID", "metric"),
                unit_mapping={"TopazID": "non-unitized", "metric": "mm"},
                warnings=(),
            ),
        ),
        use_tabular_payload=True,
    )

    assert payload.payload == b""
    assert payload.tabular_frame is not None
    assert list(payload.tabular_frame.columns) == ["TopazID", "metric"]
    assert payload.row_count == 2
    assert payload.feature_count == 2
    assert column_metadata["selected_columns"] == ["TopazID", "metric"]
    assert column_metadata["description_mapping"] == {
        "TopazID": "Topaz ID.",
        "metric": "Metric (mm).",
    }


@pytest.mark.parametrize("source_id,expected_value", [(2, 7.5), (99, None)])
def test_key_first_spatial_event_payload_reads_geometry_and_attributes(
    tmp_path: Path, source_id: int, expected_value: float | None,
) -> None:
    geometry_path = tmp_path / "carrier.geojson"
    gpd.GeoDataFrame(
        {"wepp_id": [2]}, geometry=[Point(-116, 46)], crs="EPSG:4326",
    ).to_file(geometry_path, driver="GeoJSON")
    layer = ResolvedLayerPlan(
        layer_id="event_metric", family="wepp_interchange", scope_class="scope_aware",
        scope="baseline", output_layer_id="baseline__event_metric", temporal_mode="event",
    )
    source = service._LayerCoreResult(
        layer=layer,
        frame=pd.DataFrame({
            service._CONSOLIDATED_JOIN_KEY_COLUMN: [str(source_id)],
            "wepp_id": [source_id], "metric": [7.5],
        }),
        selected_columns=("wepp_id", "metric"),
        unit_mapping={"wepp_id": "non-unitized", "metric": "non-unitized"},
        warnings=(), catalog_layer_raw={"join": {"primary_key": "wepp_id"}},
    )
    dependency = SimpleNamespace(
        dependency_role="geometry", dependency_id="geometry", relpath=geometry_path.name,
    )
    payload, metadata = service._build_key_first_materialized_layer_payload(
        wd=tmp_path, layer=layer, source_layers=(layer,), source_results=(source,),
        entries_by_output_layer_id={layer.output_layer_id: (dependency,)},
        use_tabular_payload=False, use_tabular_long_layout=False, tabular_event_selector=None,
        watershed_identity_lookup_cache={}, units_mode="si",
    )

    document = json.loads(payload.payload)
    feature, = document["feature_collection"]["features"]
    assert document["crs_epsg"] == 4326
    assert feature["geometry"]["coordinates"] == [-116, 46]
    assert int(feature["properties"]["wepp_id"]) == 2
    assert feature["properties"]["metric"] == expected_value
    assert payload.tabular_frame is None
    assert payload.row_count == payload.feature_count == 1
    assert metadata["materialization"] == {
        "strategy": "key_first_geometry_last", "carrier_layer": None,
        "geometry_relpath": geometry_path.name, "carrier_key_column": "wepp_id",
        "core_row_count": 1, "geometry_row_count": 1,
    }


def test_key_first_tabular_payload_does_not_touch_geometry_carrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp_interchange.sbs_map-subcatchments",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="clogging-starch-sbs_map-subcatchments",
        temporal_mode="yearly",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    source_layer = ResolvedLayerPlan(
        layer_id="wepp.interchange.hill_ebe",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.interchange.hill_ebe",
        temporal_mode="yearly",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    source_result = service._LayerCoreResult(
        layer=source_layer,
        frame=pd.DataFrame(
            {
                service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2"],
                "wepp_id": [1, 2],
                "ER_yr2000": [0.1, 0.2],
            }
        ),
        selected_columns=("wepp_id", "ER_yr2000"),
        unit_mapping={"wepp_id": "non-unitized", "ER_yr2000": "non-unitized"},
        warnings=(),
        catalog_layer_raw={
            "join": {"primary_key": "wepp_id"},
            "geometry": {"feature_id_keys": ["wepp_id"]},
        },
    )

    def _raise_geometry_access(*args, **kwargs):
        raise AssertionError("geometry carrier should not be loaded for tabular payloads")

    monkeypatch.setattr(service, "build_canonical_geometry_carrier", _raise_geometry_access)

    payload, column_metadata = service._build_key_first_materialized_layer_payload(
        wd=tmp_path,
        layer=layer,
        source_layers=(source_layer,),
        source_results=(source_result,),
        entries_by_output_layer_id={},
        use_tabular_payload=True,
        use_tabular_long_layout=False,
        tabular_event_selector=None,
        watershed_identity_lookup_cache={},
        units_mode="si",
    )

    assert payload.tabular_frame is not None
    assert list(payload.tabular_frame.columns) == ["topaz_id", "wepp_id", "ER_yr2000"]
    assert payload.tabular_frame["topaz_id"].isna().all()
    assert payload.payload == b""
    assert column_metadata["materialization"]["strategy"] == "key_first_tabular_no_geometry"
    assert column_metadata["selected_columns"][:2] == ["topaz_id", "wepp_id"]
    assert column_metadata["description_mapping"]["topaz_id"] == "Topaz ID."
    assert column_metadata["description_mapping"]["wepp_id"] == "WEPP ID."


def test_key_first_tabular_payload_populates_channel_descriptions(tmp_path: Path) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp.summary.channels",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="run-1-chan_map-channels",
        context="base",
        carrier_layer="chan_map-channels",
    )
    source_layer = ResolvedLayerPlan(
        layer_id="wepp.summary.channels",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.channels",
        context="base",
        carrier_layer="chan_map-channels",
    )
    source_result = service._LayerCoreResult(
        layer=source_layer,
        frame=pd.DataFrame(
            {
                service._CONSOLIDATED_JOIN_KEY_COLUMN: ["101"],
                "topaz_id": [1],
                "wepp_id": [101],
                "discharge_mm": [12.5],
                "sediment_delivery_kg_ha": [3.2],
            }
        ),
        selected_columns=("topaz_id", "wepp_id", "discharge_mm", "sediment_delivery_kg_ha"),
        unit_mapping={
            "topaz_id": "non-unitized",
            "wepp_id": "non-unitized",
            "discharge_mm": "mm",
            "sediment_delivery_kg_ha": "kg/ha",
        },
        warnings=(),
        catalog_layer_raw={
            "join": {"primary_key": "wepp_id"},
            "geometry": {"feature_id_keys": ["topaz_id", "wepp_id"]},
            "columns": [
                {
                    "column_id": "discharge_mm",
                    "description": "Average annual channel discharge depth.",
                    "unit": {"display_unit": "mm"},
                },
                {
                    "column_id": "sediment_delivery_kg_ha",
                    "description": "Average annual sediment delivery per channel area.",
                    "unit": {"display_unit": "kg/ha"},
                },
            ],
        },
    )

    payload, column_metadata = service._build_key_first_materialized_layer_payload(
        wd=tmp_path,
        layer=layer,
        source_layers=(source_layer,),
        source_results=(source_result,),
        entries_by_output_layer_id={},
        use_tabular_payload=True,
        use_tabular_long_layout=False,
        tabular_event_selector=None,
        watershed_identity_lookup_cache={},
        units_mode="si",
    )

    assert payload.tabular_frame is not None
    assert column_metadata["description_mapping"]["discharge_mm"] == (
        "Average annual channel discharge depth."
    )
    assert column_metadata["description_mapping"]["sediment_delivery_kg_ha"] == (
        "Average annual sediment delivery per channel area."
    )


def test_key_first_tabular_payload_backfills_topaz_id_from_watershed_parquet(tmp_path: Path) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp_interchange.sbs_map-subcatchments",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="clogging-starch-sbs_map-subcatchments",
        temporal_mode="yearly",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    source_layer = ResolvedLayerPlan(
        layer_id="wepp.interchange.hill_ebe",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.interchange.hill_ebe",
        temporal_mode="yearly",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    source_result = service._LayerCoreResult(
        layer=source_layer,
        frame=pd.DataFrame(
            {
                service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2"],
                "wepp_id": [1, 2],
                "ER_yr2000": [0.1, 0.2],
            }
        ),
        selected_columns=("wepp_id", "ER_yr2000"),
        unit_mapping={"wepp_id": "non-unitized", "ER_yr2000": "non-unitized"},
        warnings=(),
        catalog_layer_raw={
            "join": {"primary_key": "wepp_id"},
            "geometry": {"feature_id_keys": ["wepp_id"]},
        },
    )

    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "topaz_id": [101, 102],
            "wepp_id": [1, 2],
        }
    ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)

    payload, _ = service._build_key_first_materialized_layer_payload(
        wd=tmp_path,
        layer=layer,
        source_layers=(source_layer,),
        source_results=(source_result,),
        entries_by_output_layer_id={},
        use_tabular_payload=True,
        use_tabular_long_layout=False,
        tabular_event_selector=None,
        watershed_identity_lookup_cache={},
        units_mode="si",
    )

    assert payload.tabular_frame is not None
    assert payload.tabular_frame["topaz_id"].tolist() == [101, 102]
    assert payload.tabular_frame["wepp_id"].tolist() == [1, 2]


def test_key_first_tabular_payload_retargets_join_key_domain_using_identity_lookup(
    tmp_path: Path,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp_interchange.sbs_map-subcatchments",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="clogging-starch-sbs_map-subcatchments",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    watershed_layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    wepp_layer = ResolvedLayerPlan(
        layer_id="wepp.interchange.loss_all_years_hill",
        family="wepp_interchange",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.interchange.loss_all_years_hill",
        temporal_mode="annual_average",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    source_results = (
        service._LayerCoreResult(
            layer=watershed_layer,
            frame=pd.DataFrame(
                {
                    service._CONSOLIDATED_JOIN_KEY_COLUMN: ["22", "23"],
                    "topaz_id": [22, 23],
                    "wepp_id": [1, 2],
                    "slope_scalar": [1.1, 2.2],
                }
            ),
            selected_columns=("topaz_id", "wepp_id", "slope_scalar"),
            unit_mapping={
                "topaz_id": "non-unitized",
                "wepp_id": "non-unitized",
                "slope_scalar": "non-unitized",
            },
            warnings=(),
            catalog_layer_raw={
                "join": {"primary_key": "topaz_id"},
                "geometry": {"feature_id_keys": ["topaz_id", "wepp_id"]},
            },
        ),
        service._LayerCoreResult(
            layer=wepp_layer,
            frame=pd.DataFrame(
                {
                    service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2"],
                    "wepp_id": [1, 2],
                    "runoff": [100.0, 200.0],
                }
            ),
            selected_columns=("wepp_id", "runoff"),
            unit_mapping={
                "wepp_id": "non-unitized",
                "runoff": "non-unitized",
            },
            warnings=(),
            catalog_layer_raw={
                "join": {"primary_key": "wepp_id"},
                "geometry": {"feature_id_keys": ["topaz_id", "wepp_id"]},
            },
        ),
    )

    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "topaz_id": [22, 23],
            "wepp_id": [1, 2],
        }
    ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)

    payload, _ = service._build_key_first_materialized_layer_payload(
        wd=tmp_path,
        layer=layer,
        source_layers=(watershed_layer, wepp_layer),
        source_results=source_results,
        entries_by_output_layer_id={},
        use_tabular_payload=True,
        use_tabular_long_layout=False,
        tabular_event_selector=None,
        watershed_identity_lookup_cache={},
        units_mode="si",
    )

    assert payload.tabular_frame is not None
    result = payload.tabular_frame.sort_values("topaz_id").reset_index(drop=True)
    assert result[["topaz_id", "wepp_id"]].values.tolist() == [[22, 1], [23, 2]]
    assert result["slope_scalar"].tolist() == [1.1, 2.2]
    assert result["runoff"].tolist() == [100.0, 200.0]


def test_materialize_export_payloads_translates_carrier_materialization_contract_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp.summary.hillslopes",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.hillslopes",
        carrier_layer="sbs_map-subcatchments",
    )
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=(layer.layer_id,),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(layer,),
        warnings=(),
    )
    submission = service.FeaturesExportSubmission(
        catalog=SimpleNamespace(get_layer=lambda layer_id: SimpleNamespace(raw={"join": {"primary_key": "topaz_id"}})),
        plan=plan,
        dependency_snapshot=DependencySnapshot(
            catalog_signature="catalog-signature",
            entries=(),
            fingerprint="dependency-fingerprint",
        ),
        cache_key_parts=CacheKeyParts(
            request_hash="request-hash",
            dependency_fingerprint="dependency-fingerprint",
            cache_key="request-hash+dependency-fingerprint",
        ),
        unitizer_preferences_fingerprint=None,
    )

    monkeypatch.setattr(
        service,
        "_build_materialized_execution_plan",
        lambda plan, runid: (plan, {layer.output_layer_id: [layer]}),
    )

    def _raise_materialization_contract_error(**kwargs):  # noqa: ARG001
        raise MaterializationContractError("carrier failure", details="carrier_fail_reason")

    monkeypatch.setattr(service, "materialize_carrier_layer_core", _raise_materialization_contract_error)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._materialize_export_payloads(submission, wd=tmp_path, runid="clogging-starch")

    assert exc_info.value.code == "materialization_error"
    assert "carrier_fail_reason" in exc_info.value.details


def test_resolve_selected_columns_prefers_discovered_units_when_catalog_columns_absent() -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp.summary.hillslopes",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.hillslopes",
    )
    frame = gpd.GeoDataFrame(
        {"Runoff Volume": [1.0], "TopazID": [101], "geometry": [Point(0, 0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    request = NormalizedExportRequest(
        format="geopackage",
        units="project",
        layers=("wepp.summary.hillslopes",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(layer,),
        warnings=(),
    )
    selected_columns, unit_mapping = service._resolve_selected_columns(
        layer=layer,
        frame=frame,
        catalog_layer_raw={"join": {"primary_key": "TopazID"}},
        request_plan=plan,
        discovered_units={"Runoff Volume": "m^3"},
    )
    assert "Runoff Volume" in selected_columns
    assert unit_mapping["Runoff Volume"] == "m^3"


def test_resolve_selected_columns_event_mode_forces_date_identity_column() -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp.temporal.events",
        family="wepp_temporal",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.temporal.events",
        temporal_mode="event",
    )
    frame = gpd.GeoDataFrame(
        {
            "topaz_id": [93],
            "date": ["2005-01-15"],
            "hill_sediment_tonnes": [0.0],
            "geometry": [Point(0.0, 0.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )
    request = NormalizedExportRequest(
        format="geopackage",
        units="project",
        layers=("wepp.temporal.events",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
        temporal=NormalizedTemporalRequest(
            mode="event",
            event=NormalizedTemporalEvent(
                selector="date",
                dates=("2005-01-15",),
            ),
        ),
        column_selection=(
            LayerColumnSelection(
                layer_id="wepp.temporal.events",
                include=("hill_sediment_tonnes", "topaz_id"),
            ),
        ),
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(layer,),
        warnings=(),
    )

    selected_columns, _unit_mapping = service._resolve_selected_columns(
        layer=layer,
        frame=frame,
        catalog_layer_raw={"join": {"primary_key": "topaz_id"}},
        request_plan=plan,
        discovered_units=None,
    )

    assert "date" in selected_columns
