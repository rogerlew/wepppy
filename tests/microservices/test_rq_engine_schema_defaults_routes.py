from __future__ import annotations

import re
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import orchestration_read_routes, schema_defaults_routes

pytestmark = pytest.mark.microservice

RUNID = "run-1"
CONFIG = "disturbed9002_wbt"

CONTROLLERS_PATH = f"/api/runs/{RUNID}/{CONFIG}/controllers"
CONTROLLER_SCHEMA_PATH = f"/api/runs/{RUNID}/{CONFIG}/controllers/climate/schema"
CONTROLLER_HINTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/controllers/climate/hints"
CONTROLLER_TEMPLATES_PATH = f"/api/runs/{RUNID}/{CONFIG}/controllers/climate/templates"
RUN_ENDPOINTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints"
RUN_ENDPOINT_SCHEMA_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_run_wepp/schema"
RUN_ENDPOINT_DEFAULTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_run_wepp/defaults"
BUILD_SOILS_SCHEMA_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_soils/schema"
BUILD_SOILS_DEFAULTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_soils/defaults"
BUILD_RUSLE_SCHEMA_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_rusle/schema"
BUILD_RUSLE_DEFAULTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_rusle/defaults"
FORK_SCHEMA_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_fork_project/schema"
FORK_DEFAULTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_fork_project/defaults"

UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

SCHEMA_DEFAULT_PATHS = (
    CONTROLLERS_PATH,
    CONTROLLER_SCHEMA_PATH,
    CONTROLLER_HINTS_PATH,
    CONTROLLER_TEMPLATES_PATH,
    RUN_ENDPOINTS_PATH,
    RUN_ENDPOINT_SCHEMA_PATH,
    RUN_ENDPOINT_DEFAULTS_PATH,
    BUILD_SOILS_SCHEMA_PATH,
    BUILD_SOILS_DEFAULTS_PATH,
    FORK_SCHEMA_PATH,
    FORK_DEFAULTS_PATH,
)


def _sample_runtime(
    *,
    active_mods: tuple[str, ...] = ("disturbed", "wepp"),
    disturbed_enabled: bool = True,
    sbs_upload_supported: bool = True,
    initial_sat: float | None = 0.75,
    disturbed_sol_ver: float | None = 2018.0,
) -> schema_defaults_routes.RuntimeState:
    return schema_defaults_routes.RuntimeState(
        runid=RUNID,
        config=CONFIG,
        active_mods=active_mods,
        region="conus",
        states={
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "climate_built": True,
            "climate_mode_code": 11,
            "climate_mode": "gridmet_prism",
            "climate_has_station": True,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "initial_sat": initial_sat,
            "wepp_has_run": False,
            "disturbed_enabled": disturbed_enabled,
            "sbs_upload_supported": sbs_upload_supported,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver": disturbed_sol_ver,
        },
        generated_at="2026-04-10T22:13:00Z",
        run_state_revision="runstate:run-1:deadbeefcafe",
    )


def _sample_orchestration_runtime_for_discovery_parity() -> dict[str, Any]:
    return {
        "runid": RUNID,
        "config": CONFIG,
        "active_mods": ("disturbed", "wepp"),
        "states": {
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "climate_built": False,
            "climate_station_ready": True,
            "climate_mode": None,
            "landuse_built": False,
            "landuse_mode": "nlcd",
            "soils_built": False,
            "soils_mode": "ssurgo",
            "wepp_has_run": False,
            "wepp_hillslopes_run": False,
            "wepp_watershed_run": False,
            "disturbed_enabled": True,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver_selected": True,
        },
        "step_completion_ts": {
            "fetch-dem-and-build-channels": 100,
            "set-outlet": 110,
            "build-subcatchments-and-abstract-watershed": 120,
            "upload-sbs": 130,
            "build-climate": None,
            "build-landuse": None,
            "build-soils": None,
            "prep-wepp-watershed": None,
            "run-wepp": None,
            "run-wepp-watershed": None,
            "build-rusle": None,
            "run-ash": None,
            "run-debris-flow": None,
        },
        "step_job": {},
        "generated_at": "2026-04-11T04:00:00Z",
    }


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


