from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / "docker" / "wepppyo3-interchange-preflight.py"
ENTRYPOINT = [
    "/opt/venv/bin/python",
    "/workdir/wepppy/docker/wepppyo3-interchange-preflight.py",
    "--",
]


def _services(path: str) -> dict[str, dict[str, object]]:
    config = yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))
    return config["services"]


@pytest.mark.parametrize(
    ("compose_path", "service_names"),
    [
        (
            "docker/docker-compose.dev.yml",
            ("query-engine", "rq-engine", "rq-worker", "rq-worker-batch", "scheduler"),
        ),
        (
            "docker/docker-compose.dev.hpc.yml",
            ("query-engine", "rq-engine", "rq-worker", "rq-worker-batch", "scheduler"),
        ),
        (
            "docker/docker-compose.prod.yml",
            (
                "query-engine",
                "rq-engine",
                "rq-worker",
                "rq-worker-batch",
                "scheduler",
            ),
        ),
        (
            "docker/docker-compose.prod.worker.yml",
            ("rq-worker", "rq-worker-batch"),
        ),
    ],
)
def test_python_services_use_native_interchange_preflight(
    compose_path: str,
    service_names: tuple[str, ...],
) -> None:
    services = _services(compose_path)
    for name in service_names:
        assert services[name]["entrypoint"] == ENTRYPOINT


def test_weppcloud_build_entrypoint_invokes_shared_preflight() -> None:
    entrypoint = (REPO_ROOT / "docker" / "weppcloud-entrypoint.sh").read_text(
        encoding="utf-8"
    )
    assert 'python "${PROJECT_ROOT}/docker/wepppyo3-interchange-preflight.py"' in entrypoint


def test_production_image_uses_one_canonical_wepppyo3_package_tree() -> None:
    dockerfile = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert 'mkdir -p "${SITE_PACKAGES}/wepppyo3"' not in dockerfile
    assert "cp -a /opt/vendor/wepppyo3" not in dockerfile
    assert "ln -s /opt/vendor/wepppyo3 /workdir/wepppyo3" in dockerfile
    assert (
        'printf "/workdir/wepppyo3/release/linux/py312/\\n" '
        '> "${SITE_PACKAGES}/wepppyo3.pth"'
    ) in dockerfile


def test_preflight_accepts_configured_release_and_reports_sha() -> None:
    completed = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "WEPPpyo3 interchange import OK:" in completed.stdout
    assert "WEPPpyo3 interchange SHA256:" in completed.stdout


def test_preflight_rejects_extension_outside_configured_release(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["WEPPPYO3_INTERCHANGE_RELEASE_ROOT"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "unexpected origins" in completed.stderr


def test_preflight_accepts_symlinked_canonical_release_root(tmp_path: Path) -> None:
    import wepppyo3  # type: ignore

    imported_release = Path(wepppyo3.__file__).resolve().parents[1]
    release_link = tmp_path / "release"
    release_link.symlink_to(imported_release, target_is_directory=True)
    env = os.environ.copy()
    env["WEPPPYO3_INTERCHANGE_RELEASE_ROOT"] = str(release_link)
    completed = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert str(imported_release) in completed.stdout
