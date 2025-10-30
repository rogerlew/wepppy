"""Codex CLI provider implementation."""

from __future__ import annotations

import base64
import logging
import os
import re
import shlex
from typing import Optional

from cli_agent_orchestrator.clients.tmux import tmux_client
from cli_agent_orchestrator.providers.base import BaseProvider
from cli_agent_orchestrator.models.terminal import TerminalStatus
from cli_agent_orchestrator.utils.agent_profiles import load_agent_profile
from cli_agent_orchestrator.utils.terminal import wait_for_shell

logger = logging.getLogger(__name__)

# Regex heuristics for Codex CLI prompts/output.
IDLE_PROMPT_PATTERN = re.compile(r"codex[^\n]*(?:[>❯›»])\s*$", re.MULTILINE)
APPROVAL_PATTERN = re.compile(r"approval required", re.IGNORECASE)
ERROR_PATTERN = re.compile(r"(?:error:|failed:)", re.IGNORECASE)


class CodexProvider(BaseProvider):
    """Provider for the Codex CLI."""

    def __init__(
        self,
        terminal_id: str,
        session_name: str,
        window_name: str,
        agent_profile: Optional[str],
    ):
        super().__init__(terminal_id, session_name, window_name)
        self._agent_profile_name = agent_profile
        self._profile = None
        if agent_profile:
            try:
                self._profile = load_agent_profile(agent_profile)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to load agent profile '%s' for Codex provider: %s",
                    agent_profile,
                    exc,
                )

    def initialize(self) -> bool:
        """Launch Codex CLI in the target tmux pane."""
        if not wait_for_shell(tmux_client, self.session_name, self.window_name, timeout=10.0):
            raise TimeoutError("Shell initialization timed out after 10 seconds")

        # For headless mode we expose the system prompt via environment and leave the pane idle.
        if self._profile and self._profile.system_prompt:
            prompt_bytes = self._profile.system_prompt.encode("utf-8")
            prompt_b64 = base64.b64encode(prompt_bytes).decode("ascii")
            export_cmd = f"export WOJAK_SYSTEM_PROMPT_B64={shlex.quote(prompt_b64)}"
            tmux_client.send_keys(self.session_name, self.window_name, export_cmd)
            logger.info(
                "Loaded Wojak system prompt into environment for terminal %s (base64 payload)",
                self.terminal_id,
            )

        # Advertise headless readiness so downstream tooling knows env is prepared.
        if not os.getenv("WOJAK_HEADLESS_READY"):
            tmux_client.send_keys(self.session_name, self.window_name, "export WOJAK_HEADLESS_READY=1")

        # For interactive profiles (e.g., wojak_interactive), launch Codex CLI.
        # For CI Samurai fixer, we rely on non-interactive 'codex exec --json' via inbox_service.
        if (self._agent_profile_name or "").startswith("wojak"):
            tmux_client.send_keys(self.session_name, self.window_name, "codex")
            logger.info(
                "Launched Codex CLI in tmux for terminal %s; awaiting interactive prompts",
                self.terminal_id,
            )
        else:
            logger.info(
                "Codex provider initialised for %s (profile=%s) without launching interactive CLI",
                self.terminal_id,
                self._agent_profile_name,
            )
        self._update_status(TerminalStatus.IDLE)
        return True

    def get_status(self, tail_lines: int = None) -> TerminalStatus:
        """Approximate Codex status using tmux history heuristics."""
        output = tmux_client.get_history(
            self.session_name,
            self.window_name,
            tail_lines=tail_lines,
        )
        if not output:
            return TerminalStatus.ERROR

        if APPROVAL_PATTERN.search(output):
            return TerminalStatus.WAITING_USER_ANSWER

        if ERROR_PATTERN.search(output):
            return TerminalStatus.ERROR

        if IDLE_PROMPT_PATTERN.search(output):
            return TerminalStatus.IDLE

        return TerminalStatus.PROCESSING

    def get_idle_pattern_for_log(self) -> str:
        """Pattern used by inbox watcher to detect idle prompts."""
        return r"codex"

    def extract_last_message_from_script(self, script_output: str) -> str:
        """Return the trailing lines from the Codex transcript."""
        if not script_output:
            raise ValueError("No Codex output captured")

        lines = [line for line in script_output.strip().splitlines() if line.strip()]
        if not lines:
            raise ValueError("Codex output did not contain any text")
        tail = lines[-50:]
        return "\n".join(tail).strip()

    def exit_cli(self) -> str:
        """Return command to exit Codex CLI."""
        return "exit"

    def cleanup(self) -> None:
        """Cleanup handler (no-op for Codex)."""
        logger.debug("Cleaning up Codex provider for terminal %s", self.terminal_id)


def _sanitize_prompt(prompt: str) -> str:
    """Collapse whitespace to produce a single-line prompt for CLI invocation."""
    collapsed = " ".join(prompt.strip().split())
    return collapsed