@pytest.mark.parametrize("path", SCHEMA_DEFAULT_PATHS)
def test_schema_defaults_routes_require_auth(path: str) -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get(path)

    assert response.status_code == 401
    _assert_canonical_error(response.json(), code="unauthorized")


@pytest.mark.parametrize("path", SCHEMA_DEFAULT_PATHS)
def test_schema_defaults_routes_reject_wrong_scope(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    _stub_auth(monkeypatch, "rq:enqueue")

    with TestClient(rq_engine.app) as client:
        response = client.get(path)

    assert response.status_code == 403
    payload = response.json()
    _assert_canonical_error(payload, code="forbidden")
    assert "rq:read" in payload["error"]["message"]
    assert "rq:status" in payload["error"]["message"]


@pytest.mark.parametrize("scope", ("rq:status", "rq:read"))
def test_schema_defaults_routes_accept_supported_scopes(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    _stub_auth(monkeypatch, scope)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        for path in SCHEMA_DEFAULT_PATHS:
            response = client.get(path)
            assert response.status_code == 200, path


def test_schema_defaults_routes_reject_run_access_without_loading_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": "rq:status"},
    )
    monkeypatch.setattr(
        schema_defaults_routes,
        "authorize_run_access",
        lambda claims, runid: (_ for _ in ()).throw(
            schema_defaults_routes.AuthError("run access denied", status_code=403, code="forbidden")
        ),
    )
    load_calls = {"count": 0}

    def _never_load(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        load_calls["count"] += 1
        return _sample_runtime()

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _never_load)

    with TestClient(rq_engine.app) as client:
        response = client.get(CONTROLLERS_PATH)

    assert response.status_code == 403
    _assert_canonical_error(response.json(), code="forbidden")
    assert load_calls["count"] == 0


def test_list_controllers_payload_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(CONTROLLERS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_domain",
        "run_state_revision",
        "run_state_vector",
        "runid",
        "config",
        "active_mods",
        "endpoints_url",
        "pipeline_url",
        "readiness_url",
        "outputs_url",
        "controllers",
    }
    assert payload["runid"] == RUNID
    assert payload["config"] == CONFIG
    assert payload["active_mods"] == ["disturbed", "wepp"]
    assert payload["run_state_domain"] == "metadata"
    assert payload["run_state_revision"].startswith("runstate:run-1:")
    assert payload["run_state_vector"] == {
        "orchestration_revision": None,
        "metadata_revision": payload["run_state_revision"],
        "outputs_revision": None,
    }

    controllers = payload["controllers"]
    assert controllers
    names = {entry["name"] for entry in controllers}
    assert {"climate", "landuse", "soils", "watershed", "wepp"}.issubset(names)
    assert "disturbed" in names

    climate = next(entry for entry in controllers if entry["name"] == "climate")
    assert set(climate) == {
        "name",
        "enabled",
        "schema_url",
        "hints_url",
        "templates_url",
        "capabilities",
    }
    assert climate["enabled"] is True
    assert climate["capabilities"] == {"schema": True, "hints": True, "templates": True}


def test_controller_schema_hints_templates_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(CONTROLLER_SCHEMA_PATH)
        assert schema_response.status_code == 200
        schema_payload = schema_response.json()
        assert set(schema_payload) == {
            "contract_version",
            "deployment_revision",
            "run_state_domain",
            "run_state_revision",
            "run_state_vector",
            "controller",
            "schema_version",
            "fields",
        }
        assert schema_payload["run_state_domain"] == "metadata"
        assert schema_payload["controller"] == "climate"
        fields = schema_payload["fields"]
        assert fields["climate_mode"]["enum"] == [0, 2, 3, 5, 6, 11]
        assert fields["climate_mode"]["constraint_mode"] == "run_resolved"
        assert fields["climatestation"]["available_if"] == {"field": "climate_mode", "op": "in", "value": [2, 6]}
        assert fields["climatestation"]["required_if"] == {"field": "climate_mode", "op": "in", "value": [2, 6]}
        assert fields["observed_start_year"]["required_if"] == {"field": "climate_mode", "op": "in", "value": [2, 11]}
        assert fields["observed_end_year"]["required_if"] == {"field": "climate_mode", "op": "in", "value": [2, 11]}
        assert fields["future_start_year"]["required_if"] == {"field": "climate_mode", "op": "eq", "value": 3}
        assert fields["future_end_year"]["required_if"] == {"field": "climate_mode", "op": "eq", "value": 3}

        hints_response = client.get(CONTROLLER_HINTS_PATH)
        assert hints_response.status_code == 200
        hints_payload = hints_response.json()
        assert set(hints_payload) == {
            "contract_version",
            "deployment_revision",
            "run_state_domain",
            "run_state_revision",
            "run_state_vector",
            "controller",
            "schema_version",
            "hints",
        }
        assert hints_payload["run_state_domain"] == "metadata"
        assert "context_fields" in hints_payload["hints"]
        assert "groups" in hints_payload["hints"]
        assert "field_hints" in hints_payload["hints"]

        templates_response = client.get(CONTROLLER_TEMPLATES_PATH)
        assert templates_response.status_code == 200
        templates_payload = templates_response.json()
        assert set(templates_payload) == {
            "contract_version",
            "deployment_revision",
            "run_state_domain",
            "run_state_revision",
            "run_state_vector",
            "controller",
            "templates",
            "run_resolved_defaults",
        }
        assert templates_payload["run_state_domain"] == "metadata"
        assert templates_payload["controller"] == "climate"
        assert isinstance(templates_payload["templates"], list)
        assert templates_payload["templates"]
        assert isinstance(templates_payload["run_resolved_defaults"], dict)


def test_controller_routes_return_404_for_unknown_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        for suffix in ("schema", "hints", "templates"):
            response = client.get(f"/api/runs/{RUNID}/{CONFIG}/controllers/unknown/{suffix}")
            assert response.status_code == 404
            _assert_canonical_error(response.json(), code="not_found")


def test_list_run_endpoints_payload_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINTS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_domain",
        "run_state_revision",
        "run_state_vector",
        "operations",
    }
    assert payload["run_state_domain"] == "metadata"

    operations = payload["operations"]
    assert operations
    operation_ids = {operation["operation_id"] for operation in operations}
    assert {
        "rq_engine_list_controllers",
        "rq_engine_get_landuse_state",
        "rq_engine_get_controller_schema",
        "rq_engine_get_controller_hints",
        "rq_engine_get_controller_templates",
        "rq_engine_list_run_endpoints",
        "rq_engine_get_run_endpoint_schema",
        "rq_engine_get_run_endpoint_defaults",
        "rq_engine_fetch_dem_and_build_channels",
        "rq_engine_set_outlet",
        "rq_engine_build_subcatchments_and_abstract_watershed",
        "rq_engine_build_climate",
        "rq_engine_build_landuse",
        "rq_engine_set_landuse_mode",
        "rq_engine_set_landuse_db",
        "rq_engine_modify_landuse_coverage",
        "rq_engine_modify_landuse_mapping",
        "rq_engine_get_landuse_user_defined_catalog",
        "rq_engine_upload_landuse_user_defined_managements",
        "rq_engine_delete_landuse_user_defined_management",
        "rq_engine_update_landuse_user_defined_management_description",
        "rq_engine_get_landuse_map_snapshot",
        "rq_engine_save_landuse_map",
        "rq_engine_clear_landuse_map_override",
        "rq_engine_modify_landuse",
        "rq_engine_build_rusle",
        "rq_engine_fork_project",
        "rq_engine_run_wepp",
    }.issubset(operation_ids)

    run_wepp_descriptor = next(
        operation for operation in operations if operation["operation_id"] == "rq_engine_run_wepp"
    )
    assert run_wepp_descriptor["run_scoped"] is True
    assert run_wepp_descriptor["execution_mode"] == "async"
    assert run_wepp_descriptor["returns_job"] is True
    assert run_wepp_descriptor["result_contract"]["kind"] == "async_job"


