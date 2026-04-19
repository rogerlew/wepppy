from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.microservice]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEV_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.dev.yml"
_PROD_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.yml"
_PROD_WEPP1_COMPOSE_PATH = _REPO_ROOT / "docker" / "docker-compose.prod.wepp1.yml"
_CADDY_WEPP1_PATH = _REPO_ROOT / "docker" / "caddy" / "Caddyfile.wepp1"


def _load_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _extract_caddy_block(caddy_text: str, marker: str) -> str:
    start = caddy_text.find(marker)
    assert start != -1, f"{marker!r} block not found in Caddyfile.wepp1"

    brace_start = caddy_text.find("{", start)
    assert brace_start != -1, f"{marker!r} block opening brace not found in Caddyfile.wepp1"

    depth = 0
    for index in range(brace_start, len(caddy_text)):
        token = caddy_text[index]
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            if depth == 0:
                return caddy_text[start : index + 1]

    raise AssertionError(f"{marker!r} block closing brace not found in Caddyfile.wepp1")


def _assert_shape_converter_hardening_contract(
    config: dict[str, object],
    *,
    expect_ro_bind_mounts: bool,
) -> None:
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
    if expect_ro_bind_mounts:
        assert volumes
        assert all(str(volume).endswith(":ro") for volume in volumes)
    else:
        assert volumes == []

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
        "SHAPE_CONVERTER_MULTIPART_MAX_PARTS",
        "SHAPE_CONVERTER_MULTIPART_MAX_FIELD_BYTES",
        "SHAPE_CONVERTER_MAX_VERTICES_PER_FEATURE",
        "SHAPE_CONVERTER_REQUEST_SCRATCH_QUOTA_BYTES",
        "SHAPE_CONVERTER_SCRATCH_PRECHECK_FREE_BYTES",
        "SHAPE_CONVERTER_RELAY_CORS_ALLOWED_ORIGINS",
    }
    assert expected_env_keys.issubset(shape_converter["environment"])


@pytest.mark.parametrize(
    ("compose_path", "expect_ro_bind_mounts"),
    [
        (_DEV_COMPOSE_PATH, True),
        (_PROD_COMPOSE_PATH, False),
    ],
)
def test_shape_converter_compose_hardening_contract(
    compose_path: Path,
    expect_ro_bind_mounts: bool,
) -> None:
    config = _load_yaml(compose_path)
    _assert_shape_converter_hardening_contract(
        config,
        expect_ro_bind_mounts=expect_ro_bind_mounts,
    )


@pytest.mark.parametrize(
    "compose_path",
    [
        _DEV_COMPOSE_PATH,
        _PROD_COMPOSE_PATH,
    ],
)
def test_shape_converter_network_isolated_to_internal_sandbox_segment(compose_path: Path) -> None:
    config = _load_yaml(compose_path)
    services = config["services"]
    networks = config["networks"]

    shape_converter = services["shape-converter"]
    caddy = services["caddy"]

    assert shape_converter["networks"] == ["shape-converter-sandbox"]
    assert "shape-converter-sandbox" in caddy["networks"]
    sandbox_network = networks["shape-converter-sandbox"]
    assert sandbox_network["internal"] is True


def test_prod_wepp1_overlay_does_not_override_shape_converter_hardening() -> None:
    config = _load_yaml(_PROD_WEPP1_COMPOSE_PATH)
    services = config["services"]
    assert "shape-converter" not in services


def test_wepp1_caddy_shape_converter_edge_policy_is_hardened() -> None:
    caddy_text = _CADDY_WEPP1_PATH.read_text(encoding="utf-8")
    block = _extract_caddy_block(caddy_text, "handle_path /utils/shape-converter/*")

    assert "request_body {" in block
    assert "max_size 120MB" in block
    assert "header_up -Forwarded" in block
    assert "header_up -X-Forwarded-For" in block
    assert "header_up -X-Forwarded-Host" in block
    assert "header_up -X-Forwarded-Proto" in block
    assert "header_up X-Forwarded-For {remote_host}" in block
    assert "header_up X-Forwarded-Host {host}" in block
    assert "header_up X-Forwarded-Proto {scheme}" in block
    assert "transport http {" in block
    assert "read_timeout 130s" in block
    assert "write_timeout 30s" in block
    assert "response_header_timeout 130s" in block
