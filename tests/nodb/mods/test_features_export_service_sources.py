from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.dependency_tracker import DependencyEntry
from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame, discover_layer_sources
from wepppy.nodb.mods.features_export.duckdb_materializer import materialize_layer_attributes
from wepppy.nodb.mods.features_export.join_planner import MaterializationContractError

pytestmark = pytest.mark.unit


def test_build_layer_frame_from_sources_required_source_missing_raises_materialization_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
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
    dependency_entries = (
        DependencyEntry(
            relpath="geometry/subcatchments.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="geometry",
            dependency_id="geometry",
        ),
    )
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_load_vector_dataframe", lambda wd, relpath: geometry_frame)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._build_layer_frame_from_sources(
            wd=tmp_path,
            layer=layer,
            catalog_layer_raw={
                "join": {"primary_key": "TopazID"},
                "sources": [{"source_id": "required_metrics", "kind": "parquet", "required": True}],
            },
            request_plan=plan,
            dependency_entries=dependency_entries,
            units_mode="si",
        )

    assert exc_info.value.code == "materialization_error"
    assert "dependency_missing" in exc_info.value.details


def test_build_layer_frame_from_sources_required_source_missing_file_raises_materialization_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
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
    dependency_entries = (
        DependencyEntry(
            relpath="geometry/subcatchments.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="geometry",
            dependency_id="geometry",
        ),
        DependencyEntry(
            relpath="missing/required.parquet",
            exists=False,
            size=None,
            mtime_ns=None,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="source",
            dependency_id="required_metrics",
        ),
    )
    required_source_path = tmp_path / "sources" / "required.geojson"
    required_source_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_load_vector_dataframe", lambda wd, relpath: geometry_frame)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._build_layer_frame_from_sources(
            wd=tmp_path,
            layer=layer,
            catalog_layer_raw={
                "join": {"primary_key": "TopazID"},
                "sources": [{"source_id": "required_metrics", "kind": "parquet", "required": True}],
            },
            request_plan=plan,
            dependency_entries=dependency_entries,
            units_mode="si",
        )

    assert exc_info.value.code == "materialization_error"
    assert "file_missing" in exc_info.value.details


def test_build_layer_frame_from_sources_required_source_unsupported_kind_raises_materialization_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
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
    source_relpath = "sources/required.data"
    source_path = tmp_path / source_relpath
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("placeholder", encoding="utf-8")
    dependency_entries = (
        DependencyEntry(
            relpath="geometry/subcatchments.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="geometry",
            dependency_id="geometry",
        ),
        DependencyEntry(
            relpath=source_relpath,
            exists=True,
            size=source_path.stat().st_size,
            mtime_ns=source_path.stat().st_mtime_ns,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="source",
            dependency_id="required_metrics",
        ),
    )
    required_source_path = tmp_path / "sources" / "required.geojson"
    required_source_path.parent.mkdir(parents=True, exist_ok=True)
    required_source_path.write_text("{}", encoding="utf-8")
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_load_vector_dataframe", lambda wd, relpath: geometry_frame)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._build_layer_frame_from_sources(
            wd=tmp_path,
            layer=layer,
            catalog_layer_raw={
                "join": {"primary_key": "TopazID"},
                "sources": [{"source_id": "required_metrics", "kind": "unsupported", "required": True}],
            },
            request_plan=plan,
            dependency_entries=dependency_entries,
            units_mode="si",
        )

    assert exc_info.value.code == "materialization_error"
    assert "unsupported_source_kind" in exc_info.value.details