def test_run_endpoint_schema_and_defaults_payload_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(RUN_ENDPOINT_SCHEMA_PATH)
        assert schema_response.status_code == 200
        schema_payload = schema_response.json()
        assert set(schema_payload) == {
            "contract_version",
            "deployment_revision",
            "run_state_domain",
            "run_state_revision",
            "run_state_vector",
            "operation_id",
            "run_scoped",
            "method",
            "path",
            "operation_descriptor",
            "schema_version",
            "request",
            "responses",
        }
        assert schema_payload["run_state_domain"] == "metadata"
        assert schema_payload["operation_id"] == "rq_engine_run_wepp"
        assert schema_payload["operation_descriptor"]["operation_id"] == "rq_engine_run_wepp"

        request_fields = schema_payload["request"]["properties"]
        assert request_fields["clip_soils"]["constraint_mode"] == "static"
        assert request_fields["clip_soils_depth"]["constraint_mode"] == "static"
        assert request_fields["initial_sat"]["constraint_mode"] == "static"

        defaults_response = client.get(RUN_ENDPOINT_DEFAULTS_PATH)
        assert defaults_response.status_code == 200
        defaults_payload = defaults_response.json()
        assert set(defaults_payload) == {
            "contract_version",
            "deployment_revision",
            "run_state_domain",
            "run_state_revision",
            "run_state_vector",
            "operation_id",
            "resolved_defaults",
            "defaults_context",
            "computed_at",
        }
        assert defaults_payload["run_state_domain"] == "metadata"
        assert defaults_payload["operation_id"] == "rq_engine_run_wepp"
        assert defaults_payload["resolved_defaults"] == {
            "clip_soils": True,
            "clip_soils_depth": 25.0,
        }
        assert defaults_payload["defaults_context"] == {
            "config": CONFIG,
            "active_mods": ["disturbed", "wepp"],
            "region": "conus",
        }
        assert UTC_TIMESTAMP_RE.match(defaults_payload["computed_at"])


