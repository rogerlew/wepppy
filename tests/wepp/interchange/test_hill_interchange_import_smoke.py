from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_hill_interchange_imports_without_circular_import_error() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = os.pathsep.join([str(repo_root), existing_pythonpath])
    else:
        env["PYTHONPATH"] = str(repo_root)
    code = (
        "import importlib; "
        "importlib.import_module('wepppy.wepp.interchange.hill_interchange'); "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Expected hill_interchange import to succeed in a clean interpreter.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
