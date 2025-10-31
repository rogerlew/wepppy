"""Minimal data models for CAO tests."""

from .agent_profile import AgentProfile
from .flow import Flow
from .inbox import InboxMessage, MessageStatus
from .terminal import TerminalStatus

__all__ = [
    "AgentProfile",
    "Flow",
    "InboxMessage",
    "MessageStatus",
    "TerminalStatus",
]
