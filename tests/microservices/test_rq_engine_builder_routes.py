from __future__ import annotations

import json
from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient
import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import builder_routes
from wepppy.weppcloud.user_preferences import CreationActor
from wepp_runner.wepp_runner import get_linux_wepp_bin_opts
from wepppy.project_config_serialization import parse_config_text

pytestmark = pytest.mark.microservice


class FakeRedis:
    def __init__(self): self.values = {}
    def set(self, key, value, *, nx=False, xx=False, ex=0):
        if nx and key in self.values: return False
        if xx and key not in self.values: return False
        self.values[key] = value; return True
    def get(self, key): return self.values.get(key)
    def delete(self, key): return int(self.values.pop(key, None) is not None)


def selections(**updates):
    value = {"locale": "continental-us", "dem": "usgs-ned13-2022", "delineation_backend": "wbt", "watershed_representation": "single-ofe", "wepp_binary": "wepp_260803", "soil": "ssurgo-gnatsgso-2025", "landuse": "nlcd-2019", "climate": "vanilla_cligen", "climate_station_database": "cligen-stations-2015", "mods": []}
    value.update(updates); return value


def request_body(**values):
    return {"builder_description_schema_version": 2, **values}


@pytest.fixture()
def client(monkeypatch, tmp_path: Path):
    claims = {"sub": "42", "roles": ["PowerUser"]}
    monkeypatch.setattr(builder_routes, "require_jwt", lambda *_a, **_k: claims)
    monkeypatch.setattr(builder_routes, "resolve_creation_actor", lambda _c: CreationActor(42, "user@example.com"))
    monkeypatch.setattr(builder_routes, "_create_run_dir", lambda _email: ("builder-run", str(tmp_path)))
    receipt = builder_routes.RunRegistrationReceipt(7, "builder-run", "config", 42)
    monkeypatch.setattr(builder_routes, "register_owned_run", lambda *_a: receipt)
    monkeypatch.setattr(builder_routes, "delete_registered_run", lambda *_a: None)
    monkeypatch.setattr(builder_routes, "ensure_readme_on_create", lambda *_a: None)
    monkeypatch.setattr("wepppy.weppcloud.utils.run_ttl.initialize_ttl", lambda *_a: None)
    idempotency = FakeRedis()
    monkeypatch.setattr(builder_routes, "_creation_idempotency_client", lambda: idempotency)
    monkeypatch.setattr(builder_routes, "Ron", lambda wd, cfg: (wd, cfg))
    with TestClient(rq_engine.app) as value:
        yield value, claims, tmp_path, idempotency


def test_description_and_validation_share_revision(client) -> None:
    http, _claims, _path, _idempotency = client
    description = http.get("/api/project-config/builder")
    assert description.status_code == 200
    body = description.json()
    assert body["config_token"] == "config"
    assert body["builder_description_schema_version"] == 2
    assert set(body["capability_graphs_by_locale"]) == {
        "continental-us", "europe", "canada", "australia", "global-earth"
    }
    assert set(body["components_by_locale"]) == set(body["capability_graphs_by_locale"])
    graph = body["capability_graph"]
    assert graph["capabilities"]["schema_version"] == 2
    assert graph["capabilities"]["locale_profiles"] == ["continental-us"]
    assert graph["capability_defaults"]["delineation_backend"] == "wbt"
    assert graph["capability_defaults"]["wepp_binary"] == "wepp_260803"
    locale = next(item for item in body["components"] if item["component_id"] == "continental-us")
    assert locale["constraints"]["allowed_dem"] == ["usgs-ned1-2024", "usgs-ned13-2022"]
    binaries = [
        item for item in body["components"] if item["kind"] == "wepp_binary"
    ]
    assert [item["component_id"] for item in binaries] == sorted(
        set(get_linux_wepp_bin_opts())
    )
    assert all(item["label"] == item["component_id"] for item in binaries)
    validated = http.post("/api/project-config/builder/validate", json=request_body(registry_revision=body["registry_revision"], selections=selections()))
    assert validated.status_code == 200
    assert validated.json()["registry_revision"] == body["registry_revision"]
    assert validated.json()["review"]["config_filename"] == "config.cfg"


def test_registry_failure_returns_diagnostic_details(client, monkeypatch) -> None:
    http, _claims, _path, _idempotency = client
    monkeypatch.setattr(
        builder_routes,
        "describe_builder",
        lambda: (_ for _ in ()).throw(builder_routes.RegistryError("missing binary role")),
    )

    response = http.get("/api/project-config/builder")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "message": "Builder registry is unavailable.",
        "details": "RegistryError: missing binary role",
        "code": "builder_registry_error",
    }


def test_owner_failure_returns_diagnostic_details(client, monkeypatch) -> None:
    http, _claims, _path, _idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    monkeypatch.setattr(
        builder_routes,
        "resolve_creation_actor",
        lambda _claims: (_ for _ in ()).throw(
            builder_routes.PreferenceIdentityError("Account identity is invalid.")
        ),
    )
    revision = http.get("/api/project-config/builder").json()["registry_revision"]

    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="12345678-1234-4234-9234-123456789abc",
            selections=selections(),
        ),
    )

    assert response.status_code == 500
    assert response.json()["error"]["details"] == (
        "PreferenceIdentityError: Account identity is invalid."
    )


