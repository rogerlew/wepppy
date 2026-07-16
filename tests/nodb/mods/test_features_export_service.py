from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import zipfile

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.contracts import (
    LayerColumnSelection,
    NormalizedExportRequest,
    NormalizedTemporalEvent,
    NormalizedTemporalRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame, discover_layer_sources
from wepppy.nodb.mods.features_export.dependency_tracker import DependencyEntry, DependencySnapshot
from wepppy.nodb.mods.features_export.duckdb_materializer import materialize_layer_attributes
from wepppy.nodb.mods.features_export.exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
    PreparedLayerPayload,
)
from wepppy.nodb.mods.features_export.join_planner import (
    MaterializationContractError,
    resolve_geometry_key,
)
from wepppy.nodb.mods.features_export.readme_builder import build_export_readme
from wepppy.nodb.mods.features_export.output_column_naming import (
    apply_unitized_column_suffixes,
)
from wepppy.nodb.mods.features_export.temporal_wide_materializer import (
    materialize_temporal_layer_wide,
)
from wepppy.nodb.mods.features_export.tabular_temporal_layout import (
    reshape_temporal_wide_to_long,
)

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


class _DummyZipWriter:
    def __init__(self, wd: Path) -> None:
        self._wd = wd

    def write(self, request) -> ExportArtifactMetadata:
        artifact_path = request.artifact_dir / "features_export.parquet.zip"
        member_path = request.artifact_dir / "hillslopes.parquet"
        member_path.write_bytes(b"dummy parquet bytes")

        with zipfile.ZipFile(artifact_path, "w") as zip_handle:
            zip_handle.writestr("hillslopes.parquet", member_path.read_bytes())

        layer_output = ExportedLayerArtifact(
            layer_id="watershed.subcatchments",
            output_layer_id="shared__watershed.subcatchments",
            scope="shared",
            scope_class="scope_invariant",
            format="parquet",
            relpath="hillslopes.parquet",
            row_count=1,
            feature_count=1,
        )
        return ExportArtifactMetadata(
            format="parquet",
            artifact_relpath=artifact_path.relative_to(self._wd).as_posix(),
            artifact_path=str(artifact_path),
            layer_outputs=(layer_output,),
            warnings=(),
            packaged_member_relpaths=("hillslopes.parquet",),
        )


