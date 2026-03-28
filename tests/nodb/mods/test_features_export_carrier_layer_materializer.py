from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from wepppy.nodb.mods.features_export import carrier_layer_materializer as materializer
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    NormalizedTemporalEvent,
    NormalizedTemporalRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame
from wepppy.nodb.mods.features_export.join_planner import JOIN_KEY_COLUMN, MaterializationContractError

pytestmark = pytest.mark.unit


def _event_layer_plan() -> ResolvedLayerPlan:
    return ResolvedLayerPlan(
        layer_id="wepp.temporal.events",
        family="wepp_temporal",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.temporal.events",
        temporal_mode="event",
        carrier_layer="sbs_map-subcatchments",
    )


def _event_request_plan(*, dates: tuple[str, ...]) -> ResolvedExportPlan:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("wepp.temporal.events",),
        temporal=NormalizedTemporalRequest(
            mode="event",
            event=NormalizedTemporalEvent(selector="date", dates=dates),
        ),
    )
    return ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(_event_layer_plan(),),
        warnings=(),
    )


def test_materialize_carrier_layer_core_filters_event_sources_by_selected_dates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_plan = _event_request_plan(dates=("2010-01-01",))
    layer = _event_layer_plan()
    source = DiscoveredSourceFrame(
        source_id="wepp_return_period_events",
        source_kind="parquet",
        required=True,
        dataframe=pd.DataFrame(
            {
                "topaz_id": [1, 1, 2],
                "calendar_year": [2010, 2011, 2010],
                "mo": [1, 1, 1],
                "da": [1, 1, 1],
                "runoff_volume_m3": [10.0, 20.0, 30.0],
            }
        ),
        units_by_column={"runoff_volume_m3": "m^3"},
    )
    monkeypatch.setattr(materializer, "discover_layer_sources", lambda **kwargs: ((source,), ()))
    monkeypatch.setattr(
        materializer,
        "resolve_selected_columns",
        lambda **kwargs: (("runoff_volume_m3",), {"runoff_volume_m3": "m^3"}),
    )

    result = materializer.materialize_carrier_layer_core(
        wd=tmp_path,
        layer=layer,
        catalog_layer_raw={"join": {"primary_key": "topaz_id", "fallback_keys": ("TopazID",)}},
        request_plan=request_plan,
        dependency_entries=(),
        consolidated_join_key_column=JOIN_KEY_COLUMN,
    )

    assert len(result.frame.index) == 2
    assert sorted(result.frame[JOIN_KEY_COLUMN].tolist()) == ["1", "2"]
    assert sorted(result.frame["runoff_volume_m3"].tolist()) == [10.0, 30.0]


def test_materialize_carrier_layer_core_skips_optional_event_source_without_date_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_plan = _event_request_plan(dates=("2010-01-01",))
    layer = _event_layer_plan()
    required_source = DiscoveredSourceFrame(
        source_id="wepp_return_period_events",
        source_kind="parquet",
        required=True,
        dataframe=pd.DataFrame(
            {
                "topaz_id": [1, 2],
                "calendar_year": [2010, 2010],
                "mo": [1, 1],
                "da": [1, 1],
                "runoff_volume_m3": [10.0, 30.0],
            }
        ),
        units_by_column={"runoff_volume_m3": "m^3"},
    )
    optional_source = DiscoveredSourceFrame(
        source_id="wepp_return_period_ranks",
        source_kind="parquet",
        required=False,
        dataframe=pd.DataFrame(
            {
                "topaz_id": [1, 1, 2, 2],
                "measure_value": [1.0, 2.0, 3.0, 4.0],
            }
        ),
        units_by_column={"measure_value": "kg"},
    )
    monkeypatch.setattr(
        materializer,
        "discover_layer_sources",
        lambda **kwargs: ((required_source, optional_source), ()),
    )
    monkeypatch.setattr(
        materializer,
        "resolve_selected_columns",
        lambda **kwargs: (("runoff_volume_m3",), {"runoff_volume_m3": "m^3"}),
    )

    result = materializer.materialize_carrier_layer_core(
        wd=tmp_path,
        layer=layer,
        catalog_layer_raw={"join": {"primary_key": "topaz_id", "fallback_keys": ("TopazID",)}},
        request_plan=request_plan,
        dependency_entries=(),
        consolidated_join_key_column=JOIN_KEY_COLUMN,
    )

    assert len(result.frame.index) == 2
    assert "measure_value" not in result.frame.columns


def test_materialize_carrier_layer_core_raises_when_required_event_source_has_no_date_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_plan = _event_request_plan(dates=("2010-01-01",))
    layer = _event_layer_plan()
    required_source = DiscoveredSourceFrame(
        source_id="wepp_return_period_events",
        source_kind="parquet",
        required=True,
        dataframe=pd.DataFrame(
            {
                "topaz_id": [1, 2],
                "runoff_volume_m3": [10.0, 30.0],
            }
        ),
        units_by_column={"runoff_volume_m3": "m^3"},
    )
    monkeypatch.setattr(materializer, "discover_layer_sources", lambda **kwargs: ((required_source,), ()))
    monkeypatch.setattr(
        materializer,
        "resolve_selected_columns",
        lambda **kwargs: (("runoff_volume_m3",), {"runoff_volume_m3": "m^3"}),
    )

    with pytest.raises(MaterializationContractError) as exc_info:
        materializer.materialize_carrier_layer_core(
            wd=tmp_path,
            layer=layer,
            catalog_layer_raw={"join": {"primary_key": "topaz_id", "fallback_keys": ("TopazID",)}},
            request_plan=request_plan,
            dependency_entries=(),
            consolidated_join_key_column=JOIN_KEY_COLUMN,
        )

    assert "selector_columns_missing" in str(exc_info.value.details)


def test_materialize_carrier_layer_core_keeps_required_source_when_event_filter_matches_no_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_plan = _event_request_plan(dates=("1999-01-01",))
    layer = _event_layer_plan()
    required_source = DiscoveredSourceFrame(
        source_id="wepp_return_period_events",
        source_kind="parquet",
        required=True,
        dataframe=pd.DataFrame(
            {
                "topaz_id": [1, 2],
                "calendar_year": [2010, 2010],
                "mo": [1, 1],
                "da": [1, 1],
                "runoff_volume_m3": [10.0, 30.0],
            }
        ),
        units_by_column={"runoff_volume_m3": "m^3"},
    )
    monkeypatch.setattr(materializer, "discover_layer_sources", lambda **kwargs: ((required_source,), ()))
    monkeypatch.setattr(
        materializer,
        "resolve_selected_columns",
        lambda **kwargs: (("runoff_volume_m3", "date"), {"runoff_volume_m3": "m^3", "date": "non-unitized"}),
    )

    result = materializer.materialize_carrier_layer_core(
        wd=tmp_path,
        layer=layer,
        catalog_layer_raw={"join": {"primary_key": "topaz_id", "fallback_keys": ("TopazID",)}},
        request_plan=request_plan,
        dependency_entries=(),
        consolidated_join_key_column=JOIN_KEY_COLUMN,
    )

    assert result.frame.empty
    assert "date" in result.frame.columns
