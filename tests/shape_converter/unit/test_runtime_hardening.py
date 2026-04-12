from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.microservice]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.dev.yml"


def _load_compose_config() -> dict[str, object]:
    return yaml.safe_load(_COMPOSE_PATH.read_text(encoding="utf-8"))


def test_shape_converter_compose_hardening_contract() -> None:
    config = _load_compose_config()
    services = config["services"]
    shape_converter = services["shape-converter"]

    assert shape_converter["read_only"] is True
    assert shape_converter["user"] not in {"0", "0:0", "root", "root:root"}
    assert "no-new-privileges:true" in shape_converter["security_opt"]
    assert "ALL" in shape_converter["cap_drop"]
    assert int(shape_converter["pids_limit"]) > 0
    assert shape_converter["mem_limit"]
    assert float(shape_converter["cpus"]) > 0

    volumes = shape_converter["volumes"]
    assert volumes
    assert all(str(volume).endswith(":ro") for volume in volumes)

    tmpfs_mounts = [str(entry) for entry in shape_converter["tmpfs"]]
    assert any(entry.startswith("/tmp:") for entry in tmpfs_mounts)
    assert any(entry.startswith("/run/shape-converter:") for entry in tmpfs_mounts)
    for entry in tmpfs_mounts:
        assert "noexec" in entry
        assert "nosuid" in entry
        assert "nodev" in entry

    expected_env_keys = {
        "SHAPE_CONVERTER_SANDBOX_MODE",
        "SHAPE_CONVERTER_REQUIRED_SANDBOX_MODE",
        "SHAPE_CONVERTER_SCRATCH_ROOT",
    }
    assert expected_env_keys.issubset(shape_converter["environment"])


def test_shape_converter_network_isolated_to_internal_sandbox_segment() -> None:
    config = _load_compose_config()
    services = config["services"]
    networks = config["networks"]

    shape_converter = services["shape-converter"]
    caddy = services["caddy"]

    assert shape_converter["networks"] == ["shape-converter-sandbox"]
    assert "shape-converter-sandbox" in caddy["networks"]
    sandbox_network = networks["shape-converter-sandbox"]
    assert sandbox_network["internal"] is True
