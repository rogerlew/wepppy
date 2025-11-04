"""Constants for CLI Agent Orchestrator application."""

import logging
import tempfile
from pathlib import Path

from cli_agent_orchestrator import __version__

logger = logging.getLogger(__name__)

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


def _ensure_directory(path: Path, *, fallback: Path | None = None) -> Path:
    """Create directory if missing, falling back when permissions block access."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except PermissionError as exc:
        if fallback is None:
            raise
        fallback.mkdir(parents=True, exist_ok=True)
        logger.debug(
            "Directory %s unavailable (%s); using fallback %s", path, exc, fallback
        )
        return fallback


# Application directories
_DEFAULT_CAO_HOME = Path.home() / ".wepppy" / "cao"
_FALLBACK_CAO_HOME = Path(tempfile.gettempdir()) / "wepppy" / "cao"
CAO_HOME_DIR = _ensure_directory(_DEFAULT_CAO_HOME, fallback=_FALLBACK_CAO_HOME)
LOG_DIR = CAO_HOME_DIR / "logs"
TERMINAL_LOG_DIR = _ensure_directory(
    LOG_DIR / "terminal",
    fallback=_FALLBACK_CAO_HOME / "logs" / "terminal",
)
LOG_DIR = TERMINAL_LOG_DIR.parent
CAO_HOME_DIR = LOG_DIR.parent
DB_DIR = CAO_HOME_DIR / "db"

# Terminal log configuration
INBOX_POLLING_INTERVAL = 5  # Seconds between polling for log file changes
INBOX_SERVICE_TAIL_LINES = 5  # Number of lines to check in get_status for inbox service

# Cleanup configuration
RETENTION_DAYS = 14  # Days to keep terminals, messages, and logs

AGENT_CONTEXT_DIR = CAO_HOME_DIR / "agent-context"

# Agent store directories
LOCAL_AGENT_STORE_DIR = CAO_HOME_DIR / "agent-store"

# Codex directories
_DEFAULT_CODEX_HOME = Path.home() / ".codex"
_FALLBACK_CODEX_HOME = Path(tempfile.gettempdir()) / "codex"
CODEX_HOME_DIR = _ensure_directory(_DEFAULT_CODEX_HOME, fallback=_FALLBACK_CODEX_HOME)
CODEX_PROMPTS_DIR = _ensure_directory(
    CODEX_HOME_DIR / "prompts",
    fallback=_FALLBACK_CODEX_HOME / "prompts",
)
CODEX_HOME_DIR = CODEX_PROMPTS_DIR.parent

# Database configuration
DATABASE_FILE = DB_DIR / "cli-agent-orchestrator.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9889
SERVER_VERSION = __version__
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
