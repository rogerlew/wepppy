from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_status_stream_node(tmp_path) -> None:
    script = Path(__file__).with_name("status_stream_test.js")
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
