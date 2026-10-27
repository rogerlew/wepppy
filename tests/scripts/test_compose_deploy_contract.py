from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "compose_deploy_contract.py"


def _run(command: str, payload: object, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), command, *arguments],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def test_build_services_covers_weppcloudr_and_deduplicates_shared_web_image() -> None:
    config = {
        "services": {
            "weppcloud": {"image": "wepppy:latest", "build": {"context": ".."}},
            "rq-engine": {"image": "wepppy:latest", "build": {"context": ".."}},
            "weppcloudr": {"image": "weppcloudr:latest", "build": {"context": ".."}},
            "cap": {"image": "cap:latest", "build": {"context": ".."}},
            "redis": {"image": "redis:latest"},
            "profiled": {"image": "profiled:latest", "build": {"context": ".."}},
        }
    }
    result = _run(
        "build-services",
        config,
        "--active-service",
        "weppcloud",
        "--active-service",
        "rq-engine",
        "--active-service",
        "weppcloudr",
        "--active-service",
        "cap",
        "--active-service",
        "redis",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["weppcloud", "weppcloudr", "cap"]


def test_build_services_rejects_conflicting_builds_for_one_image() -> None:
    config = {
        "services": {
            "weppcloud": {"image": "wepppy:latest", "build": {"context": ".."}},
            "rq-worker": {
                "image": "wepppy:latest",
                "build": {"context": "../different"},
            },
        }
    }
    result = _run(
        "build-services",
        config,
        "--active-service",
        "weppcloud",
        "--active-service",
        "rq-worker",
    )
    assert result.returncode == 2
    assert "conflicting build definitions" in result.stderr


def test_validate_ps_rejects_absent_stopped_and_unhealthy_services() -> None:
    records = [
        {"Service": "weppcloud", "Name": "web-1", "State": "running", "Health": "healthy"},
        {"Service": "cap", "Name": "cap-1", "State": "restarting", "Health": ""},
        {"Service": "weppcloudr", "Name": "renderer-1", "State": "running", "Health": "starting"},
    ]
    result = _run(
        "validate-ps",
        records,
        "--expected-service",
        "weppcloud",
        "--expected-service",
        "cap",
        "--expected-service",
        "weppcloudr",
        "--expected-service",
        "redis",
    )

    assert result.returncode == 1
    assert "cap-1' state is restarting" in result.stderr
    assert "renderer-1' health is starting" in result.stderr
    assert "service 'redis' has no container" in result.stderr


def test_expected_services_excludes_scaled_zero_service() -> None:
    config = {
        "services": {
            "weppcloud": {"image": "wepppy:latest"},
            "disabled-worker": {"image": "wepppy:latest", "deploy": {"replicas": 0}},
            "status-build": {"image": "golang:latest"},
        }
    }
    result = _run(
        "expected-services",
        config,
        "--active-service",
        "weppcloud",
        "--active-service",
        "disabled-worker",
        "--active-service",
        "status-build",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["weppcloud"]


def test_validate_ps_accepts_running_services_without_healthchecks() -> None:
    records = [{"Service": "worker", "Name": "worker-1", "State": "running", "Health": ""}]
    result = _run("validate-ps", records, "--expected-service", "worker")
    assert result.returncode == 0, result.stderr


def test_candidate_images_reports_only_locally_built_expected_services() -> None:
    config = {
        "services": {
            "weppcloud": {"image": "wepppy:latest", "build": {"context": ".."}},
            "redis": {"image": "redis:latest"},
        }
    }
    result = _run(
        "candidate-images",
        config,
        "--expected-service",
        "weppcloud",
        "--expected-service",
        "redis",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "weppcloud\twepppy:latest\n"


@pytest.mark.parametrize("service", [
    "weppcloud", "browse", "download", "dtale", "query-engine",
    "rq-engine", "rq-worker", "rq-worker-batch",
])
def test_runtime_contract_rejects_lazy_flask_consumer_without_secrets(service: str) -> None:
    result = _run("validate-runtime-config", {"services": {service: {}}},
                  "--active-service", service)
    assert result.returncode == 1
    assert "missing SECRET_KEY" in result.stderr
    assert "missing SECURITY_PASSWORD_SALT" in result.stderr
    assert "missing POSTGRES_PASSWORD" in result.stderr


def test_runtime_contract_checks_mount_targets_and_does_not_print_values() -> None:
    service = {"environment": {
        "SECRET_KEY_FILE": "/run/secrets/flask_key",
        "SECURITY_PASSWORD_SALT": "private-salt-do-not-print",
        "DATABASE_URL": "postgresql://private-do-not-print",
    }, "secrets": [{"source": "key", "target": "flask_key"}]}
    config = {"services": {"browse": service}, "secrets": {"key": {"file": "hidden"}}}
    good = _run("validate-runtime-config", config, "--active-service", "browse")
    assert good.returncode == 0, good.stderr
    service["secrets"] = []
    bad = _run("validate-runtime-config", config, "--active-service", "browse")
    assert bad.returncode == 1
    assert "no matching secret mount" in bad.stderr
    assert "private" not in bad.stderr + bad.stdout


def test_runtime_contract_rejects_undefined_secret_and_empty_binding() -> None:
    config = {"services": {"browse": {
        "environment": {"SECRET_KEY": "", "SECURITY_PASSWORD_SALT_FILE": "/run/secrets/salt"},
        "secrets": ["salt"],
    }}}
    result = _run("validate-runtime-config", config, "--active-service", "browse")
    assert result.returncode == 1
    assert "undefined secret" in result.stderr
    assert "missing SECRET_KEY" in result.stderr


def test_runtime_contract_preserves_database_only_and_nonconsumer_services() -> None:
    config = {"services": {
        "scheduler": {"environment": {"POSTGRES_PASSWORD": "test-only"}},
        "rq-worker-fork-archive": {"environment": {"POSTGRES_PASSWORD": "test-only"}},
        "profile-playback": {},
    }}
    result = _run("validate-runtime-config", config,
                  "--active-service", "scheduler", "--active-service", "rq-worker-fork-archive",
                  "--active-service", "profile-playback")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("filename", [
    "docker-compose.dev.yml", "docker-compose.prod.yml", "docker-compose.dev.hpc.yml",
    "docker-compose.prod.worker.yml", "docker-compose.prod.wepp3.yml",
    "docker-compose.test.yml", "docker-compose.canary-smoke.yml",
])
def test_repository_topologies_supply_consumer_dependencies(filename: str) -> None:
    import yaml
    # Source anchors resolve here; production also checks fully rendered overrides.
    config = yaml.safe_load((_REPO_ROOT / "docker" / filename).read_text())
    arguments = [arg for name in config["services"] for arg in ("--active-service", name)]
    result = _run("validate-runtime-config", config, *arguments)
    assert result.returncode == 0, result.stderr


def test_runtime_contract_rejects_blank_values_and_requires_explicit_scope() -> None:
    config = {"services": {"browse": {"environment": {
        "SECRET_KEY": " ", "SECURITY_PASSWORD_SALT_FILE": "\t", "DATABASE_URL": " ",
    }}}}
    result = _run("validate-runtime-config", config, "--active-service", "browse")
    assert result.returncode == 1
    assert "missing SECRET_KEY" in result.stderr
    assert "missing SECURITY_PASSWORD_SALT" in result.stderr
    assert "missing POSTGRES_PASSWORD" in result.stderr
    assert _run("validate-runtime-config", config).returncode == 2