def test_watershed_mutation_operations_are_discoverable_with_schema_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(),
    )

    operation_ids = (
        "rq_engine_fetch_dem_and_build_channels",
        "rq_engine_set_outlet",
        "rq_engine_build_subcatchments_and_abstract_watershed",
    )

    with TestClient(rq_engine.app) as client:
        endpoints_response = client.get(RUN_ENDPOINTS_PATH)
        assert endpoints_response.status_code == 200
        listed_ids = {operation["operation_id"] for operation in endpoints_response.json()["operations"]}
        for operation_id in operation_ids:
            assert operation_id in listed_ids

            schema_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/schema")
            assert schema_response.status_code == 200
            schema_payload = schema_response.json()
            assert schema_payload["operation_id"] == operation_id
            assert schema_payload["operation_descriptor"]["returns_job"] is True
            assert schema_payload["responses"]["success"]["required"] == ["job_id"]

            defaults_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/defaults")
            assert defaults_response.status_code == 200
            defaults_payload = defaults_response.json()
            assert defaults_payload["operation_id"] == operation_id
            assert defaults_payload["defaults_context"]["config"] == CONFIG


def test_landuse_operations_are_discoverable_with_schema_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(),
    )

    operation_ids = (
        "rq_engine_get_landuse_state",
        "rq_engine_build_landuse",
        "rq_engine_set_landuse_mode",
        "rq_engine_set_landuse_db",
        "rq_engine_modify_landuse_coverage",
        "rq_engine_modify_landuse_mapping",
        "rq_engine_get_landuse_user_defined_catalog",
        "rq_engine_upload_landuse_user_defined_managements",
        "rq_engine_delete_landuse_user_defined_management",
        "rq_engine_update_landuse_user_defined_management_description",
        "rq_engine_get_landuse_map_snapshot",
        "rq_engine_save_landuse_map",
        "rq_engine_clear_landuse_map_override",
        "rq_engine_modify_landuse",
    )

    with TestClient(rq_engine.app) as client:
        endpoints_response = client.get(RUN_ENDPOINTS_PATH)
        assert endpoints_response.status_code == 200
        listed_ids = {operation["operation_id"] for operation in endpoints_response.json()["operations"]}
        for operation_id in operation_ids:
            assert operation_id in listed_ids

            schema_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/schema")
            assert schema_response.status_code == 200
            schema_payload = schema_response.json()
            assert schema_payload["operation_id"] == operation_id

            defaults_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/defaults")
            assert defaults_response.status_code == 200
            defaults_payload = defaults_response.json()
            assert defaults_payload["operation_id"] == operation_id


