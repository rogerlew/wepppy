from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Optional

from wepppy.cli_agent_orchestrator.models.agent_profile import AgentProfile
from wepppy.cli_agent_orchestrator.models.terminal import TerminalStatus
from .base import BaseProvider

AGENT_CONTEXT_DIR = Path("/tmp/cao_agent_context")


class _TmuxClient:
    """Fallback tmux client; tests stub behavior via monkeypatch."""

    def send_keys(self, session_name: str, window_name: str, keys: str) -> None:  # noqa: ARG002
        raise RuntimeError("tmux_client.send_keys must be monkeypatched in tests")

    def get_history(
        self, session_name: str, window_name: str, tail_lines: Optional[int] = None  # noqa: ARG002
    ) -> str:
        raise RuntimeError("tmux_client.get_history must be monkeypatched in tests")


tmux_client = _TmuxClient()


def wait_for_shell(*_args, **_kwargs) -> bool:
    """Placeholder wait helper overridden by tests."""

    return True


def load_agent_profile(agent_profile: str) -> AgentProfile:  # noqa: D401
    """Load an agent profile; tests monkeypatch this to return fixtures."""

    raise LookupError(f"Agent profile '{agent_profile}' not available in shim")


ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
IDLE_PROMPT_PATTERN = re.compile(r"Type your message or @path/to/file", re.IGNORECASE)
WAITING_PATTERN = re.compile(
    r"(?:confirm|approval|press\s+[yn]/[yn]|are you sure|sign in|login)", re.IGNORECASE
)
ERROR_PATTERN = re.compile(
    r"(?:error[:\s]|failed|exception|traceback|quota|rate limit)", re.IGNORECASE
)


class GeminiProvider(BaseProvider):
    """Lightweight Gemini provider used by the unit tests."""

    def __init__(
        self,
        terminal_id: str,
        session_name: str,
        window_name: str,
        agent_profile: Optional[str],
    ) -> None:
        super().__init__(terminal_id, session_name, window_name)
        self._agent_profile_name = agent_profile
        self._profile: Optional[AgentProfile] = None
        self._context_dir = AGENT_CONTEXT_DIR / terminal_id
        self._system_prompt_path: Optional[Path] = None

        if agent_profile:
            try:
                self._profile = load_agent_profile(agent_profile)
            except Exception:  # pragma: no cover - exercised when load fails
                self._profile = None

    def initialize(self) -> bool:
        """Initialize the Gemini session inside tmux."""

        if not wait_for_shell(tmux_client, self.session_name, self.window_name):
            raise TimeoutError("Shell initialization timed out")

        self._context_dir.mkdir(parents=True, exist_ok=True)

        prompt = None
        if self._profile is not None:
            prompt = getattr(self._profile, "system_prompt", None)
        if prompt:
            prompt = prompt.strip()
            if prompt:
                self._system_prompt_path = self._context_dir / "system.md"
                self._system_prompt_path.write_text(f"{prompt}\n", encoding="utf-8")
                export_cmd = f"export GEMINI_SYSTEM_MD={shlex.quote(str(self._system_prompt_path))}"
                tmux_client.send_keys(self.session_name, self.window_name, export_cmd)

        tmux_client.send_keys(self.session_name, self.window_name, "gemini")
        self._update_status(TerminalStatus.IDLE)
        return True

    def get_status(self, tail_lines: Optional[int] = None) -> TerminalStatus:
        """Infer status by inspecting tmux history."""

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
        """Return the textual tail of a Gemini transcript."""

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
        """Return the command that exits the Gemini CLI."""

        return "exit"

    def cleanup(self) -> None:
        """Remove generated prompt files."""

        if self._system_prompt_path and self._system_prompt_path.exists():
            self._system_prompt_path.unlink()
        if self._context_dir.exists():
            try:
                next(self._context_dir.iterdir())
            except StopIteration:
                self._context_dir.rmdir()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""

    return ANSI_ESCAPE_PATTERN.sub("", text)


__all__ = ["AGENT_CONTEXT_DIR", "GeminiProvider", "load_agent_profile", "tmux_client", "wait_for_shell"]
