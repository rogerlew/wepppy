from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import schema_defaults_routes
from wepppy.microservices.rq_engine import upload_climate_routes
from wepppy.microservices.rq_engine import upload_disturbed_routes
from wepppy.microservices.rq_engine import watershed_routes

pytestmark = pytest.mark.microservice

RUNID = "run-1"
CONFIG = "disturbed9002_wbt"

GEOSPATIAL_PATH = f"/api/runs/{RUNID}/{CONFIG}/geospatial-metadata"
RUN_ENDPOINTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints"
_UNSET = object()
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _sample_runtime(
    *,
    climate_has_station: bool = True,
    map_bounds: list[float] | None | object = _UNSET,
    watershed_csa: float | None = 12.0,
    watershed_mcl: float | None = 88.0,
    sbs_upload_supported: bool = True,
    has_dem: bool = True,
) -> schema_defaults_routes.RuntimeState:
    resolved_bounds = (
        [-116.5, 45.5, -116.1, 45.8] if map_bounds is _UNSET else map_bounds
    )
    return schema_defaults_routes.RuntimeState(
        runid=RUNID,
        config=CONFIG,
        active_mods=("disturbed", "wepp"),
        region="conus",
        states={
            "has_dem": has_dem,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "watershed_csa": watershed_csa,
            "watershed_mcl": watershed_mcl,
            "delineation_backend": "wbt",
            "climate_built": True,
            "climate_mode_code": 11,
            "climate_mode": "gridmet_prism",
            "climate_has_station": climate_has_station,
            "climate_station_required": False,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "initial_sat": 0.75,
            "wepp_has_run": False,
            "disturbed_enabled": True,
            "sbs_upload_supported": sbs_upload_supported,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver": 2018.0,
            "map_center": [-116.3, 45.65],
            "map_bounds": resolved_bounds,
            "map_zoom": 11.0,
            "map_zoom_resolution_m_per_px": 9.6,
            "dem_coverage_source": "3dep",
            "uploaded_dem_filename": "dem.tif",
        },
        generated_at="2026-04-10T23:01:00Z",
        run_state_revision="runstate:run-1:abc123def456",
    )


def _stub_auth(monkeypatch: pytest.MonkeyPatch, scope: str, *, token_class: str = "service") -> None:
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": token_class, "scope": scope},
    )
    monkeypatch.setattr(schema_defaults_routes, "authorize_run_access", lambda claims, runid: None)


def _assert_canonical_error(payload: dict[str, Any], *, code: str | None = None) -> None:
    assert set(payload).issuperset({"error"})
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["error"].get("message"), str)
    assert isinstance(payload["error"].get("details"), str)
    if code is not None:
        assert payload["error"].get("code") == code


def test_geospatial_metadata_requires_auth() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 401
    _assert_canonical_error(response.json(), code="unauthorized")


def test_geospatial_metadata_rejects_wrong_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:enqueue")

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 403
    payload = response.json()
    _assert_canonical_error(payload, code="forbidden")
    assert "rq:read" in payload["error"]["message"]
    assert "rq:status" in payload["error"]["message"]


