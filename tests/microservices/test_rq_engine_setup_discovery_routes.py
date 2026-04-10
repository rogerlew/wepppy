from __future__ import annotations

import re
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import setup_discovery_routes

pytestmark = pytest.mark.microservice

UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SETUP_DISCOVERY_PATHS = (
    "/api/configs",
    "/api/configs/disturbed9002_wbt",
    "/api/endpoints",
    "/api/endpoints/rq_engine_create/schema",
    "/api/endpoints/rq_engine_create/defaults",
    "/api/endpoints/rq_engine_create/errors",
)


def _stub_auth(monkeypatch: pytest.MonkeyPatch, scope: str, *, token_class: str = "service") -> None:
    monkeypatch.setattr(
        setup_discovery_routes,
        "require_jwt",
        lambda request: {"sub": "7", "token_class": token_class, "scope": scope},
    )


def _assert_canonical_error(payload: dict[str, Any], *, code: str | None = None) -> None:
    assert set(payload).issuperset({"error"})
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["error"].get("message"), str)
    assert isinstance(payload["error"].get("details"), str)
    if code is not None:
        assert payload["error"].get("code") == code


@pytest.mark.parametrize("path", SETUP_DISCOVERY_PATHS)
def test_setup_discovery_routes_require_auth(path: str) -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get(path)

    assert response.status_code == 401
    _assert_canonical_error(response.json(), code="unauthorized")