def test_build_layer_frame_from_sources_required_source_join_unresolved_raises_materialization_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
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
    dependency_entries = (
        DependencyEntry(
            relpath="geometry/subcatchments.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="geometry",
            dependency_id="geometry",
        ),
        DependencyEntry(
            relpath="sources/required.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="source",
            dependency_id="required_metrics",
        ),
    )
    required_source_path = tmp_path / "sources" / "required.geojson"
    required_source_path.parent.mkdir(parents=True, exist_ok=True)
    required_source_path.write_text("{}", encoding="utf-8")
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_frame = gpd.GeoDataFrame(
        {"ForeignID": [1], "metric": [5.0], "geometry": [Point(1.0, 1.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_frame.to_file(required_source_path, driver="GeoJSON")
    monkeypatch.setattr(service, "_load_vector_dataframe", lambda wd, relpath: geometry_frame)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._build_layer_frame_from_sources(
            wd=tmp_path,
            layer=layer,
            catalog_layer_raw={
                "join": {"primary_key": "TopazID"},
                "sources": [{"source_id": "required_metrics", "kind": "vector", "required": True}],
            },
            request_plan=plan,
            dependency_entries=dependency_entries,
            units_mode="si",
        )

    assert exc_info.value.code == "materialization_error"
    assert "required_source_join_unresolved" in exc_info.value.details


def test_build_layer_frame_from_sources_appends_unit_suffixes_for_unitized_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layer = ResolvedLayerPlan(
        layer_id="wepp.summary.hillslopes",
        family="wepp_summary",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.hillslopes",
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
    dependency_entries = (
        DependencyEntry(
            relpath="geometry/subcatchments.geojson",
            exists=True,
            size=1,
            mtime_ns=1,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            dependency_role="geometry",
            dependency_id="geometry",
        ),
    )
    geometry_frame = gpd.GeoDataFrame(
        {"topaz_id": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    merged_frame = gpd.GeoDataFrame(
        {
            "topaz_id": [1],
            "hillslope_area": [2.5],
            "runoff_volume": [4.2],
            "geometry": [Point(0.0, 0.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_load_vector_dataframe", lambda wd, relpath: geometry_frame)
    monkeypatch.setattr(
        service,
        "build_legacy_merged_frame",
        lambda **kwargs: SimpleNamespace(
            frame=merged_frame,
            discovered_units={
                "hillslope_area": "ha",
                "runoff_volume": "m^3",
            },
            warnings=(),
        ),
    )

    result = service._build_layer_frame_from_sources(
        wd=tmp_path,
        layer=layer,
        catalog_layer_raw={
            "join": {"primary_key": "topaz_id"},
            "sources": [],
        },
        request_plan=plan,
        dependency_entries=dependency_entries,
        units_mode="si",
    )

    assert result.selected_columns == ("topaz_id", "wepp_id", "hillslope_area_ha", "runoff_volume_m3")
    assert result.frame["wepp_id"].isna().all()
    assert "hillslope_area_ha" in result.frame.columns
    assert "runoff_volume_m3" in result.frame.columns
    assert result.unit_mapping == {
        "topaz_id": "non-unitized",
        "wepp_id": "non-unitized",
        "hillslope_area_ha": "ha",
        "runoff_volume_m3": "m^3",
    }


def test_discover_layer_sources_required_missing_dependency_raises_materialization_contract_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(MaterializationContractError) as exc_info:
        discover_layer_sources(
            wd=tmp_path,
            layer_id="wepp.summary.hillslopes",
            scope="baseline",
            catalog_layer_raw={
                "sources": [{"source_id": "required_metrics", "kind": "parquet", "required": True}],
            },
            dependency_entries=(),
        )

    assert "dependency_missing" in exc_info.value.details


def test_discover_layer_sources_required_missing_file_raises_materialization_contract_error(
    tmp_path: Path,
) -> None:
    dependency_entries = (
        DependencyEntry(
            relpath="missing/required.parquet",
            exists=False,
            size=None,
            mtime_ns=None,
            layer_id="wepp.summary.hillslopes",
            output_layer_id="baseline__wepp.summary.hillslopes",
            dependency_role="source",
            dependency_id="required_metrics",
        ),
    )
    with pytest.raises(MaterializationContractError) as exc_info:
        discover_layer_sources(
            wd=tmp_path,
            layer_id="wepp.summary.hillslopes",
            scope="baseline",
            catalog_layer_raw={
                "sources": [{"source_id": "required_metrics", "kind": "parquet", "required": True}],
            },
            dependency_entries=dependency_entries,
        )

    assert "file_missing" in exc_info.value.details


def test_discover_layer_sources_required_unsupported_kind_raises_materialization_contract_error(
    tmp_path: Path,
) -> None:
    source_relpath = "sources/required.data"
    source_path = tmp_path / source_relpath
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("placeholder", encoding="utf-8")
    dependency_entries = (
        DependencyEntry(
            relpath=source_relpath,
            exists=True,
            size=source_path.stat().st_size,
            mtime_ns=source_path.stat().st_mtime_ns,
            layer_id="wepp.summary.hillslopes",
            output_layer_id="baseline__wepp.summary.hillslopes",
            dependency_role="source",
            dependency_id="required_metrics",
        ),
    )
    with pytest.raises(MaterializationContractError) as exc_info:
        discover_layer_sources(
            wd=tmp_path,
            layer_id="wepp.summary.hillslopes",
            scope="baseline",
            catalog_layer_raw={
                "sources": [{"source_id": "required_metrics", "kind": "unsupported", "required": True}],
            },
            dependency_entries=dependency_entries,
        )

    assert "unsupported_source_kind" in exc_info.value.details


def test_merge_source_dataframe_preserves_duplicate_columns_with_source_suffix() -> None:
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "area": [10.0], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_df = pd.DataFrame({"topaz_id": [1], "area": [20.0], "metric": [5.0]})

    merged, joined, source_column_map = service._merge_source_dataframe(
        geometry_frame=geometry_frame,
        source_df=source_df,
        source_id="landuse.table",
        join_contract={
            "primary_key": "topaz_id",
            "fallback_keys": ["TopazID"],
            "source_key_map": {"landuse.table": ["topaz_id"]},
        },
    )

    assert joined is True
    assert merged.loc[0, "area"] == pytest.approx(10.0)
    assert merged.loc[0, "area__landusetable"] == pytest.approx(20.0)
    assert merged.loc[0, "metric"] == pytest.approx(5.0)
    assert source_column_map["area"] == "area__landusetable"


def test_merge_source_dataframe_returns_false_when_join_key_is_missing() -> None:
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_df = pd.DataFrame({"channel_id": [1], "metric": [5.0]})

    merged, joined, source_column_map = service._merge_source_dataframe(
        geometry_frame=geometry_frame,
        source_df=source_df,
        source_id="missing.join",
        join_contract={
            "primary_key": "topaz_id",
            "fallback_keys": ["TopazID"],
            "source_key_map": {"missing.join": ["topaz_id"]},
        },
    )

    assert joined is False
    assert list(merged.columns) == list(geometry_frame.columns)
    assert source_column_map == {}


def test_merge_source_dataframe_supports_duplicate_right_keys_fanout() -> None:
    geometry_frame = gpd.GeoDataFrame(
        {"TopazID": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )
    source_df = pd.DataFrame(
        {"topaz_id": [1, 1], "metric": [5.0, 7.0]},
    )

    merged, joined, source_column_map = service._merge_source_dataframe(
        geometry_frame=geometry_frame,
        source_df=source_df,
        source_id="fanout.source",
        join_contract={
            "primary_key": "topaz_id",
            "fallback_keys": ["TopazID"],
            "source_key_map": {"fanout.source": ["topaz_id"]},
        },
    )

    assert joined is True
    assert len(merged.index) == 2
    assert sorted(merged["metric"].tolist()) == [5.0, 7.0]
    assert source_column_map["metric"] == "metric"


def test_materialize_layer_attributes_rejects_conflicting_duplicate_source_keys() -> None:
    with pytest.raises(MaterializationContractError, match="many-to-many"):
        materialize_layer_attributes(
            layer_id="wepp.summary.hillslopes",
            carrier_layer="sbs_map-subcatchments",
            join_contract={"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
            sources=(
                DiscoveredSourceFrame(
                    source_id="conflicting_source",
                    source_kind="parquet",
                    required=True,
                    dataframe=pd.DataFrame(
                        {
                            "topaz_id": [1, 1],
                            "runoff_mm": [5.0, 7.0],
                        }
                    ),
                    units_by_column={},
                ),
            ),
        )


def test_materialize_layer_attributes_collapses_benign_duplicate_source_keys() -> None:
    merged, _ = materialize_layer_attributes(
        layer_id="wepp.summary.hillslopes",
        carrier_layer="sbs_map-subcatchments",
        join_contract={"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
        sources=(
            DiscoveredSourceFrame(
                source_id="duplicate_source",
                source_kind="parquet",
                required=True,
                dataframe=pd.DataFrame(
                    {
                        "topaz_id": [1, 1],
                        "runoff_mm": [5.0, 5.0],
                    }
                ),
                units_by_column={"runoff_mm": "mm"},
            ),
        ),
    )

    assert len(merged.index) == 1
    assert merged.iloc[0]["runoff_mm"] == pytest.approx(5.0)


def test_wepp_summary_channels_catalog_joins_internal_sources_on_wepp_id() -> None:
    catalog = load_layer_catalog()
    catalog_layer = catalog.get_layer("wepp.summary.channels")
    assert catalog_layer is not None

    join_contract = dict(catalog_layer.raw["join"])
    assert join_contract["primary_key"] == "wepp_id"
    assert join_contract["source_key_map"]["wepp_channel_attributes"][0] == "wepp_id"

    merged, _ = materialize_layer_attributes(
        layer_id="wepp.summary.channels",
        carrier_layer="chan_map-channels",
        join_contract=join_contract,
        sources=(
            DiscoveredSourceFrame(
                source_id="wepp_loss_channel",
                source_kind="parquet",
                required=True,
                dataframe=pd.DataFrame(
                    {
                        "wepp_id": [1743, 1744],
                        "chn_enum": [1, 2],
                        "Soil Loss": [84.2, 12.5],
                    }
                ),
                units_by_column={"Soil Loss": "kg"},
            ),
            DiscoveredSourceFrame(
                source_id="wepp_channel_attributes",
                source_kind="parquet",
                required=False,
                dataframe=pd.DataFrame(
                    {
                        "topaz_id": [24, 34],
                        "wepp_id": [1743, 1744],
                        "order": [6, 1],
                    }
                ),
                units_by_column={},
            ),
        ),
    )

    assert merged[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == ["1743", "1744"]
    assert merged["topaz_id"].tolist() == [24, 34]
    assert merged["Soil Loss"].tolist() == pytest.approx([84.2, 12.5])


def test_ag_fields_subfield_metrics_do_not_collapse_shared_parent_identity() -> None:
    catalog = load_layer_catalog()
    catalog_layer = catalog.get_layer("ag_fields.metrics.subfields")
    assert catalog_layer is not None
    join_contract = dict(catalog_layer.raw["join"])

    geometry_identity = {
        "sub_field_id": [1, 2],
        "field_id": [7, 7],
        "wepp_id": [99, 99],
    }
    merged, _ = materialize_layer_attributes(
        layer_id="ag_fields.metrics.subfields",
        carrier_layer="ag_fields_subfields_geojson",
        join_contract=join_contract,
        sources=(
            DiscoveredSourceFrame(
                source_id="ag_fields_subfields_geojson",
                source_kind="vector",
                required=True,
                dataframe=pd.DataFrame(geometry_identity),
                units_by_column={},
            ),
            DiscoveredSourceFrame(
                source_id="ag_fields_hill_pass",
                source_kind="parquet",
                required=True,
                dataframe=pd.DataFrame(
                    {
                        "sub_field_id": [1, 1, 2, 2],
                        "field_id": [7, 7, 7, 7],
                        "year": [2023, 2024, 2023, 2024],
                        "runoff": [1.25, 2.5, 9.5, 10.5],
                    }
                ),
                units_by_column={"runoff": "m"},
            ),
        ),
        allow_non_unique_keys=True,
    )

    assert merged[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == [
        "1",
        "1",
        "2",
        "2",
    ]
    assert merged["runoff"].tolist() == [1.25, 2.5, 9.5, 10.5]
    assert merged["field_id"].tolist() == [7, 7, 7, 7]