def _write_valid_geopackage_zip(artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    gpkg_member_path = artifact_path.parent / "features_export.gpkg"
    with sqlite3.connect(gpkg_member_path) as conn:
        conn.execute("PRAGMA application_id=0x47504B47")
        conn.commit()

    with zipfile.ZipFile(artifact_path, "w") as zip_handle:
        zip_handle.write(gpkg_member_path, arcname="features_export.gpkg")


def _build_submission(cache_key: str, *, format_token: str = "geopackage") -> service.FeaturesExportSubmission:
    request = NormalizedExportRequest(
        format=format_token,
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


def _ag_fields_metric_plan() -> ResolvedExportPlan:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("ag_fields.metrics.subfields",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    return ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="ag_fields.metrics.subfields",
                family="ag_fields_metrics",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__ag_fields.metrics.subfields",
            ),
        ),
        warnings=(),
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


def test_ensure_join_key_column_requires_contract_defined_identity_key() -> None:
    frame = gpd.GeoDataFrame(
        {"legacy_id": [7], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._ensure_join_key_column(
            frame,
            join_contract={"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
            catalog_layer_raw={"geometry": {"feature_id_keys": ["wepp_id"]}},
        )

    assert exc_info.value.code == "materialization_error"
    assert "identity_candidates" in exc_info.value.details


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


def test_ensure_join_key_column_uses_fallback_candidate_when_primary_is_missing() -> None:
    frame = gpd.GeoDataFrame(
        {"WeppID": [2], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
        crs="EPSG:4326",
    )

    resolved = service._ensure_join_key_column(
        frame,
        join_contract={"primary_key": "TopazID", "fallback_keys": ["WeppID"]},
        catalog_layer_raw={"geometry": {"feature_id_keys": ["TopazID"]}},
    )

    assert service._CONSOLIDATED_JOIN_KEY_COLUMN in resolved.columns
    assert resolved.loc[0, service._CONSOLIDATED_JOIN_KEY_COLUMN] == "2"


def test_project_spatial_frame_for_request_wgs_requires_source_crs() -> None:
    frame = gpd.GeoDataFrame(
        {"topaz_id": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._project_spatial_frame_for_request(frame, requested_crs="wgs")

    assert exc_info.value.code == "materialization_error"
    assert "missing CRS metadata for WGS84 export" in exc_info.value.details


def test_project_spatial_frame_for_request_utm_requires_source_crs() -> None:
    frame = gpd.GeoDataFrame(
        {"topaz_id": [1], "geometry": [Point(0.0, 0.0)]},
        geometry="geometry",
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service._project_spatial_frame_for_request(frame, requested_crs="utm")

    assert exc_info.value.code == "materialization_error"
    assert "missing CRS metadata for UTM export" in exc_info.value.details


def test_layer_outputs_from_cache_entry_skips_malformed_entries_and_falls_back_to_plan() -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(layer,),
        warnings=(),
    )

    outputs = service._layer_outputs_from_cache_entry(
        {
            "layer_outputs": [
                {"layer_id": "", "output_layer_id": "missing-layer-id"},
                {"layer_id": "missing-output-id", "output_layer_id": ""},
                {"scope": "shared"},
                123,
            ]
        },
        plan,
        "export/features/artifacts/cache/features_export.gpkg",
        "geopackage",
    )

    assert len(outputs) == 1
    assert outputs[0].layer_id == "watershed.subcatchments"
    assert outputs[0].output_layer_id == "shared__watershed.subcatchments"
    assert outputs[0].row_count is None
    assert outputs[0].feature_count is None


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


def test_resolve_geometry_key_prefers_layer_candidates_before_carrier_defaults() -> None:
    resolved = resolve_geometry_key(
        geometry_columns=("TopazID", "WeppID"),
        carrier_layer="sbs_map-subcatchments",
        candidate_tokens=("wepp_id",),
    )

    assert resolved == "WeppID"


def test_backfill_identity_from_geometry_key_fills_missing_event_identity_values() -> None:
    frame = gpd.GeoDataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["93", "22", "23"],
            "TopazID": [93, 22, 23],
            "topaz_id": [93.0, float("nan"), float("nan")],
            "hill_sediment_tonnes": [0.0, None, None],
            "geometry": [Point(0.0, 0.0), Point(1.0, 1.0), Point(2.0, 2.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    result = service._backfill_identity_from_geometry_key(
        frame,
        geometry_key_column="TopazID",
        consolidated_join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
    )

    assert result["topaz_id"].tolist() == [93.0, 22.0, 23.0]


def test_align_carrier_identity_join_key_prefers_topaz_join_for_subcatchments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        service,
        "_backfill_tabular_identity_from_watershed",
        lambda **kwargs: kwargs["frame"],  # noqa: ARG005
    )

    existing_join_frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2", "3"],
            "wepp_id": [1, 2, 3],
            "topaz_id": [101, 101, 102],
        }
    )
    existing_join_result = service._align_carrier_identity_join_key(
        frame=existing_join_frame,
        wd=tmp_path,
        carrier_layer="sbs_map-subcatchments",
        cache={},
    )
    assert existing_join_result[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == ["1", "2", "3"]

    # Retarget onto topaz_id when wepp/topaz are one-to-one and topaz values are
    # available; geometry carriers for subcatchments resolve canonical geometry
    # on TopazID-compatible keys.
    one_to_one_identity_frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2", "3"],
            "wepp_id": [1, 2, 3],
            "topaz_id": [101, 102, 103],
        }
    )
    one_to_one_identity_result = service._align_carrier_identity_join_key(
        frame=one_to_one_identity_frame,
        wd=tmp_path,
        carrier_layer="sbs_map-subcatchments",
        cache={},
    )
    assert one_to_one_identity_result[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == [
        "101",
        "102",
        "103",
    ]

    # Production regression guard: if the incoming join key is already in the
    # TopazID domain while wepp_id differs one-to-one, preserve TopazID domain.
    topaz_domain_frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["71", "72", "82"],
            "wepp_id": [13, 14, 17],
            "topaz_id": [71, 72, 82],
        }
    )
    topaz_domain_result = service._align_carrier_identity_join_key(
        frame=topaz_domain_frame,
        wd=tmp_path,
        carrier_layer="sbs_map-subcatchments",
        cache={},
    )
    assert topaz_domain_result[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == ["71", "72", "82"]

    missing_join_frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: [None, None, "3"],
            "wepp_id": [1, 2, 3],
            "topaz_id": [101, 101, 102],
        }
    )
    missing_join_result = service._align_carrier_identity_join_key(
        frame=missing_join_frame,
        wd=tmp_path,
        carrier_layer="sbs_map-subcatchments",
        cache={},
    )
    assert missing_join_result[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == ["1", "2", "3"]


def test_align_carrier_identity_join_key_retargets_to_backfilled_topaz_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_backfill(**kwargs):
        frame = kwargs["frame"].copy()
        frame["topaz_id"] = [71, 72, 82]
        return frame

    monkeypatch.setattr(service, "_backfill_tabular_identity_from_watershed", _fake_backfill)

    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["13", "14", "17"],
            "wepp_id": [13, 14, 17],
        }
    )
    result = service._align_carrier_identity_join_key(
        frame=frame,
        wd=tmp_path,
        carrier_layer="sbs_map-subcatchments",
        cache={},
    )
    assert result[service._CONSOLIDATED_JOIN_KEY_COLUMN].tolist() == ["71", "72", "82"]


def test_apply_unitized_column_suffixes_appends_canonical_unit_token() -> None:
    frame = gpd.GeoDataFrame(
        {
            "topaz_id": [101],
            "hillslope_area": [12.5],
            "runoff_volume": [8.1],
            "geometry": [Point(0.0, 0.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    renamed_frame, selected_columns, unit_mapping = apply_unitized_column_suffixes(
        frame=frame,
        selected_columns=("topaz_id", "hillslope_area", "runoff_volume"),
        unit_mapping={
            "topaz_id": "non-unitized",
            "hillslope_area": "ha",
            "runoff_volume": "m^3",
        },
        geometry_name="geometry",
        consolidated_join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
    )

    assert selected_columns == ("topaz_id", "hillslope_area_ha", "runoff_volume_m3")
    assert "hillslope_area_ha" in renamed_frame.columns
    assert "runoff_volume_m3" in renamed_frame.columns
    assert "hillslope_area" not in renamed_frame.columns
    assert "runoff_volume" not in renamed_frame.columns
    assert unit_mapping == {
        "topaz_id": "non-unitized",
        "hillslope_area_ha": "ha",
        "runoff_volume_m3": "m^3",
    }


def test_apply_unitized_column_suffixes_avoids_double_append_and_dedupes_collisions() -> None:
    frame = gpd.GeoDataFrame(
        {
            "runoff": [8.1],
            "runoff_mm": [7.0],
            "sediment_yield_kg_ha": [0.4],
            "geometry": [Point(0.0, 0.0)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    renamed_frame, selected_columns, unit_mapping = apply_unitized_column_suffixes(
        frame=frame,
        selected_columns=("runoff", "runoff_mm", "sediment_yield_kg_ha"),
        unit_mapping={
            "runoff": "mm",
            "runoff_mm": "mm",
            "sediment_yield_kg_ha": "kg/ha",
        },
        geometry_name="geometry",
        consolidated_join_key_column=service._CONSOLIDATED_JOIN_KEY_COLUMN,
    )

    assert selected_columns == ("runoff_mm_2", "runoff_mm", "sediment_yield_kg_ha")
    assert "runoff_mm_2" in renamed_frame.columns
    assert "runoff_mm" in renamed_frame.columns
    assert "sediment_yield_kg_ha" in renamed_frame.columns
    assert unit_mapping == {
        "runoff_mm_2": "mm",
        "runoff_mm": "mm",
        "sediment_yield_kg_ha": "kg/ha",
    }


def test_apply_unit_conversions_uses_unitizer_metadata_and_converted_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = pd.DataFrame(
        {
            "topaz_id": [101, 102],
            "runoff_volume_m3": [1.0, 2.0],
        }
    )

    class _FakeUnitizer:
        def convert_table(self, table, column_units, *, units_mode="project", target_units=None):  # noqa: ARG002
            assert units_mode == "english"
            assert column_units == {
                "topaz_id": "non-unitized",
                "runoff_volume_m3": "m^3",
            }
            converted = table.copy()
            converted["runoff_volume_m3"] = converted["runoff_volume_m3"] * 35.3146667
            return SimpleNamespace(
                data=converted,
                metadata_by_column={
                    "topaz_id": SimpleNamespace(source_unit="non-unitized", target_unit="non-unitized"),
                    "runoff_volume_m3": SimpleNamespace(source_unit="m^3", target_unit="ft^3"),
                },
            )

    monkeypatch.setattr(service.Unitizer, "getInstance", lambda wd, **kwargs: _FakeUnitizer())

    converted_frame, converted_mapping = service._apply_unit_conversions(
        wd=tmp_path,
        frame=frame,
        selected_columns=("topaz_id", "runoff_volume_m3"),
        unit_mapping={
            "topaz_id": "non-unitized",
            "runoff_volume_m3": "m^3",
        },
        units_mode="english",
    )

    assert converted_frame["runoff_volume_m3"].tolist() == pytest.approx([35.3146667, 70.6293334])
    assert converted_mapping["runoff_volume_m3"] == "ft^3"
    assert converted_mapping["topaz_id"] == "non-unitized"


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


def test_execute_features_export_rejects_empty_job_id_before_export_dir_creation(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "export"
    assert not export_root.exists()

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.execute_features_export(
            tmp_path,
            runid="run-1",
            config="cfg",
            payload={"format": "geopackage"},
            job_id="",
        )

    assert exc.value.status_code == 500
    assert str(exc.value) == "job_id must be a non-empty string."
    assert not export_root.exists()


def test_execute_features_export_creates_export_root_before_cache_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: None)

    def _fake_cache_miss(
        wd: Path,
        *,
        runid: str,
        config: str,
        job_id: str,
        submission: service.FeaturesExportSubmission,
    ) -> dict[str, object]:
        assert (wd / "export").is_dir()
        assert runid == "run-1"
        assert config == "cfg"
        assert job_id == "job-source"
        assert submission.cache_key_parts.cache_key == "request-hash+dependency-fingerprint"
        return {"ok": True}

    monkeypatch.setattr(service, "_run_cache_miss_export", _fake_cache_miss)
    assert not (tmp_path / "export").exists()

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    assert result == {"ok": True}
    assert (tmp_path / "export").is_dir()


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
        == "/rq-engine/api/runs/run-1/cfg/export/features/job/job-source/download"
    )
    assert result["manifest_relpath"] == "export/features/jobs/job-source/manifest.json"
    assert isinstance(result["warnings"], list)
    assert (tmp_path / str(result["artifact_relpath"])).is_file()
    assert (tmp_path / result["manifest_relpath"]).is_file()
    assert str(result["artifact_relpath"]).endswith(".zip")

    artifact_zip_path = tmp_path / str(result["artifact_relpath"])
    with zipfile.ZipFile(artifact_zip_path, "r") as zip_handle:
        names = set(zip_handle.namelist())
        assert "manifest.json" in names
        assert "README.md" in names
        assert "features_export.gpkg" in names
        assert "profile.yml" not in names
        assert not any(name.endswith(".yml") for name in names)

        manifest = json.loads(zip_handle.read("manifest.json").decode("utf-8"))
        readme_text = zip_handle.read("README.md").decode("utf-8")

    assert manifest["artifact"]["packaged_member_relpaths"] == [
        "README.md",
        "features_export.gpkg",
        "manifest.json",
    ]
    assert manifest["artifact_id"] == result["artifact_id"]
    assert manifest["artifact"]["artifact_relpath"] == "features_export.geopackage.zip"
    assert "| Run ID | run-1 |" in readme_text
    assert "| Config | cfg |" in readme_text
    assert f"| Artifact ID | {result['artifact_id']} |" in readme_text
    assert "shared__watershed.subcatchments" in readme_text
    assert "features_export.gpkg" in readme_text
    assert "`manifest.json` is the canonical machine-readable provenance" in readme_text

    cache_entry = service.get_cache_index_entry(tmp_path, submission.cache_key_parts.cache_key)
    assert cache_entry is not None
    assert cache_entry["source_job_id"] == "job-source"


def test_execute_features_export_cache_miss_retains_final_zip_for_zip_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(
        cache_key="request-hash+dependency-fingerprint+parquet",
        format_token="parquet",
    )
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyZipWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "parquet"},
        job_id="job-source",
    )

    artifact_zip_path = tmp_path / str(result["artifact_relpath"])
    assert artifact_zip_path.is_file()
    with zipfile.ZipFile(artifact_zip_path, "r") as zip_handle:
        names = set(zip_handle.namelist())
        assert "hillslopes.parquet" in names
        assert "README.md" in names
        assert "manifest.json" in names
        assert "profile.yml" not in names
        assert not any(name.endswith(".yml") for name in names)
        manifest = json.loads(zip_handle.read("manifest.json").decode("utf-8"))
        readme_text = zip_handle.read("README.md").decode("utf-8")

    assert manifest["artifact"]["packaged_member_relpaths"] == [
        "README.md",
        "hillslopes.parquet",
        "manifest.json",
    ]
    assert "hillslopes.parquet" in readme_text

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
        == "/rq-engine/api/runs/run-1/cfg/export/features/job/job-cache/download"
    )
    assert hit_result["manifest_relpath"] == "export/features/jobs/job-cache/manifest.json"

    manifest = service.load_job_manifest(tmp_path, "job-cache")
    assert manifest is not None
    assert manifest["cache_hit"] is True
    assert manifest["source_job_id"] == "job-source"
    assert "README.md" in manifest["artifact"]["packaged_member_relpaths"]
    assert "manifest.json" in manifest["artifact"]["packaged_member_relpaths"]


def test_build_export_readme_is_deterministic_and_redacts_absolute_paths() -> None:
    manifest = {
        "artifact_id": "artifact-123",
        "cache_hit": False,
        "generated_at_utc": "2026-03-29T23:10:00Z",
        "source_job_id": None,
        "artifact": {
            "format": "geopackage",
            "artifact_relpath": "features_export.geopackage.zip",
            "packaged_member_relpaths": ["features_export.gpkg", "manifest.json", "README.md"],
        },
        "request": {
            "resolved": {
                "format": "geopackage",
                "units": "si",
                "crs": "wgs",
                "layers": ["watershed.subcatchments"],
                "output_scopes": ["baseline"],
            },
        },
        "crs": {
            "requested_crs": "wgs",
            "resolved_crs": "wgs",
            "resolved_epsg": 4326,
        },
        "layers": [
            {
                "layer_id": "watershed.subcatchments",
                "output_layer_id": "shared__watershed.subcatchments",
                "scope": "shared",
                "context": "base",
                "row_count": 1,
                "feature_count": 1,
                "artifact_relpath": "features_export.gpkg",
            }
        ],
        "columns": {
            "output_layer_metadata": {
                "shared__watershed.subcatchments": {
                    "source_layer_ids": ["watershed.subcatchments"],
                    "selected_columns": ["TopazID"],
                    "unit_mapping": {"TopazID": "non-unitized"},
                    "description_mapping": {"TopazID": "Unique hillslope identifier."},
                }
            }
        },
        "dependency_snapshot": {
            "catalog_signature": "catalog-signature",
            "fingerprint": "dependency-fingerprint",
            "entries": [
                {
                    "dependency_role": "source",
                    "dependency_id": "sbs",
                    "layer_id": "watershed.subcatchments",
                    "output_layer_id": "shared__watershed.subcatchments",
                    "relpath": "/wc1/runs/run-1/private/path.parquet",
                    "exists": True,
                    "size": 101,
                }
            ],
        },
        "warnings": [],
    }

    rendered_a = build_export_readme(manifest=manifest, runid="run-1", config="cfg")
    rendered_b = build_export_readme(manifest=manifest, runid="run-1", config="cfg")

    assert rendered_a == rendered_b
    assert "## Layer inventory" in rendered_a
    assert "| Column | Unit | Description |" in rendered_a
    assert "| TopazID | non-unitized | Unique hillslope identifier. |" in rendered_a
    assert "## Dependency lineage summary" in rendered_a
    assert "[redacted-absolute-path]" in rendered_a
    assert "/wc1/runs/run-1/private/path.parquet" not in rendered_a


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


def _write_shallow_ag_fields_bundle(wd: Path) -> tuple[Path, Path]:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path = wd / "ag_fields" / "sub_fields" / "fields.parquet"
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "field_id": pa.array([7], type=pa.int32()),
                "sub_field_id": pa.array([2], type=pa.int32()),
            }
        ),
        mapping_path,
    )
    interchange_dir = wd / "wepp" / "ag_fields" / "output" / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, dict[str, object]] = {}
    for family, contract in interchange._FAMILY_CONTRACTS.items():
        target_path = interchange_dir / contract[2]
        target_path.write_bytes(f"bundle-{family}".encode("ascii"))
        zero_row_source_count = 1 if family == "ebe" else 0
        identity_count = 1 - zero_row_source_count
        summaries[family] = {
            "rows": identity_count,
            "row_groups": identity_count,
            "size_bytes": target_path.stat().st_size,
            "identity_count": identity_count,
            "source_count": 1,
            "zero_row_source_count": zero_row_source_count,
            "zero_row_sub_field_ids": [2] if zero_row_source_count else [],
        }
    manifest_path = interchange_dir / "interchange_version.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_kind": interchange.DATASET_KIND,
                "ag_fields_schema_version": interchange.AG_FIELDS_SCHEMA_VERSION,
                "major": interchange.INTERCHANGE_VERSION.major,
                "source_mapping_sha256": hashlib.sha256(
                    mapping_path.read_bytes()
                ).hexdigest(),
                "files": summaries,
            }
        ),
        encoding="utf-8",
    )
    return mapping_path, manifest_path


