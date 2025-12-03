from __future__ import annotations

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Fast, isolated unit tests")


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir(parents=True, exist_ok=True)
    (docker_dir / ".env").write_text(
        "UID=1000\n"
        "GID=993\n"
        "PROFILE_PLAYBACK_URL=http://127.0.0.1:8070\n"
        "PROFILE_PLAYBACK_BASE_URL=http://weppcloud:8000/weppcloud\n"
        "PLAYWRIGHT_DEV_PROJECT=runs0\n"
    )
    (docker_dir / "docker-compose.dev.yml").write_text("services: {}\n")
    return tmp_path
