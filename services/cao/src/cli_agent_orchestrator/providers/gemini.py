"""Gemini CLI provider implementation."""

from __future__ import annotations

import logging
import os
import re
import shlex
from pathlib import Path
from typing import Optional

from cli_agent_orchestrator.clients.tmux import tmux_client
from cli_agent_orchestrator.constants import AGENT_CONTEXT_DIR
from cli_agent_orchestrator.models.terminal import TerminalStatus
from cli_agent_orchestrator.providers.base import BaseProvider
from cli_agent_orchestrator.utils.agent_profiles import load_agent_profile
from cli_agent_orchestrator.utils.terminal import wait_for_shell

logger = logging.getLogger(__name__)

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
IDLE_PROMPT_PATTERN = re.compile(r"Type your message or @path/to/file", re.IGNORECASE)
WAITING_PATTERN = re.compile(
    r"(?:confirm|approval|press\s+[yn]/[yn]|are you sure|sign in|login)", re.IGNORECASE
)
ERROR_PATTERN = re.compile(
    r"(?:error[:\s]|failed|exception|traceback|quota|rate limit)", re.IGNORECASE
)


class GeminiProvider(BaseProvider):
    """Provider for the Gemini CLI."""

    def __init__(
        self,
        terminal_id: str,
        session_name: str,
        window_name: str,
        agent_profile: Optional[str],
    ) -> None:
        super().__init__(terminal_id, session_name, window_name)
        self._agent_profile_name = agent_profile
        self._profile = None
        self._context_dir = AGENT_CONTEXT_DIR / terminal_id
        self._system_prompt_path: Optional[Path] = None

        if agent_profile:
            try:
                self._profile = load_agent_profile(agent_profile)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to load agent profile '%s' for Gemini provider: %s",
                    agent_profile,
                    exc,
                )

    def initialize(self) -> bool:
        """Launch Gemini CLI in the target tmux pane."""
        if not wait_for_shell(tmux_client, self.session_name, self.window_name, timeout=10.0):
            raise TimeoutError("Shell initialization timed out after 10 seconds")

        self._context_dir.mkdir(parents=True, exist_ok=True)

        if self._profile and getattr(self._profile, "system_prompt", None):
            prompt_text = self._profile.system_prompt.strip()
            if prompt_text:
                try:
                    self._system_prompt_path = self._context_dir / "system.md"
                    self._system_prompt_path.write_text(f"{prompt_text}\n", encoding="utf-8")
                    export_cmd = f"export GEMINI_SYSTEM_MD={shlex.quote(str(self._system_prompt_path))}"
                    tmux_client.send_keys(self.session_name, self.window_name, export_cmd)
                    logger.info(
                        "Loaded Gemini system prompt into environment for terminal %s",
                        self.terminal_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to materialize system prompt for terminal %s: %s",
                        self.terminal_id,
                        exc,
                    )

        tmux_client.send_keys(self.session_name, self.window_name, "gemini")
        logger.info("Launched Gemini CLI in tmux for terminal %s", self.terminal_id)
        self._update_status(TerminalStatus.IDLE)
        return True

    def get_status(self, tail_lines: int = None) -> TerminalStatus:
        """Approximate Gemini status using tmux history heuristics."""
        output = tmux_client.get_history(
            self.session_name,
            self.window_name,
            tail_lines=tail_lines,
        )
        if not output:
            self._update_status(TerminalStatus.ERROR)
            return TerminalStatus.ERROR

        stripped = _strip_ansi(output)

        if WAITING_PATTERN.search(stripped):
            status = TerminalStatus.WAITING_USER_ANSWER
        elif ERROR_PATTERN.search(stripped):
            status = TerminalStatus.ERROR
        elif IDLE_PROMPT_PATTERN.search(stripped):
            status = TerminalStatus.IDLE
        else:
            status = TerminalStatus.PROCESSING

        self._update_status(status)
        return status

    def get_idle_pattern_for_log(self) -> str:
        """Pattern used by inbox watcher to detect idle prompts."""
        return r"Type your message or @path/to/file"

    def extract_last_message_from_script(self, script_output: str) -> str:
        """Return trailing lines from the Gemini transcript."""
        if not script_output:
            raise ValueError("No Gemini output captured")

        stripped = _strip_ansi(script_output).strip()
        if not stripped:
            raise ValueError("Gemini output did not contain any text")

        lines = [line for line in stripped.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Gemini output did not contain any text")
        tail = lines[-50:]
        return "\n".join(tail).strip()

    def exit_cli(self) -> str:
        """Return command to exit Gemini CLI."""
        return "exit"

    def cleanup(self) -> None:
        """Cleanup handler for Gemini context artifacts."""
        try:
            if self._system_prompt_path and self._system_prompt_path.exists():
                self._system_prompt_path.unlink()
            if self._context_dir.exists():
                # Remove directory if empty to avoid clobbering shared assets.
                try:
                    next(self._context_dir.iterdir())
                except StopIteration:
                    self._context_dir.rmdir()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Cleanup skipped for Gemini provider (%s): %s", self.terminal_id, exc
            )


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub("", text)
