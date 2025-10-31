"""Constants for CLI Agent Orchestrator application."""

from pathlib import Path

from cli_agent_orchestrator import __version__

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
CAO_HOME_DIR = Path.home() / ".wepppy" / "cao"
DB_DIR = CAO_HOME_DIR / "db"
LOG_DIR = CAO_HOME_DIR / "logs"
TERMINAL_LOG_DIR = LOG_DIR / "terminal"
TERMINAL_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Terminal log configuration
INBOX_POLLING_INTERVAL = 5  # Seconds between polling for log file changes
INBOX_SERVICE_TAIL_LINES = 5  # Number of lines to check in get_status for inbox service

# Cleanup configuration
RETENTION_DAYS = 14  # Days to keep terminals, messages, and logs

AGENT_CONTEXT_DIR = CAO_HOME_DIR / "agent-context"

# Agent store directories
LOCAL_AGENT_STORE_DIR = CAO_HOME_DIR / "agent-store"

# Codex directories
CODEX_HOME_DIR = Path.home() / ".codex"
CODEX_PROMPTS_DIR = CODEX_HOME_DIR / "prompts"
CODEX_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_FILE = DB_DIR / "cli-agent-orchestrator.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9889
SERVER_VERSION = __version__
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