@pytest.mark.parametrize("scope", ("rq:status", "rq:read"))
def test_geospatial_metadata_accepts_supported_scopes(
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    _stub_auth(monkeypatch, scope)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 200


def test_geospatial_metadata_payload_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_domain",
        "run_state_revision",
        "run_state_vector",
        "updated_at",
        "data_state",
        "data_updated_at",
        "etag",
        "runid",
        "config",
        "region",
        "dem_coverage",
        "recommended_defaults",
        "dynamic_constraints",
        "field_availability",
        "computed_at",
    }
    assert payload["runid"] == RUNID
    assert payload["config"] == CONFIG
    assert payload["run_state_domain"] == "metadata"
    assert payload["run_state_vector"] == {
        "orchestration_revision": None,
        "metadata_revision": payload["run_state_revision"],
        "outputs_revision": None,
    }
    assert payload["data_state"] == "materialized"
    assert payload["data_updated_at"] == payload["updated_at"]
    assert payload["etag"].startswith('W/"geospatial:')
    assert UTC_TIMESTAMP_RE.match(payload["updated_at"])
    assert payload["dem_coverage"]["source"] == "3dep"
    assert payload["dem_coverage"]["has_dem"] is True
    assert payload["recommended_defaults"]["map_center"] == [-116.3, 45.65]
    assert payload["recommended_defaults"]["map_bounds"] == [-116.5, 45.5, -116.1, 45.8]
    assert payload["recommended_defaults"]["map_zoom"] == 11
    assert payload["recommended_defaults"]["csa"] == 12.0
    assert payload["recommended_defaults"]["mcl"] == 88.0
    assert payload["dynamic_constraints"]["climate_mode"]["enum_available"] == [0, 2, 5, 6, 11]
    assert payload["field_availability"]["map_bounds"]["state"] == "available"
    assert payload["field_availability"]["station_catalog"]["state"] == "available"
    assert payload["computed_at"] == payload["updated_at"]
    updated_at = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))
    assert updated_at <= datetime.now(timezone.utc)


def test_geospatial_metadata_fallbacks_when_run_resolved_fields_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(
            climate_has_station=False,
            map_bounds=None,
            watershed_csa=None,
            watershed_mcl=None,
            has_dem=False,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 200
    payload = response.json()
    defaults = payload["recommended_defaults"]
    assert defaults["map_bounds"] == pytest.approx([-116.4, 45.55, -116.2, 45.75])
    assert defaults["csa"] == 10.0
    assert defaults["mcl"] == 75.0
    assert payload["field_availability"]["map_bounds"]["state"] == "pending"
    assert payload["field_availability"]["map_bounds"]["reason_code"] == "awaiting_dem_upload"
    assert payload["field_availability"]["csa"]["state"] == "pending"
    assert payload["field_availability"]["mcl"]["state"] == "pending"
    assert payload["field_availability"]["station_catalog"]["state"] == "pending"
    assert payload["field_availability"]["station_catalog"]["reason_code"] == "awaiting_dem_fetch"
    assert payload["dynamic_constraints"]["climate_mode"]["enum_available"] == [0, 5, 6, 11]


@pytest.mark.parametrize(
    "climate_has_station,expected_modes",
    (
        (True, [0, 2, 5, 6, 11]),
        (False, [0, 5, 6, 11]),
    ),
)
def test_geospatial_climate_mode_constraints_match_climate_schema(
    monkeypatch: pytest.MonkeyPatch,
    climate_has_station: bool,
    expected_modes: list[int],
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(climate_has_station=climate_has_station),
    )

    climate_schema_path = f"/api/runs/{RUNID}/{CONFIG}/controllers/climate/schema"

    with TestClient(rq_engine.app) as client:
        geospatial_response = client.get(GEOSPATIAL_PATH)
        climate_schema_response = client.get(climate_schema_path)

    assert geospatial_response.status_code == 200
    assert climate_schema_response.status_code == 200

    geospatial_modes = geospatial_response.json()["dynamic_constraints"]["climate_mode"]["enum_available"]
    climate_schema_modes = climate_schema_response.json()["fields"]["climate_mode"]["enum_available"]
    assert geospatial_modes == expected_modes
    assert climate_schema_modes == expected_modes
    assert geospatial_modes == climate_schema_modes


def test_geospatial_metadata_reports_404_for_unknown_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _missing(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        raise FileNotFoundError("missing run")

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _missing)

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 404
    _assert_canonical_error(response.json(), code="not_found")


def test_geospatial_metadata_reports_401_for_unexpected_auth_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: (_ for _ in ()).throw(RuntimeError("auth helper failure")),
    )

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 401
    _assert_canonical_error(response.json())


def test_geospatial_metadata_reports_404_for_config_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _mismatch(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        raise schema_defaults_routes.RunConfigMismatchError("mismatch")

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _mismatch)

    with TestClient(rq_engine.app) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 404
    _assert_canonical_error(response.json(), code="not_found")


