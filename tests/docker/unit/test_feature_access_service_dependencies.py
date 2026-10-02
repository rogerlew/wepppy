from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATHS = (
    "docker/docker-compose.dev.yml",
    "docker/docker-compose.dev.hpc.yml",
    "docker/docker-compose.prod.yml",
)


@pytest.mark.parametrize("compose_path", COMPOSE_PATHS)
def test_feature_access_consumers_receive_live_account_dependencies(
    compose_path: str,
) -> None:
    config = yaml.safe_load((REPO_ROOT / compose_path).read_text(encoding="utf-8"))
    services = config["services"]

    for service_name in ("browse", "dtale", "query-engine"):
        service = services[service_name]
        assert "postgres_password" in service["secrets"]
        assert service["environment"]["POSTGRES_PASSWORD_FILE"] == (
            "/run/secrets/postgres_password"
        )
        assert service["depends_on"]["postgres"]["condition"] == "service_healthy"
        assert service["depends_on"]["redis"]["condition"] == "service_started"

    query_engine = services["query-engine"]
    assert "wepp_auth_jwt_secrets" in query_engine["secrets"]
    assert query_engine["environment"]["WEPP_AUTH_JWT_SECRETS_FILE"] == (
        "/run/secrets/wepp_auth_jwt_secrets"
    )
