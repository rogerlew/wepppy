from __future__ import annotations

from typing import Optional

from wepppy.cli_agent_orchestrator.models.terminal import TerminalStatus


class BaseProvider:
    """Very small subset of the provider contract."""

    def __init__(self, terminal_id: str, session_name: str, window_name: str) -> None:
        self.terminal_id = terminal_id
        self.session_name = session_name
        self.window_name = window_name
        self.status: Optional[TerminalStatus] = None

    def _update_status(self, status: TerminalStatus) -> None:
        self.status = status


__all__ = ["BaseProvider"]