def test_invalid_writer_configuration_is_diagnostic_server_error(client, monkeypatch) -> None:
    http, _claims, path, _idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "sometimes")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]

    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="writer-config-1234567890",
            selections=selections(),
        ),
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "builder_configuration_error"
    assert "strict boolean" in response.json()["error"]["details"]
    assert list(path.iterdir()) == []


def test_registry_value_error_is_not_misclassified_as_client_input(client, monkeypatch) -> None:
    http, _claims, path, _idempotency = client
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    monkeypatch.setattr(
        builder_routes,
        "load_registry",
        lambda: (_ for _ in ()).throw(ValueError("provider selector is incomplete")),
    )

    response = http.post(
        "/api/project-config/builder/validate",
        json=request_body(registry_revision=revision, selections=selections()),
    )

    assert response.status_code == 500
    assert response.json()["error"] == {
        "message": "Builder registry is unavailable.",
        "details": "ValueError: provider selector is incomplete",
        "code": "builder_registry_error",
    }
    assert list(path.iterdir()) == []


def test_stale_revision_and_ordinary_override_fail(client) -> None:
    http, claims, _path, _idempotency = client
    stale = http.post("/api/project-config/builder/validate", json=request_body(registry_revision="stale", selections=selections()))
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_builder_schema"
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    claims["roles"] = ["User"]
    forbidden = http.post("/api/project-config/builder/validate", json=request_body(registry_revision=revision, selections=selections(cellsize_override=30)))
    assert forbidden.status_code == 403


def test_enabled_creation_writes_fixed_pair(client, monkeypatch) -> None:
    http, _claims, path, _idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post("/api/project-config/builder/create", json=request_body(registry_revision=revision, creation_idempotency_key="12345678-1234-4234-9234-123456789abc", selections=selections()))
    assert response.status_code == 201
    assert response.json()["config_token"] == "config"
    assert (path / "config.cfg").is_file()
    assert (path / "config-manifest.json").is_file()


@pytest.mark.parametrize(
    ("profile_id", "profile_selections", "runtime_token"),
    (
        ("continental-us", {}, "us"),
        ("europe", {
            "dem": "europe-eudem-v1-1", "soil": "esdac-europe",
            "landuse": "corine-2018",
        }, "eu"),
        ("canada", {
            "dem": "copernicus-dem-30", "soil": "isric-global",
            "landuse": "c3s-landcover-2020",
        }, "canada"),
        ("australia", {
            "dem": "australia-srtm-1s", "soil": "asris-australia",
            "landuse": "australia-landuse-2010-2011",
        }, "au"),
        ("global-earth", {
            "dem": "copernicus-dem-30", "soil": "isric-global",
            "landuse": "c3s-landcover-2020",
        }, "earth"),
    ),
)
def test_writer_enabled_creation_resolves_each_locale_graph(
    client, monkeypatch, profile_id: str,
    profile_selections: dict[str, str], runtime_token: str,
) -> None:
    http, _claims, path, _idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    selected = selections(
        locale=profile_id,
        capability_profile=f"{profile_id}-capabilities",
        climate_station_database=(
            "cligen-stations-2015"
            if profile_id == "continental-us"
            else "cligen-stations-ghcn"
        ),
        **profile_selections,
    )

    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key=f"profile-{profile_id}-1234567890",
            selections=selected,
        ),
    )

    assert response.status_code == 201
    config = parse_config_text((path / "config.cfg").read_text(encoding="utf-8"))
    manifest = json.loads((path / "config-manifest.json").read_text(encoding="utf-8"))
    assert config["general"]["locales"] == [runtime_token]
    assert config["climate"]["cligen_db"] == (
        "2015_stations.db" if profile_id == "continental-us" else "ghcn_stations.db"
    )
    assert manifest["selections"]["locale"] == profile_id
    assert manifest["selections"]["climate"] == "vanilla_cligen"


def test_named_role_override_and_replay_return_original_project(client, monkeypatch) -> None:
    http, claims, _path, _idempotency = client
    claims["roles"] = [{"name": "ADMIN"}]
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    body = request_body(registry_revision=revision, creation_idempotency_key="abcdef12-1234-4234-9234-123456789abc", selections=selections(cellsize_override=30))
    first = http.post("/api/project-config/builder/create", json=body)
    replay = http.post("/api/project-config/builder/create", json=body)
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["run_id"] == first.json()["run_id"]


