from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROD_COMPOSE = _REPO_ROOT / "docker" / "docker-compose.prod.yml"
_FLAGS = {
    "WEPPPY_PROJECT_CONFIG_READER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED",
    "WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED",
}


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
