from __future__ import annotations

import json

import pytest

from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import FeaturesExportValidationError
from wepppy.nodb.mods.features_export.planner import normalize_export_request, resolve_export_plan

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def catalog():
    return load_layer_catalog()


def _base_payload() -> dict[str, object]:
    return {
        "format": "geopackage",
        "units": "project",
        "layers": ["watershed.subcatchments"],
    }


def test_resolve_export_plan_valid_minimal_request(catalog) -> None:
    plan = resolve_export_plan(_base_payload(), catalog)

    assert plan.request.format == "geopackage"
    assert plan.request.units == "project"
    assert plan.request.crs == "wgs"
    assert plan.request.output_scopes == ("baseline",)
    assert [layer.output_layer_id for layer in plan.layers] == ["shared__watershed.subcatchments"]
    assert plan.warnings == ()


def test_normalize_export_request_sets_tabular_defaults_for_csv(catalog) -> None:
    payload = {
        "format": "csv",
        "units": "project",
        "layers": ["watershed.subcatchments"],
    }

    normalized = normalize_export_request(payload, catalog)

    assert normalized.tabular is not None
    assert normalized.tabular.concatenate_tables is False
    assert normalized.tabular.temporal_layout == "wide"


def test_normalize_export_request_rejects_tabular_options_for_non_tabular_formats(catalog) -> None:
    payload = {
        "format": "geopackage",
        "units": "project",
        "layers": ["watershed.subcatchments"],
        "tabular": {"concatenate_tables": True, "temporal_layout": "long"},
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(
        issue.code == "invalid_selector_combo" and issue.path == "tabular"
        for issue in exc.value.issues
    )


def test_normalize_export_request_rejects_non_boolean_tabular_concatenate_tables(catalog) -> None:
    payload = {
        "format": "parquet",
        "units": "project",
        "layers": ["watershed.subcatchments"],
        "tabular": {"concatenate_tables": "yes"},
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(
        issue.code == "invalid_type" and issue.path == "tabular.concatenate_tables"
        for issue in exc.value.issues
    )


def test_normalize_export_request_rejects_long_tabular_layout_with_mixed_event_and_yearly_modes(
    catalog,
) -> None:
    payload = {
        "format": "csv",
        "units": "project",
        "layers": [
            "wepp.temporal.events",
            "wepp.interchange.loss_all_years_hill",
        ],
        "temporal": {
            "layer_modes": {
                "wepp.temporal.events": "event",
                "wepp.interchange.loss_all_years_hill": "yearly",
            },
            "event": {"selector": "date", "dates": ["2005-01-15"]},
            "year_selection": "all",
        },
        "tabular": {"temporal_layout": "long"},
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(
        issue.code == "mixed_temporal_modes" and issue.path == "tabular.temporal_layout"
        for issue in exc.value.issues
    )


def test_normalize_export_plan_format_alias_f_esri_maps_to_geodatabase(catalog) -> None:
    payload = _base_payload()
    payload["format"] = "f_esri"

    normalized = normalize_export_request(payload, catalog)

    assert normalized.format == "geodatabase"


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "shapezip"),
        ("units", "metric"),
        ("crs", "epsg3857"),
    ],
)
def test_normalize_export_request_rejects_invalid_enum_values(
    catalog,
    field: str,
    value: str,
) -> None:
    payload = _base_payload()
    payload[field] = value

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(issue.code == "invalid_enum" and issue.path.startswith(field) for issue in exc.value.issues)


def test_normalize_export_request_rejects_invalid_output_scopes(catalog) -> None:
    payload = _base_payload()
    payload["output_scopes"] = ["baseline", "mars"]

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(
        issue.code == "invalid_enum" and issue.path.startswith("output_scopes")
        for issue in exc.value.issues
    )


def test_normalize_export_request_rejects_mixed_omni_scenario_and_contrast_families(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": [
            "omni.scenarios.hillslopes",
            "omni.contrasts.hillslopes",
        ],
        "scenario": "control_a",
        "contrast_id": "delta_a",
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(issue.code in {"invalid_selector_combo", "mutually_exclusive"} for issue in exc.value.issues)