def test_geospatial_metadata_reports_canonical_500_for_state_load_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _state_failure(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        raise RuntimeError("unexpected state load failure")

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _state_failure)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 500
    _assert_canonical_error(response.json())


def test_geospatial_metadata_reports_canonical_500_for_payload_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())
    monkeypatch.setattr(
        schema_defaults_routes,
        "_geospatial_payload",
        lambda runtime: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get(GEOSPATIAL_PATH)

    assert response.status_code == 500
    _assert_canonical_error(response.json())


def test_run_endpoints_publish_geospatial_and_upload_metadata_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINTS_PATH)

    assert response.status_code == 200
    operations = {item["operation_id"]: item for item in response.json()["operations"]}
    required = {
        "rq_engine_geospatial_metadata",
        "rq_engine_upload_dem",
        "rq_engine_upload_cli",
        "rq_engine_upload_sbs",
        "rq_engine_upload_cover_transform",
    }
    assert required.issubset(operations.keys())

    geospatial = operations["rq_engine_geospatial_metadata"]
    assert geospatial["method"] == "GET"
    assert geospatial["path"] == "/api/runs/{runid}/{config}/geospatial-metadata"
    assert geospatial["file_fields"] == []

    upload_dem = operations["rq_engine_upload_dem"]
    dem_field = upload_dem["file_fields"][0]
    assert dem_field["name"] == "input_upload_dem"
    assert dem_field["allowed_extensions"] == [f".{ext}" for ext in watershed_routes.UPLOAD_DEM_ALLOWED_EXTENSIONS]
    assert dem_field["resolution_requirements"]["max_dimension_px"] == watershed_routes.UPLOAD_DEM_MAX_DIMENSION
    assert dem_field["crs_requirements"]["allow_reprojection"] is True
    assert dem_field["resolution_requirements"]["mode"] == "square_pixels_required"
    assert dem_field["value_semantics"]["classification_type"] == "continuous_elevation"

    upload_cli = operations["rq_engine_upload_cli"]
    cli_field = upload_cli["file_fields"][0]
    assert cli_field["name"] == "input_upload_cli"
    assert cli_field["allowed_extensions"] == [
        f".{ext}" for ext in upload_climate_routes.UPLOAD_CLI_ALLOWED_EXTENSIONS
    ]
    assert cli_field["max_bytes"] == upload_climate_routes.UPLOAD_CLI_MAX_BYTES
    assert cli_field["value_semantics"]["classification_type"] == "station_climate_timeseries"

    upload_sbs = operations["rq_engine_upload_sbs"]
    sbs_field = upload_sbs["file_fields"][0]
    assert sbs_field["name"] == "input_upload_sbs"
    assert sbs_field["allowed_extensions"] == [
        f".{ext}" for ext in upload_disturbed_routes.UPLOAD_SBS_ALLOWED_EXTENSIONS
    ]
    assert sbs_field["max_bytes"] == upload_disturbed_routes.UPLOAD_SBS_MAX_BYTES
    assert sbs_field["crs_requirements"]["mode"] == "must_have_valid_projection"
    assert sbs_field["value_semantics"]["classification_type"] == "integer_class_raster"
    assert sbs_field["value_semantics"]["max_unique_classes"] == 256

    upload_cover = operations["rq_engine_upload_cover_transform"]
    cover_field = upload_cover["file_fields"][0]
    assert cover_field["name"] == "input_upload_cover_transform"
    assert cover_field["allowed_extensions"] == [
        f".{ext}" for ext in upload_disturbed_routes.UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS
    ]
    assert cover_field["max_bytes"] == upload_disturbed_routes.UPLOAD_COVER_TRANSFORM_MAX_BYTES
    assert upload_cover["available_if"] == []
    assert upload_cover["required_if"] == []


