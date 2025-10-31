"""Constants for CLI Agent Orchestrator application."""

from pathlib import Path

from cli_agent_orchestrator import __version__


def _resolve_cao_home() -> Path:
    """Find a writable CAO state directory and ensure log folders exist."""
    candidates = [
        Path.home() / ".wepppy" / "cao",
        Path.cwd() / ".wepppy" / "cao",
    ]

    for candidate in candidates:
        try:
            (candidate / "logs" / "terminal").mkdir(parents=True, exist_ok=True)
        except PermissionError:
            continue
        else:
            return candidate

    raise PermissionError("Unable to initialise CAO home directory")


def _ensure_dir(path: Path) -> None:
    """Create a directory tree if possible, ignoring permission issues."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass


def _resolve_codex_prompts_dir() -> Path:
    """Locate a writable Codex prompts directory."""
    candidates = [
        Path.home() / ".codex" / "prompts",
        Path.cwd() / ".codex" / "prompts",
    ]

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            continue
        else:
            return candidate

    # Fall back to the final candidate even if creation previously failed.
    fallback = candidates[-1]
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

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
CAO_HOME_DIR = _resolve_cao_home()
DB_DIR = CAO_HOME_DIR / "db"
LOG_DIR = CAO_HOME_DIR / "logs"
TERMINAL_LOG_DIR = LOG_DIR / "terminal"
_ensure_dir(DB_DIR)

# Terminal log configuration
INBOX_POLLING_INTERVAL = 5  # Seconds between polling for log file changes
INBOX_SERVICE_TAIL_LINES = 5  # Number of lines to check in get_status for inbox service

# Cleanup configuration
RETENTION_DAYS = 14  # Days to keep terminals, messages, and logs

AGENT_CONTEXT_DIR = CAO_HOME_DIR / "agent-context"

# Agent store directories
LOCAL_AGENT_STORE_DIR = CAO_HOME_DIR / "agent-store"

# Codex directories
CODEX_PROMPTS_DIR = _resolve_codex_prompts_dir()
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
