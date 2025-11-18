from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def resolve_asset_version() -> str:
    """Return a stable asset version string for cache busting."""
    env_version = os.getenv("ASSET_VERSION")
    if env_version:
        return env_version.strip()

    repo_root = Path(__file__).resolve().parents[3]
    try:
        git_version = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
        ).strip()
        if git_version:
            return git_version
    except Exception:
        LOGGER.debug("Falling back to timestamp for asset version", exc_info=True)

    return datetime.utcnow().strftime("%Y%m%d%H%M%S")