def test_geospatial_soils_mode_constraints_match_soils_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())
    soils_schema_path = f"/api/runs/{RUNID}/{CONFIG}/controllers/soils/schema"

    with TestClient(rq_engine.app) as client:
        geospatial_response = client.get(GEOSPATIAL_PATH)
        soils_schema_response = client.get(soils_schema_path)

    assert geospatial_response.status_code == 200
    assert soils_schema_response.status_code == 200
    geospatial_modes = geospatial_response.json()["dynamic_constraints"]["soils_mode"]["enum_available"]
    soils_schema_modes = soils_schema_response.json()["fields"]["soils_mode"]["enum_available"]
    assert geospatial_modes == soils_schema_modes


@pytest.mark.parametrize(
    "watershed_csa,watershed_mcl",
    (
        (12.0, 88.0),
        (None, None),
    ),
)
def test_geospatial_watershed_defaults_match_watershed_templates(
    monkeypatch: pytest.MonkeyPatch,
    watershed_csa: float | None,
    watershed_mcl: float | None,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(watershed_csa=watershed_csa, watershed_mcl=watershed_mcl),
    )
    watershed_templates_path = f"/api/runs/{RUNID}/{CONFIG}/controllers/watershed/templates"

    with TestClient(rq_engine.app) as client:
        geospatial_response = client.get(GEOSPATIAL_PATH)
        templates_response = client.get(watershed_templates_path)

    assert geospatial_response.status_code == 200
    assert templates_response.status_code == 200

    geo_defaults = geospatial_response.json()["recommended_defaults"]
    template_defaults = templates_response.json()["run_resolved_defaults"]
    assert geo_defaults["csa"] == template_defaults["csa"]
    assert geo_defaults["mcl"] == template_defaults["mcl"]


@pytest.mark.parametrize(
    "operation_id,required_field,constraint_mode,constraint_source",
    (
        ("rq_engine_upload_dem", "input_upload_dem", "run_resolved", "geospatial_metadata"),
        ("rq_engine_upload_cli", "input_upload_cli", "static", None),
        ("rq_engine_upload_sbs", "input_upload_sbs", "run_resolved", "geospatial_metadata"),
        ("rq_engine_upload_cover_transform", "input_upload_cover_transform", "static", None),
    ),
)
def test_upload_schema_and_defaults_routes_include_hardened_file_metadata(
    monkeypatch: pytest.MonkeyPatch,
    operation_id: str,
    required_field: str,
    constraint_mode: str,
    constraint_source: str | None,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    schema_path = f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/schema"
    defaults_path = f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/defaults"

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(schema_path)
        defaults_response = client.get(defaults_path)

    assert schema_response.status_code == 200, operation_id
    schema_payload = schema_response.json()
    descriptor = schema_payload["operation_descriptor"]
    assert descriptor["operation_id"] == operation_id
    assert descriptor["content_types"] == ["multipart/form-data"]
    assert descriptor["file_fields"][0]["name"] == required_field
    assert schema_payload["request"]["required"] == [required_field]
    field_metadata = schema_payload["request"]["properties"][required_field]
    assert field_metadata["constraint_mode"] == constraint_mode
    if constraint_source is None:
        assert "constraint_source" not in field_metadata
    else:
        assert field_metadata["constraint_source"] == constraint_source

    if operation_id == "rq_engine_upload_sbs":
        sbs_field = descriptor["file_fields"][0]
        assert sbs_field["value_semantics"]["max_unique_classes"] == 256
        assert sbs_field["value_semantics"]["color_table_mode"] == "optional_but_if_present_must_map_known_severity"
    if operation_id == "rq_engine_upload_dem":
        dem_field = descriptor["file_fields"][0]
        assert dem_field["resolution_requirements"]["max_dimension_px"] == watershed_routes.UPLOAD_DEM_MAX_DIMENSION

    assert defaults_response.status_code == 200, operation_id
    defaults_payload = defaults_response.json()
    assert defaults_payload["operation_id"] == operation_id
    assert defaults_payload["defaults_context"]["config"] == CONFIG
    assert defaults_payload["defaults_context"]["active_mods"] == ["disturbed", "wepp"]