def test_disabled_writer_creates_nothing(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", raising=False)
    http, _claims, path, _idempotency = client
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post("/api/project-config/builder/create", json=request_body(registry_revision=revision, creation_idempotency_key="fedcba98-1234-4234-9234-123456789abc", selections=selections()))
    assert response.status_code == 503
    assert list(path.iterdir()) == []


def test_old_client_and_cross_locale_selection_fail_before_creation(client, monkeypatch) -> None:
    http, _claims, path, _idempotency = client
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    old_client = http.post(
        "/api/project-config/builder/create",
        json={
            "registry_revision": revision,
            "creation_idempotency_key": "01234567-1234-4234-9234-123456789abc",
            "selections": selections(),
        },
    )
    assert old_client.status_code == 409
    assert old_client.json()["error"]["code"] == "unsupported_builder_schema"
    assert "must be 2" in old_client.json()["error"]["details"]

    cross_locale = http.post(
        "/api/project-config/builder/validate",
        json=request_body(
            registry_revision=revision,
            selections=selections(
                locale="europe",
                capability_profile="europe-capabilities",
                climate_station_database="cligen-stations-ghcn",
            ),
        ),
    )
    assert cross_locale.status_code == 400
    error = cross_locale.json()["errors"][0]
    assert error["field"] == "dem"
    assert error["code"] == "unsupported_combination"
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    cross_locale_create = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="cross-locale-create-1234",
            selections=selections(
                locale="europe",
                capability_profile="europe-capabilities",
                climate_station_database="cligen-stations-ghcn",
            ),
        ),
    )
    assert cross_locale_create.status_code == 400
    assert cross_locale_create.json()["errors"][0]["code"] == "unsupported_combination"
    assert list(path.iterdir()) == []


def test_unexpected_initialization_failure_cleans_run_and_reservation(client, monkeypatch) -> None:
    http, _claims, path, idempotency = client
    cleaned = []
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    monkeypatch.setattr(builder_routes, "Ron", lambda *_args: (_ for _ in ()).throw(LookupError("boom")))

    def cleanup(runid: str, wd: str) -> None:
        cleaned.append((runid, wd))
        for child in Path(wd).iterdir():
            child.unlink()

    monkeypatch.setattr(builder_routes, "cleanup_new_run_directory", cleanup)
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post("/api/project-config/builder/create", json=request_body(registry_revision=revision, creation_idempotency_key="deadbeef-1234-4234-9234-123456789abc", selections=selections()))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "run_initialization_failed"
    assert response.json()["error"]["details"] == "LookupError: boom"
    assert cleaned == [("builder-run", str(path))]
    assert list(path.iterdir()) == []
    assert idempotency.values == {}


def test_post_registration_failure_compensates_owner_row_and_allows_retry(
    client, monkeypatch,
) -> None:
    http, _claims, path, idempotency = client
    deleted = []
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    monkeypatch.setattr(builder_routes, "delete_registered_run", deleted.append)
    monkeypatch.setattr(
        builder_routes,
        "ensure_readme_on_create",
        lambda *_args: (_ for _ in ()).throw(OSError("README storage failed")),
    )

    def cleanup(_runid: str, wd: str) -> None:
        for child in Path(wd).iterdir():
            child.unlink()

    monkeypatch.setattr(builder_routes, "cleanup_new_run_directory", cleanup)
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="post-registration-123456",
            selections=selections(),
        ),
    )

    assert response.status_code == 500
    assert response.json()["error"]["details"] == "OSError: README storage failed"
    assert deleted == [builder_routes.RunRegistrationReceipt(7, "builder-run", "config", 42)]
    assert list(path.iterdir()) == []
    assert idempotency.values == {}


def test_failed_owner_compensation_retains_idempotency_reservation(
    client, monkeypatch,
) -> None:
    http, _claims, path, idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    monkeypatch.setattr(
        builder_routes,
        "delete_registered_run",
        lambda *_args: (_ for _ in ()).throw(
            builder_routes.PreferenceIdentityError("receipt no longer matches")
        ),
    )
    monkeypatch.setattr(
        builder_routes,
        "ensure_readme_on_create",
        lambda *_args: (_ for _ in ()).throw(OSError("README storage failed")),
    )

    def cleanup(_runid: str, wd: str) -> None:
        for child in Path(wd).iterdir():
            child.unlink()

    monkeypatch.setattr(builder_routes, "cleanup_new_run_directory", cleanup)
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="failed-compensation-12345",
            selections=selections(),
        ),
    )

    assert response.status_code == 500
    assert list(path.iterdir()) == []
    assert len(idempotency.values) == 1


def test_idempotency_completion_failure_compensates_registered_run(
    client, monkeypatch,
) -> None:
    http, _claims, path, idempotency = client
    deleted = []
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    monkeypatch.setattr(builder_routes, "delete_registered_run", deleted.append)
    monkeypatch.setattr(
        builder_routes,
        "complete_creation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            builder_routes.CreationIdempotencyError("completion failed")
        ),
    )

    def cleanup(_runid: str, wd: str) -> None:
        for child in Path(wd).iterdir():
            child.unlink()

    monkeypatch.setattr(builder_routes, "cleanup_new_run_directory", cleanup)
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post(
        "/api/project-config/builder/create",
        json=request_body(
            registry_revision=revision,
            creation_idempotency_key="completion-failure-12345",
            selections=selections(),
        ),
    )

    assert response.status_code == 500
    assert response.json()["error"]["details"] == (
        "CreationIdempotencyError: completion failed"
    )
    assert deleted == [builder_routes.RunRegistrationReceipt(7, "builder-run", "config", 42)]
    assert list(path.iterdir()) == []
    assert idempotency.values == {}