def _files_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    "stale_reason",
    ("cleared_completion_marker", "mapping_hash_mismatch", "wrong_major"),
)
def test_prepare_export_submission_rejects_stale_ag_fields_interchange_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stale_reason: str,
) -> None:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path, manifest_path = _write_shallow_ag_fields_bundle(tmp_path)
    completion_marker_current = stale_reason != "cleared_completion_marker"
    if stale_reason == "mapping_hash_mismatch":
        pq.write_table(
            pa.table(
                {
                    "field_id": pa.array([8], type=pa.int32()),
                    "sub_field_id": pa.array([2], type=pa.int32()),
                }
            ),
            mapping_path,
        )
    elif stale_reason == "wrong_major":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["major"] = interchange.INTERCHANGE_VERSION.major + 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    controller = SimpleNamespace(
        has_current_wepp_ag_fields_interchange=lambda: (
            completion_marker_current
            and interchange._is_wepp_ag_fields_interchange_complete(
                tmp_path / "wepp" / "ag_fields" / "output",
                mapping_path,
            )
        )
    )
    monkeypatch.setattr(
        service.AgFields,
        "load_detached",
        classmethod(lambda _cls, _wd, allow_nonexistent=True: controller),
    )
    plan = _ag_fields_metric_plan()
    monkeypatch.setattr(service, "load_layer_catalog", lambda: SimpleNamespace())
    monkeypatch.setattr(service, "resolve_export_plan", lambda _payload, _catalog: plan)
    monkeypatch.setattr(service, "_resolve_plan_swat_run_id", lambda value, _wd: value)
    monkeypatch.setattr(
        service,
        "build_dependency_snapshot",
        lambda *_args, **_kwargs: pytest.fail(
            "stale AgFields readiness must fail before dependency planning"
        ),
    )
    before = _files_snapshot(tmp_path)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service.prepare_export_submission(tmp_path, {"format": "geopackage"})

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ag_fields_interchange_not_current"
    assert _files_snapshot(tmp_path) == before