def test_normalize_export_request_validates_event_selector_contract(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": ["wepp.temporal.events"],
        "temporal": {
            "mode": "event",
            "event": {
                "selector": "date",
                "dates": ["2025-01-01"],
                "return_periods": [2],
            },
        },
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(
        issue.code == "mutually_exclusive" and issue.path == "temporal.event.return_periods"
        for issue in exc.value.issues
    )


def test_normalize_export_request_rejects_daily_temporal_mode(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": ["wepp.summary.hillslopes"],
        "temporal": {"mode": "daily"},
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(issue.code == "unsupported_temporal_mode" for issue in exc.value.issues)


def test_resolve_export_plan_drops_temporally_incompatible_layers_with_warning(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": ["wepp.summary.channels", "wepp.temporal.events"],
        "temporal": {
            "mode": "event",
            "event": {"selector": "date", "dates": ["2025-01-01"]},
        },
    }

    plan = resolve_export_plan(payload, catalog)

    assert [layer.output_layer_id for layer in plan.layers] == ["baseline__wepp.temporal.events"]
    assert any(
        warning.code == "layer_unavailable" and warning.layer_id == "wepp.summary.channels"
        for warning in plan.warnings
    )


def test_resolve_export_plan_rejects_when_temporal_mode_excludes_all_layers(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": ["wepp.summary.channels"],
        "temporal": {
            "mode": "event",
            "event": {"selector": "date", "dates": ["2025-01-01"]},
        },
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        resolve_export_plan(payload, catalog)

    assert any(issue.code == "no_exportable_layers" for issue in exc.value.issues)


def test_resolve_export_plan_keeps_atemporal_layers_when_temporal_mode_is_selected(catalog) -> None:
    payload = {
        "format": "geoparquet",
        "units": "si",
        "layers": [
            "landuse.dominant",
            "soils.dominant",
            "watershed.channels",
            "watershed.subcatchments",
        ],
        "temporal": {
            "mode": "annual_average",
        },
    }

    plan = resolve_export_plan(payload, catalog)

    assert [layer.output_layer_id for layer in plan.layers] == [
        "shared__landuse.dominant",
        "shared__soils.dominant",
        "shared__watershed.channels",
        "shared__watershed.subcatchments",
    ]
    assert plan.warnings == ()


def test_resolve_export_plan_hill_wat_supports_event_mode(catalog) -> None:
    payload = {
        "format": "geopackage",
        "units": "project",
        "layers": ["wepp.interchange.hill_wat"],
        "temporal": {
            "layer_modes": {"wepp.interchange.hill_wat": "event"},
            "event": {"selector": "date", "dates": ["2005-01-15"]},
        },
    }

    plan = resolve_export_plan(payload, catalog)

    assert [layer.output_layer_id for layer in plan.layers] == ["baseline__wepp.interchange.hill_wat"]
    assert plan.warnings == ()


def test_resolve_export_plan_new_interchange_layers_are_cataloged(catalog) -> None:
    payload = {
        "format": "geopackage",
        "units": "project",
        "layers": [
            "wepp.interchange.hill_ebe",
            "wepp.interchange.hill_soil",
            "wepp.interchange.hill_pass_events",
            "wepp.interchange.hill_pass_metadata",
            "wepp.interchange.loss_all_years_hill",
            "wepp.interchange.loss_all_years_channel",
        ],
    }

    plan = resolve_export_plan(payload, catalog)

    assert [layer.output_layer_id for layer in plan.layers] == [
        "baseline__wepp.interchange.hill_ebe",
        "baseline__wepp.interchange.hill_pass_events",
        "baseline__wepp.interchange.hill_pass_metadata",
        "baseline__wepp.interchange.hill_soil",
        "baseline__wepp.interchange.loss_all_years_channel",
        "baseline__wepp.interchange.loss_all_years_hill",
    ]


def test_resolve_export_plan_is_deterministic_for_ordering_and_serialization(catalog) -> None:
    payload_a = {
        "format": "geoparquet",
        "units": "si",
        "layers": [
            "wepp.summary.channels",
            "watershed.channels",
            "wepp.summary.hillslopes",
        ],
        "output_scopes": ["ROADS", "baseline", "roads"],
    }
    payload_b = {
        "format": "geoparquet",
        "units": "si",
        "layers": [
            "wepp.summary.hillslopes",
            "wepp.summary.channels",
            "watershed.channels",
        ],
        "output_scopes": ["baseline", "roads"],
    }

    plan_a = resolve_export_plan(payload_a, catalog)
    plan_b = resolve_export_plan(payload_b, catalog)

    expected_layer_ids = [
        "baseline__wepp.summary.channels",
        "baseline__wepp.summary.hillslopes",
        "roads__wepp.summary.channels",
        "roads__wepp.summary.hillslopes",
        "shared__watershed.channels",
    ]
    assert [layer.output_layer_id for layer in plan_a.layers] == expected_layer_ids
    assert plan_a.to_mapping() == plan_b.to_mapping()
    assert json.dumps(plan_a.to_mapping(), sort_keys=True) == json.dumps(
        plan_b.to_mapping(), sort_keys=True
    )


def test_normalize_export_request_rejects_unknown_layer_ids(catalog) -> None:
    payload = {
        "format": "geojson",
        "units": "si",
        "layers": ["watershed.subcatchments", "unknown.layer"],
    }

    with pytest.raises(FeaturesExportValidationError) as exc:
        normalize_export_request(payload, catalog)

    assert any(issue.code == "unknown_layer_id" for issue in exc.value.issues)


def test_normalize_export_request_allows_dynamic_column_selection_without_explicit_contract(catalog) -> None:
    payload = {
        "format": "geopackage",
        "units": "project",
        "layers": ["wepp.summary.hillslopes"],
        "column_selection": {
            "wepp.summary.hillslopes": {
                "include": ["Runoff Volume", "Soil Loss", "TopazID"],
            }
        },
    }

    normalized = normalize_export_request(payload, catalog)

    assert normalized.column_selection
    selection = normalized.column_selection[0]
    assert selection.layer_id == "wepp.summary.hillslopes"
    assert selection.include == ("Runoff Volume", "Soil Loss", "TopazID")
