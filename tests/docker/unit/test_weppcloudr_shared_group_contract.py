from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "compose_path",
    (
        "docker/docker-compose.dev.yml",
        "docker/docker-compose.prod.yml",
    ),
)
def test_weppcloudr_joins_the_worker_data_group(compose_path: str) -> None:
    compose = yaml.safe_load((REPO_ROOT / compose_path).read_text(encoding="utf-8"))

    assert compose["services"]["weppcloudr"]["group_add"] == ["${GID:-1000}"]


def test_dev_source_mount_preserves_image_vendored_assets() -> None:
    compose = yaml.safe_load(
        (REPO_ROOT / "docker/docker-compose.dev.yml").read_text(encoding="utf-8")
    )

    volumes = compose["services"]["weppcloudr"]["volumes"]
    assert "weppcloudr-vendor:/srv/weppcloudr/vendor:ro" in volumes
    assert "weppcloudr-vendor" in compose["volumes"]
