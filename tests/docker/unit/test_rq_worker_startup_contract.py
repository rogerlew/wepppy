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
    assert wepp3_worker["user"] == "1002:130"
    assert wepp3_worker["build"]["args"]["APP_UID"] == "1002"
    assert wepp3_worker["build"]["args"]["APP_GID"] == "130"
    assert wepp3_worker["stop_grace_period"] == "216000s"
    assert all("docker.sock" not in str(volume) for volume in wepp3_worker["volumes"])
    assert wepp3_worker["secrets"] == [
        "redis_password",
        {
            "source": "discord_bot_token",
            "target": "/opt/vendor/weppcloud2/weppcloud2/discord_bot/.bot_token",
        },
    ]
    assert _load_yaml(_PROD_WEPP3_COMPOSE_PATH)["secrets"]["discord_bot_token"] == {
        "file": "${DISCORD_BOT_TOKEN_FILE:-/dev/null}"
    }
    assert wepp3_worker["volumes"] == ["/geodata/wc1:/wc1", "/geodata:/geodata:ro"]

    for path in (_PROD_WORKER_COMPOSE_PATH, _HPC_COMPOSE_PATH):
        assert "rq-worker-fork-archive" not in _load_yaml(path).get("services", {})

    wepp1_worker = _load_yaml(_PROD_WEPP1_COMPOSE_PATH)["services"]["rq-worker-fork-archive"]
    assert wepp1_worker == {"scale": 0}


def test_production_deploy_script_supports_guarded_wepp3_mode() -> None:
    deploy_script = (_REPO_ROOT / "scripts" / "deploy-production.sh").read_text(
        encoding="utf-8"
    )

    assert 'DEPLOY_MODE="wepp3-fork-archive"' in deploy_script
    assert "BUILD_SERVICES=(rq-worker-fork-archive)" in deploy_script
    assert "Unsupported production Compose topology; refusing to guess" in deploy_script
    assert "Deployment script changed during pull; restarting" in deploy_script
    assert 'exec "${SCRIPT_DIR}/deploy-production.sh" "${ORIGINAL_ARGS[@]}" --skip-pull' in deploy_script
    assert deploy_script.count("configure_deploy_topology") >= 3
    assert "test -r /run/secrets/redis_password" in deploy_script
    assert "test -r /opt/vendor/weppcloud2/weppcloud2/discord_bot/.bot_token" in deploy_script
    assert "If DISCORD_BOT_TOKEN_FILE is set" in deploy_script
    assert "setfacl -m u:1002:r" in deploy_script
    assert "docker compose stop --timeout" in deploy_script
    assert "FORK_ARCHIVE_STOP_TIMEOUT_SECONDS" in deploy_script
    assert '!= "1002:130"' in deploy_script
    assert 'worker.hostname == socket.gethostname()' in deploy_script
    assert 'connection.ttl(worker.key) > 0' in deploy_script
    assert 'REGISTERED_FORK_ARCHIVE_WORKERS}" != "1:1"' in deploy_script
    assert "rq-info --service rq-worker-fork-archive --detail" in deploy_script
    assert "Skipping broad Docker runtime prune on the dedicated wepp3 host" in deploy_script


def test_production_deploy_script_supports_targeted_web_mode() -> None:
    deploy_script = (_REPO_ROOT / "scripts" / "deploy-production.sh").read_text(
        encoding="utf-8"
    )

    assert "--targeted-web" in deploy_script
    assert "BUILD_SERVICES=(weppcloud)" in deploy_script
    assert "races two writes to the same tag" in deploy_script
    assert "--targeted-web requires a full stack" in deploy_script
    assert "--targeted-web cannot be combined with --flush-rq-db" in deploy_script
    assert "Skipping stack shutdown; workers and dependencies remain running" in deploy_script
    assert (
        "docker compose up -d --no-deps --force-recreate weppcloud rq-engine"
        in deploy_script
    )
    assert "RQ_ENGINE_HEALTHCHECK_URL" in deploy_script
    assert "Skipping broad Docker runtime prune after targeted deployment" in deploy_script
