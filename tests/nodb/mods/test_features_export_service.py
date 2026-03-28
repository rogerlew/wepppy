from __future__ import annotations

from pathlib import Path
import sqlite3
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame
from wepppy.nodb.mods.features_export.dependency_tracker import DependencyEntry, DependencySnapshot
from wepppy.nodb.mods.features_export.duckdb_materializer import materialize_layer_attributes
from wepppy.nodb.mods.features_export.exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
    PreparedLayerPayload,
)
from wepppy.nodb.mods.features_export.join_planner import MaterializationContractError

pytestmark = pytest.mark.unit


class _DummyWriter:
    def __init__(self, wd: Path) -> None:
        self._wd = wd

    def write(self, request) -> ExportArtifactMetadata:
        artifact_path = request.artifact_dir / "features_export.gpkg"
        with sqlite3.connect(artifact_path) as conn:
            conn.execute("PRAGMA application_id=0x47504B47")
            conn.execute(
                """
                CREATE TABLE gpkg_contents (
                    table_name TEXT NOT NULL PRIMARY KEY,
                    data_type TEXT NOT NULL
                )
                """
            )
            conn.commit()
        artifact_relpath = artifact_path.relative_to(self._wd).as_posix()

        layer_output = ExportedLayerArtifact(
            layer_id="watershed.subcatchments",
            output_layer_id="shared__watershed.subcatchments",
            scope="shared",
            scope_class="scope_invariant",
            format="geopackage",
            relpath=artifact_relpath,
            row_count=1,
            feature_count=1,
        )
        return ExportArtifactMetadata(
            format="geopackage",
            artifact_relpath=artifact_relpath,
            artifact_path=str(artifact_path),
            layer_outputs=(layer_output,),
            warnings=(),
            packaged_member_relpaths=(),
        )


def _build_submission(cache_key: str) -> service.FeaturesExportSubmission:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
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
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    dependency_snapshot = DependencySnapshot(
        catalog_signature="catalog-signature",
        entries=(),
        fingerprint="dependency-fingerprint",
    )
    cache_key_parts = CacheKeyParts(
        request_hash="request-hash",
        dependency_fingerprint=dependency_snapshot.fingerprint,
        cache_key=cache_key,
    )
    return service.FeaturesExportSubmission(
        catalog=SimpleNamespace(),
        plan=plan,
        dependency_snapshot=dependency_snapshot,
        cache_key_parts=cache_key_parts,
        unitizer_preferences_fingerprint=None,
    )


def _stub_materialize_export_payloads(submission, *, wd, runid):  # noqa: ARG001
    payload = PreparedLayerPayload(
        output_layer_id="shared__watershed.subcatchments",
        payload="{}",
        row_count=1,
        feature_count=1,
    )
    return submission.plan, {"shared__watershed.subcatchments": payload}, {}


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


def test_dedupe_identity_selected_columns_drops_suffixed_join_key_duplicates() -> None:
    columns = [
        "TopazID",
        "TopazID__soilsdominant",
        "TopazID__watershedsubcatchments",
        "runoff_mm",
        "wepp_id",
        "wepp_id__landusedominant",
        "sediment_yield_kg_ha",
    ]
    assert service._dedupe_identity_selected_columns(columns) == [
        "TopazID",
        "runoff_mm",
        "wepp_id",
        "sediment_yield_kg_ha",
    ]


def test_execute_features_export_cache_miss_result_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    assert result["cache_hit"] is False
    assert result["source_job_id"] is None
    assert isinstance(result["artifact_id"], str) and result["artifact_id"]
    assert (
        result["download_url"]
        == f"/weppcloud/runs/run-1/cfg/download/export/features/artifacts/{result['artifact_id']}/features_export.gpkg"
    )
    assert result["manifest_relpath"] == "export/features/jobs/job-source/manifest.json"
    assert isinstance(result["warnings"], list)
    assert (tmp_path / str(result["artifact_relpath"])).is_file()
    assert (tmp_path / result["manifest_relpath"]).is_file()

    cache_entry = service.get_cache_index_entry(tmp_path, submission.cache_key_parts.cache_key)
    assert cache_entry is not None
    assert cache_entry["source_job_id"] == "job-source"


def test_execute_features_export_cache_hit_returns_new_job_id_and_source_job_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    miss_result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    class _UnexpectedWriter:
        def write(self, request):
            raise AssertionError("cache-hit path should not call writer.write")

    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _UnexpectedWriter())

    hit_result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-cache",
    )

    assert hit_result["cache_hit"] is True
    assert hit_result["source_job_id"] == "job-source"
    assert hit_result["artifact_id"] == miss_result["artifact_id"]
    assert (
        hit_result["download_url"]
        == f"/weppcloud/runs/run-1/cfg/download/{miss_result['artifact_relpath']}"
    )
    assert hit_result["manifest_relpath"] == "export/features/jobs/job-cache/manifest.json"

    manifest = service.load_job_manifest(tmp_path, "job-cache")
    assert manifest is not None
    assert manifest["cache_hit"] is True
    assert manifest["source_job_id"] == "job-source"