def test_ag_fields_interchange_readiness_gate_accepts_current_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path, _manifest_path = _write_shallow_ag_fields_bundle(tmp_path)
    controller = SimpleNamespace(
        has_current_wepp_ag_fields_interchange=lambda: (
            interchange._is_wepp_ag_fields_interchange_complete(
                tmp_path / "wepp" / "ag_fields" / "output",
                mapping_path,
            )
        )
    )
    monkeypatch.setattr(
        service.AgFields,
        "load_detached",
        classmethod(lambda _cls, _wd, allow_nonexistent=True: controller),
    )
    before = _files_snapshot(tmp_path)

    service._require_current_ag_fields_interchange(
        tmp_path,
        _ag_fields_metric_plan(),
    )

    assert _files_snapshot(tmp_path) == before


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

    with zipfile.ZipFile(artifact_path, "r") as zip_handle:
        gpkg_member = next(name for name in zip_handle.namelist() if name.endswith(".gpkg"))
        gpkg_bytes = zip_handle.read(gpkg_member)

    extracted_gpkg = tmp_path / "extracted.gpkg"
    extracted_gpkg.write_bytes(gpkg_bytes)

    with sqlite3.connect(extracted_gpkg) as conn:
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


def test_publish_profile_artifact_and_resolve_published_artifact_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)

    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )

    entry = service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    assert entry["profile"] == "prep-wepp"
    assert entry["artifact_relpath"] == artifact_relpath
    registry = service.load_publication_registry(tmp_path)
    profiles = registry.get("profiles", {})
    assert isinstance(profiles, dict)
    assert "prep-wepp" in profiles

    resolved_path, resolved_relpath = service.resolve_published_artifact_path(
        tmp_path,
        profile="prep-wepp",
    )
    assert resolved_path == artifact_path
    assert resolved_relpath == artifact_relpath


