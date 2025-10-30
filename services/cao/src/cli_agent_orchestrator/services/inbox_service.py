"""Inbox service with watchdog for automatic message delivery."""

import logging
import re
import subprocess
from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

import base64
import os
import shlex
from cli_agent_orchestrator.clients.database import get_pending_messages, update_message_status
from cli_agent_orchestrator.models.inbox import MessageStatus
from cli_agent_orchestrator.models.terminal import TerminalStatus
from cli_agent_orchestrator.providers.manager import provider_manager
from cli_agent_orchestrator.services import terminal_service
from cli_agent_orchestrator.constants import TERMINAL_LOG_DIR, INBOX_SERVICE_TAIL_LINES

logger = logging.getLogger(__name__)


def _get_log_tail(terminal_id: str, lines: int = 5) -> str:
    """Get last N lines from terminal log file."""
    log_path = TERMINAL_LOG_DIR / f"{terminal_id}.log"
    try:
        result = subprocess.run(
            ['tail', '-n', str(lines), str(log_path)],
            capture_output=True,
            text=True,
            timeout=1
        )
        return result.stdout
    except Exception:
        return ""


def _has_idle_pattern(terminal_id: str) -> bool:
    """Check if log tail contains idle pattern without expensive tmux calls."""
    tail = _get_log_tail(terminal_id)
    if not tail:
        return False
    
    try:
        provider = provider_manager.get_provider(terminal_id)
        idle_pattern = provider.get_idle_pattern_for_log()
        return bool(re.search(idle_pattern, tail))
    except Exception:
        return False


def check_and_send_pending_messages(terminal_id: str) -> bool:
    """Check for pending messages and send if terminal is ready.
    
    Args:
        terminal_id: Terminal ID to check messages for
        
    Returns:
        bool: True if a message was sent, False otherwise
        
    Raises:
        ValueError: If provider not found for terminal
    """
    # Check for pending messages
    messages = get_pending_messages(terminal_id, limit=1)
    if not messages:
        return False
    
    message = messages[0]
    
    # Get provider
    provider = provider_manager.get_provider(terminal_id)

    # For Codex provider, we run non-interactive 'codex exec --json' and skip idle gating.
    # For other providers, require IDLE/COMPLETED to avoid interleaving input.
    try:
        from cli_agent_orchestrator.providers.codex import CodexProvider  # local import to avoid cycles
        is_codex = isinstance(provider, CodexProvider)
    except Exception:
        is_codex = False

    if not is_codex:
        status = provider.get_status(tail_lines=INBOX_SERVICE_TAIL_LINES)
        if status not in (TerminalStatus.IDLE, TerminalStatus.COMPLETED):
            logger.debug(f"Terminal {terminal_id} not ready (status={status})")
            return False
    
    # Send message
    try:
        payload = message.message
        if is_codex:
            # Prefix payload with the agent profile's system prompt when available so the Codex
            # run receives the role instructions that define the workflow contract.
            system_prompt = None
            profile = getattr(provider, "_profile", None)
            if profile is not None:
                system_prompt = getattr(profile, "system_prompt", None)
            if system_prompt:
                payload = f"{system_prompt.strip()}\n\n{payload.lstrip()}"

            # Build codex exec flags with optional sandbox and working directory
            sandbox = os.getenv("CAO_CODEX_SANDBOX_MODE", "").strip()
            # Per-profile override: CAO_SANDBOX_<profile>
            try:
                profile = getattr(provider, "_agent_profile_name", None) or ""
            except Exception:
                profile = ""
            if profile:
                override = os.getenv(f"CAO_SANDBOX_{profile}", "").strip()
                if override:
                    sandbox = override
            cwd = os.getenv("CAO_CODEX_CWD", "").strip()

            flags = ["--json", "--full-auto", "--skip-git-repo-check"]
            if cwd:
                flags += ["--cd", cwd]
            if sandbox:
                flags += ["--sandbox", sandbox]
            flags_str = " ".join(shlex.quote(f) for f in flags)

            # Build a single-line shell command that base64-encodes the payload and pipes it to codex exec
            b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
            cmd = (
                "export CAO_MSG_B64='" + b64 + "'; "
                "tmp=$(mktemp -t cao_msg.XXXX); "
                "echo \"$CAO_MSG_B64\" | base64 -d > \"$tmp\"; "
                f"codex exec {flags_str} \"$(cat \"$tmp\")\"; "
                "rm -f \"$tmp\""
            )
            terminal_service.send_input(terminal_id, cmd)
        else:
            terminal_service.send_input(terminal_id, payload)
        update_message_status(message.id, MessageStatus.DELIVERED)
        logger.info(f"Delivered message {message.id} to terminal {terminal_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message {message.id} to {terminal_id}: {e}")
        update_message_status(message.id, MessageStatus.FAILED)
        raise


class LogFileHandler(FileSystemEventHandler):
    """Handler for terminal log file changes."""
    
    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.log'):
            log_path = Path(event.src_path)
            terminal_id = log_path.stem
            logger.debug(f"Log file modified: {terminal_id}.log")
            self._handle_log_change(terminal_id)
    
    def _handle_log_change(self, terminal_id: str):
        """Handle log file change and attempt message delivery."""
        try:
            # Check for pending messages first
            messages = get_pending_messages(terminal_id, limit=1)
            if not messages:
                logger.debug(f"No pending messages for {terminal_id}, skipping")
                return
            
            # Fast check: does log tail have idle pattern?
            if not _has_idle_pattern(terminal_id):
                logger.debug(f"Terminal {terminal_id} not idle (no idle pattern in log tail), skipping")
                return
            
            # Attempt delivery
            check_and_send_pending_messages(terminal_id)
                
        except Exception as e:
            logger.error(f"Error handling log change for {terminal_id}: {e}")
