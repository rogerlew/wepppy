from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEV_COMPOSE = _REPO_ROOT / "docker" / "docker-compose.dev.yml"
_PROD_COMPOSE = _REPO_ROOT / "docker" / "docker-compose.prod.yml"
_PROD_WORKER_COMPOSE = _REPO_ROOT / "docker" / "docker-compose.prod.worker.yml"
_PROD_WEPP3_COMPOSE = _REPO_ROOT / "docker" / "docker-compose.prod.wepp3.yml"
_PROD_WEPP1_OVERRIDE = _REPO_ROOT / "docker" / "docker-compose.prod.wepp1.yml"
_FLAGS = {
    "WEPPPY_PROJECT_CONFIG_READER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED",
}


def _docker_compose_command() -> list[str]:
    candidates = (["docker", "compose"], ["docker-compose"])
    for candidate in candidates:
        if shutil.which(candidate[0]) is None:
            continue
        result = subprocess.run(
            [*candidate, "version"],
            cwd=_REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    pytest.skip("Docker Compose is unavailable in this test environment")


def _render_compose(*compose_paths: Path) -> dict[str, object]:
    command = _docker_compose_command()
    for compose_path in compose_paths:
        command.extend(("-f", str(compose_path)))
    command.extend(("config", "--format", "json"))
    result = subprocess.run(
        command,
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_production_compose_passes_project_config_flags_default_off() -> None:
    config = yaml.safe_load(_PROD_COMPOSE.read_text(encoding="utf-8"))
    shared = config["x-wepppy-env"]

    assert set(shared).issuperset(_FLAGS)
    for flag in _FLAGS:
        assert shared[flag] == f"${{{flag}:-false}}"


@pytest.mark.parametrize(
    "service_name",
    ("weppcloud", "rq-engine", "rq-worker", "rq-worker-batch", "scheduler"),
)
def test_project_config_flags_reach_web_and_worker_fleet(service_name: str) -> None:
    config = yaml.safe_load(_PROD_COMPOSE.read_text(encoding="utf-8"))
    environment = config["services"][service_name]["environment"]

    assert _FLAGS.issubset(environment)


@pytest.mark.parametrize(
    ("compose_path", "environment_anchor"),
    ((_PROD_WORKER_COMPOSE, "x-worker-env"), (_PROD_WEPP3_COMPOSE, None)),
)
def test_project_config_flags_reach_dedicated_worker_hosts(
    compose_path: Path,
    environment_anchor: str | None,
) -> None:
    config = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    environment = (
        config[environment_anchor]
        if environment_anchor is not None
        else config["services"]["rq-worker-fork-archive"]["environment"]
    )

    assert _FLAGS.issubset(environment)
    for flag in _FLAGS:
        assert environment[flag] == f"${{{flag}:-false}}"


@pytest.mark.requires_docker
@pytest.mark.parametrize(
    "compose_paths",
    ((_PROD_COMPOSE,), (_PROD_COMPOSE, _PROD_WEPP1_OVERRIDE)),
    ids=("prod", "prod-wepp1"),
)
def test_resolved_shape_converter_uses_isolated_dedicated_image(
    compose_paths: tuple[Path, ...],
) -> None:
    services = _render_compose(*compose_paths)["services"]
    shape_service = services["shape-converter"]

    assert shape_service["build"]["dockerfile"] == "docker/Dockerfile.shape-converter"
    assert shape_service["image"] != services["weppcloud"]["image"]
    assert shape_service["user"] == "10001:10001"
    assert shape_service["read_only"] is True
    assert shape_service["cap_drop"] == ["ALL"]
    assert shape_service["security_opt"] == ["no-new-privileges:true"]
    assert shape_service["networks"] == {"shape-converter-sandbox": None}
    assert shape_service["command"] == [
        "uvicorn",
        "wepppy.microservices.shape_converter:app",
        "--workers",
        "1",
        "--host",
        "0.0.0.0",
        "--port",
        "8060",
        "--timeout-keep-alive",
        "5",
    ]
    assert shape_service.get("volumes") in (None, [])
    for inherited_key in ("secrets", "env_file", "depends_on"):
        assert not shape_service.get(inherited_key)
    for inherited_environment in (
        "REDIS_URL",
        "REDIS_PASSWORD_FILE",
        "POSTGRES_PASSWORD_FILE",
        "SECRET_KEY_FILE",
    ):
        assert inherited_environment not in shape_service["environment"]


@pytest.mark.requires_docker
def test_resolved_dev_shape_converter_mounts_only_service_source_read_only() -> None:
    shape_service = _render_compose(_DEV_COMPOSE)["services"]["shape-converter"]

    assert shape_service["build"]["dockerfile"] == "docker/Dockerfile.shape-converter"
    mounts = shape_service["volumes"]
    assert {mount["target"] for mount in mounts} == {
        "/opt/app/wepppy/microservices/shape_converter",
        "/opt/app/wepppy/observability",
    }
    assert all(mount["type"] == "bind" and mount["read_only"] for mount in mounts)
