"""Microservice-suite adapters for app-level request lifecycle controls."""

from __future__ import annotations

import pytest

import wepppy.microservices.rq_engine as rq_engine


@pytest.fixture(autouse=True)
def _disable_deployment_catalog_for_route_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "disabled")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")


@pytest.fixture(autouse=True)
def _stub_lifecycle_bearer_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep route auth tests authoritative while bypassing duplicate middleware JWT decode."""
    monkeypatch.setattr(rq_engine, "_verify_lifecycle_bearer", lambda request: None)
