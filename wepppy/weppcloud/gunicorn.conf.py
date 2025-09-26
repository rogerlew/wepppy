"""Gunicorn settings for weppcloud."""

import subprocess
import sys
from pathlib import Path


def on_starting(server):
    project_root = Path(__file__).resolve().parent
    script = project_root / "controllers_js" / "build_controllers_js.py"
    server.log.info("Rendering controllers bundle via %s", script)

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        server.log.info("controllers.js build stdout:\n%s", result.stdout.strip())

    if result.stderr.strip():
        server.log.warning("controllers.js build stderr:\n%s", result.stderr.strip())

    if result.returncode != 0:
        server.log.critical(
            "controllers.js build failed with exit code %s", result.returncode
        )
        raise SystemExit(result.returncode)

    server.log.info("controllers bundle ready")
