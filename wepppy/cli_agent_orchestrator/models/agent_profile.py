from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentProfile:
    """Lightweight agent profile description used in tests."""

    name: str
    description: str
    system_prompt: str = ""


__all__ = ["AgentProfile"]
