from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEPLOY = _REPO_ROOT / "scripts" / "deploy-production.sh"


def _run_plan(tmp_path: Path, services: dict[str, object], *arguments: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    fake_wctl = bin_dir / "wctl"
    fake_wctl.write_text(
        """#!/bin/bash
set -euo pipefail
if [[ "$*" == *"config --services"* ]]; then
    printf '%s\\n' "${FAKE_SERVICES}"
elif [[ "$*" == *"config --format json"* ]]; then
    printf '%s\\n' "${FAKE_CONFIG}"
else
    echo "unexpected wctl call: $*" >&2
    exit 90
fi
""",
        encoding="utf-8",
    )
    fake_wctl.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    environment["FAKE_SERVICES"] = "\n".join(services)
    environment["FAKE_CONFIG"] = json.dumps({"services": services})
    return subprocess.run(
        [str(_DEPLOY), "--print-plan", *arguments],
        cwd=_REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _full_services() -> dict[str, object]:
    return {
        "weppcloud": {"image": "wepppy:latest", "build": {"context": ".."}},
        "rq-engine": {"image": "wepppy:latest", "build": {"context": ".."}},
        "rq-worker": {"image": "wepppy:latest", "build": {"context": ".."}},
        "weppcloudr": {"image": "weppcloudr:latest", "build": {"context": ".."}},
        "cap": {"image": "cap:latest", "build": {"context": ".."}},
        "redis": {"image": "redis:latest"},
        "disabled": {
            "image": "wepppy:latest",
            "build": {"context": ".."},
            "deploy": {"replicas": 0},
        },
    }


def test_full_plan_builds_each_local_image_and_validates_full_recreate_set(tmp_path: Path) -> None:
    result = _run_plan(tmp_path, _full_services())
    assert result.returncode == 0, result.stderr
    assert "mode=full" in result.stdout
    assert "build=weppcloud weppcloudr cap" in result.stdout
    assert "recreate=weppcloud rq-engine rq-worker weppcloudr cap redis" in result.stdout
    assert "expected-running=weppcloud rq-engine rq-worker weppcloudr cap redis" in result.stdout


def test_targeted_modes_have_narrow_recreate_and_acceptance_sets(tmp_path: Path) -> None:
    web = _run_plan(tmp_path / "web", _full_services(), "--targeted-web")
    cap = _run_plan(tmp_path / "cap", _full_services(), "--targeted-cap")
    assert web.returncode == 0, web.stderr
    assert "build=weppcloud" in web.stdout
    assert "recreate=weppcloud rq-engine" in web.stdout
    assert cap.returncode == 0, cap.stderr
    assert "build=cap" in cap.stdout
    assert "recreate=cap" in cap.stdout
