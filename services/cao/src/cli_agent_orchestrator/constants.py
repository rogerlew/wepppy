"""Constants for CLI Agent Orchestrator application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from cli_agent_orchestrator import __version__


def _iter_home_candidates(env_var: str, default_subpath: Iterable[str]) -> Iterable[Path]:
    """Yield candidate directories for application data."""
    env_value = os.environ.get(env_var)
    if env_value:
        yield Path(env_value).expanduser()

    home = Path.home()
    if home != Path("/"):
        yield home.joinpath(*default_subpath)

    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        yield Path(xdg_data).expanduser().joinpath(*default_subpath)

    tmpdir = Path(os.environ.get("TMPDIR", "/tmp"))
    yield tmpdir.joinpath(*default_subpath)


def _select_home(env_var: str, default_subpath: Iterable[str]) -> Path:
    for candidate in _iter_home_candidates(env_var, default_subpath):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            continue
        return candidate

    raise RuntimeError(f"Unable to create writable directory for {env_var}")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# Session configuration
SESSION_PREFIX = "cao-"

# Available providers
PROVIDERS = ['codex', 'gemini']
DEFAULT_PROVIDER = "codex"

# Tmux capture limits
TMUX_HISTORY_LINES = 200

# TODO: remove the terminal history lines and status check lines if they aren't used anywhere
# Terminal output capture limits
TERMINAL_HISTORY_LINES = 200
STATUS_CHECK_LINES = 100

# Application directories
CAO_HOME_DIR = _select_home("CAO_HOME_DIR", (".wepppy", "cao"))
DB_DIR = _ensure_dir(CAO_HOME_DIR / "db")
LOG_DIR = _ensure_dir(CAO_HOME_DIR / "logs")
TERMINAL_LOG_DIR = _ensure_dir(LOG_DIR / "terminal")

# Terminal log configuration
INBOX_POLLING_INTERVAL = 5  # Seconds between polling for log file changes
INBOX_SERVICE_TAIL_LINES = 5  # Number of lines to check in get_status for inbox service

# Cleanup configuration
RETENTION_DAYS = 14  # Days to keep terminals, messages, and logs

AGENT_CONTEXT_DIR = _ensure_dir(CAO_HOME_DIR / "agent-context")

# Agent store directories
LOCAL_AGENT_STORE_DIR = _ensure_dir(CAO_HOME_DIR / "agent-store")

# Codex directories
CODEX_HOME_DIR = _select_home("CODEX_HOME_DIR", (".codex",))
CODEX_PROMPTS_DIR = _ensure_dir(CODEX_HOME_DIR / "prompts")

# Database configuration
DATABASE_FILE = DB_DIR / "cli-agent-orchestrator.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9889
SERVER_VERSION = __version__
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