@pytest.mark.parametrize("path", SETUP_DISCOVERY_PATHS)
def test_setup_discovery_routes_reject_wrong_scope(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    _stub_auth(monkeypatch, "rq:enqueue")

    with TestClient(rq_engine.app) as client:
        response = client.get(path)

    assert response.status_code == 403
    payload = response.json()
    _assert_canonical_error(payload, code="forbidden")
    message = payload["error"]["message"]
    assert "rq:read" in message and "rq:status" in message


@pytest.mark.parametrize("scope", ("rq:status", "rq:read"))
def test_setup_discovery_routes_accept_supported_scopes(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    _stub_auth(monkeypatch, scope)

    with TestClient(rq_engine.app) as client:
        config_catalog = client.get("/api/configs")
        assert config_catalog.status_code == 200
        config_id = config_catalog.json()["configs"][0]["config_id"]

        paths = (
            "/api/configs",
            f"/api/configs/{config_id}",
            "/api/endpoints",
            "/api/endpoints/rq_engine_create/schema",
            "/api/endpoints/rq_engine_create/defaults",
            "/api/endpoints/rq_engine_create/errors",
        )
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200, path


def test_list_configs_payload_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/configs")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"contract_version", "deployment_revision", "configs"}
    assert isinstance(payload["contract_version"], str)
    assert isinstance(payload["deployment_revision"], str)
    assert isinstance(payload["configs"], list)
    assert payload["configs"]

    first_config = payload["configs"][0]
    assert set(first_config) == {
        "config_id",
        "display_name",
        "active_mods",
        "supported_regions",
        "required_upload_steps",
        "recommended_for",
    }
    assert isinstance(first_config["config_id"], str)
    assert isinstance(first_config["display_name"], str)
    assert isinstance(first_config["active_mods"], list)
    assert isinstance(first_config["supported_regions"], list)
    assert isinstance(first_config["required_upload_steps"], list)
    assert isinstance(first_config["recommended_for"], list)


def test_get_config_returns_entry_and_404(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    with TestClient(rq_engine.app) as client:
        catalog = client.get("/api/configs").json()["configs"]
        config_id = catalog[0]["config_id"]

        response = client.get(f"/api/configs/{config_id}")
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"contract_version", "deployment_revision", "config"}
        assert set(payload["config"]) == {
            "config_id",
            "display_name",
            "active_mods",
            "supported_regions",
            "required_upload_steps",
            "recommended_for",
        }
        assert payload["config"]["config_id"] == config_id

        missing = client.get("/api/configs/does-not-exist")
        assert missing.status_code == 404
        _assert_canonical_error(missing.json(), code="not_found")


def test_setup_catalog_includes_create_and_expected_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/endpoints")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"contract_version", "deployment_revision", "operations"}
    operations = payload["operations"]
    assert operations
    operation_ids = {operation["operation_id"] for operation in operations}
    assert all(operation_id.startswith("rq_engine_") for operation_id in operation_ids)

    expected_ids = {
        "rq_engine_list_configs",
        "rq_engine_get_config",
        "rq_engine_create",
        "rq_engine_list_setup_endpoints",
        "rq_engine_get_setup_endpoint_schema",
        "rq_engine_get_setup_endpoint_defaults",
        "rq_engine_get_setup_endpoint_errors",
    }
    assert expected_ids.issubset(operation_ids)

    create_operation = next(operation for operation in operations if operation["operation_id"] == "rq_engine_create")
    assert create_operation["config_catalog_url"] == "/api/configs"
    assert set(create_operation["accepted_auth"]) == {
        "rq_token",
        "bearer_jwt",
        "session_cookie_same_origin",
        "captcha",
    }
    idempotency_policy = create_operation["idempotency_policy"]
    assert idempotency_policy["supported"] is False
    assert idempotency_policy["key_locations"] == []
    assert create_operation["response_mode"] == "redirect"
    assert create_operation["success_status_codes"] == [303]
    result_contract = create_operation["result_contract"]
    assert result_contract["kind"] == "sync_redirect"
    assert result_contract["required_response_fields"] == []
    assert result_contract["location_header_required"] is True


def test_setup_operation_schema_defaults_and_errors_for_create(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    operation_id = "rq_engine_create"

    with TestClient(rq_engine.app) as client:
        schema_response = client.get(f"/api/endpoints/{operation_id}/schema")
        assert schema_response.status_code == 200
        schema_payload = schema_response.json()
        assert set(schema_payload) == {
            "contract_version",
            "deployment_revision",
            "operation_id",
            "run_scoped",
            "method",
            "path",
            "operation_descriptor",
            "schema_version",
            "request",
            "responses",
        }
        assert schema_payload["operation_id"] == operation_id
        assert schema_payload["operation_descriptor"]["operation_id"] == operation_id
        assert schema_payload["responses"]["success"]["required"] == []
        assert schema_payload["responses"]["success"]["location_header_required"] is True

        config_field = schema_payload["request"]["properties"]["config"]
        assert config_field["dynamic_enum_from"] == "/api/configs"
        assert config_field["enum"]

        defaults_response = client.get(f"/api/endpoints/{operation_id}/defaults")
        assert defaults_response.status_code == 200
        defaults_payload = defaults_response.json()
        assert set(defaults_payload) == {
            "contract_version",
            "deployment_revision",
            "operation_id",
            "resolved_defaults",
            "defaults_context",
            "computed_at",
        }
        assert defaults_payload["operation_id"] == operation_id
        assert isinstance(defaults_payload["resolved_defaults"], dict)
        assert isinstance(defaults_payload["defaults_context"], dict)
        assert isinstance(defaults_payload["computed_at"], str)
        assert UTC_TIMESTAMP_RE.match(defaults_payload["computed_at"])

        errors_response = client.get(f"/api/endpoints/{operation_id}/errors")
        assert errors_response.status_code == 200
        errors_payload = errors_response.json()
        assert set(errors_payload) == {"contract_version", "deployment_revision", "operation_id", "errors"}
        assert errors_payload["operation_id"] == operation_id
        error_codes = {entry["error_code"] for entry in errors_payload["errors"]}
        assert {"validation_error", "captcha_required"}.issubset(error_codes)


def test_setup_operation_detail_routes_return_404_for_unknown_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")

    with TestClient(rq_engine.app) as client:
        for suffix in ("schema", "defaults", "errors"):
            response = client.get(f"/api/endpoints/rq_engine_unknown/{suffix}")
            assert response.status_code == 404
            _assert_canonical_error(response.json(), code="not_found")


def test_setup_operation_error_catalog_uses_runtime_not_found_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    with TestClient(rq_engine.app) as client:
        config_errors = client.get("/api/endpoints/rq_engine_get_config/errors").json()["errors"]
        assert any(error["error_code"] == "not_found" for error in config_errors)
        schema_errors = client.get("/api/endpoints/rq_engine_get_setup_endpoint_schema/errors").json()["errors"]
        assert any(error["error_code"] == "not_found" for error in schema_errors)
        defaults_errors = client.get("/api/endpoints/rq_engine_get_setup_endpoint_defaults/errors").json()["errors"]
        assert any(error["error_code"] == "not_found" for error in defaults_errors)
        operation_errors = client.get("/api/endpoints/rq_engine_get_setup_endpoint_errors/errors").json()["errors"]
        assert any(error["error_code"] == "not_found" for error in operation_errors)


def test_get_config_internal_error_returns_canonical_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _boom() -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(setup_discovery_routes, "_config_lookup", _boom)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get("/api/configs/disturbed9002_wbt")

    assert response.status_code == 500
    _assert_canonical_error(response.json())


def test_list_setup_endpoints_internal_error_returns_canonical_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _boom() -> dict[str, dict[str, Any]]:
        raise RuntimeError("boom")

    monkeypatch.setattr(setup_discovery_routes, "_setup_operation_registry", _boom)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get("/api/endpoints")

    assert response.status_code == 500
    _assert_canonical_error(response.json())


@pytest.mark.parametrize(
    "path,patched",
    (
        ("/api/endpoints/rq_engine_create/schema", "_resolve_operation_descriptor"),
        ("/api/endpoints/rq_engine_create/schema", "_resolve_operation_docs"),
        ("/api/endpoints/rq_engine_create/defaults", "_resolve_operation_descriptor"),
        ("/api/endpoints/rq_engine_create/defaults", "_resolve_operation_docs"),
        ("/api/endpoints/rq_engine_create/errors", "_resolve_operation_descriptor"),
        ("/api/endpoints/rq_engine_create/errors", "_resolve_operation_docs"),
    ),
)
def test_setup_operation_detail_internal_errors_return_canonical_500(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    patched: str,
) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(setup_discovery_routes, patched, _boom)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        response = client.get(path)

    assert response.status_code == 500
    _assert_canonical_error(response.json())