def test_fetch_dem_and_build_channels_schema_marks_bounds_required_for_modes_0_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(
            f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_fetch_dem_and_build_channels/schema"
        )

    assert response.status_code == 200
    payload = response.json()
    request_fields = payload["request"]["properties"]
    assert request_fields["map_bounds"]["required_if"] == {
        "field": "set_extent_mode",
        "op": "in",
        "value": [0, 1],
    }
    assert request_fields["map_center"]["derived_if_missing"]["field"] == "map_bounds"
    assert request_fields["map_zoom"]["derived_if_missing"]["field"] == "map_bounds"
    assert "mcl" in payload["request"]["required"]
    assert "csa" in payload["request"]["required"]


def test_run_endpoint_schema_and_defaults_exist_for_each_listed_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        list_response = client.get(RUN_ENDPOINTS_PATH)
        assert list_response.status_code == 200
        operations = list_response.json()["operations"]
        assert operations

        for operation in operations:
            operation_id = operation["operation_id"]
            schema_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/schema")
            assert schema_response.status_code == 200, operation_id
            schema_payload = schema_response.json()
            assert schema_payload["operation_id"] == operation_id
            assert schema_payload["operation_descriptor"]["operation_id"] == operation_id
            assert schema_payload["path"] == operation["path"]
            assert isinstance(schema_payload["request"]["properties"], dict)

            defaults_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/defaults")
            assert defaults_response.status_code == 200, operation_id
            defaults_payload = defaults_response.json()
            assert defaults_payload["operation_id"] == operation_id
            defaults_context = defaults_payload["defaults_context"]
            assert defaults_context["config"] == CONFIG
            assert defaults_context["active_mods"] == ["disturbed", "wepp"]
            assert defaults_context["region"] == "conus"


def test_build_climate_defaults_emit_integer_climate_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_climate/defaults")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["resolved_defaults"]["climate_mode"], int)
    assert payload["resolved_defaults"]["climate_mode"] == 11


def test_build_climate_defaults_switch_to_future_years_for_future_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    runtime = _sample_runtime()
    runtime.states["climate_mode_code"] = 3
    runtime.states["climate_mode"] = "future"
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: runtime)

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_climate/defaults")

    assert response.status_code == 200
    resolved_defaults = response.json()["resolved_defaults"]
    assert resolved_defaults["climate_mode"] == 3
    assert resolved_defaults["future_start_year"] == 2040
    assert resolved_defaults["future_end_year"] == 2060
    assert "observed_start_year" not in resolved_defaults
    assert "observed_end_year" not in resolved_defaults


def test_build_climate_schema_includes_future_window_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_climate/schema")

    assert response.status_code == 200
    payload = response.json()
    request_fields = payload["request"]["properties"]
    assert request_fields["climate_mode"]["enum"] == [0, 2, 3, 5, 6, 11]
    assert request_fields["observed_start_year"]["required_if"] == {
        "field": "climate_mode",
        "op": "in",
        "value": [2, 11],
    }
    assert request_fields["future_start_year"]["required_if"] == {
        "field": "climate_mode",
        "op": "eq",
        "value": 3,
    }
    assert request_fields["future_end_year"]["required_if"] == {
        "field": "climate_mode",
        "op": "eq",
        "value": 3,
    }


def test_controller_schema_does_not_expose_unknown_runtime_climate_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    runtime = _sample_runtime()
    runtime.states["climate_mode_code"] = 999
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: runtime)

    with TestClient(rq_engine.app) as client:
        response = client.get(CONTROLLER_SCHEMA_PATH)

    assert response.status_code == 200
    enum_available = response.json()["fields"]["climate_mode"]["enum_available"]
    assert 999 not in enum_available