def test_prepare_export_submission_passes_nodb_ref_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
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
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    fake_catalog = SimpleNamespace()
    captured: dict[str, object] = {}

    monkeypatch.setattr(service, "load_layer_catalog", lambda: fake_catalog)
    monkeypatch.setattr(service, "resolve_export_plan", lambda payload, catalog: plan)
    monkeypatch.setattr(service, "_resolve_plan_swat_run_id", lambda resolved_plan, wd_path: resolved_plan)

    def _fake_build_dependency_snapshot(plan_arg, catalog_arg, wd_path_arg, **kwargs):
        captured["plan"] = plan_arg
        captured["catalog"] = catalog_arg
        captured["wd_path"] = wd_path_arg
        captured["resolver"] = kwargs.get("nodb_ref_resolver")
        return DependencySnapshot(
            catalog_signature="catalog-signature",
            entries=(),
            fingerprint="dependency-fingerprint",
        )

    monkeypatch.setattr(service, "build_dependency_snapshot", _fake_build_dependency_snapshot)
    monkeypatch.setattr(
        service,
        "build_cache_key",
        lambda *args, **kwargs: CacheKeyParts(
            request_hash="request-hash",
            dependency_fingerprint="dependency-fingerprint",
            cache_key="request-hash+dependency-fingerprint",
        ),
    )
    monkeypatch.setattr(
        service,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda wd: SimpleNamespace(subwta_shp="watershed/subwta.shp"),
        ),
    )

    submission = service.prepare_export_submission(tmp_path, {"format": "geopackage"})

    assert submission.plan is plan
    assert captured["plan"] is plan
    assert captured["catalog"] is fake_catalog
    resolver = captured["resolver"]
    assert callable(resolver)
    assert resolver(str(tmp_path), "watershed", "subwta_shp") == "watershed/subwta.shp"


def test_nodb_ref_resolver_rejects_unsupported_controller(tmp_path: Path) -> None:
    with pytest.raises(service.FeaturesExportServiceError, match="Unsupported nodb_ref controller"):
        service._resolve_nodb_ref_relpath(str(tmp_path), "landuse", "landuse_shp")


def test_execute_features_export_invalid_cached_geopackage_forces_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    stale_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-stale" / "features_export.gpkg"
    )
    stale_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    stale_artifact_path.write_text('{"format":"geopackage","placeholder":true}', encoding="utf-8")

    stale_cache_entry = {
        "artifact_id": "artifact-stale",
        "artifact_relpath": stale_artifact_path.relative_to(tmp_path).as_posix(),
        "artifact_format": "geopackage",
        "layer_outputs": [],
        "packaged_member_relpaths": [],
        "source_job_id": "job-stale",
        "manifest_relpath": "export/features/jobs/job-stale/manifest.json",
        "warnings": [],
    }
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: stale_cache_entry)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-new",
    )

    assert result["cache_hit"] is False
    assert result["artifact_id"] != "artifact-stale"


def test_execute_features_export_cached_sqlite_without_gpkg_markers_forces_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    stale_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-stale-sqlite" / "features_export.gpkg"
    )
    stale_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(stale_artifact_path) as conn:
        conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY)")
        conn.commit()

    stale_cache_entry = {
        "artifact_id": "artifact-stale-sqlite",
        "artifact_relpath": stale_artifact_path.relative_to(tmp_path).as_posix(),
        "artifact_format": "geopackage",
        "layer_outputs": [],
        "packaged_member_relpaths": [],
        "source_job_id": "job-stale-sqlite",
        "manifest_relpath": "export/features/jobs/job-stale-sqlite/manifest.json",
        "warnings": [],
    }
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: stale_cache_entry)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-new-sqlite",
    )

    assert result["cache_hit"] is False
    assert result["artifact_id"] != "artifact-stale-sqlite"


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


def test_execute_features_export_writes_spatial_geopackage_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geometry_path = tmp_path / "dem" / "wbt" / "subcatchments.WGS.geojson"
    geometry_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_path.write_text(
        (
            '{"type":"FeatureCollection","features":['
            '{"type":"Feature","properties":{"TopazID":1,"Name":"A"},'
            '"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}},'
            '{"type":"Feature","properties":{"TopazID":2,"Name":"B"},'
            '"geometry":{"type":"Polygon","coordinates":[[[1,1],[2,1],[2,2],[1,2],[1,1]]]}}]}'
        ),
        encoding="utf-8",
    )

    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
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
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    dependency_snapshot = DependencySnapshot(
        catalog_signature="catalog-signature",
        entries=(
            DependencyEntry(
                relpath="dem/wbt/subcatchments.WGS.geojson",
                exists=True,
                size=geometry_path.stat().st_size,
                mtime_ns=geometry_path.stat().st_mtime_ns,
                layer_id="watershed.subcatchments",
                output_layer_id="shared__watershed.subcatchments",
                dependency_role="geometry",
                dependency_id="geometry",
            ),
            DependencyEntry(
                relpath="dem/wbt/subcatchments.WGS.geojson",
                exists=True,
                size=geometry_path.stat().st_size,
                mtime_ns=geometry_path.stat().st_mtime_ns,
                layer_id="watershed.subcatchments",
                output_layer_id="shared__watershed.subcatchments",
                dependency_role="source",
                dependency_id="watershed_subcatchments_geojson",
            ),
        ),
        fingerprint="dependency-fingerprint",
    )
    cache_key_parts = CacheKeyParts(
        request_hash="request-hash",
        dependency_fingerprint=dependency_snapshot.fingerprint,
        cache_key="request-hash+dependency-fingerprint",
    )
    submission = service.FeaturesExportSubmission(
        catalog=load_layer_catalog(),
        plan=plan,
        dependency_snapshot=dependency_snapshot,
        cache_key_parts=cache_key_parts,
        unitizer_preferences_fingerprint=None,
    )

    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-spatial",
    )

    artifact_path = tmp_path / str(result["artifact_relpath"])
    assert artifact_path.is_file()

    with sqlite3.connect(artifact_path) as conn:
        content_row = conn.execute(
            "SELECT table_name, data_type FROM gpkg_contents WHERE identifier = ?",
            ("shared__watershed.subcatchments",),
        ).fetchone()

        assert content_row is not None
        table_name, data_type = content_row
        assert data_type == "features"

        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        geom_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE geom IS NOT NULL'
        ).fetchone()[0]

    assert row_count == 2
    assert geom_count == 2
