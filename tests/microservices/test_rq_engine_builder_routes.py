from __future__ import annotations

from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient
import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import builder_routes
from wepppy.weppcloud.user_preferences import CreationActor
from wepp_runner.wepp_runner import get_linux_wepp_bin_opts

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
    value = {"locale": "continental-us", "dem": "usgs-ned13-2022", "delineation_backend": "wbt", "watershed_representation": "single-ofe", "wepp_binary": "wepp_260803", "soil": "ssurgo-gnatsgso-2025", "landuse": "nlcd-2019", "climate": "vanilla_cligen", "mods": []}
    value.update(updates); return value


@pytest.fixture()
def client(monkeypatch, tmp_path: Path):
    claims = {"sub": "42", "roles": ["PowerUser"]}
    monkeypatch.setattr(builder_routes, "require_jwt", lambda *_a, **_k: claims)
    monkeypatch.setattr(builder_routes, "resolve_creation_actor", lambda _c: CreationActor(42, "user@example.com"))
    monkeypatch.setattr(builder_routes, "_create_run_dir", lambda _email: ("builder-run", str(tmp_path)))
    monkeypatch.setattr(builder_routes, "register_owned_run", lambda *_a: None)
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
    validated = http.post("/api/project-config/builder/validate", json={"registry_revision": body["registry_revision"], "selections": selections()})
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
        "details": "missing binary role",
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
        json={
            "registry_revision": revision,
            "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
            "selections": selections(),
        },
    )

    assert response.status_code == 500
    assert response.json()["error"]["details"] == "Account identity is invalid."


def test_stale_revision_and_ordinary_override_fail(client) -> None:
    http, claims, _path, _idempotency = client
    stale = http.post("/api/project-config/builder/validate", json={"registry_revision": "stale", "selections": selections()})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_builder_schema"
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    claims["roles"] = ["User"]
    forbidden = http.post("/api/project-config/builder/validate", json={"registry_revision": revision, "selections": selections(cellsize_override=30)})
    assert forbidden.status_code == 403


def test_enabled_creation_writes_fixed_pair(client, monkeypatch) -> None:
    http, _claims, path, _idempotency = client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post("/api/project-config/builder/create", json={"registry_revision": revision, "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc", "selections": selections()})
    assert response.status_code == 201
    assert response.json()["config_token"] == "config"
    assert (path / "config.cfg").is_file()
    assert (path / "config-manifest.json").is_file()


def test_named_role_override_and_replay_return_original_project(client, monkeypatch) -> None:
    http, claims, _path, _idempotency = client
    claims["roles"] = [{"name": "ADMIN"}]
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", "1")
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    body = {"registry_revision": revision, "creation_idempotency_key": "abcdef12-1234-4234-9234-123456789abc", "selections": selections(cellsize_override=30)}
    first = http.post("/api/project-config/builder/create", json=body)
    replay = http.post("/api/project-config/builder/create", json=body)
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["run_id"] == first.json()["run_id"]


def test_disabled_writer_creates_nothing(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED", raising=False)
    http, _claims, path, _idempotency = client
    revision = http.get("/api/project-config/builder").json()["registry_revision"]
    response = http.post("/api/project-config/builder/create", json={"registry_revision": revision, "creation_idempotency_key": "fedcba98-1234-4234-9234-123456789abc", "selections": selections()})
    assert response.status_code == 503
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
    response = http.post("/api/project-config/builder/create", json={"registry_revision": revision, "creation_idempotency_key": "deadbeef-1234-4234-9234-123456789abc", "selections": selections()})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "run_initialization_failed"
    assert cleaned == [("builder-run", str(path))]
    assert list(path.iterdir()) == []
    assert idempotency.values == {}