def test_resolve_published_artifact_path_repairs_registry_from_cache_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission_fresh = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission_fresh)
    service.upsert_cache_index_entry(
        tmp_path,
        submission_fresh.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    drift_cache_key = "request-hash-drifted+dependency-fingerprint-drifted"
    service.upsert_cache_index_entry(
        tmp_path,
        drift_cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )

    cache_index_path = tmp_path / "export" / "features" / "cache" / "index.json"
    cache_index = json.loads(cache_index_path.read_text(encoding="utf-8"))
    cache_index["entries"] = {
        drift_cache_key: cache_index["entries"][drift_cache_key],
    }
    cache_index_path.write_text(
        json.dumps(cache_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    resolved_path, resolved_relpath = service.resolve_published_artifact_path(
        tmp_path,
        profile="prep-wepp",
    )
    assert resolved_path == artifact_path
    assert resolved_relpath == artifact_relpath

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp"]
    assert profile_entry["cache_key"] == drift_cache_key
    assert profile_entry["request_hash"] == "request-hash-drifted"
    assert profile_entry["dependency_fingerprint"] == "dependency-fingerprint-drifted"


def test_resolve_published_artifact_path_rejects_missing_cache_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    cache_index_path = tmp_path / "export" / "features" / "cache" / "index.json"
    cache_index = json.loads(cache_index_path.read_text(encoding="utf-8"))
    cache_index["entries"] = {}
    cache_index_path.write_text(
        json.dumps(cache_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_artifact_path_rejects_incompatible_cache_artifact_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpkg_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gpkg" / "features_export.geopackage.zip"
    )
    _write_valid_geopackage_zip(gpkg_artifact_path)
    gpkg_artifact_relpath = gpkg_artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "artifact_path": str(gpkg_artifact_path),
            "artifact_paths": [gpkg_artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": ["features_export.gpkg"],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gpkg/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    gdb_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gdb" / "features_export.gdb.zip"
    )
    gdb_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(gdb_artifact_path, "w") as zip_handle:
        zip_handle.writestr("features_export.gdb/table.gdbtable", b"gdb-bytes")
    gdb_artifact_relpath = gdb_artifact_path.relative_to(tmp_path).as_posix()
    gdb_cache_key = "request-hash-gdb+dependency-fingerprint-gdb"
    service.upsert_cache_index_entry(
        tmp_path,
        gdb_cache_key,
        {
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "artifact_path": str(gdb_artifact_path),
            "artifact_paths": [gdb_artifact_relpath],
            "artifact_format": "geodatabase",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gdb/manifest.json",
            "warnings": [],
        },
    )

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp"]
    profile_entry["artifact_relpath"] = gdb_artifact_relpath
    profile_entry["cache_key"] = gdb_cache_key
    profile_entry["request_hash"] = "request-hash-gdb"
    profile_entry["dependency_fingerprint"] = "dependency-fingerprint-gdb"
    service._write_publication_registry(tmp_path, registry)

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_artifact_path_rejects_incompatible_geodatabase_cache_artifact_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_prepare_export_submission(_wd: Path, payload: dict[str, object]) -> service.FeaturesExportSubmission:
        format_token = str(payload.get("format") or "").strip().lower()
        if format_token == "geodatabase":
            return _build_submission(
                cache_key="request-hash-gdb+dependency-fingerprint-gdb",
                format_token="geodatabase",
            )
        return _build_submission(
            cache_key="request-hash-gpkg+dependency-fingerprint-gpkg",
            format_token="geopackage",
        )

    monkeypatch.setattr(service, "prepare_export_submission", _fake_prepare_export_submission)

    gdb_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gdb" / "features_export.gdb.zip"
    )
    gdb_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(gdb_artifact_path, "w") as zip_handle:
        zip_handle.writestr("features_export.gdb/table.gdbtable", b"gdb-bytes")
    gdb_artifact_relpath = gdb_artifact_path.relative_to(tmp_path).as_posix()
    gdb_cache_key = "request-hash-gdb+dependency-fingerprint-gdb"
    service.upsert_cache_index_entry(
        tmp_path,
        gdb_cache_key,
        {
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "artifact_path": str(gdb_artifact_path),
            "artifact_paths": [gdb_artifact_relpath],
            "artifact_format": "geodatabase",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gdb/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp-geodatabase",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    gpkg_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gpkg" / "features_export.geopackage.zip"
    )
    _write_valid_geopackage_zip(gpkg_artifact_path)
    gpkg_artifact_relpath = gpkg_artifact_path.relative_to(tmp_path).as_posix()
    gpkg_cache_key = "request-hash-gpkg+dependency-fingerprint-gpkg"
    service.upsert_cache_index_entry(
        tmp_path,
        gpkg_cache_key,
        {
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "artifact_path": str(gpkg_artifact_path),
            "artifact_paths": [gpkg_artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": ["features_export.gpkg"],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gpkg/manifest.json",
            "warnings": [],
        },
    )

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp-geodatabase"]
    profile_entry["artifact_relpath"] = gpkg_artifact_relpath
    profile_entry["cache_key"] = gpkg_cache_key
    profile_entry["request_hash"] = "request-hash-gpkg"
    profile_entry["dependency_fingerprint"] = "dependency-fingerprint-gpkg"
    service._write_publication_registry(tmp_path, registry)

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp-geodatabase")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_profile_request_supports_cutover_profiles() -> None:
    prep_wepp_profile, prep_wepp_request = service.resolve_published_profile_request("prep-wepp")
    assert prep_wepp_profile == "prep-wepp"
    assert prep_wepp_request["format"] == "geopackage"

    prep_details_profile, prep_details_request = service.resolve_published_profile_request(
        "prep-details"
    )
    assert prep_details_profile == "prep-details"
    assert prep_details_request["format"] == "csv"

    dual_profile, dual_request = service.resolve_published_profile_request("prep-wepp-gpkg-gdb")
    assert dual_profile == "prep-wepp-gpkg-gdb"
    assert dual_request["format"] == "geopackage"

    geodatabase_profile, geodatabase_request = service.resolve_published_profile_request(
        "prep-wepp-geodatabase"
    )
    assert geodatabase_profile == "prep-wepp-geodatabase"
    assert geodatabase_request["format"] == "geodatabase"


def test_publish_profile_execution_artifacts_dual_profile_co_creates_geodatabase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_dir = tmp_path / "export" / "features" / "artifacts" / "artifact-1"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    source_zip_path = artifact_dir / "features_export.geopackage.zip"
    source_zip_path.write_bytes(b"source-geopackage-zip")
    source_gpkg_path = artifact_dir / "features_export.gpkg"
    source_gpkg_path.write_bytes(b"source-gpkg")

    def _fake_prepare_export_submission(_wd: Path, payload: dict[str, object]):
        format_token = str(payload.get("format") or "").strip().lower()
        if format_token == "geodatabase":
            return _build_submission(
                cache_key="request-hash+dependency-fingerprint-geodatabase",
                format_token="geodatabase",
            )
        return _build_submission(
            cache_key="request-hash+dependency-fingerprint-geopackage",
            format_token="geopackage",
        )

    monkeypatch.setattr(service, "prepare_export_submission", _fake_prepare_export_submission)
    monkeypatch.setattr(service.f_esri, "has_f_esri", True)

    def _fake_convert_gpkg_to_gdb(gpkg_path: str, gdb_path: str, zip_output: bool = True) -> None:
        assert Path(gpkg_path) == source_gpkg_path
        assert zip_output is True
        gdb_dir = Path(gdb_path)
        gdb_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(gdb_dir.with_suffix(".gdb.zip"), "w") as zip_handle:
            zip_handle.writestr("features_export.gdb/table.gdbtable", b"co-created-gdb-bytes")

    monkeypatch.setattr(service.f_esri, "c2c_gpkg_to_gdb", _fake_convert_gpkg_to_gdb)

    source_artifact_relpath = source_zip_path.relative_to(tmp_path).as_posix()
    published_entries = service.publish_profile_execution_artifacts(
        tmp_path,
        requested_profile="prep-wepp-gpkg-gdb",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": source_artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    assert set(published_entries.keys()) == {"prep-wepp", "prep-wepp-geodatabase"}
    gdb_entry = published_entries["prep-wepp-geodatabase"]
    gdb_relpath = str(gdb_entry["artifact_relpath"])
    assert gdb_relpath.endswith("features_export.gdb.zip")
    assert (tmp_path / gdb_relpath).is_file()
    assert not (artifact_dir / "features_export.gdb").exists()

    gdb_cache_entry = service.get_cache_index_entry(
        tmp_path,
        "request-hash+dependency-fingerprint-geodatabase",
    )
    assert isinstance(gdb_cache_entry, dict)
    assert gdb_cache_entry["artifact_relpath"] == gdb_relpath

    resolved_path, resolved_relpath = service.resolve_published_artifact_path(
        tmp_path,
        profile="prep-wepp-geodatabase",
    )
    assert resolved_relpath == gdb_relpath
    assert resolved_path == tmp_path / gdb_relpath