def test_list_run_endpoints_can_include_operation_docs_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"{RUN_ENDPOINTS_PATH}?include_operation_docs=true")

    assert response.status_code == 200
    payload = response.json()
    assert "operation_docs" in payload
    operation_docs = payload["operation_docs"]
    assert isinstance(operation_docs, dict)
    assert "rq_engine_build_climate" in operation_docs

    climate_doc = operation_docs["rq_engine_build_climate"]
    assert climate_doc["operation_descriptor"]["operation_id"] == "rq_engine_build_climate"
    assert "resolved_defaults" in climate_doc
    assert "defaults_context" in climate_doc
    assert "computed_at" in climate_doc
    assert isinstance(climate_doc["errors"], list)


def test_list_run_endpoints_rejects_invalid_include_operation_docs_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"{RUN_ENDPOINTS_PATH}?include_operation_docs=maybe")

    assert response.status_code == 422
    payload = response.json()
    assert isinstance(payload.get("detail"), list)
    assert any(
        isinstance(item, dict) and item.get("loc", [None])[-1] == "include_operation_docs"
        for item in payload["detail"]
    )


def test_build_soils_schema_and_defaults_require_disturbed_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(BUILD_SOILS_SCHEMA_PATH)
        assert schema_response.status_code == 200
        schema_payload = schema_response.json()
        assert schema_payload["operation_id"] == "rq_engine_build_soils"
        assert schema_payload["request"]["required"] == ["initial_sat", "sol_ver"]

        request_fields = schema_payload["request"]["properties"]
        assert request_fields["initial_sat"]["constraint_mode"] == "static"
        assert request_fields["sol_ver"]["constraint_mode"] == "run_resolved"
        assert request_fields["sol_ver"]["constraint_source"] == "controller_state"
        assert request_fields["sol_ver"]["required_if"]["field"] == "context.active_mods"
        assert request_fields["sol_ver"]["required_if"]["op"] == "contains"
        assert request_fields["sol_ver"]["required_if"]["value"] == "disturbed"
        assert 2018.0 in request_fields["sol_ver"]["enum_available"]
        assert 9002.0 in request_fields["sol_ver"]["enum_available"]

        defaults_response = client.get(BUILD_SOILS_DEFAULTS_PATH)
        assert defaults_response.status_code == 200
        defaults_payload = defaults_response.json()
        assert defaults_payload["operation_id"] == "rq_engine_build_soils"
        assert defaults_payload["resolved_defaults"]["initial_sat"] == 0.75
        assert defaults_payload["resolved_defaults"]["sol_ver"] == 2018.0


def test_build_soils_defaults_omit_sol_ver_when_disturbed_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(
            active_mods=("wepp",),
            disturbed_enabled=False,
            sbs_upload_supported=False,
            initial_sat=0.71,
        ),
    )

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(BUILD_SOILS_SCHEMA_PATH)
        defaults_response = client.get(BUILD_SOILS_DEFAULTS_PATH)

    assert schema_response.status_code == 200
    schema_payload = schema_response.json()
    assert schema_payload["request"]["required"] == ["initial_sat"]

    assert defaults_response.status_code == 200
    defaults_payload = defaults_response.json()
    assert defaults_payload["resolved_defaults"] == {"initial_sat": 0.71}


def test_build_soils_defaults_fall_back_to_initial_sat_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(initial_sat=None),
    )

    with TestClient(rq_engine.app) as client:
        defaults_response = client.get(BUILD_SOILS_DEFAULTS_PATH)

    assert defaults_response.status_code == 200
    defaults_payload = defaults_response.json()
    assert defaults_payload["resolved_defaults"]["initial_sat"] == 0.75


def test_build_soils_defaults_infer_sol_ver_from_disturbed9002_config_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(disturbed_sol_ver=None),
    )

    with TestClient(rq_engine.app) as client:
        defaults_response = client.get(BUILD_SOILS_DEFAULTS_PATH)

    assert defaults_response.status_code == 200
    defaults_payload = defaults_response.json()
    assert defaults_payload["resolved_defaults"]["sol_ver"] == 9002.0


