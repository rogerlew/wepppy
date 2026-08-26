from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "docker" / "docker-compose.canary-smoke.yml"
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "publish-weppcloud-image.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _require_docker_compose() -> None:
    """Skip local contract validation when Docker Compose v2 is unavailable."""

    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        pytest.skip(f"Docker Compose v2 is unavailable in this environment: {exc}")

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        reason = detail[-1] if detail else "the Docker Compose capability probe failed"
        pytest.skip(f"Docker Compose v2 is unavailable in this environment: {reason}")


def _smoke_environment() -> dict[str, str]:
    return {
        **os.environ,
        "WEPPCLOUD_SMOKE_IMAGE": "wepppy-canary-smoke:sha-" + ("a" * 40),
        "WEPPCLOUD_SMOKE_REDIS_PASSWORD": "ephemeral-test-only-redis",
        "WEPPCLOUD_SMOKE_SECRET_KEY": "ephemeral-test-only-flask-key",
        "WEPPCLOUD_SMOKE_PASSWORD_SALT": "ephemeral-test-only-salt",
        "WEPPCLOUD_SMOKE_AGENT_JWT_SECRET": "ephemeral-test-only-agent-jwt",
    }


@pytest.mark.requires_docker
def test_compose_contract_renders_only_minimum_isolated_services() -> None:
    _require_docker_compose()
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "config", "--format", "json"],
        cwd=REPO_ROOT,
        env=_smoke_environment(),
        check=True,
        capture_output=True,
        text=True,
    )
    model = __import__("json").loads(result.stdout)

    assert set(model["services"]) == {"caddy", "redis", "weppcloud"}
    assert model["networks"]["canary"]["internal"] is True
    assert model["services"]["caddy"]["networks"] == {"canary": None, "edge": None}
    assert model["services"]["redis"]["networks"] == {"canary": None}
    assert model["services"]["weppcloud"]["networks"] == {"canary": None}
    assert "ports" not in model["services"]["redis"]
    assert "ports" not in model["services"]["weppcloud"]
    assert model["services"]["caddy"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert model["secrets"]["disabled-discord-token"]["file"] == "/dev/null"
    assert model["services"]["weppcloud"]["tmpfs"] == [
        "/wc1:uid=1000,gid=993,mode=0770",
        "/geodata:uid=1000,gid=993,mode=0550",
    ]

    rendered = result.stdout.lower()
    for forbidden in (
        "docker.sock",
        "rq-worker",
        "oauth_",
        "smtp",
        "captcha",
        "opentopography",
        "climate_engine",
        "/wc1:/wc1",
        "/geodata:/geodata",
    ):
        assert forbidden not in rendered


def test_workflow_has_minimum_permissions_immutable_tags_and_pinned_actions() -> None:
    workflow_text = WORKFLOW_FILE.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["permissions"] == {"contents": "read", "packages": "write"}
    assert "workflow_dispatch" in workflow[True]
    assert workflow[True]["push"]["branches"] == ["master"]
    assert "secrets.GITHUB_TOKEN" in workflow_text
    assert "sha-${GITHUB_SHA}" in workflow_text
    assert "steps.build.outputs.digest" in workflow_text
    assert "docker/Dockerfile" in workflow_text
    assert "context: ." in workflow_text
    assert "RUNTIME_BASE_IMAGE=python:3.12-slim@sha256:" in workflow_text
    assert "STATIC_BUILDER_IMAGE=node:20-alpine@sha256:" in workflow_text
    assert "UV_INSTALLER_URL=https://astral.sh/uv/0.12.3/install.sh" in workflow_text
    for build_arg in (
        "ROSETTA_REF",
        "WEPPCLOUD2_REF",
        "WBT_REF",
        "WEPPPYO3_REF",
    ):
        assert re.search(rf"^\s*{build_arg}=[0-9a-f]{{40}}$", workflow_text, re.MULTILINE)

    uses = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow_text, flags=re.MULTILINE)
    assert uses
    for action in uses:
        _, separator, revision = action.partition("@")
        assert separator == "@"
        assert FULL_SHA.fullmatch(revision), action

    assert re.search(r"(?:^|:)\s*(?:latest|main|master)\s*$", workflow_text, re.MULTILINE) is None
