from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROD_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.yml"
_PROD_WORKER_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.worker.yml"
_RQ_STARTUP_SCRIPT_PATH = _REPO_ROOT / "docker" / "rq-worker-startup.sh"
_WAIT_ENV_KEYS = {
    "RQ_REDIS_WAIT_TIMEOUT_SECONDS",
    "RQ_REDIS_WAIT_INTERVAL_SECONDS",
    "RQ_REDIS_PROBE_CONNECT_TIMEOUT_SECONDS",
    "RQ_REDIS_PROBE_SOCKET_TIMEOUT_SECONDS",
    "RQ_WORKER_STARTUP_DELAY_SECONDS",
}


def _load_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _command_block(service: dict[str, object]) -> str:
    command = service["command"]
    assert isinstance(command, list)
    return "\n".join(str(token) for token in command)


def test_prod_compose_workers_use_startup_gate_contract() -> None:
    config = _load_yaml(_PROD_COMPOSE_PATH)
    services = config["services"]

    rq_worker = services["rq-worker"]
    rq_worker_batch = services["rq-worker-batch"]

    assert (
        rq_worker["depends_on"]["redis"]["condition"] == "service_healthy"
    )
    assert (
        rq_worker_batch["depends_on"]["redis"]["condition"] == "service_healthy"
    )

    assert "exec /workdir/wepppy/docker/rq-worker-startup.sh 6 default" in _command_block(
        rq_worker
    )
    assert "exec /workdir/wepppy/docker/rq-worker-startup.sh 4 batch" in _command_block(
        rq_worker_batch
    )

    assert _WAIT_ENV_KEYS.issubset(rq_worker["environment"])
    assert _WAIT_ENV_KEYS.issubset(rq_worker_batch["environment"])

    redis_healthcheck = services["redis"]["healthcheck"]["test"]
    assert isinstance(redis_healthcheck, list)
    assert "grep -qx PONG" in redis_healthcheck[1]


def test_prod_worker_compose_workers_use_startup_gate_contract() -> None:
    config = _load_yaml(_PROD_WORKER_COMPOSE_PATH)
    services = config["services"]

    rq_worker = services["rq-worker"]
    rq_worker_batch = services["rq-worker-batch"]
    weppcloudr = services["weppcloudr"]

    assert (
        rq_worker["depends_on"]["weppcloudr"]["condition"] == "service_healthy"
    )
    assert (
        rq_worker_batch["depends_on"]["weppcloudr"]["condition"] == "service_healthy"
    )

    assert "exec /workdir/wepppy/docker/rq-worker-startup.sh 6 default" in _command_block(
        rq_worker
    )
    assert "exec /workdir/wepppy/docker/rq-worker-startup.sh 4 batch" in _command_block(
        rq_worker_batch
    )

    assert _WAIT_ENV_KEYS.issubset(rq_worker["environment"])
    assert _WAIT_ENV_KEYS.issubset(rq_worker_batch["environment"])
    assert str(rq_worker["environment"]["RQ_REDIS_URL"]).startswith("${RQ_REDIS_URL:?")
    assert str(rq_worker_batch["environment"]["RQ_REDIS_URL"]).startswith("${RQ_REDIS_URL:?")
    assert str(rq_worker["environment"]["REDIS_URL"]).startswith("${RQ_REDIS_URL:?")
    assert str(rq_worker_batch["environment"]["REDIS_URL"]).startswith("${RQ_REDIS_URL:?")

    healthcheck_test = weppcloudr["healthcheck"]["test"]
    assert isinstance(healthcheck_test, list)
    assert "/healthz" in healthcheck_test[1]


def test_rq_worker_startup_script_uses_url_based_probe() -> None:
    script_text = _RQ_STARTUP_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "redis.Redis.from_url(" in script_text
    assert "redis_url(" in script_text
    assert "Invalid worker Redis URL" in script_text
    assert "RQ_REDIS_PROBE_CONNECT_TIMEOUT_SECONDS" in script_text
    assert "RQ_REDIS_PROBE_SOCKET_TIMEOUT_SECONDS" in script_text
