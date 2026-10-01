import importlib

import pytest
from fastapi.testclient import TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.nodb import persistence_events


pytestmark = pytest.mark.microservice


def test_shared_auth_import_does_not_initialize_catalog(monkeypatch):
    calls = []
    monkeypatch.setattr(persistence_events, "initialize_project_commits", lambda: calls.append(True))
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)

    importlib.reload(rq_engine)
    importlib.import_module("wepppy.microservices.rq_engine.auth")

    assert calls == []


def test_asgi_startup_initializes_catalog(monkeypatch):
    calls = []
    monkeypatch.setattr(persistence_events, "initialize_project_commits", lambda: calls.append(True))

    with TestClient(rq_engine.app) as client:
        assert calls == [True]
        assert client.get("/health").status_code == 200


def test_asgi_startup_preserves_configuration_failure(monkeypatch):
    def fail():
        raise RuntimeError("missing catalog configuration")

    monkeypatch.setattr(persistence_events, "initialize_project_commits", fail)

    with pytest.raises(RuntimeError, match="missing catalog configuration"):
        with TestClient(rq_engine.app):
            pytest.fail("Invalid producer configuration must fail startup")