def test_build_rusle_schema_and_defaults_include_rock_fraction_partition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(BUILD_RUSLE_SCHEMA_PATH)
        defaults_response = client.get(BUILD_RUSLE_DEFAULTS_PATH)

    assert schema_response.status_code == 200
    schema_payload = schema_response.json()
    request_properties = schema_payload["request"]["properties"]
    assert request_properties["rock_fraction_of_rap_bare"]["type"] == "string_or_number"
    assert request_properties["rock_fraction_of_rap_bare"]["constraint_mode"] == "static"
    assert request_properties["rock_fraction_of_rap_bare"]["one_of"] == [
        {"type": "string", "enum": ["auto"]},
        {"type": "number", "minimum": 0.0, "maximum": 1.0},
    ]
    assert request_properties["rock_fraction_of_rap_bare"]["available_if"] == {
        "field": "c_mode",
        "op": "eq",
        "value": "observed_rap",
    }
    assert request_properties["rock_fraction_of_sbs_bare"]["type"] == "string_or_number"
    assert request_properties["rock_fraction_of_sbs_bare"]["constraint_mode"] == "static"
    assert request_properties["rock_fraction_of_sbs_bare"]["one_of"] == [
        {"type": "string", "enum": ["auto"]},
        {"type": "number", "minimum": 0.0, "maximum": 1.0},
    ]
    assert request_properties["rock_fraction_of_sbs_bare"]["available_if"] == {
        "field": "c_mode",
        "op": "eq",
        "value": "scenario_sbs",
    }

    assert defaults_response.status_code == 200
    defaults_payload = defaults_response.json()
    assert defaults_payload["resolved_defaults"]["force_polaris_refresh"] is False
    assert defaults_payload["resolved_defaults"]["rock_fraction_of_rap_bare"] == "auto"
    assert defaults_payload["resolved_defaults"]["rock_fraction_of_sbs_bare"] == "auto"


