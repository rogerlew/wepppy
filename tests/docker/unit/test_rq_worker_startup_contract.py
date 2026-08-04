from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROD_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.yml"
_PROD_WORKER_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.worker.yml"
_DEV_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.dev.yml"
_PROD_WEPP1_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.wepp1.yml"
_PROD_WEPP3_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.wepp3.yml"
_HPC_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.dev.hpc.yml"
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
    assert "/opt/venv/bin/python - <<'PY'" in script_text
    assert '/opt/venv/bin/python - "$redis_url"' in script_text
    assert '/opt/venv/bin/python - "$startup_delay"' in script_text


def test_fork_archive_worker_topology_is_single_process_and_host_scoped() -> None:
    dev_services = _load_yaml(_DEV_COMPOSE_PATH)["services"]
    forest_services = _load_yaml(_PROD_COMPOSE_PATH)["services"]
    wepp3_services = _load_yaml(_PROD_WEPP3_COMPOSE_PATH)["services"]

    assert "worker-pool -n \"1\"" in _command_block(dev_services["rq-worker-fork-archive"])
    forest_worker = forest_services["rq-worker-fork-archive"]
    assert forest_worker["profiles"] == ["fork-archive"]
    assert "rq-worker-startup.sh 1 fork-archive" in _command_block(forest_worker)

    assert set(wepp3_services) == {"rq-worker-fork-archive"}
    wepp3_worker = wepp3_services["rq-worker-fork-archive"]
    assert "rq-worker-startup.sh 1 fork-archive" in _command_block(wepp3_worker)
    assert all("docker.sock" not in str(volume) for volume in wepp3_worker["volumes"])
    assert wepp3_worker["secrets"] == ["redis_password"]
    assert wepp3_worker["volumes"] == ["/geodata/wc1:/wc1", "/geodata:/geodata:ro"]

    for path in (_PROD_WORKER_COMPOSE_PATH, _HPC_COMPOSE_PATH):
        assert "rq-worker-fork-archive" not in _load_yaml(path).get("services", {})

    wepp1_worker = _load_yaml(_PROD_WEPP1_COMPOSE_PATH)["services"]["rq-worker-fork-archive"]
    assert wepp1_worker == {"scale": 0}
