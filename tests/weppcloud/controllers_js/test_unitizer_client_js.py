from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_unitizer_client_preserves_blank_numeric_fields() -> None:
    script = Path(__file__).with_name("unitizer_client_test.js")
    if not script.exists():
        raise AssertionError(f"Missing Node test script: {script}")

    result = subprocess.run(
        ["node", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
    assert result.returncode == 0


def test_unitizer_bundle_contains_blank_guard() -> None:
    bundle_path = (
        Path(__file__).resolve().parents[3]
        / "wepppy"
        / "weppcloud"
        / "static"
        / "js"
        / "controllers.js"
    )
    contents = bundle_path.read_text(encoding="utf-8")
    needle = 'element.dataset.unitizerCanonicalValue = "";'
    assert needle in contents, "controllers.js is missing the blank-to-empty guard"
