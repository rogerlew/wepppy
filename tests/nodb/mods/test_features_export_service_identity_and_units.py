from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from wepppy.nodb.mods.features_export import carrier_identity, service
from wepppy.nodb.mods.features_export.join_planner import (
    MaterializationContractError,
    resolve_geometry_key,
)
from wepppy.nodb.mods.features_export.output_column_naming import (
    apply_unitized_column_suffixes,
)

pytestmark = pytest.mark.unit


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

    result = carrier_identity.backfill_identity_from_geometry_key(
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
        carrier_identity,
        "backfill_tabular_identity_from_watershed",
        lambda **kwargs: kwargs["frame"],  # noqa: ARG005
    )

    existing_join_frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["1", "2", "3"],
            "wepp_id": [1, 2, 3],
            "topaz_id": [101, 101, 102],
        }
    )
    existing_join_result = carrier_identity.align_carrier_identity_join_key(
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
    one_to_one_identity_result = carrier_identity.align_carrier_identity_join_key(
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
    topaz_domain_result = carrier_identity.align_carrier_identity_join_key(
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
    missing_join_result = carrier_identity.align_carrier_identity_join_key(
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

    monkeypatch.setattr(carrier_identity, "backfill_tabular_identity_from_watershed", _fake_backfill)

    frame = pd.DataFrame(
        {
            service._CONSOLIDATED_JOIN_KEY_COLUMN: ["13", "14", "17"],
            "wepp_id": [13, 14, 17],
        }
    )
    result = carrier_identity.align_carrier_identity_join_key(
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


@pytest.mark.parametrize("geometry_key,geometry_ids", [("WeppID", ["3", "31"]), ("TopazID", ["31", "163"])])
def test_geometry_attachment_uses_resolved_identity_domain(geometry_key, geometry_ids):
    from wepppy.nodb.mods.features_export.geometry_carriers import CanonicalGeometryCarrier, attach_geometry_once

    key = service._CONSOLIDATED_JOIN_KEY_COLUMN
    core = pd.DataFrame({key: ["31"], "wepp_id": [3], "topaz_id": [31], "ET": [3.61]})
    geometry = gpd.GeoDataFrame({key: geometry_ids, "geometry": [Point(3, 0), Point(31, 0)]}, crs=4326)
    aligned = carrier_identity.align_core_to_geometry_identity(
        core, geometry_key_column=geometry_key, carrier_layer="sbs_map-subcatchments"
    )
    result = attach_geometry_once(
        core_table=aligned,
        geometry_carrier=CanonicalGeometryCarrier("sbs_map-subcatchments", "fixture", geometry_key, geometry),
        allow_non_unique_keys=True,
    )
    observed = result.loc[result.ET.notna()]
    assert len(observed) == 1
    assert observed.geometry.iloc[0].equals(Point(3, 0))
    assert result.ET.isna().sum() == 1


@pytest.mark.parametrize("identities", [[3, None], [3, 3]])
def test_geometry_identity_rejects_missing_or_collapsing_mapping(identities):
    core = pd.DataFrame({service._CONSOLIDATED_JOIN_KEY_COLUMN: ["31", "163"], "wepp_id": identities})
    with pytest.raises(MaterializationContractError, match="complete and one-to-one"):
        carrier_identity.align_core_to_geometry_identity(
            core, geometry_key_column="WeppID", carrier_layer="sbs_map-subcatchments"
        )


def test_geometry_identity_rejects_missing_column_and_preserves_other_carriers():
    core = pd.DataFrame({service._CONSOLIDATED_JOIN_KEY_COLUMN: ["31"]})
    with pytest.raises(MaterializationContractError, match="missing the resolved"):
        carrier_identity.align_core_to_geometry_identity(
            core, geometry_key_column="WeppID", carrier_layer="sbs_map-subcatchments"
        )
    assert carrier_identity.align_core_to_geometry_identity(
        core, geometry_key_column="WeppID", carrier_layer="ag_fields_subfields_geojson"
    ) is core
