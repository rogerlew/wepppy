from __future__ import annotations

from enum import Enum


class TerminalStatus(str, Enum):
    """Subset of terminal states required by unit tests."""

    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_USER_ANSWER = "waiting_user_answer"
    ERROR = "error"
    COMPLETED = "completed"


__all__ = ["TerminalStatus"]