def test_run_endpoints_include_upload_sbs_for_baer_mod(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(
            active_mods=("baer", "wepp"),
            disturbed_enabled=False,
            sbs_upload_supported=True,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINTS_PATH)

    assert response.status_code == 200
    operation_ids = {operation["operation_id"] for operation in response.json()["operations"]}
    assert "rq_engine_upload_sbs" in operation_ids
    assert "rq_engine_build_rusle" in operation_ids


def test_fork_endpoint_schema_and_defaults_include_skip_wepp_runs_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(FORK_SCHEMA_PATH)
        defaults_response = client.get(FORK_DEFAULTS_PATH)

    assert schema_response.status_code == 200
    schema_payload = schema_response.json()
    request_properties = schema_payload["request"]["properties"]
    assert request_properties["skip_wepp_runs_output"]["type"] == "boolean"
    assert request_properties["skip_wepp_runs_output"]["constraint_mode"] == "static"
    assert "skip_wepp_runs_output" in schema_payload["responses"]["success"]["required"]

    assert defaults_response.status_code == 200
    defaults_payload = defaults_response.json()
    assert defaults_payload["resolved_defaults"]["undisturbify"] is False
    assert defaults_payload["resolved_defaults"]["skip_wepp_runs_output"] is False


def test_run_endpoints_omit_upload_sbs_when_fire_mods_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(
            active_mods=("wepp",),
            disturbed_enabled=False,
            sbs_upload_supported=False,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINTS_PATH)

    assert response.status_code == 200
    operation_ids = {operation["operation_id"] for operation in response.json()["operations"]}
    assert "rq_engine_upload_sbs" not in operation_ids
    assert "rq_engine_build_rusle" not in operation_ids
    assert "rq_engine_fork_project" in operation_ids


def test_run_endpoint_errors_exist_for_each_listed_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        list_response = client.get(RUN_ENDPOINTS_PATH)
        assert list_response.status_code == 200
        operations = list_response.json()["operations"]

        for operation in operations:
            operation_id = operation["operation_id"]
            errors_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/errors")
            assert errors_response.status_code == 200, operation_id
            payload = errors_response.json()
            assert payload["operation_id"] == operation_id
            assert isinstance(payload["errors"], list)


@pytest.mark.parametrize(
    "operation_id",
    [
        "rq_engine_run_wepp",
        "rq_engine_run_wepp_watershed",
    ],
)
def test_wepp_run_endpoint_errors_include_invalid_abstraction_recovery(
    monkeypatch: pytest.MonkeyPatch,
    operation_id: str,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_runtime(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(
            f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/errors"
        )

    assert response.status_code == 200
    invalid_state_errors = [
        error
        for error in response.json()["errors"]
        if error["error_code"] == "invalid_watershed_abstraction_state"
    ]
    assert invalid_state_errors == [
        {
            "error_code": "invalid_watershed_abstraction_state",
            "recoverable": True,
            "http_statuses": [409],
            "recovery_actions": [
                {
                    "operation_id": "rq_engine_build_subcatchments_and_abstract_watershed",
                    "required_fields": [],
                }
            ],
            "recovery_notes": [
                "This recovery action enqueues subcatchment rebuild work only "
                "outside batch/_base contexts. Batch/_base callers must "
                "materialize watershed.subwta through their normal setup flow "
                "before retrying run-wepp endpoints."
            ],
        }
    ]


def test_readiness_ready_operations_are_discoverable_in_run_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(orchestration_read_routes, "require_jwt", lambda request: {"scope": "rq:status"})
    monkeypatch.setattr(orchestration_read_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())
    monkeypatch.setattr(
        orchestration_read_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_orchestration_runtime_for_discovery_parity(),
    )

    with TestClient(rq_engine.app) as client:
        readiness_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/readiness")
        endpoints_response = client.get(RUN_ENDPOINTS_PATH)

        assert readiness_response.status_code == 200
        assert endpoints_response.status_code == 200

        ready_operation_ids = [entry["operation_id"] for entry in readiness_response.json()["ready_operations"]]
        endpoint_operation_ids = {operation["operation_id"] for operation in endpoints_response.json()["operations"]}

        for operation_id in ready_operation_ids:
            assert operation_id in endpoint_operation_ids, operation_id
            for suffix in ("schema", "defaults", "errors"):
                detail_response = client.get(
                    f"/api/runs/{RUNID}/{CONFIG}/endpoints/{operation_id}/{suffix}"
                )
                assert detail_response.status_code == 200, f"{operation_id}/{suffix}"


def test_run_endpoint_detail_routes_return_404_for_unknown_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    with TestClient(rq_engine.app) as client:
        for suffix in ("schema", "defaults"):
            response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_unknown/{suffix}")
            assert response.status_code == 404
            _assert_canonical_error(response.json(), code="not_found")


def test_schema_defaults_routes_return_404_for_unknown_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _missing(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        raise FileNotFoundError("missing run")

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _missing)

    with TestClient(rq_engine.app) as client:
        response = client.get(CONTROLLERS_PATH)

    assert response.status_code == 404
    _assert_canonical_error(response.json(), code="not_found")


def test_schema_defaults_routes_return_404_for_config_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _mismatch(runid: str, config: str) -> schema_defaults_routes.RuntimeState:
        raise schema_defaults_routes.RunConfigMismatchError("mismatch")

    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", _mismatch)

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINTS_PATH)

    assert response.status_code == 404
    _assert_canonical_error(response.json(), code="not_found")


@pytest.mark.parametrize(
    "path,patched",
    (
        (CONTROLLERS_PATH, "_controller_catalog"),
        (CONTROLLER_SCHEMA_PATH, "_controller_schema"),
        (CONTROLLER_HINTS_PATH, "_controller_hints"),
        (CONTROLLER_TEMPLATES_PATH, "_controller_templates"),
        (RUN_ENDPOINTS_PATH, "_build_run_operations"),
        (RUN_ENDPOINT_SCHEMA_PATH, "_build_run_operations"),
        (RUN_ENDPOINT_DEFAULTS_PATH, "_build_run_operations"),
    ),
)
def test_schema_defaults_route_internal_errors_return_canonical_500(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    patched: str,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_runtime())

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(schema_defaults_routes, patched, _boom)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get(path)

    assert response.status_code == 500
    _assert_canonical_error(response.json())
